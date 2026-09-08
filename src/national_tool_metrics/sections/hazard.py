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
from shapely.geometry import box, mapping

from ..boundaries import load_admin_boundaries
from ..config import PipelineConfig
from ..outputs import (
    CARD_IDENTIFIER_COLUMNS,
    build_card_identifier_frame,
    build_identifier_frame,
    merge_metric_tables,
    namespace_metric_table,
    validate_card_output,
    validate_section_output,
)
from ..raster import raster_window_cell_areas_km2


RIVER_FLOOD_RETURN_PERIODS = (10, 20, 50, 75, 100, 200, 500)
RIVER_FLOOD_METRIC_NAMESPACE = "river_flood_jrc_baseline"
TROPICAL_CYCLONE_RETURN_PERIODS = (10, 20, 50, 100, 200, 500, 1000)
TROPICAL_CYCLONE_METRIC_NAMESPACE = "tropical_cyclone_storm_baseline_2020"
TROPICAL_CYCLONE_CATEGORY_THRESHOLDS_MS = {
    "tropical_storm_plus": 18.0,
    "cat1plus": 29.0,
    "cat2plus": 37.6,
    "cat3plus": 43.4,
    "cat4plus": 51.1,
    "cat5plus": 61.6,
}

RIVER_FLOOD_CARD = "river_flooding"
TROPICAL_CYCLONE_CARD = "tropical_cyclone_wind"
RIVER_FLOOD_CARD_DIMENSIONS = (
    "hazard",
    "model",
    "scenario",
    "return_period_years",
    "metric",
    "unit",
)
TROPICAL_CYCLONE_CARD_DIMENSIONS = (
    "hazard",
    "model",
    "scenario",
    "epoch",
    "return_period_years",
    "wind_threshold",
    "wind_threshold_ms",
    "display_mode",
    "metric",
    "unit",
)
HAZARD_CARD_DIMENSIONS = {
    RIVER_FLOOD_CARD: RIVER_FLOOD_CARD_DIMENSIONS,
    TROPICAL_CYCLONE_CARD: TROPICAL_CYCLONE_CARD_DIMENSIONS,
}


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


def _require_tropical_cyclone_raster(
    directory: Path,
    return_period: int,
) -> Path:
    path = directory / (
        "STORM_FIXED_RETURN_PERIODS_constant_"
        f"{return_period}_YR_RP.tif"
    )
    if not path.is_file():
        raise FileNotFoundError(
            f"Required tropical-cyclone raster not found: {path}"
        )
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


def _summarize_admin_wind_threshold_areas(
    source: rasterio.io.DatasetReader,
    region_weights: list[tuple[Window, np.ndarray] | None],
    admin_areas_km2: np.ndarray,
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    summaries = {
        category: (
            np.zeros(len(region_weights), dtype="float64"),
            np.zeros(len(region_weights), dtype="float64"),
        )
        for category in TROPICAL_CYCLONE_CATEGORY_THRESHOLDS_MS
    }

    for position, weighted_window in enumerate(region_weights):
        if weighted_window is None:
            continue
        window, cell_areas = weighted_window
        wind_speeds = source.read(1, window=window)
        valid = (cell_areas > 0) & np.isfinite(wind_speeds)
        if source.nodata is not None and np.isfinite(source.nodata):
            valid &= wind_speeds != source.nodata
        if not valid.any():
            continue

        for category, threshold in (
            TROPICAL_CYCLONE_CATEGORY_THRESHOLDS_MS.items()
        ):
            above_threshold = valid & (wind_speeds >= threshold)
            if not above_threshold.any():
                continue
            area = min(
                float(cell_areas[above_threshold].sum()),
                float(admin_areas_km2[position]),
            )
            areas, shares = summaries[category]
            areas[position] = area
            shares[position] = area / admin_areas_km2[position] * 100

    return summaries


def _admin_raster_intersection_weights(
    source: rasterio.io.DatasetReader,
    regions: gpd.GeoDataFrame,
) -> list[tuple[Window, np.ndarray] | None]:
    """Calculate exact raster-cell area inside each administrative region."""
    if source.crs is None:
        raise ValueError(f"Tropical-cyclone raster has no CRS: {source.name}")
    crs = PyprojCRS.from_user_input(source.crs)
    if crs.is_projected and crs.axis_info:
        projected_area_factor = (
            crs.axis_info[0].unit_conversion_factor**2 / 1_000_000
        )
        geod = None
    elif crs.is_geographic:
        projected_area_factor = None
        geod = crs.get_geod()
    else:
        raise ValueError(f"Cannot calculate raster intersections in {crs}")

    weighted_windows: list[tuple[Window, np.ndarray] | None] = []
    for geometry in regions.geometry:
        try:
            window = _clipped_window(source, tuple(geometry.bounds))
        except ValueError:
            weighted_windows.append(None)
            continue
        transform = window_transform(window, source.transform)
        candidates = geometry_mask(
            [mapping(geometry)],
            out_shape=(int(window.height), int(window.width)),
            transform=transform,
            invert=True,
            all_touched=True,
        )
        intersection_areas = np.zeros(candidates.shape, dtype="float64")
        for row, column in np.argwhere(candidates):
            first_x, first_y = transform * (int(column), int(row))
            second_x, second_y = transform * (
                int(column) + 1,
                int(row) + 1,
            )
            cell = box(
                min(first_x, second_x),
                min(first_y, second_y),
                max(first_x, second_x),
                max(first_y, second_y),
            )
            intersection = geometry.intersection(cell)
            if intersection.is_empty:
                continue
            if projected_area_factor is not None:
                area = intersection.area * projected_area_factor
            else:
                geodesic_area = geod.geometry_area_perimeter(intersection)[0]
                area = abs(geodesic_area) / 1_000_000
            intersection_areas[row, column] = area
        weighted_windows.append((window, intersection_areas))

    return weighted_windows


def _validate_tropical_cyclone_metrics(metrics: pd.DataFrame) -> None:
    metric_values = metrics.drop(columns="adm_id").to_numpy(dtype="float64")
    if not np.isfinite(metric_values).all() or (metric_values < 0).any():
        raise ValueError("Tropical-cyclone hazard metrics contain invalid values")

    categories = tuple(TROPICAL_CYCLONE_CATEGORY_THRESHOLDS_MS)
    for return_period in TROPICAL_CYCLONE_RETURN_PERIODS:
        area_columns = [
            f"wind_area_{category}_rp{return_period}_km2"
            for category in categories
        ]
        share_columns = [
            f"wind_area_{category}_rp{return_period}_pct_admin"
            for category in categories
        ]
        if (metrics[share_columns].to_numpy(dtype="float64") > 100.5).any():
            raise ValueError(
                "Tropical-cyclone wind area exceeds administrative-region area"
            )
        category_increases = np.diff(
            metrics[area_columns].to_numpy(dtype="float64"),
            axis=1,
        ) > 0.01
        if category_increases.any():
            row, category_index = np.argwhere(category_increases)[0]
            raise ValueError(
                "Tropical-cyclone wind area increases between category "
                f"thresholds for admin {metrics.iloc[row]['adm_id']}: "
                f"{categories[category_index]} to "
                f"{categories[category_index + 1]} at RP{return_period}"
            )

    for category in categories:
        area_columns = [
            f"wind_area_{category}_rp{return_period}_km2"
            for return_period in TROPICAL_CYCLONE_RETURN_PERIODS
        ]
        return_period_decreases = np.diff(
            metrics[area_columns].to_numpy(dtype="float64"),
            axis=1,
        ) < -0.01
        if return_period_decreases.any():
            row, period_index = np.argwhere(return_period_decreases)[0]
            raise ValueError(
                "Tropical-cyclone wind area decreases between return periods "
                f"for admin {metrics.iloc[row]['adm_id']} and {category}: "
                f"RP{TROPICAL_CYCLONE_RETURN_PERIODS[period_index]} to "
                f"RP{TROPICAL_CYCLONE_RETURN_PERIODS[period_index + 1]}"
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


def build_tropical_cyclone_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """Summarize area exceeding STORM wind-category thresholds."""
    _validate_admin_regions(admin_regions)
    directory = config.source("tropical_cyclone_hazard_dir")
    metrics = admin_regions[["adm_id"]].copy()
    reference_path = _require_tropical_cyclone_raster(
        directory,
        TROPICAL_CYCLONE_RETURN_PERIODS[0],
    )
    with rasterio.open(reference_path) as reference_source:
        reference_grid = _grid_from_source(reference_source)
        regions = admin_regions.to_crs(reference_source.crs)
        region_weights = _admin_raster_intersection_weights(
            reference_source,
            regions,
        )
    admin_areas = _admin_areas_km2(admin_regions, reference_grid.crs)

    for return_period in TROPICAL_CYCLONE_RETURN_PERIODS:
        path = _require_tropical_cyclone_raster(directory, return_period)
        with rasterio.open(path) as source:
            _validate_matching_grid(source, reference_grid)
            summaries = _summarize_admin_wind_threshold_areas(
                source,
                region_weights,
                admin_areas,
            )

        for category, (area, share) in summaries.items():
            metrics[
                f"wind_area_{category}_rp{return_period}_km2"
            ] = area
            metrics[
                f"wind_area_{category}_rp{return_period}_pct_admin"
            ] = share

    _validate_tropical_cyclone_metrics(metrics)
    return metrics


def _format_river_flood_card_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    metrics: pd.DataFrame,
) -> pd.DataFrame:
    metric_specs = (
        ("flooded_area", "km2", "flooded_area_rp{return_period}_km2"),
        (
            "area_flooded_percentage",
            "percent",
            "flooded_area_rp{return_period}_pct_admin",
        ),
        (
            "mean_flood_depth",
            "m",
            "flood_depth_mean_rp{return_period}_m",
        ),
        (
            "p90_flood_depth",
            "m",
            "flood_depth_p90_rp{return_period}_m",
        ),
    )
    parts: list[pd.DataFrame] = []
    for return_period in RIVER_FLOOD_RETURN_PERIODS:
        for metric_order, (metric, unit, template) in enumerate(metric_specs):
            source_column = template.format(return_period=return_period)
            part = metrics[["adm_id", source_column]].rename(
                columns={source_column: "value"}
            )
            part["hazard"] = "river_flood"
            part["model"] = "jrc"
            part["scenario"] = "baseline"
            part["return_period_years"] = return_period
            part["metric"] = metric
            part["unit"] = unit
            part["_metric_order"] = metric_order
            parts.append(part)

    long_metrics = pd.concat(parts, ignore_index=True)
    long_metrics["value"] = long_metrics["value"].round(3)
    identifiers = build_card_identifier_frame(
        admin_regions,
        config,
        section="hazard",
        card=RIVER_FLOOD_CARD,
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
        ["_admin_order", "return_period_years", "_metric_order"],
        kind="stable",
    ).drop(columns=["_admin_order", "_metric_order"])
    output = output[
        [*CARD_IDENTIFIER_COLUMNS, *RIVER_FLOOD_CARD_DIMENSIONS, "value"]
    ].reset_index(drop=True)
    validate_card_output(
        output,
        "hazard",
        RIVER_FLOOD_CARD,
        RIVER_FLOOD_CARD_DIMENSIONS,
    )
    return output


def _format_tropical_cyclone_card_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    metrics: pd.DataFrame,
) -> pd.DataFrame:
    display_specs = (
        ("area", "km2", "km2"),
        ("percentage", "percent", "pct_admin"),
    )
    parts: list[pd.DataFrame] = []
    for return_period in TROPICAL_CYCLONE_RETURN_PERIODS:
        for threshold_order, (threshold, threshold_ms) in enumerate(
            TROPICAL_CYCLONE_CATEGORY_THRESHOLDS_MS.items()
        ):
            for display_order, (display_mode, unit, suffix) in enumerate(
                display_specs
            ):
                source_column = (
                    f"wind_area_{threshold}_rp{return_period}_{suffix}"
                )
                part = metrics[["adm_id", source_column]].rename(
                    columns={source_column: "value"}
                )
                part["hazard"] = "tropical_cyclone"
                part["model"] = "storm"
                part["scenario"] = "baseline"
                part["epoch"] = 2020
                part["return_period_years"] = return_period
                part["wind_threshold"] = threshold
                part["wind_threshold_ms"] = threshold_ms
                part["display_mode"] = display_mode
                part["metric"] = "wind_area"
                part["unit"] = unit
                part["_threshold_order"] = threshold_order
                part["_display_order"] = display_order
                parts.append(part)

    long_metrics = pd.concat(parts, ignore_index=True)
    long_metrics["value"] = long_metrics["value"].round(3)
    identifiers = build_card_identifier_frame(
        admin_regions,
        config,
        section="hazard",
        card=TROPICAL_CYCLONE_CARD,
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
        [
            "_admin_order",
            "return_period_years",
            "_threshold_order",
            "_display_order",
        ],
        kind="stable",
    ).drop(
        columns=["_admin_order", "_threshold_order", "_display_order"]
    )
    output = output[
        [
            *CARD_IDENTIFIER_COLUMNS,
            *TROPICAL_CYCLONE_CARD_DIMENSIONS,
            "value",
        ]
    ].reset_index(drop=True)
    validate_card_output(
        output,
        "hazard",
        TROPICAL_CYCLONE_CARD,
        TROPICAL_CYCLONE_CARD_DIMENSIONS,
    )
    return output


def build_hazard_card_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    """Build the two tidy downloadable Hazard card tables."""
    if admin_regions is None:
        admin_regions = load_admin_boundaries(config)
    river_flood_metrics = build_river_flood_metrics(config, admin_regions)
    tropical_cyclone_metrics = build_tropical_cyclone_metrics(
        config,
        admin_regions,
    )
    return {
        RIVER_FLOOD_CARD: _format_river_flood_card_metrics(
            config,
            admin_regions,
            river_flood_metrics,
        ),
        TROPICAL_CYCLONE_CARD: _format_tropical_cyclone_card_metrics(
            config,
            admin_regions,
            tropical_cyclone_metrics,
        ),
    }


def assemble_hazard_run_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    metric_tables: list[pd.DataFrame],
    metric_namespace: str,
) -> pd.DataFrame:
    """Add identifiers and namespace one hazard run's metric tables."""
    identifiers = build_identifier_frame(
        admin_regions,
        config,
        section="hazard",
    )
    namespaced_tables = [
        namespace_metric_table(metrics, metric_namespace)
        for metrics in metric_tables
    ]
    output = merge_metric_tables(identifiers, namespaced_tables)
    validate_section_output(output, "hazard")
    return output


def build_hazard_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame | None = None,
) -> pd.DataFrame:
    """Build river-flood and tropical-cyclone Hazard metrics."""
    if admin_regions is None:
        admin_regions = load_admin_boundaries(config)
    river_flood_metrics = build_river_flood_metrics(config, admin_regions)
    tropical_cyclone_metrics = build_tropical_cyclone_metrics(
        config,
        admin_regions,
    )
    identifiers = build_identifier_frame(
        admin_regions,
        config,
        section="hazard",
    )
    output = merge_metric_tables(
        identifiers,
        [
            namespace_metric_table(
                river_flood_metrics,
                RIVER_FLOOD_METRIC_NAMESPACE,
            ),
            namespace_metric_table(
                tropical_cyclone_metrics,
                TROPICAL_CYCLONE_METRIC_NAMESPACE,
            ),
        ],
    )
    validate_section_output(output, "hazard")
    return output
