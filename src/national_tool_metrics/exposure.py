from __future__ import annotations

import warnings

import geopandas as gpd
import pandas as pd

from .utils import (
    build_selected_cards,
    metric_rows,
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
_FACILITY_TYPES = {HEALTHCARE_FACILITIES_CARD: "hospitals", EDUCATIONAL_FACILITIES_CARD: "schools"}
FACILITY_CARDS = frozenset(_FACILITY_TYPES)
_NETWORKS = {
    ROADS_CARD: ("road_network", "road_length", "asset_type"),
    RAIL_CARD: ("rail_network", "rail_length", None),
    POWER_CARD: ("power_network", "power_transmission_length", None),
}

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
    *,
    cards: tuple[str, ...] = tuple(_NETWORKS),
) -> pd.DataFrame:
    """Build network lengths for the requested Exposure cards."""
    metrics = admin_regions[["adm_id"]].copy()
    for card in cards:
        source, prefix, group = _NETWORKS[card]
        lengths = network_length_by_admin(
            config.source(source), admin_regions, group_column=group, metric_prefix=prefix,
        )
        metrics = metrics.merge(lengths, on="adm_id", how="left", validate="one_to_one")
    lengths = metrics.columns.drop("adm_id")
    metrics[lengths] = metrics[lengths].fillna(0)
    return metrics


def build_facility_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    *,
    cards: tuple[str, ...] = tuple(_FACILITY_TYPES),
) -> pd.DataFrame:
    """Build facility counts, retaining numeric no-data for absent files.

    Missing files leave the corresponding count and derived rates as NaN.
    Available summaries retain the existing zero-fill for unmatched regions.
    """
    directory = config.source("facility_dir")
    admin_level = config.country.admin_level.upper()
    country_iso3 = config.country.iso3
    metrics = admin_regions[["adm_id"]].copy()
    for card in cards:
        facility = _FACILITY_TYPES[card]
        metric_name = f"gov_{facility}_count"
        summary_path = directory / f"building_{facility}_gov_summary_{admin_level}__{country_iso3}.csv"
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


def _population_rows(population: pd.DataFrame) -> pd.DataFrame:
    total = population["pop_total"].where(population["pop_total"] != 0)
    measures = []
    for group, source in DEMOGRAPHIC_GROUP_METRICS.items():
        measures.extend([
            (source, dict(demographic_group=group, display_mode="absolute", unit="people")),
            (population[source] / total * 100,
             dict(demographic_group=group, display_mode="percentage", unit="percent")),
        ])
    return metric_rows(population, measures)


def _capital_stock_rows(capital_stock: pd.DataFrame) -> pd.DataFrame:
    total = capital_stock[list(CAPITAL_STOCK_SECTOR_METRICS.values())].sum(axis=1)
    sectors = {"total": total, **CAPITAL_STOCK_SECTOR_METRICS}
    return metric_rows(
        capital_stock, [(values, dict(sector=sector)) for sector, values in sectors.items()],
        unit="usd",
    )


def _roads_rows(network: pd.DataFrame) -> pd.DataFrame:
    no_roads = pd.Series(0.0, index=network.index)
    roads = {
        road_class: network.get(f"road_length_{road_class}_km", no_roads)
        for road_class in ROAD_CLASSES
    }
    road_classes = {"all": sum(roads.values(), no_roads), **roads}
    return metric_rows(
        network, [(values, dict(road_class=road_class)) for road_class, values in road_classes.items()],
        unit="km",
    )


def build_exposure_card_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    """Build the selected downloadable Exposure card tables."""
    population_metrics = None

    def population(regions: gpd.GeoDataFrame) -> pd.DataFrame:
        nonlocal population_metrics
        if population_metrics is None:
            population_metrics = build_population_metrics(config, regions)
        return population_metrics

    def network_rows(regions: gpd.GeoDataFrame, card: str) -> pd.DataFrame:
        lengths = build_network_metrics(config, regions, cards=(card,))
        if card == ROADS_CARD:
            return _roads_rows(lengths)
        _, prefix, _ = _NETWORKS[card]
        return metric_rows(lengths, [(f"{prefix}_km", {})], unit="km")

    def facility_rows(regions: gpd.GeoDataFrame, card: str) -> pd.DataFrame:
        counts = build_facility_metrics(config, regions, cards=(card,))
        return _facility_rows(counts, population(regions), f"gov_{_FACILITY_TYPES[card]}_count")

    return build_selected_cards(
        config, "exposure", EXPOSURE_CARD_DIMENSIONS,
        {
            POPULATION_CARD: lambda regions: _population_rows(population(regions)),
            CAPITAL_STOCK_CARD: lambda regions: _capital_stock_rows(build_capital_stock_metrics(config, regions)),
            ROADS_CARD: lambda regions: network_rows(regions, ROADS_CARD),
            RAIL_CARD: lambda regions: network_rows(regions, RAIL_CARD),
            POWER_CARD: lambda regions: network_rows(regions, POWER_CARD),
            HEALTHCARE_FACILITIES_CARD: lambda regions: facility_rows(regions, HEALTHCARE_FACILITIES_CARD),
            EDUCATIONAL_FACILITIES_CARD: lambda regions: facility_rows(regions, EDUCATIONAL_FACILITIES_CARD),
        },
        admin_regions,
        allow_empty_value_cards=FACILITY_CARDS,
    )
