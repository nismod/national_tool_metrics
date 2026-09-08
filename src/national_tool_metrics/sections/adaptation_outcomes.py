from __future__ import annotations

from pathlib import Path
import warnings

import geopandas as gpd
import numpy as np
import pandas as pd

from ..boundaries import load_admin_boundaries
from ..config import PipelineConfig
from ..outputs import (
    CARD_IDENTIFIER_COLUMNS,
    build_card_identifier_frame,
    validate_card_output,
)
from ..tables import read_gpkg_attributes, validate_columns, validate_unique


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

_SOCIAL_CONTEXT_COLUMNS = ("Population", "Population Coverage (%)")


def _dry_proofing_stems(config: PipelineConfig) -> dict[str, str]:
    iso3 = config.country.iso3
    admin_level = config.country.admin_level.upper()
    return {
        "cost": f"{iso3}_adaptation-cost_dp_m-jrc_{admin_level}",
        "economic_adapted": (
            f"{iso3}_{admin_level}_metrics_jrc-flood_"
            "AALs_adapted_dp_capstock"
        ),
        "economic_baseline": (
            f"{iso3}_{admin_level}_metrics_jrc-flood_"
            "protected_AAR_baseline_capstock"
        ),
        "social_adapted": (
            f"{iso3}_{admin_level}_metrics_jrc-flood_"
            "adapted_AAR_V-EXP_S-rwi_dp"
        ),
        "social_baseline": (
            f"{iso3}_{admin_level}_metrics_jrc-flood_"
            "protected_AAR_V-EXP_S-rwi"
        ),
    }


def _relocation_stems(
    config: PipelineConfig,
    urbanisation_threshold_code: int,
) -> dict[str, str]:
    iso3 = config.country.iso3
    admin_level = config.country.admin_level.upper()
    threshold = f"duc{urbanisation_threshold_code}"
    return {
        "cost": (
            f"{iso3}_adaptation-cost_rl_m-jrc_{threshold}_{admin_level}"
        ),
        "economic_adapted": (
            f"{iso3}_{admin_level}_metrics_jrc-flood_"
            f"AALs_adapted_rl_{threshold}_capstock"
        ),
        "economic_baseline": (
            f"{iso3}_{admin_level}_metrics_jrc-flood_"
            "protected_AAR_baseline_capstock"
        ),
        "social_adapted": (
            f"{iso3}_{admin_level}_metrics_jrc-flood_"
            f"adapted_AAR_V-EXP_S-rwi_rl_{threshold}"
        ),
        "social_baseline": (
            f"{iso3}_{admin_level}_metrics_jrc-flood_"
            "protected_AAR_V-EXP_S-rwi"
        ),
    }


def _flood_protection_stems(
    config: PipelineConfig,
    urbanisation_threshold_code: int,
    design_return_period_years: int,
) -> dict[str, str]:
    iso3 = config.country.iso3
    admin_level = config.country.admin_level.upper()
    threshold = f"duc{urbanisation_threshold_code}"
    return_period = f"rp{design_return_period_years}"
    return {
        "cost": (
            f"{iso3}_adaptation-cost_fp_{return_period}_{threshold}_"
            f"{admin_level}"
        ),
        "economic_adapted": (
            f"{iso3}_{admin_level}_metrics_jrc-flood_"
            f"AALs_adapted_fp_{return_period}_{threshold}_capstock"
        ),
        "economic_baseline": (
            f"{iso3}_{admin_level}_metrics_jrc-flood_"
            "protected_AAR_baseline_capstock"
        ),
        "social_adapted": (
            f"{iso3}_{admin_level}_metrics_jrc-flood_"
            f"adapted_AAR_V-EXP_S-rwi_fp_{return_period}_{threshold}"
        ),
        "social_baseline": (
            f"{iso3}_{admin_level}_metrics_jrc-flood_"
            "protected_AAR_V-EXP_S-rwi"
        ),
    }


def _read_source(directory: Path, stem: str) -> pd.DataFrame:
    return read_gpkg_attributes(directory / f"{stem}.gpkg", stem)


def _validate_admin_reference(
    source: pd.DataFrame,
    admin_regions: gpd.GeoDataFrame,
    label: str,
    *,
    allow_single_admin_id: bool = False,
) -> pd.DataFrame:
    validate_columns(source, {"shapeName"}, label)
    if "shapeID" not in source:
        if (
            not allow_single_admin_id
            or len(source) != 1
            or len(admin_regions) != 1
        ):
            validate_columns(source, {"shapeID"}, label)
        source = source.copy()
        source.insert(0, "shapeID", admin_regions.iloc[0]["adm_id"])
    validate_unique(source, ["shapeID"], label)

    normalized = source.copy()
    normalized["shapeID"] = normalized["shapeID"].astype("string")
    normalized["shapeName"] = normalized["shapeName"].astype("string")
    expected_ids = set(admin_regions["adm_id"].astype("string"))
    observed_ids = set(normalized["shapeID"])
    missing_ids = sorted(expected_ids.difference(observed_ids))
    extra_ids = sorted(observed_ids.difference(expected_ids))
    if missing_ids or extra_ids:
        raise ValueError(
            f"{label} administrative coverage does not match boundaries. "
            f"Missing: {missing_ids[:5]}; extra: {extra_ids[:5]}"
        )

    expected_names = admin_regions[["adm_id", "adm_name"]].copy()
    expected_names["adm_id"] = expected_names["adm_id"].astype("string")
    name_check = normalized[["shapeID", "shapeName"]].merge(
        expected_names,
        left_on="shapeID",
        right_on="adm_id",
        how="left",
        validate="one_to_one",
    )
    mismatched_names = name_check[
        name_check["shapeName"] != name_check["adm_name"]
    ]
    if not mismatched_names.empty:
        example = mismatched_names[["shapeID", "shapeName", "adm_name"]].head()
        raise ValueError(
            f"{label} administrative names do not match boundaries. "
            f"Example:\n{example}"
        )
    return normalized


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


def _require_reconciliation(
    frame: pd.DataFrame,
    total_column: str,
    component_columns: list[str],
    label: str,
) -> None:
    component_total = frame[component_columns].sum(axis=1)
    if not np.allclose(
        frame[total_column],
        component_total,
        rtol=1e-6,
        atol=0.01,
    ):
        maximum_difference = (component_total - frame[total_column]).abs().max()
        raise ValueError(
            f"{label} components do not reconcile with {total_column}. "
            f"Maximum absolute difference: {maximum_difference}"
        )


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


def build_dry_proofing_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame | None = None,
) -> pd.DataFrame:
    """Load and calculate one-row-per-admin dry-proofing outcome metrics."""
    if admin_regions is None:
        admin_regions = load_admin_boundaries(config)

    directory = config.source("adaptation_outcomes_dir")
    stems = _dry_proofing_stems(config)
    sources = {
        name: _validate_admin_reference(
            _read_source(directory, stem),
            admin_regions,
            f"Dry-proofing {name.replace('_', ' ')}",
            allow_single_admin_id=(config.country.admin_level == "adm0"),
        )
        for name, stem in stems.items()
    }

    cost = sources["cost"]
    _validate_numeric_columns(
        cost,
        ["area_dry-proofed"],
        "Dry-proofing cost",
    )

    economic_columns = list(ECONOMIC_SOURCE_COLUMNS)
    for source_name in ("economic_baseline", "economic_adapted"):
        source = sources[source_name]
        label = f"Dry-proofing {source_name.replace('_', ' ')}"
        _validate_numeric_columns(source, economic_columns, label)
        _require_reconciliation(
            source,
            "total_losses",
            ["res_losses", "nres_losses", "infr_losses"],
            label,
        )

    social_columns = [
        *SOCIAL_SOURCE_COLUMNS,
        "CI",
        *_SOCIAL_CONTEXT_COLUMNS,
    ]
    for source_name in ("social_baseline", "social_adapted"):
        source = sources[source_name]
        label = f"Dry-proofing {source_name.replace('_', ' ')}"
        _validate_numeric_columns(
            source,
            [*SOCIAL_SOURCE_COLUMNS, *_SOCIAL_CONTEXT_COLUMNS],
            label,
        )
        _validate_numeric_columns(
            source,
            ["CI"],
            label,
            nonnegative=False,
            allow_missing=True,
        )
        if ((source["Population Coverage (%)"] < 0) | (
            source["Population Coverage (%)"] > 100
        )).any():
            raise ValueError(f"{label} population coverage must be 0 to 100")
        if ((source["CI"] < -1) | (source["CI"] > 1)).any():
            raise ValueError(f"{label} concentration index must be -1 to 1")
        invalid_missing_ci = source["CI"].isna() & source[
            "Total Flood Risk"
        ].ne(0)
        if invalid_missing_ci.any():
            raise ValueError(
                f"{label} concentration index is missing for positive flood "
                "exposure"
            )
        _require_reconciliation(
            source,
            "Total Flood Risk",
            [f"Q{quintile} Flood Risk" for quintile in range(1, 6)],
            label,
        )

    _warn_social_context_difference(
        sources["social_baseline"],
        sources["social_adapted"],
        "Dry-proofing",
    )

    metrics = admin_regions[["adm_id"]].copy()
    metrics["adm_id"] = metrics["adm_id"].astype("string")
    for source_name, source in sources.items():
        source = source.rename(columns={"shapeID": "adm_id"})
        source["adm_id"] = source["adm_id"].astype("string")
        source_columns: list[str]
        if source_name == "cost":
            source_columns = ["area_dry-proofed"]
        elif source_name.startswith("economic"):
            source_columns = economic_columns
        else:
            source_columns = social_columns
        renamed = source[["adm_id", *source_columns]].rename(
            columns={
                column: f"{source_name}_{column}"
                for column in source_columns
            }
        )
        metrics = metrics.merge(
            renamed,
            on="adm_id",
            how="left",
            validate="one_to_one",
        )

    metrics["cost_area_dry_proofed_m2"] = metrics.pop(
        "cost_area_dry-proofed"
    )
    for source_column, output_sector in ECONOMIC_SOURCE_COLUMNS.items():
        baseline_column = f"economic_baseline_{source_column}"
        adapted_column = f"economic_adapted_{source_column}"
        metrics[f"economic_avoided_{output_sector}"] = (
            metrics[baseline_column] - metrics[adapted_column]
        )
    for source_column, wealth_group in SOCIAL_SOURCE_COLUMNS.items():
        baseline_column = f"social_baseline_{source_column}"
        adapted_column = f"social_adapted_{source_column}"
        metrics[f"social_avoided_{wealth_group}"] = (
            metrics[baseline_column] - metrics[adapted_column]
        )
    metrics["social_change_ci"] = (
        metrics["social_adapted_CI"] - metrics["social_baseline_CI"]
    )
    return metrics


def build_relocation_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame | None = None,
) -> pd.DataFrame:
    """Calculate relocation outcomes for every supported urban threshold."""
    if admin_regions is None:
        admin_regions = load_admin_boundaries(config)

    directory = config.source("adaptation_outcomes_dir")
    allow_single_admin_id = config.country.admin_level == "adm0"
    economic_columns = list(ECONOMIC_SOURCE_COLUMNS)
    social_columns = [
        *SOCIAL_SOURCE_COLUMNS,
        "CI",
        *_SOCIAL_CONTEXT_COLUMNS,
    ]
    threshold_metrics = []

    for threshold_code, threshold_label in URBANISATION_THRESHOLDS.items():
        stems = _relocation_stems(config, threshold_code)
        sources = {
            name: _validate_admin_reference(
                _read_source(directory, stem),
                admin_regions,
                (
                    f"Relocation {threshold_label} ({threshold_code}) "
                    f"{name.replace('_', ' ')}"
                ),
                allow_single_admin_id=allow_single_admin_id,
            )
            for name, stem in stems.items()
        }

        cost = sources["cost"]
        _validate_numeric_columns(
            cost,
            ["capstock_relocated"],
            f"Relocation {threshold_label} ({threshold_code}) cost",
        )

        for source_name in ("economic_baseline", "economic_adapted"):
            source = sources[source_name]
            label = (
                f"Relocation {threshold_label} ({threshold_code}) "
                f"{source_name.replace('_', ' ')}"
            )
            _validate_numeric_columns(source, economic_columns, label)
            _require_reconciliation(
                source,
                "total_losses",
                ["res_losses", "nres_losses", "infr_losses"],
                label,
            )

        for source_name in ("social_baseline", "social_adapted"):
            source = sources[source_name]
            label = (
                f"Relocation {threshold_label} ({threshold_code}) "
                f"{source_name.replace('_', ' ')}"
            )
            _validate_numeric_columns(
                source,
                [*SOCIAL_SOURCE_COLUMNS, *_SOCIAL_CONTEXT_COLUMNS],
                label,
            )
            _validate_numeric_columns(
                source,
                ["CI"],
                label,
                nonnegative=False,
                allow_missing=True,
            )
            if ((source["Population Coverage (%)"] < 0) | (
                source["Population Coverage (%)"] > 100
            )).any():
                raise ValueError(
                    f"{label} population coverage must be 0 to 100"
                )
            if ((source["CI"] < -1) | (source["CI"] > 1)).any():
                raise ValueError(
                    f"{label} concentration index must be -1 to 1"
                )
            invalid_missing_ci = source["CI"].isna() & source[
                "Total Flood Risk"
            ].ne(0)
            if invalid_missing_ci.any():
                raise ValueError(
                    f"{label} concentration index is missing for positive "
                    "flood exposure"
                )
            _require_reconciliation(
                source,
                "Total Flood Risk",
                [f"Q{quintile} Flood Risk" for quintile in range(1, 6)],
                label,
            )

        _warn_social_context_difference(
            sources["social_baseline"],
            sources["social_adapted"],
            f"Relocation {threshold_label} ({threshold_code})",
        )

        metrics = admin_regions[["adm_id"]].copy()
        metrics["adm_id"] = metrics["adm_id"].astype("string")
        for source_name, source in sources.items():
            source = source.rename(columns={"shapeID": "adm_id"})
            source["adm_id"] = source["adm_id"].astype("string")
            source_columns: list[str]
            if source_name == "cost":
                source_columns = ["capstock_relocated"]
            elif source_name.startswith("economic"):
                source_columns = economic_columns
            else:
                source_columns = social_columns
            renamed = source[["adm_id", *source_columns]].rename(
                columns={
                    column: f"{source_name}_{column}"
                    for column in source_columns
                }
            )
            metrics = metrics.merge(
                renamed,
                on="adm_id",
                how="left",
                validate="one_to_one",
            )

        for source_column, output_sector in ECONOMIC_SOURCE_COLUMNS.items():
            baseline_column = f"economic_baseline_{source_column}"
            adapted_column = f"economic_adapted_{source_column}"
            metrics[f"economic_avoided_{output_sector}"] = (
                metrics[baseline_column] - metrics[adapted_column]
            )
        for source_column, wealth_group in SOCIAL_SOURCE_COLUMNS.items():
            baseline_column = f"social_baseline_{source_column}"
            adapted_column = f"social_adapted_{source_column}"
            metrics[f"social_avoided_{wealth_group}"] = (
                metrics[baseline_column] - metrics[adapted_column]
            )
        metrics["social_change_ci"] = (
            metrics["social_adapted_CI"] - metrics["social_baseline_CI"]
        )
        metrics.insert(1, "urbanisation_threshold", threshold_label)
        metrics.insert(2, "urbanisation_threshold_code", threshold_code)
        threshold_metrics.append(metrics)

    output = pd.concat(threshold_metrics, ignore_index=True)
    validate_unique(
        output,
        ["adm_id", "urbanisation_threshold_code"],
        "Relocation outcome metrics",
    )
    return output


def build_flood_protection_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame | None = None,
) -> pd.DataFrame:
    """Calculate flood-protection outcomes for every DUC and design RP."""
    if admin_regions is None:
        admin_regions = load_admin_boundaries(config)

    directory = config.source("adaptation_outcomes_dir")
    allow_single_admin_id = config.country.admin_level == "adm0"
    economic_columns = list(ECONOMIC_SOURCE_COLUMNS)
    social_columns = [
        *SOCIAL_SOURCE_COLUMNS,
        "CI",
        *_SOCIAL_CONTEXT_COLUMNS,
    ]
    scenario_metrics = []

    for threshold_code, threshold_label in URBANISATION_THRESHOLDS.items():
        for return_period in FLOOD_PROTECTION_RETURN_PERIODS:
            scenario_label = (
                f"Flood protection {threshold_label} ({threshold_code}), "
                f"RP{return_period}"
            )
            stems = _flood_protection_stems(
                config,
                threshold_code,
                return_period,
            )
            sources = {
                name: _validate_admin_reference(
                    _read_source(directory, stem),
                    admin_regions,
                    f"{scenario_label} {name.replace('_', ' ')}",
                    allow_single_admin_id=allow_single_admin_id,
                )
                for name, stem in stems.items()
            }

            cost = sources["cost"]
            cost_columns = [
                "adaptation_cost",
                "min_adaptation_cost",
                "max_adaptation_cost",
            ]
            _validate_numeric_columns(
                cost,
                cost_columns,
                f"{scenario_label} cost",
                allow_missing=True,
            )
            missing_cost = cost[cost_columns].isna()
            partially_missing_cost = missing_cost.any(axis=1) & (
                ~missing_cost.all(axis=1)
            )
            if partially_missing_cost.any():
                raise ValueError(
                    f"{scenario_label} cost estimates must either all be "
                    "present or all be missing"
                )
            invalid_cost_order = (
                (cost["min_adaptation_cost"] > cost["adaptation_cost"])
                | (cost["adaptation_cost"] > cost["max_adaptation_cost"])
            )
            if invalid_cost_order.any():
                raise ValueError(
                    f"{scenario_label} cost must satisfy lower <= estimate "
                    "<= upper"
                )

            for source_name in ("economic_baseline", "economic_adapted"):
                source = sources[source_name]
                label = f"{scenario_label} {source_name.replace('_', ' ')}"
                _validate_numeric_columns(source, economic_columns, label)
                _require_reconciliation(
                    source,
                    "total_losses",
                    ["res_losses", "nres_losses", "infr_losses"],
                    label,
                )

            for source_name in ("social_baseline", "social_adapted"):
                source = sources[source_name]
                label = f"{scenario_label} {source_name.replace('_', ' ')}"
                _validate_numeric_columns(
                    source,
                    [*SOCIAL_SOURCE_COLUMNS, *_SOCIAL_CONTEXT_COLUMNS],
                    label,
                )
                _validate_numeric_columns(
                    source,
                    ["CI"],
                    label,
                    nonnegative=False,
                    allow_missing=True,
                )
                if ((source["Population Coverage (%)"] < 0) | (
                    source["Population Coverage (%)"] > 100
                )).any():
                    raise ValueError(
                        f"{label} population coverage must be 0 to 100"
                    )
                if ((source["CI"] < -1) | (source["CI"] > 1)).any():
                    raise ValueError(
                        f"{label} concentration index must be -1 to 1"
                    )
                invalid_missing_ci = source["CI"].isna() & source[
                    "Total Flood Risk"
                ].ne(0)
                if invalid_missing_ci.any():
                    raise ValueError(
                        f"{label} concentration index is missing for positive "
                        "flood exposure"
                    )
                _require_reconciliation(
                    source,
                    "Total Flood Risk",
                    [
                        f"Q{quintile} Flood Risk"
                        for quintile in range(1, 6)
                    ],
                    label,
                )

            _warn_social_context_difference(
                sources["social_baseline"],
                sources["social_adapted"],
                scenario_label,
            )

            metrics = admin_regions[["adm_id"]].copy()
            metrics["adm_id"] = metrics["adm_id"].astype("string")
            for source_name, source in sources.items():
                source = source.rename(columns={"shapeID": "adm_id"})
                source["adm_id"] = source["adm_id"].astype("string")
                source_columns: list[str]
                if source_name == "cost":
                    source_columns = cost_columns
                elif source_name.startswith("economic"):
                    source_columns = economic_columns
                else:
                    source_columns = social_columns
                renamed = source[["adm_id", *source_columns]].rename(
                    columns={
                        column: f"{source_name}_{column}"
                        for column in source_columns
                    }
                )
                metrics = metrics.merge(
                    renamed,
                    on="adm_id",
                    how="left",
                    validate="one_to_one",
                )

            for source_column, output_sector in ECONOMIC_SOURCE_COLUMNS.items():
                baseline_column = f"economic_baseline_{source_column}"
                adapted_column = f"economic_adapted_{source_column}"
                metrics[f"economic_avoided_{output_sector}"] = (
                    metrics[baseline_column] - metrics[adapted_column]
                )
            for source_column, wealth_group in SOCIAL_SOURCE_COLUMNS.items():
                baseline_column = f"social_baseline_{source_column}"
                adapted_column = f"social_adapted_{source_column}"
                metrics[f"social_avoided_{wealth_group}"] = (
                    metrics[baseline_column] - metrics[adapted_column]
                )
            metrics["social_change_ci"] = (
                metrics["social_adapted_CI"]
                - metrics["social_baseline_CI"]
            )
            metrics.insert(1, "urbanisation_threshold", threshold_label)
            metrics.insert(2, "urbanisation_threshold_code", threshold_code)
            metrics.insert(3, "design_return_period_years", return_period)
            scenario_metrics.append(metrics)

    output = pd.concat(scenario_metrics, ignore_index=True)
    validate_unique(
        output,
        [
            "adm_id",
            "urbanisation_threshold_code",
            "design_return_period_years",
        ],
        "Flood-protection outcome metrics",
    )
    return output


def _finalize_adaptation_outcomes_card(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    long_metrics: pd.DataFrame,
    card: str,
) -> pd.DataFrame:
    dimensions = ADAPTATION_OUTCOMES_CARD_DIMENSIONS[card]
    identifiers = build_card_identifier_frame(
        admin_regions,
        config,
        section="adaptation_outcomes",
        card=card,
    )
    admin_order = {
        adm_id: order for order, adm_id in enumerate(identifiers["adm_id"])
    }
    output = identifiers.merge(
        long_metrics,
        on="adm_id",
        how="left",
        validate="one_to_many",
    )
    output["_admin_order"] = output["adm_id"].map(admin_order)
    output = output.sort_values(
        ["_admin_order", "_row_order"],
        kind="stable",
    ).drop(columns=["_admin_order", "_row_order"])
    output["value"] = output["value"].round(3)
    output = output[
        [*CARD_IDENTIFIER_COLUMNS, *dimensions, "value"]
    ].reset_index(drop=True)
    validate_card_output(
        output,
        "adaptation_outcomes",
        card,
        dimensions,
        optional_dimension_columns=(
            ADAPTATION_OUTCOMES_CARD_OPTIONAL_DIMENSIONS[card]
        ),
    )
    return output


def _metric_part(
    metrics: pd.DataFrame,
    source_column: str,
    *,
    outcome_type: str,
    metric: str,
    statistic: str,
    sector: object = pd.NA,
    wealth_group: object = pd.NA,
    unit: str,
    row_order: int,
    dimension_columns: tuple[str, ...] = (),
) -> pd.DataFrame:
    part = metrics[["adm_id", *dimension_columns, source_column]].rename(
        columns={source_column: "value"}
    )
    part["outcome_type"] = outcome_type
    part["hazard"] = "river_flood"
    part["model"] = "jrc"
    part["metric"] = metric
    part["statistic"] = statistic
    part["sector"] = sector
    part["wealth_group"] = wealth_group
    part["unit"] = unit
    part["_row_order"] = row_order
    return part


def _build_outcome_parts(
    metrics: pd.DataFrame,
    *,
    cost_specs: tuple[tuple[str, str], ...],
    cost_metric: str,
    cost_unit: str,
    dimension_columns: tuple[str, ...] = (),
) -> pd.DataFrame:
    parts = []
    for row_order, (source_column, statistic) in enumerate(cost_specs):
        parts.append(
            _metric_part(
                metrics,
                source_column,
                outcome_type="cost",
                metric=cost_metric,
                statistic=statistic,
                unit=cost_unit,
                row_order=row_order,
                dimension_columns=dimension_columns,
            )
        )

    row_order = len(parts)
    for source_column, sector in ECONOMIC_SOURCE_COLUMNS.items():
        for statistic, prefix in (
            ("baseline", "economic_baseline"),
            ("adapted", "economic_adapted"),
            ("avoided", "economic_avoided"),
        ):
            column = (
                f"{prefix}_{source_column}"
                if statistic != "avoided"
                else f"{prefix}_{sector}"
            )
            parts.append(
                _metric_part(
                    metrics,
                    column,
                    outcome_type="economic_benefit",
                    metric="average_annual_loss",
                    statistic=statistic,
                    sector=sector,
                    unit="usd_per_year",
                    row_order=row_order,
                    dimension_columns=dimension_columns,
                )
            )
            row_order += 1

    for source_column, wealth_group in SOCIAL_SOURCE_COLUMNS.items():
        for statistic, prefix in (
            ("baseline", "social_baseline"),
            ("adapted", "social_adapted"),
            ("avoided", "social_avoided"),
        ):
            column = (
                f"{prefix}_{source_column}"
                if statistic != "avoided"
                else f"{prefix}_{wealth_group}"
            )
            parts.append(
                _metric_part(
                    metrics,
                    column,
                    outcome_type="social_benefit",
                    metric="average_annual_flood_exposure",
                    statistic=statistic,
                    wealth_group=wealth_group,
                    unit="people_per_year",
                    row_order=row_order,
                    dimension_columns=dimension_columns,
                )
            )
            row_order += 1

    for statistic, column in (
        ("baseline", "social_baseline_CI"),
        ("adapted", "social_adapted_CI"),
        ("change", "social_change_ci"),
    ):
        parts.append(
            _metric_part(
                metrics,
                column,
                outcome_type="social_benefit",
                metric="concentration_index",
                statistic=statistic,
                wealth_group="total",
                unit="index",
                row_order=row_order,
                dimension_columns=dimension_columns,
            )
        )
        row_order += 1

    return pd.concat(parts, ignore_index=True)


def assemble_adaptation_outcomes_card_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    dry_proofing_metrics: pd.DataFrame,
    relocation_metrics: pd.DataFrame | None = None,
    flood_protection_metrics: pd.DataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    """Reshape Adaptation Outcomes calculations into downloadable cards."""
    dry_proofing_long = _build_outcome_parts(
        dry_proofing_metrics,
        cost_specs=(("cost_area_dry_proofed_m2", "estimate"),),
        cost_metric="area_dry_proofed",
        cost_unit="m2",
    )
    cards = {
        DRY_PROOFING_CARD: _finalize_adaptation_outcomes_card(
            config,
            admin_regions,
            dry_proofing_long,
            DRY_PROOFING_CARD,
        )
    }

    if relocation_metrics is not None:
        relocation_long = _build_outcome_parts(
            relocation_metrics,
            cost_specs=(("cost_capstock_relocated", "estimate"),),
            cost_metric="capstock_relocated",
            cost_unit="usd",
            dimension_columns=(
                "urbanisation_threshold",
                "urbanisation_threshold_code",
            ),
        )
        threshold_order = {
            code: order
            for order, code in enumerate(URBANISATION_THRESHOLDS)
        }
        rows_per_threshold = int(relocation_long["_row_order"].max()) + 1
        relocation_long["_row_order"] = (
            relocation_long["urbanisation_threshold_code"]
            .map(threshold_order)
            .mul(rows_per_threshold)
            .add(relocation_long["_row_order"])
        )
        cards[RELOCATION_CARD] = _finalize_adaptation_outcomes_card(
            config,
            admin_regions,
            relocation_long,
            RELOCATION_CARD,
        )

    if flood_protection_metrics is not None:
        flood_protection_long = _build_outcome_parts(
            flood_protection_metrics,
            cost_specs=(
                ("cost_adaptation_cost", "estimate"),
                ("cost_min_adaptation_cost", "lower"),
                ("cost_max_adaptation_cost", "upper"),
            ),
            cost_metric="adaptation_cost",
            cost_unit="million_usd",
            dimension_columns=(
                "urbanisation_threshold",
                "urbanisation_threshold_code",
                "design_return_period_years",
            ),
        )
        threshold_order = {
            code: order
            for order, code in enumerate(URBANISATION_THRESHOLDS)
        }
        return_period_order = {
            return_period: order
            for order, return_period in enumerate(
                FLOOD_PROTECTION_RETURN_PERIODS
            )
        }
        scenario_order = (
            flood_protection_long["urbanisation_threshold_code"]
            .map(threshold_order)
            .mul(len(FLOOD_PROTECTION_RETURN_PERIODS))
            .add(
                flood_protection_long["design_return_period_years"].map(
                    return_period_order
                )
            )
        )
        rows_per_scenario = (
            int(flood_protection_long["_row_order"].max()) + 1
        )
        flood_protection_long["_row_order"] = (
            scenario_order.mul(rows_per_scenario).add(
                flood_protection_long["_row_order"]
            )
        )
        cards[FLOOD_PROTECTION_CARD] = (
            _finalize_adaptation_outcomes_card(
                config,
                admin_regions,
                flood_protection_long,
                FLOOD_PROTECTION_CARD,
            )
        )
    return cards


def build_adaptation_outcomes_card_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    """Calculate and build the available Adaptation Outcomes cards."""
    if admin_regions is None:
        admin_regions = load_admin_boundaries(config)
    dry_proofing_metrics = build_dry_proofing_metrics(config, admin_regions)
    relocation_metrics = build_relocation_metrics(config, admin_regions)
    flood_protection_metrics = build_flood_protection_metrics(
        config,
        admin_regions,
    )
    return assemble_adaptation_outcomes_card_metrics(
        config,
        admin_regions,
        dry_proofing_metrics,
        relocation_metrics,
        flood_protection_metrics,
    )
