from __future__ import annotations

from pathlib import Path
import re

import geopandas as gpd
import pandas as pd

from ..boundaries import load_admin_boundaries
from ..config import PipelineConfig
from ..outputs import build_identifier_frame, merge_metric_tables
from ..raster import find_single_raster, zonal_raster_sum
from ..tables import read_admin_summary_csv
from ..vector import network_length_by_admin


_AGE_SEX_RASTER_PATTERN = re.compile(
    r"^(?P<country>[a-z]{3})_(?P<sex>[fmt])_"
    r"(?P<age>\d{2})_(?P<year>\d{4})_.*\.tif$",
    re.IGNORECASE,
)

_AGE_GROUPS = {
    "pop_under_5": ("t", [0, 1]),
    "pop_school_children_5_14": ("t", [5, 10]),
    "pop_working_age_15_64": ("t", list(range(15, 65, 5))),
    "pop_older_65_plus": ("t", list(range(65, 95, 5))),
    "pop_female_childbearing_15_49": ("f", list(range(15, 50, 5))),
}


def _worldpop_inventory(
    directory: Path,
    country_iso3: str,
    year: int,
) -> pd.DataFrame:
    if not directory.is_dir():
        raise FileNotFoundError(f"WorldPop directory not found: {directory}")

    records = []
    for path in sorted(directory.glob("*.tif")):
        match = _AGE_SEX_RASTER_PATTERN.match(path.name)
        if (
            match
            and match.group("country").upper() == country_iso3.upper()
            and int(match.group("year")) == year
        ):
            records.append(
                {
                    "sex": match.group("sex").lower(),
                    "age_start": int(match.group("age")),
                    "path": path,
                }
            )

    inventory = pd.DataFrame.from_records(records)
    if inventory.empty:
        raise FileNotFoundError(
            f"No WorldPop age-sex rasters found in {directory} for "
            f"{country_iso3.upper()} {year}"
        )

    duplicate_bands = inventory.duplicated(["sex", "age_start"], keep=False)
    if duplicate_bands.any():
        duplicates = inventory.loc[
            duplicate_bands, ["sex", "age_start", "path"]
        ]
        raise ValueError(
            "Multiple WorldPop rasters represent the same sex/age band. "
            f"Example:\n{duplicates.head()}"
        )

    return inventory.sort_values(["sex", "age_start"]).reset_index(drop=True)


def _sum_age_group(
    inventory: pd.DataFrame,
    sex: str,
    ages: list[int],
    admin_regions: gpd.GeoDataFrame,
) -> pd.Series:
    selected = inventory[
        (inventory["sex"] == sex)
        & (inventory["age_start"].isin(ages))
    ]
    missing_ages = sorted(set(ages).difference(selected["age_start"]))
    if missing_ages:
        raise FileNotFoundError(
            f"Missing WorldPop rasters for sex={sex}, ages={missing_ages}"
        )

    total = pd.Series(0.0, index=admin_regions.index, dtype="float64")
    for raster_path in selected["path"]:
        total = total + zonal_raster_sum(raster_path, admin_regions)
    return total


def build_population_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """Build the Population card, including the agreed demographic groups."""
    worldpop_directory = config.source("worldpop_dir")
    worldpop_year = int(config.parameters["worldpop_year"])
    inventory = _worldpop_inventory(
        worldpop_directory,
        config.country.iso3,
        worldpop_year,
    )
    total_population_raster = find_single_raster(
        worldpop_directory,
        (
            f"{config.country.iso3.lower()}_pop_{worldpop_year}_*.tif"
        ),
        "WorldPop total-population raster",
    )

    metrics = admin_regions[["adm_id"]].copy()
    metrics["pop_total"] = zonal_raster_sum(
        total_population_raster,
        admin_regions,
    )

    all_ages = sorted(inventory["age_start"].unique().tolist())
    metrics["pop_female"] = _sum_age_group(
        inventory,
        "f",
        all_ages,
        admin_regions,
    )
    metrics["pop_male"] = _sum_age_group(
        inventory,
        "m",
        all_ages,
        admin_regions,
    )
    for metric_name, (sex, ages) in _AGE_GROUPS.items():
        metrics[metric_name] = _sum_age_group(
            inventory,
            sex,
            ages,
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
