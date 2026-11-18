from __future__ import annotations

import warnings

import geopandas as gpd
import numpy as np
import pandas as pd

from .utils import (
    build_selected_cards,
    metric_rows,
    load_admin_boundaries,
    PipelineConfig,
    read_gpkg_attributes,
    require_reconciliation,
    validate_admin_reference,
    validate_columns,
    validate_unique,
)


DRY_PROOFING_CARD = "dry_proofing"
RELOCATION_CARD = "relocation"
FLOOD_PROTECTION_CARD = "flood_protection"

URBANISATION_THRESHOLDS = {
    11: "remote_area",
    12: "low_density_rural",
    13: "rural_settlement",
    21: "suburban_area",
    22: "semi_dense_urban_area",
    23: "dense_urban",
    30: "urban_centre",
}
FLOOD_PROTECTION_RETURN_PERIODS = (10, 20, 50, 100, 200)

ADAPTATION_OUTCOMES_CARD_DIMENSIONS = {
    DRY_PROOFING_CARD: (
        "outcome_type",
        "hazard",
        "model",
        "metric",
        "statistic",
        "sector",
        "wealth_group",
        "unit",
    ),
    RELOCATION_CARD: (
        "outcome_type",
        "hazard",
        "model",
        "urbanisation_threshold",
        "urbanisation_threshold_code",
        "metric",
        "statistic",
        "sector",
        "wealth_group",
        "unit",
    ),
    FLOOD_PROTECTION_CARD: (
        "outcome_type",
        "hazard",
        "model",
        "urbanisation_threshold",
        "urbanisation_threshold_code",
        "design_return_period_years",
        "metric",
        "statistic",
        "sector",
        "wealth_group",
        "unit",
    ),
}
ADAPTATION_OUTCOMES_CARD_OPTIONAL_DIMENSIONS = {
    DRY_PROOFING_CARD: ("sector", "wealth_group"),
    RELOCATION_CARD: ("sector", "wealth_group"),
    FLOOD_PROTECTION_CARD: ("sector", "wealth_group"),
}

ECONOMIC_SOURCE_COLUMNS = {
    "res_losses": "residential",
    "nres_losses": "non_residential",
    "infr_losses": "infrastructure",
    "total_losses": "total",
}
SOCIAL_SOURCE_COLUMNS = {
    "Total Flood Risk": "total",
    "Q1 Flood Risk": "q1",
    "Q2 Flood Risk": "q2",
    "Q3 Flood Risk": "q3",
    "Q4 Flood Risk": "q4",
    "Q5 Flood Risk": "q5",
}

_PROTECTION_COST_COLUMNS = (
    "adaptation_cost", "min_adaptation_cost", "max_adaptation_cost",
)
_SOCIAL_CONTEXT_COLUMNS = ("Population", "Population Coverage (%)")


def _outcome_stems(
    config: PipelineConfig,
    scenario: str,
    cost_suffix: str,
) -> dict[str, str]:
    iso3 = config.country.iso3
    level = config.country.admin_level.upper()
    prefix = f"{iso3}_{level}_metrics_jrc-flood"
    return {
        "cost": f"{iso3}_adaptation-cost_{cost_suffix}_{level}",
        "economic_adapted": f"{prefix}_AALs_adapted_{scenario}_capstock",
        "economic_baseline": f"{prefix}_protected_AAR_baseline_capstock",
        "social_adapted": f"{prefix}_adapted_AAR_V-EXP_S-rwi_{scenario}",
        "social_baseline": f"{prefix}_protected_AAR_V-EXP_S-rwi",
    }


def _validate_numeric_columns(
    frame: pd.DataFrame,
    columns: list[str] | tuple[str, ...],
    label: str,
    *,
    nonnegative: bool = True,
    allow_missing: bool = False,
) -> None:
    validate_columns(frame, set(columns), label)
    for column in columns:
        values = pd.to_numeric(frame[column], errors="coerce")
        observed = values.dropna() if allow_missing else values
        if (not allow_missing and values.isna().any()) or not np.isfinite(
            observed
        ).all():
            raise ValueError(f"{label} contains invalid values in {column}")
        if nonnegative and (observed < 0).any():
            raise ValueError(f"{label} contains negative values in {column}")


def _warn_social_context_difference(
    baseline: pd.DataFrame,
    adapted: pd.DataFrame,
    label: str,
) -> None:
    differing_columns = []
    for column in _SOCIAL_CONTEXT_COLUMNS:
        if not np.allclose(
            baseline[column],
            adapted[column],
            rtol=1e-6,
            atol=0.01,
        ):
            differing_columns.append(column)
    if differing_columns:
        warnings.warn(
            f"{label} baseline and adapted social inputs differ in "
            f"context fields: {differing_columns}. Review population coverage "
            "before interpreting avoided exposure.",
            RuntimeWarning,
            stacklevel=2,
        )


def _calculate_outcomes(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    stems: dict[str, str],
    label: str,
    cost_columns: tuple[str, ...],
) -> pd.DataFrame:
    directory = config.source("adaptation_outcomes_dir")
    sources = {
        name: validate_admin_reference(
            read_gpkg_attributes(directory / f"{stem}.gpkg", stem),
            admin_regions,
            f"{label} {name.replace('_', ' ')}",
            allow_single_admin_id=config.country.admin_level == "adm0",
        )
        for name, stem in stems.items()
    }

    cost = sources["cost"]
    has_cost_range = cost_columns == _PROTECTION_COST_COLUMNS
    _validate_numeric_columns(
        cost, cost_columns, f"{label} cost", allow_missing=has_cost_range
    )
    if has_cost_range:
        missing = cost[list(cost_columns)].isna()
        if (missing.any(axis=1) & ~missing.all(axis=1)).any():
            raise ValueError(
                f"{label} cost estimates must either all be present or all be missing"
            )
        estimate, lower, upper = (cost[column] for column in cost_columns)
        if ((lower > estimate) | (estimate > upper)).any():
            raise ValueError(f"{label} cost must satisfy lower <= estimate <= upper")

    for name in ("economic_baseline", "economic_adapted"):
        data = sources[name]
        source_label = f"{label} {name.replace('_', ' ')}"
        _validate_numeric_columns(data, list(ECONOMIC_SOURCE_COLUMNS), source_label)
        require_reconciliation(
            data, "total_losses", ["res_losses", "nres_losses", "infr_losses"], source_label
        )

    for name in ("social_baseline", "social_adapted"):
        data = sources[name]
        source_label = f"{label} {name.replace('_', ' ')}"
        _validate_numeric_columns(
            data, [*SOCIAL_SOURCE_COLUMNS, *_SOCIAL_CONTEXT_COLUMNS], source_label
        )
        _validate_numeric_columns(
            data, ["CI"], source_label, nonnegative=False, allow_missing=True
        )
        if (~data["Population Coverage (%)"].between(0, 100)).any():
            raise ValueError(f"{source_label} population coverage must be 0 to 100")
        if ((data["CI"] < -1) | (data["CI"] > 1)).any():
            raise ValueError(f"{source_label} concentration index must be -1 to 1")
        if (data["CI"].isna() & data["Total Flood Risk"].ne(0)).any():
            raise ValueError(
                f"{source_label} concentration index is missing for positive flood exposure"
            )
        require_reconciliation(
            data, "Total Flood Risk", [f"Q{q} Flood Risk" for q in range(1, 6)], source_label
        )
    _warn_social_context_difference(
        sources["social_baseline"], sources["social_adapted"], label
    )

    economic_columns = list(ECONOMIC_SOURCE_COLUMNS)
    social_columns = [*SOCIAL_SOURCE_COLUMNS, "CI", *_SOCIAL_CONTEXT_COLUMNS]
    columns_by_source = {
        "cost": cost_columns,
        "economic_adapted": economic_columns,
        "economic_baseline": economic_columns,
        "social_adapted": social_columns,
        "social_baseline": social_columns,
    }
    metrics = admin_regions[["adm_id"]].astype("string")
    for name, data in sources.items():
        columns = columns_by_source[name]
        column_names = {column: f"{name}_{column}" for column in columns}
        column_names["shapeID"] = "adm_id"
        renamed = data[["shapeID", *columns]].rename(columns=column_names)
        metrics = metrics.merge(
            renamed, on="adm_id", how="left", validate="one_to_one"
        )

    if "cost_area_dry-proofed" in metrics:
        metrics["cost_area_dry_proofed_m2"] = metrics.pop("cost_area_dry-proofed")
    avoided_columns = {"economic": ECONOMIC_SOURCE_COLUMNS, "social": SOCIAL_SOURCE_COLUMNS}
    for kind, columns in avoided_columns.items():
        for column, group in columns.items():
            metrics[f"{kind}_avoided_{group}"] = (
                metrics[f"{kind}_baseline_{column}"] - metrics[f"{kind}_adapted_{column}"]
            )
    metrics["social_change_ci"] = (
        metrics["social_adapted_CI"] - metrics["social_baseline_CI"]
    )
    return metrics


def build_dry_proofing_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame | None = None,
) -> pd.DataFrame:
    """Load and calculate one-row-per-admin dry-proofing outcome metrics."""
    if admin_regions is None:
        admin_regions = load_admin_boundaries(config)
    return _calculate_outcomes(
        config, admin_regions, _outcome_stems(config, "dp", "dp_m-jrc"),
        "Dry-proofing", ("area_dry-proofed",),
    )


def build_relocation_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame | None = None,
) -> pd.DataFrame:
    """Calculate relocation outcomes for every supported urban threshold."""
    if admin_regions is None:
        admin_regions = load_admin_boundaries(config)
    threshold_metrics = []
    for code, threshold in URBANISATION_THRESHOLDS.items():
        stems = _outcome_stems(config, f"rl_duc{code}", f"rl_m-jrc_duc{code}")
        metrics = _calculate_outcomes(
            config, admin_regions, stems,
            f"Relocation {threshold} ({code})", ("capstock_relocated",),
        )
        metrics.insert(1, "urbanisation_threshold", threshold)
        metrics.insert(2, "urbanisation_threshold_code", code)
        threshold_metrics.append(metrics)
    output = pd.concat(threshold_metrics, ignore_index=True)
    validate_unique(
        output, ["adm_id", "urbanisation_threshold_code"], "Relocation outcome metrics"
    )
    return output


def build_flood_protection_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame | None = None,
) -> pd.DataFrame:
    """Calculate flood-protection outcomes for every DUC and design RP."""
    if admin_regions is None:
        admin_regions = load_admin_boundaries(config)
    scenario_metrics = []
    for code, threshold in URBANISATION_THRESHOLDS.items():
        for return_period in FLOOD_PROTECTION_RETURN_PERIODS:
            scenario = f"fp_rp{return_period}_duc{code}"
            stems = _outcome_stems(config, scenario, scenario)
            metrics = _calculate_outcomes(
                config, admin_regions, stems,
                f"Flood protection {threshold} ({code}), RP{return_period}",
                _PROTECTION_COST_COLUMNS,
            )
            metrics.insert(1, "urbanisation_threshold", threshold)
            metrics.insert(2, "urbanisation_threshold_code", code)
            metrics.insert(3, "design_return_period_years", return_period)
            scenario_metrics.append(metrics)
    output = pd.concat(scenario_metrics, ignore_index=True)
    validate_unique(
        output,
        ["adm_id", "urbanisation_threshold_code", "design_return_period_years"],
        "Flood-protection outcome metrics",
    )
    return output


_COST_MEASURES = {
    DRY_PROOFING_CARD: ("area_dry_proofed", "m2", (("cost_area_dry_proofed_m2", "estimate"),)),
    RELOCATION_CARD: ("capstock_relocated", "usd", (("cost_capstock_relocated", "estimate"),)),
    FLOOD_PROTECTION_CARD: (
        "adaptation_cost", "million_usd",
        (("cost_adaptation_cost", "estimate"),
         ("cost_min_adaptation_cost", "lower"),
         ("cost_max_adaptation_cost", "upper")),
    ),
}


def _outcome_rows(metrics: pd.DataFrame, card: str) -> pd.DataFrame:
    cost_metric, cost_unit, costs = _COST_MEASURES[card]
    rows = [
        (column, dict(outcome_type="cost", statistic=statistic, metric=cost_metric, unit=cost_unit))
        for column, statistic in costs
    ]
    for kind, measures, group, metric, unit in (
        ("economic", ECONOMIC_SOURCE_COLUMNS, "sector", "average_annual_loss", "usd_per_year"),
        ("social", SOCIAL_SOURCE_COLUMNS, "wealth_group", "average_annual_flood_exposure", "people_per_year"),
    ):
        for source, label in measures.items():
            for statistic in ("baseline", "adapted", "avoided"):
                column = f"{kind}_{statistic}_{label if statistic == 'avoided' else source}"
                rows.append((
                    column,
                    dict(outcome_type=f"{kind}_benefit", statistic=statistic,
                         metric=metric, unit=unit, **{group: label}),
                ))
    rows.extend(
        (column, dict(outcome_type="social_benefit", statistic=statistic,
                      metric="concentration_index", wealth_group="total", unit="index"))
        for statistic, column in (
            ("baseline", "social_baseline_CI"), ("adapted", "social_adapted_CI"),
            ("change", "social_change_ci"),
        )
    )

    scenario = ()
    if card != DRY_PROOFING_CARD:
        scenario = ("urbanisation_threshold", "urbanisation_threshold_code")
    if card == FLOOD_PROTECTION_CARD:
        scenario += ("design_return_period_years",)
    return metric_rows(
        metrics, rows, id_columns=("adm_id", *scenario), hazard="river_flood", model="jrc",
        sector=pd.NA, wealth_group=pd.NA,
    )


def build_adaptation_outcomes_card_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    """Build the selected downloadable Adaptation Outcomes card tables."""
    return build_selected_cards(
        config, "adaptation_outcomes", ADAPTATION_OUTCOMES_CARD_DIMENSIONS,
        {
            DRY_PROOFING_CARD: lambda regions: _outcome_rows(
                build_dry_proofing_metrics(config, regions), DRY_PROOFING_CARD
            ),
            RELOCATION_CARD: lambda regions: _outcome_rows(
                build_relocation_metrics(config, regions), RELOCATION_CARD
            ),
            FLOOD_PROTECTION_CARD: lambda regions: _outcome_rows(
                build_flood_protection_metrics(config, regions), FLOOD_PROTECTION_CARD
            ),
        },
        admin_regions,
        optional_dimensions=ADAPTATION_OUTCOMES_CARD_OPTIONAL_DIMENSIONS,
        sort_columns={
            RELOCATION_CARD: ("urbanisation_threshold_code", "_row_order"),
            FLOOD_PROTECTION_CARD: (
                "urbanisation_threshold_code", "design_return_period_years", "_row_order",
            ),
        },
    )
