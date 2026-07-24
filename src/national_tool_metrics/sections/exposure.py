from __future__ import annotations

import geopandas as gpd
import pandas as pd

from ..boundaries import load_admin_boundaries
from ..config import PipelineConfig
from ..outputs import build_identifier_frame, merge_metric_tables
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
        hazard="none",
        scenario="baseline",
        model_run="baseline_inputs",
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
