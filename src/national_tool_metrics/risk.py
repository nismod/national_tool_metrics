from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd

from .utils import (
    finalize_card_output,
    metric_rows,
    line_ead_by_admin,
    load_admin_boundaries,
    PipelineConfig,
    read_gpkg_attributes,
    require_reconciliation,
    RiskRunConfig,
    validate_admin_reference,
    validate_columns,
    validate_unique,
)


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
        map_source = validate_admin_reference(
            map_source,
            admin_regions,
            map_label,
            allow_single_admin_id=config.country.admin_level == "adm0",
            repeated_ids=True,
        )

        groups = set(map_source["population_group"].dropna().astype(str))
        missing_groups = sorted(expected_groups.difference(groups))
        extra_groups = sorted(groups.difference(expected_groups))
        if missing_groups or extra_groups:
            raise ValueError(
                f"{map_label} groups do not match the expected groups. "
                f"Missing: {missing_groups}; extra: {extra_groups}"
            )

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

        require_reconciliation(
            map_metrics,
            f"{prefix}_total",
            [f"{prefix}_female", f"{prefix}_male"],
            f"{map_label} sex groups",
        )
        require_reconciliation(
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
        require_reconciliation(
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
                "shapeName",
                *CAPITAL_STOCK_COMPONENT_TOKENS,
            },
            map_label,
        )
        source = validate_admin_reference(
            source,
            admin_regions,
            map_label,
            allow_single_admin_id=(config.country.admin_level == "adm0"),
        )
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
        require_reconciliation(
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
        require_reconciliation(
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


def _population_risk_rows(metrics: pd.DataFrame) -> pd.DataFrame:
    groups = [
        ("demographics", group, source) for group, source in RISK_DEMOGRAPHIC_GROUP_METRICS.items()
    ] + [("wealth", group, source) for group, source in RISK_WEALTH_GROUP_METRICS.items()]
    groups.append(("wealth", "bottom_40", None))
    rows = []
    for layer, group, source in groups:
        for risk_map, prefix in POPULATION_RISK_MAP_PREFIXES.items():
            metric, unit = _population_risk_metric(risk_map)
            values = (
                metrics[f"{prefix}_wealth_q1"] + metrics[f"{prefix}_wealth_q2"]
                if source is None else f"{prefix}_{source}"
            )
            rows.append((
                values, dict(population_layer=layer, population_group=group, risk_metric=metric, unit=unit),
            ))
    return metric_rows(
        metrics, rows, risk_subsection="socioeconomic", hazard="river_flood", model="jrc", scenario="baseline",
    )


def _capital_stock_risk_rows(metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sector in RISK_CAPITAL_STOCK_SECTORS:
        for risk_map, prefix in CAPITAL_STOCK_RISK_MAP_PREFIXES.items():
            metric, unit = _capital_stock_risk_metric(risk_map)
            rows.append((f"{prefix}_{sector}", dict(sector=sector, risk_metric=metric, unit=unit)))
    return metric_rows(
        metrics, rows, risk_subsection="socioeconomic", hazard="river_flood", model="jrc", scenario="baseline",
    )


def _direct_damage_rows(river: pd.DataFrame, cyclone: pd.DataFrame) -> pd.DataFrame:
    common = dict(risk_subsection="infrastructure_networks", scenario="baseline",
                  metric="direct_damage", unit="usd_per_year")
    river_specs = [
        ("road_ead_total", "road", "all"),
        *((f"road_ead_{road_class}", "road", road_class) for road_class in RISK_ROAD_CLASSES),
        ("rail_ead_total", "rail", "all"),
    ]
    river_rows = metric_rows(
        river,
        [(river.get(column, 0.0), dict(infrastructure_type=kind, asset_class=asset_class))
         for column, kind, asset_class in river_specs],
        **common, hazard="river_flood", model="jrc", epoch=pd.NA,
    )
    cyclone_rows = metric_rows(
        cyclone, [(cyclone.get("power_ead_total", 0.0), {})],
        **common, hazard="tropical_cyclone", model="storm", epoch=2020,
        infrastructure_type="power", asset_class="all",
    )
    cyclone_rows["_row_order"] += len(river_specs)
    return pd.concat([river_rows, cyclone_rows], ignore_index=True)


def assemble_risk_card_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    population_metrics: pd.DataFrame,
    capital_stock_metrics: pd.DataFrame,
    river_direct_metrics: pd.DataFrame,
    cyclone_direct_metrics: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Reshape the three supported Risk calculations into card tables."""
    cards = {
        POPULATION_CARD: _population_risk_rows(population_metrics),
        CAPITAL_STOCK_CARD: _capital_stock_risk_rows(capital_stock_metrics),
        DIRECT_DAMAGE_CARD: _direct_damage_rows(river_direct_metrics, cyclone_direct_metrics),
    }
    return {
        card: finalize_card_output(
            rows, config, admin_regions, "risk", card, RISK_CARD_DIMENSIONS[card],
            optional_dimensions=RISK_CARD_OPTIONAL_DIMENSIONS[card],
        )
        for card, rows in cards.items()
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
