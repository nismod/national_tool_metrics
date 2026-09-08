from __future__ import annotations

import geopandas as gpd
import pandas as pd

from ..boundaries import load_admin_boundaries
from ..config import PipelineConfig
from ..outputs import (
    CARD_IDENTIFIER_COLUMNS,
    build_card_identifier_frame,
    build_identifier_frame,
    merge_metric_tables,
    validate_card_output,
)
from ..raster import zonal_raster_sum
from ..tables import read_admin_summary_csv
from ..vector import network_length_by_admin


_WORLDPOP_RASTER_SUFFIXES = {
    "pop_total": "total",
    "pop_female": "female",
    "pop_male": "male",
    "pop_under_5": "children_under5",
    "pop_school_children_5_14": "school-age_5-14",
    "pop_working_age_15_64": "working-age_15-64",
    "pop_older_65_plus": "older_65plus",
    "pop_female_childbearing_15_49": "female_15-49",
}

DEMOGRAPHIC_GROUP_METRICS = {
    "total": "pop_total",
    "female": "pop_female",
    "male": "pop_male",
    "infant": "pop_under_5",
    "schoolage": "pop_school_children_5_14",
    "working": "pop_working_age_15_64",
    "childbearing": "pop_female_childbearing_15_49",
    "elderly": "pop_older_65_plus",
}

POPULATION_CARD = "population"
CAPITAL_STOCK_CARD = "capital_stock"
ROADS_CARD = "roads"
RAIL_CARD = "rail"
POWER_CARD = "power"
HEALTHCARE_FACILITIES_CARD = "healthcare_facilities"
EDUCATIONAL_FACILITIES_CARD = "educational_facilities"

POPULATION_CARD_DIMENSIONS = (
    "demographic_group",
    "display_mode",
    "unit",
)
CAPITAL_STOCK_CARD_DIMENSIONS = ("sector", "unit")
ROADS_CARD_DIMENSIONS = ("road_class", "unit")
NETWORK_CARD_DIMENSIONS = ("unit",)
FACILITIES_CARD_DIMENSIONS = ("metric", "demographic_group", "unit")
EXPOSURE_CARD_DIMENSIONS = {
    POPULATION_CARD: POPULATION_CARD_DIMENSIONS,
    CAPITAL_STOCK_CARD: CAPITAL_STOCK_CARD_DIMENSIONS,
    ROADS_CARD: ROADS_CARD_DIMENSIONS,
    RAIL_CARD: NETWORK_CARD_DIMENSIONS,
    POWER_CARD: NETWORK_CARD_DIMENSIONS,
    HEALTHCARE_FACILITIES_CARD: FACILITIES_CARD_DIMENSIONS,
    EDUCATIONAL_FACILITIES_CARD: FACILITIES_CARD_DIMENSIONS,
}

CAPITAL_STOCK_SECTOR_METRICS = {
    "residential": "capstock_residential",
    "non_residential": "capstock_non_residential",
    "infrastructure": "capstock_infrastructure",
}
ROAD_CLASSES = ("motorway", "trunk", "primary", "secondary", "tertiary")


def build_population_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """Build the Population card from pre-aggregated 90 m WorldPop rasters."""
    worldpop_directory = config.source("worldpop_dir")

    metrics = admin_regions[["adm_id"]].copy()
    for metric_name, raster_suffix in _WORLDPOP_RASTER_SUFFIXES.items():
        raster_path = worldpop_directory / (
            f"{config.country.iso3}_worldpop_{raster_suffix}.tif"
        )
        metrics[metric_name] = zonal_raster_sum(
            raster_path,
            admin_regions,
        )

    return metrics


def build_capital_stock_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """Build residential, non-residential, and infrastructure capital stock."""
    directory = config.source("capital_stock_dir")
    raster_paths = {
        "capstock_non_residential": (
            directory / f"{config.country.iso3}_nres_capstock.tif"
        ),
        "capstock_residential": (
            directory / f"{config.country.iso3}_res_capstock.tif"
        ),
        "capstock_infrastructure": (
            directory / f"{config.country.iso3}_inf_capstock.tif"
        ),
    }

    metrics = admin_regions[["adm_id"]].copy()
    for metric_name, raster_path in raster_paths.items():
        metrics[metric_name] = zonal_raster_sum(
            raster_path,
            admin_regions,
        )
    return metrics


def build_network_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """Build the Roads, Rail, and Power exposure cards."""
    road_metrics = network_length_by_admin(
        config.source("road_network"),
        admin_regions,
        group_column="asset_type",
        metric_prefix="road_length",
    )
    rail_metrics = network_length_by_admin(
        config.source("rail_network"),
        admin_regions,
        metric_prefix="rail_length",
    )
    power_metrics = network_length_by_admin(
        config.source("power_network"),
        admin_regions,
        metric_prefix="power_transmission_length",
    )

    metrics = admin_regions[["adm_id"]].copy()
    for table in (road_metrics, rail_metrics, power_metrics):
        metrics = metrics.merge(
            table,
            on="adm_id",
            how="left",
            validate="one_to_one",
        )
    numeric_columns = [
        column for column in metrics.columns if column != "adm_id"
    ]
    metrics[numeric_columns] = metrics[numeric_columns].fillna(0)
    return metrics


def build_facility_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """Build the Hospitals and Schools exposure cards."""
    directory = config.source("facility_dir")
    admin_level = config.country.admin_level.upper()
    country_iso3 = config.country.iso3
    summaries = {
        "gov_hospitals_count": directory
        / (
            f"building_hospitals_gov_summary_{admin_level}"
            f"__{country_iso3}.csv"
        ),
        "gov_schools_count": directory
        / (
            f"building_schools_gov_summary_{admin_level}"
            f"__{country_iso3}.csv"
        ),
    }

    metrics = admin_regions[["adm_id"]].copy()
    for metric_name, summary_path in summaries.items():
        summary = read_admin_summary_csv(
            summary_path,
            ["n_buildings"],
        ).rename(columns={"n_buildings": metric_name})
        metrics = metrics.merge(
            summary,
            on="adm_id",
            how="left",
            validate="one_to_one",
        )

    count_columns = [
        column for column in metrics.columns if column != "adm_id"
    ]
    metrics[count_columns] = metrics[count_columns].fillna(0)
    return metrics


def _finalize_card_output(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    card: str,
    dimensions: tuple[str, ...],
    long_metrics: pd.DataFrame,
) -> pd.DataFrame:
    identifiers = build_card_identifier_frame(
        admin_regions,
        config,
        section="exposure",
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
    validate_card_output(output, "exposure", card, dimensions)
    return output


def _format_population_card_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    metrics: pd.DataFrame,
) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    total_population = metrics["pop_total"].where(metrics["pop_total"] != 0)
    for group_order, (group, source_column) in enumerate(
        DEMOGRAPHIC_GROUP_METRICS.items()
    ):
        absolute = metrics[["adm_id", source_column]].rename(
            columns={source_column: "value"}
        )
        absolute["demographic_group"] = group
        absolute["display_mode"] = "absolute"
        absolute["unit"] = "people"
        absolute["_row_order"] = group_order * 2
        parts.append(absolute)

        percentage = metrics[["adm_id"]].copy()
        percentage["value"] = metrics[source_column] / total_population * 100
        percentage["demographic_group"] = group
        percentage["display_mode"] = "percentage"
        percentage["unit"] = "percent"
        percentage["_row_order"] = group_order * 2 + 1
        parts.append(percentage)

    return _finalize_card_output(
        config,
        admin_regions,
        POPULATION_CARD,
        POPULATION_CARD_DIMENSIONS,
        pd.concat(parts, ignore_index=True),
    )


def _format_capital_stock_card_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    metrics: pd.DataFrame,
) -> pd.DataFrame:
    component_columns = list(CAPITAL_STOCK_SECTOR_METRICS.values())
    values = {"total": metrics[component_columns].sum(axis=1)}
    values.update(
        {
            sector: metrics[source_column]
            for sector, source_column in CAPITAL_STOCK_SECTOR_METRICS.items()
        }
    )
    parts: list[pd.DataFrame] = []
    for row_order, (sector, sector_values) in enumerate(values.items()):
        part = metrics[["adm_id"]].copy()
        part["sector"] = sector
        part["unit"] = "usd"
        part["value"] = sector_values
        part["_row_order"] = row_order
        parts.append(part)
    return _finalize_card_output(
        config,
        admin_regions,
        CAPITAL_STOCK_CARD,
        CAPITAL_STOCK_CARD_DIMENSIONS,
        pd.concat(parts, ignore_index=True),
    )


def _format_roads_card_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    metrics: pd.DataFrame,
) -> pd.DataFrame:
    class_values = {
        road_class: (
            metrics[f"road_length_{road_class}_km"]
            if f"road_length_{road_class}_km" in metrics.columns
            else pd.Series(0.0, index=metrics.index)
        )
        for road_class in ROAD_CLASSES
    }
    all_road_values = pd.Series(0.0, index=metrics.index)
    for road_values in class_values.values():
        all_road_values = all_road_values + road_values
    values = {
        "all": all_road_values,
        **class_values,
    }
    parts: list[pd.DataFrame] = []
    for row_order, (road_class, road_values) in enumerate(values.items()):
        part = metrics[["adm_id"]].copy()
        part["road_class"] = road_class
        part["unit"] = "km"
        part["value"] = road_values
        part["_row_order"] = row_order
        parts.append(part)
    return _finalize_card_output(
        config,
        admin_regions,
        ROADS_CARD,
        ROADS_CARD_DIMENSIONS,
        pd.concat(parts, ignore_index=True),
    )


def _format_network_card_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    metrics: pd.DataFrame,
    card: str,
    source_column: str,
) -> pd.DataFrame:
    long_metrics = metrics[["adm_id", source_column]].rename(
        columns={source_column: "value"}
    )
    long_metrics["unit"] = "km"
    long_metrics["_row_order"] = 0
    return _finalize_card_output(
        config,
        admin_regions,
        card,
        NETWORK_CARD_DIMENSIONS,
        long_metrics,
    )


def _format_facilities_card_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    facility_metrics: pd.DataFrame,
    population_metrics: pd.DataFrame,
    card: str,
    count_column: str,
) -> pd.DataFrame:
    inputs = facility_metrics[["adm_id", count_column]].merge(
        population_metrics[["adm_id", *DEMOGRAPHIC_GROUP_METRICS.values()]],
        on="adm_id",
        how="left",
        validate="one_to_one",
    )
    count = inputs[["adm_id", count_column]].rename(
        columns={count_column: "value"}
    )
    count["metric"] = "count"
    count["demographic_group"] = "total"
    count["unit"] = "facilities"
    count["_row_order"] = 0
    parts = [count]

    for group_order, (group, population_column) in enumerate(
        DEMOGRAPHIC_GROUP_METRICS.items(),
        start=1,
    ):
        denominator = inputs[population_column].where(
            inputs[population_column] != 0
        )
        rate = inputs[["adm_id"]].copy()
        rate["value"] = inputs[count_column] / denominator * 100_000
        rate["metric"] = "per_100k"
        rate["demographic_group"] = group
        rate["unit"] = "facilities_per_100k_people"
        rate["_row_order"] = group_order
        parts.append(rate)

    return _finalize_card_output(
        config,
        admin_regions,
        card,
        FACILITIES_CARD_DIMENSIONS,
        pd.concat(parts, ignore_index=True),
    )


def assemble_exposure_card_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    population_metrics: pd.DataFrame,
    capital_stock_metrics: pd.DataFrame,
    network_metrics: pd.DataFrame,
    facility_metrics: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Reshape calculated Exposure metrics into seven card tables."""
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
        ROADS_CARD: _format_roads_card_metrics(
            config,
            admin_regions,
            network_metrics,
        ),
        RAIL_CARD: _format_network_card_metrics(
            config,
            admin_regions,
            network_metrics,
            RAIL_CARD,
            "rail_length_km",
        ),
        POWER_CARD: _format_network_card_metrics(
            config,
            admin_regions,
            network_metrics,
            POWER_CARD,
            "power_transmission_length_km",
        ),
        HEALTHCARE_FACILITIES_CARD: _format_facilities_card_metrics(
            config,
            admin_regions,
            facility_metrics,
            population_metrics,
            HEALTHCARE_FACILITIES_CARD,
            "gov_hospitals_count",
        ),
        EDUCATIONAL_FACILITIES_CARD: _format_facilities_card_metrics(
            config,
            admin_regions,
            facility_metrics,
            population_metrics,
            EDUCATIONAL_FACILITIES_CARD,
            "gov_schools_count",
        ),
    }


def build_exposure_card_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    """Calculate and build the seven downloadable Exposure card tables."""
    if admin_regions is None:
        admin_regions = load_admin_boundaries(config)
    return assemble_exposure_card_metrics(
        config,
        admin_regions,
        build_population_metrics(config, admin_regions),
        build_capital_stock_metrics(config, admin_regions),
        build_network_metrics(config, admin_regions),
        build_facility_metrics(config, admin_regions),
    )


def build_exposure_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame | None = None,
) -> pd.DataFrame:
    """Build the complete Exposure section without writing it to disk."""
    if admin_regions is None:
        admin_regions = load_admin_boundaries(config)

    identifiers = build_identifier_frame(
        admin_regions,
        config,
        section="exposure",
    )
    return merge_metric_tables(
        identifiers,
        [
            build_population_metrics(config, admin_regions),
            build_capital_stock_metrics(config, admin_regions),
            build_network_metrics(config, admin_regions),
            build_facility_metrics(config, admin_regions),
        ],
    )
