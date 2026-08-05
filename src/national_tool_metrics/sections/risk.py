from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd

from ..boundaries import load_admin_boundaries
from ..config import PipelineConfig, RiskRunConfig
from ..outputs import (
    IDENTIFIER_COLUMNS,
    build_identifier_frame,
    merge_metric_tables,
    namespace_metric_table,
    validate_section_output,
)
from ..tables import read_gpkg_attributes, validate_columns, validate_unique
from ..vector import line_ead_by_admin


DEFAULT_POPULATION_RISK_MAP = "AAR_protected"
RETURN_PERIOD_RISK_MAPS = (
    "RP10",
    "RP20",
    "RP50",
    "RP75",
    "RP100",
    "RP200",
    "RP500",
)
POPULATION_RISK_MAP_PREFIXES = {
    DEFAULT_POPULATION_RISK_MAP: "flooded_pop_ea_protected",
    **{
        risk_map: f"flooded_pop_{risk_map.lower()}"
        for risk_map in RETURN_PERIOD_RISK_MAPS
    },
}
DEFAULT_CAPITAL_STOCK_RISK_MAP = "protected_AAR"
CAPITAL_STOCK_RISK_MAP_PREFIXES = {
    DEFAULT_CAPITAL_STOCK_RISK_MAP: "capstock_aal",
    **{
        risk_map: f"capstock_{risk_map.lower()}"
        for risk_map in RETURN_PERIOD_RISK_MAPS
    },
}
CAPITAL_STOCK_COMPONENT_TOKENS = {
    "res_losses": "residential",
    "nres_losses": "non_residential",
    "infr_losses": "infrastructure",
    "total_losses": "total",
}

POPULATION_GROUP_TOKENS = {
    "total": "total",
    "female": "female",
    "male": "male",
    "children_under5": "under_5",
    "school_age_5_14": "school_children_5_14",
    "working_age_15_64": "working_age_15_64",
    "female_15_49": "female_childbearing_15_49",
    "older_65plus": "older_65_plus",
    "wealth_q1": "wealth_q1",
    "wealth_q2": "wealth_q2",
    "wealth_q3": "wealth_q3",
    "wealth_q4": "wealth_q4",
    "wealth_q5": "wealth_q5",
}


def _validate_admin_reference(
    source: pd.DataFrame,
    admin_regions: gpd.GeoDataFrame,
    label: str,
) -> None:
    """Require source identifiers and names to match the selected boundaries."""
    validate_columns(source, {"shapeID", "shapeName"}, label)
    reference = source[["shapeID", "shapeName"]].drop_duplicates().copy()
    reference["shapeID"] = reference["shapeID"].astype("string")
    reference["shapeName"] = reference["shapeName"].astype("string")
    validate_unique(reference, ["shapeID"], label)

    expected_ids = set(admin_regions["adm_id"].astype(str))
    actual_ids = set(reference["shapeID"].astype(str))
    missing_ids = sorted(expected_ids.difference(actual_ids))
    extra_ids = sorted(actual_ids.difference(expected_ids))
    if missing_ids or extra_ids:
        raise ValueError(
            f"{label} administrative coverage does not match the boundaries. "
            f"Missing IDs: {missing_ids[:5]}; extra IDs: {extra_ids[:5]}"
        )

    name_check = admin_regions[["adm_id", "adm_name"]].merge(
        reference,
        left_on="adm_id",
        right_on="shapeID",
        how="inner",
        validate="one_to_one",
    )
    mismatches = name_check[
        name_check["adm_name"].astype(str)
        != name_check["shapeName"].astype(str)
    ]
    if not mismatches.empty:
        example = mismatches[["adm_id", "adm_name", "shapeName"]].head()
        raise ValueError(
            f"{label} administrative names do not match the boundaries. "
            f"Example:\n{example}"
        )


def _validate_source_context(
    source: pd.DataFrame,
    config: PipelineConfig,
    label: str,
) -> None:
    """Validate country and administrative-level fields when present."""
    if "ISO3" in source.columns:
        countries = set(source["ISO3"].dropna().astype(str).str.upper())
        if countries != {config.country.iso3}:
            raise ValueError(
                f"{label} country values do not match "
                f"{config.country.iso3}: {sorted(countries)}"
            )
    if "admin_level" in source.columns:
        levels = set(source["admin_level"].dropna().astype(str).str.upper())
        expected_level = config.country.admin_level.upper()
        if levels != {expected_level}:
            raise ValueError(
                f"{label} administrative level does not match "
                f"{expected_level}: {sorted(levels)}"
            )


def _validate_numeric_columns(
    frame: pd.DataFrame,
    columns: list[str],
    label: str,
) -> None:
    """Convert risk metrics to numeric values and reject invalid losses."""
    for column in columns:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
        values = frame[column].to_numpy(dtype="float64")
        if not np.isfinite(values).all():
            raise ValueError(
                f"{label} contains missing or non-finite values in {column}"
            )
        if (values < 0).any():
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
        difference = (component_total - frame[total_column]).abs()
        raise ValueError(
            f"{label} components do not reconcile with {total_column}. "
            f"Maximum absolute difference: {difference.max()}"
        )


def _population_risk_stem(config: PipelineConfig) -> str:
    return (
        f"{config.country.iso3}_{config.country.admin_level.upper()}_"
        "jrc_population_risk_metrics"
    )


def _capital_stock_risk_stem(
    config: PipelineConfig,
    risk_map: str,
) -> str:
    return (
        f"{config.country.iso3}_{config.country.admin_level.upper()}_"
        f"metrics_jrc-flood_{risk_map}_baseline_capstock"
    )


def build_population_risk_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    run: RiskRunConfig,
    risk_maps: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Build annual-average and return-period flooded-population metrics."""
    stem = _population_risk_stem(config)
    source = read_gpkg_attributes(
        run.inputs["population_risk_dir"] / f"{stem}.gpkg",
        stem,
    )
    required_columns = {
        "shapeID",
        "shapeName",
        "ISO3",
        "admin_level",
        "risk_map",
        "population_group",
        "exposed_population",
    }
    validate_columns(source, required_columns, "Population risk summary")
    _validate_source_context(source, config, "Population risk summary")

    selected_risk_maps = (
        tuple(POPULATION_RISK_MAP_PREFIXES)
        if risk_maps is None
        else risk_maps
    )
    unknown_risk_maps = sorted(
        set(selected_risk_maps).difference(POPULATION_RISK_MAP_PREFIXES)
    )
    if unknown_risk_maps:
        raise ValueError(
            "Population risk maps do not have configured metric prefixes: "
            f"{unknown_risk_maps}"
        )
    if not selected_risk_maps:
        raise ValueError("At least one population risk map is required")

    available_risk_maps = set(source["risk_map"].dropna().astype(str))
    missing_risk_maps = sorted(
        set(selected_risk_maps).difference(available_risk_maps)
    )
    if missing_risk_maps:
        raise ValueError(
            "Population risk summary is missing required risk maps: "
            f"{missing_risk_maps}"
        )

    metrics = admin_regions[["adm_id"]].copy()
    expected_groups = set(POPULATION_GROUP_TOKENS)
    for risk_map in selected_risk_maps:
        map_label = f"Population risk summary ({risk_map})"
        map_source = source[source["risk_map"] == risk_map].copy()
        _validate_admin_reference(map_source, admin_regions, map_label)

        groups = set(map_source["population_group"].dropna().astype(str))
        missing_groups = sorted(expected_groups.difference(groups))
        extra_groups = sorted(groups.difference(expected_groups))
        if missing_groups or extra_groups:
            raise ValueError(
                f"{map_label} groups do not match the expected groups. "
                f"Missing: {missing_groups}; extra: {extra_groups}"
            )

        map_source["shapeID"] = map_source["shapeID"].astype("string")
        validate_unique(
            map_source,
            ["shapeID", "population_group"],
            map_label,
        )
        _validate_numeric_columns(
            map_source,
            ["exposed_population"],
            map_label,
        )

        pivoted = map_source.pivot(
            index="shapeID",
            columns="population_group",
            values="exposed_population",
        )
        if pivoted.isna().any().any():
            raise ValueError(
                f"{map_label} has incomplete admin/group coverage"
            )
        pivoted = pivoted[list(POPULATION_GROUP_TOKENS)]
        prefix = POPULATION_RISK_MAP_PREFIXES[risk_map]
        pivoted = pivoted.rename(
            columns={
                group: f"{prefix}_{token}"
                for group, token in POPULATION_GROUP_TOKENS.items()
            }
        )
        pivoted.columns.name = None
        map_metrics = pivoted.reset_index().rename(
            columns={"shapeID": "adm_id"}
        )

        _require_reconciliation(
            map_metrics,
            f"{prefix}_total",
            [f"{prefix}_female", f"{prefix}_male"],
            f"{map_label} sex groups",
        )
        _require_reconciliation(
            map_metrics,
            f"{prefix}_total",
            [
                f"{prefix}_under_5",
                f"{prefix}_school_children_5_14",
                f"{prefix}_working_age_15_64",
                f"{prefix}_older_65_plus",
            ],
            f"{map_label} age groups",
        )
        _require_reconciliation(
            map_metrics,
            f"{prefix}_total",
            [
                f"{prefix}_wealth_q{quintile}"
                for quintile in range(1, 6)
            ],
            f"{map_label} wealth groups",
        )
        metrics = metrics.merge(
            map_metrics,
            on="adm_id",
            how="left",
            validate="one_to_one",
        )

    selected_return_periods = [
        risk_map
        for risk_map in RETURN_PERIOD_RISK_MAPS
        if risk_map in selected_risk_maps
    ]
    if len(selected_return_periods) > 1:
        for token in POPULATION_GROUP_TOKENS.values():
            columns = [
                f"{POPULATION_RISK_MAP_PREFIXES[risk_map]}_{token}"
                for risk_map in selected_return_periods
            ]
            values = metrics[columns].to_numpy(dtype="float64")
            if (np.diff(values, axis=1) < -0.01).any():
                raise ValueError(
                    "Population return-period metrics are not monotonic "
                    f"for population group {token}"
                )
    return metrics


def build_capital_stock_risk_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    run: RiskRunConfig,
    risk_maps: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Load annual-average and return-period capital-stock losses."""
    selected_risk_maps = (
        tuple(CAPITAL_STOCK_RISK_MAP_PREFIXES)
        if risk_maps is None
        else risk_maps
    )
    unknown_risk_maps = sorted(
        set(selected_risk_maps).difference(
            CAPITAL_STOCK_RISK_MAP_PREFIXES
        )
    )
    if unknown_risk_maps:
        raise ValueError(
            "Capital stock risk maps do not have configured metric "
            f"prefixes: {unknown_risk_maps}"
        )
    if not selected_risk_maps:
        raise ValueError("At least one capital stock risk map is required")

    metrics = admin_regions[["adm_id"]].copy()
    for risk_map in selected_risk_maps:
        stem = _capital_stock_risk_stem(config, risk_map)
        source = read_gpkg_attributes(
            run.inputs["capital_stock_risk_dir"] / f"{stem}.gpkg",
            stem,
        )
        map_label = f"Capital stock risk summary ({risk_map})"
        validate_columns(
            source,
            {
                "shapeID",
                "shapeName",
                *CAPITAL_STOCK_COMPONENT_TOKENS,
            },
            map_label,
        )
        _validate_admin_reference(
            source,
            admin_regions,
            map_label,
        )
        source["shapeID"] = source["shapeID"].astype("string")
        validate_unique(source, ["shapeID"], map_label)
        _validate_numeric_columns(
            source,
            list(CAPITAL_STOCK_COMPONENT_TOKENS),
            map_label,
        )

        prefix = CAPITAL_STOCK_RISK_MAP_PREFIXES[risk_map]
        source_columns = {
            column: f"{prefix}_{token}"
            for column, token in CAPITAL_STOCK_COMPONENT_TOKENS.items()
        }
        map_metrics = source[
            ["shapeID", *source_columns]
        ].rename(columns={"shapeID": "adm_id", **source_columns})
        _require_reconciliation(
            map_metrics,
            f"{prefix}_total",
            [
                f"{prefix}_residential",
                f"{prefix}_non_residential",
                f"{prefix}_infrastructure",
            ],
            map_label,
        )
        metrics = metrics.merge(
            map_metrics,
            on="adm_id",
            how="left",
            validate="one_to_one",
        )

    selected_return_periods = [
        risk_map
        for risk_map in RETURN_PERIOD_RISK_MAPS
        if risk_map in selected_risk_maps
    ]
    if len(selected_return_periods) > 1:
        for token in CAPITAL_STOCK_COMPONENT_TOKENS.values():
            columns = [
                f"{CAPITAL_STOCK_RISK_MAP_PREFIXES[risk_map]}_{token}"
                for risk_map in selected_return_periods
            ]
            national_totals = metrics[columns].sum(axis=0).to_numpy(
                dtype="float64"
            )
            if (np.diff(national_totals) < -0.01).any():
                raise ValueError(
                    "National capital stock return-period totals are not "
                    f"monotonic for component {token}"
                )
    return metrics


def build_direct_network_risk_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    run: RiskRunConfig,
) -> pd.DataFrame:
    """Build direct road, rail, or power EAD metrics configured for a run."""
    metric_tables: list[pd.DataFrame] = []
    if "road_damage" in run.inputs:
        metric_tables.append(
            line_ead_by_admin(
                run.inputs["road_damage"],
                admin_regions,
                run.columns["road_ead"],
                "road_ead_total",
                group_column="asset_type",
                group_metric_prefix="road_ead",
            )
        )
    if "rail_damage" in run.inputs:
        metric_tables.append(
            line_ead_by_admin(
                run.inputs["rail_damage"],
                admin_regions,
                run.columns["rail_ead"],
                "rail_ead_total",
            )
        )
    if "power_damage" in run.inputs:
        metric_tables.append(
            line_ead_by_admin(
                run.inputs["power_damage"],
                admin_regions,
                run.columns["power_ead"],
                "power_ead_total",
            )
        )
    if not metric_tables:
        raise ValueError(
            f"Risk run {run.name} contains no direct-network inputs"
        )

    metrics = admin_regions[["adm_id"]].copy()
    for table in metric_tables:
        metrics = metrics.merge(
            table,
            on="adm_id",
            how="left",
            validate="one_to_one",
        )
    metric_columns = [
        column for column in metrics.columns if column != "adm_id"
    ]
    metrics[metric_columns] = metrics[metric_columns].fillna(0)
    _validate_numeric_columns(
        metrics,
        metric_columns,
        f"{run.name} direct-network metrics",
    )

    road_type_columns = [
        column
        for column in metric_columns
        if column.startswith("road_ead_") and column != "road_ead_total"
    ]
    if road_type_columns:
        _require_reconciliation(
            metrics,
            "road_ead_total",
            road_type_columns,
            "Road EAD",
        )
    return metrics


def assemble_risk_run_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    run: RiskRunConfig,
    metric_tables: list[pd.DataFrame],
) -> pd.DataFrame:
    """Attach identifiers and namespace metrics for one configured run."""
    identifiers = build_identifier_frame(
        admin_regions,
        config,
        section="risk",
    )
    namespaced_tables = [
        namespace_metric_table(metrics, run.name) for metrics in metric_tables
    ]
    return merge_metric_tables(identifiers, namespaced_tables)


def build_risk_run_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    run: RiskRunConfig,
) -> pd.DataFrame:
    """Build all currently available components for one Risk model run."""
    metric_tables: list[pd.DataFrame] = []
    if "population_risk_dir" in run.inputs:
        metric_tables.append(
            build_population_risk_metrics(config, admin_regions, run)
        )
    if "capital_stock_risk_dir" in run.inputs:
        metric_tables.append(
            build_capital_stock_risk_metrics(config, admin_regions, run)
        )
    if {"road_damage", "rail_damage", "power_damage"}.intersection(
        run.inputs
    ):
        metric_tables.append(
            build_direct_network_risk_metrics(config, admin_regions, run)
        )
    if not metric_tables:
        raise ValueError(f"Risk run {run.name} contains no supported inputs")
    return assemble_risk_run_metrics(
        config,
        admin_regions,
        run,
        metric_tables,
    )


def combine_risk_run_outputs(
    risk_runs: list[pd.DataFrame],
) -> pd.DataFrame:
    """Merge namespaced run outputs into one row per administrative region."""
    if not risk_runs:
        raise ValueError("At least one Risk run output is required")
    for run_output in risk_runs:
        validate_section_output(run_output, "risk")

    identifiers = risk_runs[0][IDENTIFIER_COLUMNS].copy()
    metric_tables = []
    for index, run_output in enumerate(risk_runs, start=1):
        run_identifiers = run_output[IDENTIFIER_COLUMNS]
        if not run_identifiers.reset_index(drop=True).equals(
            identifiers.reset_index(drop=True)
        ):
            raise ValueError(
                f"Risk run output {index} identifiers do not match the first run"
            )
        metric_columns = [
            column
            for column in run_output.columns
            if column not in IDENTIFIER_COLUMNS
        ]
        metric_tables.append(run_output[["adm_id", *metric_columns]])

    combined = merge_metric_tables(identifiers, metric_tables)
    validate_section_output(combined, "risk")
    return combined


def build_risk_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame | None = None,
) -> pd.DataFrame:
    """Build the consolidated Risk section without writing the CSV."""
    if admin_regions is None:
        admin_regions = load_admin_boundaries(config)
    outputs = [
        build_risk_run_metrics(config, admin_regions, run)
        for run in config.risk_runs.values()
    ]
    return combine_risk_run_outputs(outputs)
