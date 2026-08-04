from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from affine import Affine
from pyproj import CRS as PyprojCRS
from rasterio.crs import CRS
from rasterio.features import geometry_mask
from rasterio.windows import Window
from rasterio.windows import transform as window_transform
from shapely.geometry import mapping

from ..boundaries import load_admin_boundaries
from ..config import PipelineConfig
from ..outputs import (
    build_identifier_frame,
    merge_metric_tables,
    validate_section_output,
)
from ..raster import raster_window_cell_areas_km2


RIVER_FLOOD_RETURN_PERIODS = (10, 20, 50, 75, 100, 200, 500)
RIVER_FLOOD_MODEL_RUN = "jrc_river_flood_baseline"


@dataclass(frozen=True)
class _RasterGrid:
    crs: CRS
    transform: Affine
    width: int
    height: int


def _require_raster(directory: Path, iso3: str, return_period: int) -> Path:
    path = directory / f"{iso3}_jrc-flood_RP{return_period}.tif"
    if not path.is_file():
        raise FileNotFoundError(f"Required river-flood raster not found: {path}")
    return path


def _validate_admin_regions(admin_regions: gpd.GeoDataFrame) -> None:
    if admin_regions.crs is None:
        raise ValueError("Administrative regions must have a CRS")
    if admin_regions.empty:
        raise ValueError("Administrative regions contain no rows")
    if admin_regions["adm_id"].duplicated().any():
        raise ValueError("Administrative regions contain duplicate IDs")
    if admin_regions.geometry.isna().any() or admin_regions.geometry.is_empty.any():
        raise ValueError("Administrative regions contain empty geometries")


def _grid_from_source(source: rasterio.io.DatasetReader) -> _RasterGrid:
    if source.crs is None:
        raise ValueError(f"River-flood raster has no CRS: {source.name}")
    if source.transform.b != 0 or source.transform.d != 0:
        raise ValueError(f"Rotated river-flood rasters are not supported: {source.name}")
    return _RasterGrid(
        crs=source.crs,
        transform=source.transform,
        width=source.width,
        height=source.height,
    )


def _validate_matching_grid(
    source: rasterio.io.DatasetReader,
    reference: _RasterGrid,
) -> None:
    if source.crs != reference.crs:
        raise ValueError(f"River-flood raster CRS does not match: {source.name}")
    if source.width != reference.width or source.height != reference.height:
        raise ValueError(f"River-flood raster shape does not match: {source.name}")
    if not source.transform.almost_equals(reference.transform):
        raise ValueError(f"River-flood raster grid does not match: {source.name}")


def _clipped_window(
    source: rasterio.io.DatasetReader,
    bounds: tuple[float, float, float, float],
) -> Window:
    left, bottom, right, top = bounds
    inverse = ~source.transform
    first_col, first_row = inverse * (left, top)
    last_col, last_row = inverse * (right, bottom)
    col_start = max(0, floor(min(first_col, last_col)))
    row_start = max(0, floor(min(first_row, last_row)))
    col_stop = min(source.width, ceil(max(first_col, last_col)))
    row_stop = min(source.height, ceil(max(first_row, last_row)))
    if col_stop <= col_start or row_stop <= row_start:
        raise ValueError(f"Administrative region does not overlap {source.name}")
    return Window(
        col_off=col_start,
        row_off=row_start,
        width=col_stop - col_start,
        height=row_stop - row_start,
    )


def _admin_areas_km2(
    admin_regions: gpd.GeoDataFrame,
    raster_crs: CRS,
) -> np.ndarray:
    regions = admin_regions.to_crs(raster_crs)
    crs = PyprojCRS.from_user_input(raster_crs)
    if crs.is_projected and crs.axis_info:
        unit_factor = crs.axis_info[0].unit_conversion_factor
        areas = (
            regions.geometry.area.to_numpy(dtype="float64")
            * unit_factor**2
            / 1_000_000
        )
    elif crs.is_geographic:
        geod = crs.get_geod()
        areas = np.asarray(
            [
                abs(geod.geometry_area_perimeter(geometry)[0]) / 1_000_000
                for geometry in regions.geometry
            ],
            dtype="float64",
        )
    else:
        raise ValueError(f"Cannot calculate administrative areas in {crs}")
    if not np.isfinite(areas).all() or (areas <= 0).any():
        raise ValueError("Administrative regions contain invalid areas")
    return areas


def _weighted_quantile(
    values: np.ndarray,
    weights: np.ndarray,
    quantile: float,
) -> float:
    if values.size == 0 or weights.size != values.size:
        raise ValueError("Weighted quantile requires matching non-empty arrays")
    if not 0 <= quantile <= 1:
        raise ValueError("Quantile must be between zero and one")
    order = np.argsort(values, kind="stable")
    sorted_values = values[order]
    sorted_weights = weights[order]
    cumulative_weights = np.cumsum(sorted_weights)
    threshold = quantile * cumulative_weights[-1]
    index = int(np.searchsorted(cumulative_weights, threshold, side="left"))
    return float(sorted_values[min(index, sorted_values.size - 1)])


def _summarize_admin_raster(
    source: rasterio.io.DatasetReader,
    regions: gpd.GeoDataFrame,
    admin_areas_km2: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    flooded_areas = np.zeros(len(regions), dtype="float64")
    flooded_shares = np.zeros(len(regions), dtype="float64")
    mean_depths = np.zeros(len(regions), dtype="float64")
    p90_depths = np.zeros(len(regions), dtype="float64")

    for position, geometry in enumerate(regions.geometry):
        window = _clipped_window(source, tuple(geometry.bounds))
        transform = window_transform(window, source.transform)
        depths = source.read(1, window=window)
        inside = geometry_mask(
            [mapping(geometry)],
            out_shape=depths.shape,
            transform=transform,
            invert=True,
            all_touched=False,
        )
        valid = inside & np.isfinite(depths) & (depths > 0)
        if source.nodata is not None and np.isfinite(source.nodata):
            valid &= depths != source.nodata
        if not valid.any():
            continue

        cell_areas = raster_window_cell_areas_km2(source, window)
        weights = cell_areas[valid]
        values = depths[valid].astype("float64")
        flooded_area = float(weights.sum())
        flooded_areas[position] = flooded_area
        flooded_shares[position] = flooded_area / admin_areas_km2[position] * 100
        mean_depths[position] = float(np.average(values, weights=weights))
        p90_depths[position] = _weighted_quantile(values, weights, 0.9)

    return flooded_areas, flooded_shares, mean_depths, p90_depths


def _validate_river_flood_metrics(metrics: pd.DataFrame) -> None:
    metric_values = metrics.drop(columns="adm_id").to_numpy(dtype="float64")
    if not np.isfinite(metric_values).all() or (metric_values < 0).any():
        raise ValueError("River-flood hazard metrics contain invalid values")

    share_columns = [
        f"flooded_area_rp{return_period}_pct_admin"
        for return_period in RIVER_FLOOD_RETURN_PERIODS
    ]
    if (metrics[share_columns].to_numpy(dtype="float64") > 100.5).any():
        raise ValueError("River-flood area exceeds administrative-region area")

    area_columns = [
        f"flooded_area_rp{return_period}_km2"
        for return_period in RIVER_FLOOD_RETURN_PERIODS
    ]
    area_values = metrics[area_columns].to_numpy(dtype="float64")
    decreases = np.diff(area_values, axis=1) < -0.01
    if decreases.any():
        row, period_index = np.argwhere(decreases)[0]
        raise ValueError(
            "River-flood extent decreases between return periods for admin "
            f"{metrics.iloc[row]['adm_id']}: "
            f"RP{RIVER_FLOOD_RETURN_PERIODS[period_index]} to "
            f"RP{RIVER_FLOOD_RETURN_PERIODS[period_index + 1]}"
        )


def build_river_flood_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """Summarize JRC flood extent and depth for seven return periods."""
    _validate_admin_regions(admin_regions)
    directory = config.source("river_flood_hazard_dir")
    metrics = admin_regions[["adm_id"]].copy()
    reference_path = _require_raster(
        directory,
        config.country.iso3,
        RIVER_FLOOD_RETURN_PERIODS[0],
    )
    with rasterio.open(reference_path) as reference_source:
        reference_grid = _grid_from_source(reference_source)
    admin_areas = _admin_areas_km2(admin_regions, reference_grid.crs)

    for return_period in RIVER_FLOOD_RETURN_PERIODS:
        path = _require_raster(
            directory,
            config.country.iso3,
            return_period,
        )
        with rasterio.open(path) as source:
            _validate_matching_grid(source, reference_grid)
            regions = admin_regions.to_crs(source.crs)
            area, share, mean_depth, p90_depth = _summarize_admin_raster(
                source,
                regions,
                admin_areas,
            )

        metrics[f"flooded_area_rp{return_period}_km2"] = area
        metrics[f"flooded_area_rp{return_period}_pct_admin"] = share
        metrics[f"flood_depth_mean_rp{return_period}_m"] = mean_depth
        metrics[f"flood_depth_p90_rp{return_period}_m"] = p90_depth

    _validate_river_flood_metrics(metrics)
    return metrics


def assemble_hazard_run_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    metric_tables: list[pd.DataFrame],
    hazard: str,
    scenario: str,
    model_run: str,
) -> pd.DataFrame:
    """Add standard identifiers to one hazard run's metric tables."""
    identifiers = build_identifier_frame(
        admin_regions,
        config,
        section="hazard",
        hazard=hazard,
        scenario=scenario,
        model_run=model_run,
    )
    output = merge_metric_tables(identifiers, metric_tables)
    validate_section_output(output, "hazard")
    return output


def build_hazard_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame | None = None,
) -> pd.DataFrame:
    """Build the currently implemented Hazard runs without writing a CSV."""
    if admin_regions is None:
        admin_regions = load_admin_boundaries(config)
    river_flood_metrics = build_river_flood_metrics(config, admin_regions)
    return assemble_hazard_run_metrics(
        config,
        admin_regions,
        [river_flood_metrics],
        hazard="river_flood",
        scenario="baseline",
        model_run=RIVER_FLOOD_MODEL_RUN,
    )
