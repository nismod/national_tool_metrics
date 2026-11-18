from __future__ import annotations

import warnings

import geopandas as gpd
import pandas as pd

from .utils import (
    finalize_card_output,
    metric_rows,
    load_admin_boundaries,
    network_length_by_admin,
    PipelineConfig,
    read_admin_summary_csv,
    zonal_raster_sum,
)


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
FACILITY_CARDS = frozenset({HEALTHCARE_FACILITIES_CARD, EDUCATIONAL_FACILITIES_CARD})

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
    """Build facility counts, retaining numeric no-data for absent files.

    Missing files leave the corresponding count and derived rates as NaN.
    Available summaries retain the existing zero-fill for unmatched regions.
    """
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
        if not summary_path.exists():
            warnings.warn(
                f"Facility summary not found: {summary_path}. "
                f"Recording {metric_name} as no data (blank CSV values).",
                stacklevel=2,
            )
            metrics[metric_name] = float("nan")
            continue
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
        metrics[metric_name] = metrics[metric_name].fillna(0)
    return metrics


def _facility_rows(
    facilities: pd.DataFrame, population: pd.DataFrame, count_column: str,
) -> pd.DataFrame:
    inputs = facilities[["adm_id", count_column]].merge(
        population[["adm_id", *DEMOGRAPHIC_GROUP_METRICS.values()]],
        on="adm_id", how="left", validate="one_to_one",
    )
    measures = [(count_column, dict(metric="count", demographic_group="total", unit="facilities"))]
    for group, source in DEMOGRAPHIC_GROUP_METRICS.items():
        denominator = inputs[source].where(inputs[source] != 0)
        measures.append((
            inputs[count_column] / denominator * 100_000,
            dict(metric="per_100k", demographic_group=group, unit="facilities_per_100k_people"),
        ))
    return metric_rows(inputs, measures)


def assemble_exposure_card_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    population_metrics: pd.DataFrame,
    capital_stock_metrics: pd.DataFrame,
    network_metrics: pd.DataFrame,
    facility_metrics: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Reshape calculated Exposure metrics into seven card tables."""
    total = population_metrics["pop_total"].where(population_metrics["pop_total"] != 0)
    population_rows = []
    for group, source in DEMOGRAPHIC_GROUP_METRICS.items():
        population_rows.extend([
            (source, dict(demographic_group=group, display_mode="absolute", unit="people")),
            (population_metrics[source] / total * 100,
             dict(demographic_group=group, display_mode="percentage", unit="percent")),
        ])

    capital_total = capital_stock_metrics[list(CAPITAL_STOCK_SECTOR_METRICS.values())].sum(axis=1)
    sectors = {"total": capital_total, **CAPITAL_STOCK_SECTOR_METRICS}
    no_roads = pd.Series(0.0, index=network_metrics.index)
    roads = {
        road_class: network_metrics.get(f"road_length_{road_class}_km", no_roads)
        for road_class in ROAD_CLASSES
    }
    road_classes = {"all": sum(roads.values(), no_roads), **roads}

    cards = {
        POPULATION_CARD: metric_rows(population_metrics, population_rows),
        CAPITAL_STOCK_CARD: metric_rows(
            capital_stock_metrics,
            [(values, dict(sector=sector)) for sector, values in sectors.items()],
            unit="usd",
        ),
        ROADS_CARD: metric_rows(
            network_metrics,
            [(values, dict(road_class=road_class)) for road_class, values in road_classes.items()],
            unit="km",
        ),
        RAIL_CARD: metric_rows(network_metrics, [("rail_length_km", {})], unit="km"),
        POWER_CARD: metric_rows(network_metrics, [("power_transmission_length_km", {})], unit="km"),
        HEALTHCARE_FACILITIES_CARD: _facility_rows(
            facility_metrics, population_metrics, "gov_hospitals_count",
        ),
        EDUCATIONAL_FACILITIES_CARD: _facility_rows(
            facility_metrics, population_metrics, "gov_schools_count",
        ),
    }
    return {
        card: finalize_card_output(
            rows, config, admin_regions, "exposure", card, EXPOSURE_CARD_DIMENSIONS[card],
            allow_empty_values=card in FACILITY_CARDS,
        )
        for card, rows in cards.items()
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
