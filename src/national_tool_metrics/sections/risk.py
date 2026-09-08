from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd

from ..boundaries import load_admin_boundaries
from ..config import PipelineConfig, RiskRunConfig
from ..outputs import (
    CARD_IDENTIFIER_COLUMNS,
    IDENTIFIER_COLUMNS,
    build_card_identifier_frame,
    build_identifier_frame,
    merge_metric_tables,
    namespace_metric_table,
    validate_card_output,
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

POPULATION_CARD = "population"
CAPITAL_STOCK_CARD = "capital_stock"
DIRECT_DAMAGE_CARD = "direct_damage"

POPULATION_CARD_DIMENSIONS = (
    "risk_subsection",
    "hazard",
    "model",
    "scenario",
    "population_layer",
    "population_group",
    "risk_metric",
    "unit",
)
CAPITAL_STOCK_CARD_DIMENSIONS = (
    "risk_subsection",
    "hazard",
    "model",
    "scenario",
    "sector",
    "risk_metric",
    "unit",
)
DIRECT_DAMAGE_CARD_DIMENSIONS = (
    "risk_subsection",
    "hazard",
    "model",
    "scenario",
    "epoch",
    "infrastructure_type",
    "asset_class",
    "metric",
    "unit",
)
RISK_CARD_DIMENSIONS = {
    POPULATION_CARD: POPULATION_CARD_DIMENSIONS,
    CAPITAL_STOCK_CARD: CAPITAL_STOCK_CARD_DIMENSIONS,
    DIRECT_DAMAGE_CARD: DIRECT_DAMAGE_CARD_DIMENSIONS,
}
RISK_CARD_OPTIONAL_DIMENSIONS = {
    POPULATION_CARD: (),
    CAPITAL_STOCK_CARD: (),
    DIRECT_DAMAGE_CARD: ("epoch",),
}

RISK_DEMOGRAPHIC_GROUP_METRICS = {
    "total": "total",
    "female": "female",
    "male": "male",
    "infant": "under_5",
    "schoolage": "school_children_5_14",
    "working": "working_age_15_64",
    "childbearing": "female_childbearing_15_49",
    "elderly": "older_65_plus",
}
RISK_WEALTH_GROUP_METRICS = {
    f"q{quintile}": f"wealth_q{quintile}"
    for quintile in range(1, 6)
}
RISK_CAPITAL_STOCK_SECTORS = (
    "total",
    "residential",
    "non_residential",
    "infrastructure",
)
RISK_ROAD_CLASSES = (
    "motorway",
    "trunk",
    "primary",
    "secondary",
    "tertiary",
)


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


def _population_risk_metric(risk_map: str) -> tuple[str, str]:
    if risk_map == DEFAULT_POPULATION_RISK_MAP:
        return "average_annual_exposure_protected", "people_per_year"
    return risk_map.lower(), "people"


def _capital_stock_risk_metric(risk_map: str) -> tuple[str, str]:
    if risk_map == DEFAULT_CAPITAL_STOCK_RISK_MAP:
        return "average_annual_loss_protected", "usd_per_year"
    return risk_map.lower(), "usd"


def _finalize_card_output(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    card: str,
    long_metrics: pd.DataFrame,
) -> pd.DataFrame:
    dimensions = RISK_CARD_DIMENSIONS[card]
    identifiers = build_card_identifier_frame(
        admin_regions,
        config,
        section="risk",
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
        "risk",
        card,
        dimensions,
        optional_dimension_columns=RISK_CARD_OPTIONAL_DIMENSIONS[card],
    )
    return output


def _format_population_card_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    metrics: pd.DataFrame,
) -> pd.DataFrame:
    risk_maps = tuple(POPULATION_RISK_MAP_PREFIXES)
    groups = [
        ("demographics", group, source_token)
        for group, source_token in RISK_DEMOGRAPHIC_GROUP_METRICS.items()
    ]
    groups.extend(
        ("wealth", group, source_token)
        for group, source_token in RISK_WEALTH_GROUP_METRICS.items()
    )
    groups.append(("wealth", "bottom_40", None))

    parts: list[pd.DataFrame] = []
    for group_order, (layer, group, source_token) in enumerate(groups):
        for risk_order, risk_map in enumerate(risk_maps):
            prefix = POPULATION_RISK_MAP_PREFIXES[risk_map]
            part = metrics[["adm_id"]].copy()
            if group == "bottom_40":
                part["value"] = (
                    metrics[f"{prefix}_wealth_q1"]
                    + metrics[f"{prefix}_wealth_q2"]
                )
            else:
                part["value"] = metrics[f"{prefix}_{source_token}"]
            risk_metric, unit = _population_risk_metric(risk_map)
            part["risk_subsection"] = "socioeconomic"
            part["hazard"] = "river_flood"
            part["model"] = "jrc"
            part["scenario"] = "baseline"
            part["population_layer"] = layer
            part["population_group"] = group
            part["risk_metric"] = risk_metric
            part["unit"] = unit
            part["_row_order"] = group_order * len(risk_maps) + risk_order
            parts.append(part)

    return _finalize_card_output(
        config,
        admin_regions,
        POPULATION_CARD,
        pd.concat(parts, ignore_index=True),
    )


def _format_capital_stock_card_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    metrics: pd.DataFrame,
) -> pd.DataFrame:
    risk_maps = tuple(CAPITAL_STOCK_RISK_MAP_PREFIXES)
    parts: list[pd.DataFrame] = []
    for sector_order, sector in enumerate(RISK_CAPITAL_STOCK_SECTORS):
        for risk_order, risk_map in enumerate(risk_maps):
            prefix = CAPITAL_STOCK_RISK_MAP_PREFIXES[risk_map]
            part = metrics[["adm_id", f"{prefix}_{sector}"]].rename(
                columns={f"{prefix}_{sector}": "value"}
            )
            risk_metric, unit = _capital_stock_risk_metric(risk_map)
            part["risk_subsection"] = "socioeconomic"
            part["hazard"] = "river_flood"
            part["model"] = "jrc"
            part["scenario"] = "baseline"
            part["sector"] = sector
            part["risk_metric"] = risk_metric
            part["unit"] = unit
            part["_row_order"] = sector_order * len(risk_maps) + risk_order
            parts.append(part)

    return _finalize_card_output(
        config,
        admin_regions,
        CAPITAL_STOCK_CARD,
        pd.concat(parts, ignore_index=True),
    )


def _direct_damage_part(
    metrics: pd.DataFrame,
    source_column: str,
    *,
    hazard: str,
    model: str,
    epoch: object,
    infrastructure_type: str,
    asset_class: str,
    row_order: int,
) -> pd.DataFrame:
    part = metrics[["adm_id"]].copy()
    part["value"] = (
        metrics[source_column]
        if source_column in metrics
        else 0.0
    )
    part["risk_subsection"] = "infrastructure_networks"
    part["hazard"] = hazard
    part["model"] = model
    part["scenario"] = "baseline"
    part["epoch"] = epoch
    part["infrastructure_type"] = infrastructure_type
    part["asset_class"] = asset_class
    part["metric"] = "direct_damage"
    part["unit"] = "usd_per_year"
    part["_row_order"] = row_order
    return part


def _format_direct_damage_card_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    river_metrics: pd.DataFrame,
    cyclone_metrics: pd.DataFrame,
) -> pd.DataFrame:
    parts = [
        _direct_damage_part(
            river_metrics,
            "road_ead_total",
            hazard="river_flood",
            model="jrc",
            epoch=pd.NA,
            infrastructure_type="road",
            asset_class="all",
            row_order=0,
        )
    ]
    for class_order, road_class in enumerate(RISK_ROAD_CLASSES, start=1):
        parts.append(
            _direct_damage_part(
                river_metrics,
                f"road_ead_{road_class}",
                hazard="river_flood",
                model="jrc",
                epoch=pd.NA,
                infrastructure_type="road",
                asset_class=road_class,
                row_order=class_order,
            )
        )
    parts.extend(
        [
            _direct_damage_part(
                river_metrics,
                "rail_ead_total",
                hazard="river_flood",
                model="jrc",
                epoch=pd.NA,
                infrastructure_type="rail",
                asset_class="all",
                row_order=6,
            ),
            _direct_damage_part(
                cyclone_metrics,
                "power_ead_total",
                hazard="tropical_cyclone",
                model="storm",
                epoch=2020,
                infrastructure_type="power",
                asset_class="all",
                row_order=7,
            ),
        ]
    )
    return _finalize_card_output(
        config,
        admin_regions,
        DIRECT_DAMAGE_CARD,
        pd.concat(parts, ignore_index=True),
    )


def assemble_risk_card_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    population_metrics: pd.DataFrame,
    capital_stock_metrics: pd.DataFrame,
    river_direct_metrics: pd.DataFrame,
    cyclone_direct_metrics: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Reshape the three supported Risk calculations into card tables."""
    return {
        POPULATION_CARD: _format_population_card_metrics(
            config,
            admin_regions,
            population_metrics,
        ),
        CAPITAL_STOCK_CARD: _format_capital_stock_card_metrics(
            config,
            admin_regions,
            capital_stock_metrics,
        ),
        DIRECT_DAMAGE_CARD: _format_direct_damage_card_metrics(
            config,
            admin_regions,
            river_direct_metrics,
            cyclone_direct_metrics,
        ),
    }


def build_risk_card_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    """Calculate and build the three supported downloadable Risk cards."""
    if admin_regions is None:
        admin_regions = load_admin_boundaries(config)
    river_run = config.risk_run("river_flood_jrc_baseline")
    cyclone_run = config.risk_run("tropical_cyclone_storm_baseline_2020")
    return assemble_risk_card_metrics(
        config,
        admin_regions,
        build_population_risk_metrics(config, admin_regions, river_run),
        build_capital_stock_risk_metrics(config, admin_regions, river_run),
        build_direct_network_risk_metrics(
            config,
            admin_regions,
            river_run,
        ),
        build_direct_network_risk_metrics(
            config,
            admin_regions,
            cyclone_run,
        ),
    )


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
