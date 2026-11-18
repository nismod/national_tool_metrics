from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor
from pathlib import Path
from typing import Iterator

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from affine import Affine
from pyproj import CRS as PyprojCRS, Geod
from rasterio.crs import CRS
from rasterio.features import rasterize
from rasterio.windows import Window
from rasterio.windows import transform as window_transform
from rasterstats import zonal_stats
from shapely.geometry import GeometryCollection, LineString, MultiLineString
from shapely.geometry.base import BaseGeometry

from .utils import (
    clipped_raster_window,
    finalize_card_output,
    metric_rows,
    load_admin_boundaries,
    PipelineConfig,
    validate_spatial_admin_regions,
)


SLOPE_FILENAME = "G_LandslideNbS_123_9s.tif"
RIVER_FILENAME = "G_PotentialNonCoastalTreeNBS_9s.tif"
MANGROVE_FILENAME = "ManRestorClass_9s.tif"
PLANTING_COST_FILENAME = "G_PlantingCost_9s.tif"
REGENERATION_COST_FILENAME = "G_RegenCost_9s.tif"
MANGROVE_PLANTING_COST_FILENAME = "ManPlantCost_9s.tif"
MANGROVE_REGENERATION_COST_FILENAME = "ManRegenCost_9s.tif"
CARBON_FILENAME = "G_CarbonBenefit_9s.tif"
BIODIVERSITY_FILENAME = "G_BioBenefit_9s.tif"

SLOPE_CLASS_NAMES = {
    1: "other",
    2: "crops",
    3: "bare_ground",
}
MANGROVE_CLASS_NAMES = {
    1: "accreting",
    2: "static_moderate_retreat",
    3: "fast_retreat",
}

URBANISATION_GROUPS = {
    "rural": {10, 11, 12, 13},
    "town": {21, 22, 23},
    "city": {30},
}

SLOPE_VEGETATION_CARD = "slope_vegetation"
MANGROVES_CARD = "mangroves"
RIVER_CATCHMENT_RESTORATION_CARD = "river_catchment_restoration"
EXISTING_FLOOD_PROTECTION_CARD = "existing_flood_protection"
RIVER_NETWORK_CONTEXT_CARD = "river_network_context"

SLOPE_VEGETATION_CARD_DIMENSIONS = (
    "adaptation_subsection",
    "land_use",
    "metric",
    "implementation_approach",
    "unit",
)
MANGROVES_CARD_DIMENSIONS = (
    "adaptation_subsection",
    "shoreline_condition",
    "metric",
    "implementation_approach",
    "unit",
)
RIVER_CATCHMENT_RESTORATION_CARD_DIMENSIONS = (
    "adaptation_subsection",
    "metric",
    "implementation_approach",
    "unit",
)
EXISTING_FLOOD_PROTECTION_CARD_DIMENSIONS = (
    "adaptation_subsection",
    "metric",
    "unit",
)
RIVER_NETWORK_CONTEXT_CARD_DIMENSIONS = (
    "adaptation_subsection",
    "urbanisation_class",
    "metric",
    "unit",
)
ADAPTATION_POTENTIAL_CARD_DIMENSIONS = {
    SLOPE_VEGETATION_CARD: SLOPE_VEGETATION_CARD_DIMENSIONS,
    MANGROVES_CARD: MANGROVES_CARD_DIMENSIONS,
    RIVER_CATCHMENT_RESTORATION_CARD: (
        RIVER_CATCHMENT_RESTORATION_CARD_DIMENSIONS
    ),
    EXISTING_FLOOD_PROTECTION_CARD: (
        EXISTING_FLOOD_PROTECTION_CARD_DIMENSIONS
    ),
    RIVER_NETWORK_CONTEXT_CARD: RIVER_NETWORK_CONTEXT_CARD_DIMENSIONS,
}
ADAPTATION_POTENTIAL_CARD_OPTIONAL_DIMENSIONS = {
    SLOPE_VEGETATION_CARD: ("implementation_approach",),
    MANGROVES_CARD: ("implementation_approach",),
    RIVER_CATCHMENT_RESTORATION_CARD: ("implementation_approach",),
    EXISTING_FLOOD_PROTECTION_CARD: (),
    RIVER_NETWORK_CONTEXT_CARD: (),
}

NBS_METRIC_ROWS = (
    ("opportunity_area", pd.NA, "km2"),
    ("implementation_cost", "native_planting", "usd_2020"),
    (
        "implementation_cost",
        "natural_regeneration",
        "usd_2020",
    ),
    ("carbon_benefit", pd.NA, "tonnes"),
    ("biodiversity_benefit", pd.NA, "index"),
)
IMPLEMENTATION_APPROACH_SOURCE_TOKENS = {
    "native_planting": "planting",
    "natural_regeneration": "regeneration",
}


@dataclass(frozen=True)
class _RasterGrid:
    crs: CRS
    transform: Affine
    shape: tuple[int, int]
    window: Window


@dataclass(frozen=True)
class _OpportunityAssignment:
    name: str
    flat_indices: np.ndarray
    admin_codes: np.ndarray
    classes: np.ndarray


def _require_raster(directory: Path, filename: str) -> Path:
    path = directory / filename
    if not path.is_file():
        raise FileNotFoundError(f"Required raster not found: {path}")
    return path


def _buffered_admin_bounds(
    admin_regions: gpd.GeoDataFrame,
    raster_crs: CRS,
    distance_m: float,
) -> tuple[float, float, float, float]:
    regions = admin_regions.to_crs(raster_crs)
    if distance_m <= 0:
        return tuple(regions.total_bounds)

    metric_crs = regions.estimate_utm_crs()
    if metric_crs is None:
        raise ValueError("Could not select a projected CRS for the coastal buffer")
    buffered = regions.to_crs(metric_crs).geometry.union_all().buffer(distance_m)
    return tuple(gpd.GeoSeries([buffered], crs=metric_crs).to_crs(raster_crs).total_bounds)


def _grid_from_source(
    source: rasterio.io.DatasetReader,
    admin_regions: gpd.GeoDataFrame,
    buffer_m: float,
) -> _RasterGrid:
    if source.crs is None:
        raise ValueError(f"Raster has no CRS: {source.name}")
    window = clipped_raster_window(
        source,
        _buffered_admin_bounds(admin_regions, source.crs, buffer_m),
    )
    return _RasterGrid(
        crs=source.crs,
        transform=window_transform(window, source.transform),
        shape=(int(window.height), int(window.width)),
        window=window,
    )


def _validate_matching_grid(
    source: rasterio.io.DatasetReader,
    reference: _RasterGrid,
) -> None:
    if source.crs != reference.crs:
        raise ValueError(f"Raster CRS does not match opportunity grid: {source.name}")
    candidate_transform = window_transform(reference.window, source.transform)
    if not candidate_transform.almost_equals(reference.transform):
        raise ValueError(f"Raster grid does not match opportunity grid: {source.name}")
    if (
        reference.window.col_off + reference.window.width > source.width
        or reference.window.row_off + reference.window.height > source.height
    ):
        raise ValueError(f"Raster extent does not cover opportunity grid: {source.name}")


def _read_window(path: Path, grid: _RasterGrid) -> tuple[np.ndarray, float | None]:
    with rasterio.open(path) as source:
        _validate_matching_grid(source, grid)
        return source.read(1, window=grid.window), source.nodata


def _valid_data_mask(values: np.ndarray, nodata: float | None) -> np.ndarray:
    valid = np.isfinite(values)
    if nodata is not None and np.isfinite(nodata):
        valid &= values != nodata
    return valid


def _validate_categories(
    values: np.ndarray,
    nodata: float | None,
    allowed: set[int],
    label: str,
) -> np.ndarray:
    valid = _valid_data_mask(values, nodata)
    observed = set(np.unique(values[valid]).tolist())
    unexpected = observed.difference({0, *allowed})
    if unexpected:
        raise ValueError(f"{label} contains unexpected classes: {sorted(unexpected)}")
    return valid & np.isin(values, list(allowed))


def _rasterized_admin_codes(
    admin_regions: gpd.GeoDataFrame,
    grid: _RasterGrid,
) -> np.ndarray:
    regions = admin_regions.to_crs(grid.crs)
    shapes = (
        (geometry, code)
        for code, geometry in enumerate(regions.geometry, start=1)
    )
    return rasterize(
        shapes,
        out_shape=grid.shape,
        transform=grid.transform,
        fill=0,
        dtype="int32",
        all_touched=False,
    )


def _build_inside_assignment(
    name: str,
    values: np.ndarray,
    opportunity_mask: np.ndarray,
    admin_codes: np.ndarray,
) -> _OpportunityAssignment:
    selected = opportunity_mask & (admin_codes > 0)
    return _OpportunityAssignment(
        name=name,
        flat_indices=np.flatnonzero(selected),
        admin_codes=admin_codes[selected].astype("int32"),
        classes=values[selected].astype("int16"),
    )


def _assign_mangrove_cells(
    values: np.ndarray,
    opportunity_mask: np.ndarray,
    admin_codes: np.ndarray,
    admin_regions: gpd.GeoDataFrame,
    grid: _RasterGrid,
    max_distance_m: float,
) -> _OpportunityAssignment:
    inside = opportunity_mask & (admin_codes > 0)
    flat_indices = [np.flatnonzero(inside)]
    assigned_codes = [admin_codes[inside].astype("int32")]
    assigned_classes = [values[inside].astype("int16")]

    outside_indices = np.flatnonzero(opportunity_mask & (admin_codes == 0))
    if outside_indices.size:
        rows, cols = np.unravel_index(outside_indices, grid.shape)
        xs = (
            grid.transform.c
            + (cols + 0.5) * grid.transform.a
            + (rows + 0.5) * grid.transform.b
        )
        ys = (
            grid.transform.f
            + (cols + 0.5) * grid.transform.d
            + (rows + 0.5) * grid.transform.e
        )
        points = gpd.GeoDataFrame(
            {"outside_index": np.arange(outside_indices.size)},
            geometry=gpd.points_from_xy(xs, ys),
            crs=grid.crs,
        )
        metric_crs = admin_regions.estimate_utm_crs()
        if metric_crs is None:
            raise ValueError("Could not select a projected CRS for mangrove assignment")
        regions = admin_regions[["adm_id", "geometry"]].copy()
        regions["admin_code"] = np.arange(1, len(regions) + 1, dtype="int32")
        nearest = gpd.sjoin_nearest(
            points.to_crs(metric_crs),
            regions.to_crs(metric_crs),
            how="left",
            max_distance=max_distance_m,
            distance_col="distance_m",
        )
        nearest = nearest.dropna(subset=["admin_code"]).copy()
        if not nearest.empty:
            nearest["adm_id"] = nearest["adm_id"].astype(str)
            nearest = nearest.sort_values(
                ["outside_index", "distance_m", "adm_id"],
                kind="stable",
            ).drop_duplicates("outside_index", keep="first")
            selected = nearest["outside_index"].to_numpy(dtype="int64")
            flat_indices.append(outside_indices[selected])
            assigned_codes.append(nearest["admin_code"].to_numpy(dtype="int32"))
            assigned_classes.append(
                values.ravel()[outside_indices[selected]].astype("int16")
            )

    return _OpportunityAssignment(
        name="mangrove",
        flat_indices=np.concatenate(flat_indices),
        admin_codes=np.concatenate(assigned_codes),
        classes=np.concatenate(assigned_classes),
    )


def _counts_by_admin(
    assignment: _OpportunityAssignment,
    admin_count: int,
    class_value: int | None = None,
) -> np.ndarray:
    selected = (
        np.ones(assignment.admin_codes.size, dtype=bool)
        if class_value is None
        else assignment.classes == class_value
    )
    return np.bincount(
        assignment.admin_codes[selected],
        minlength=admin_count + 1,
    )[1:].astype("float64")


def _aggregate_continuous_values(
    values: np.ndarray,
    nodata: float | None,
    assignment: _OpportunityAssignment,
    admin_count: int,
    mean: bool,
    nominal_cell_area_ha: float,
    class_value: int | None = None,
) -> np.ndarray:
    assignment_mask = (
        np.ones(assignment.classes.size, dtype=bool)
        if class_value is None
        else assignment.classes == class_value
    )
    selected = values.ravel()[assignment.flat_indices[assignment_mask]].astype(
        "float64"
    )
    valid = _valid_data_mask(selected, nodata)
    valid &= selected >= 0
    codes = assignment.admin_codes[assignment_mask][valid]
    selected = selected[valid]
    if not mean:
        return np.bincount(
            codes, weights=selected * nominal_cell_area_ha, minlength=admin_count + 1,
        )[1:]
    totals = np.bincount(codes, weights=selected, minlength=admin_count + 1)[1:]
    counts = np.bincount(codes, minlength=admin_count + 1)[1:]
    return np.divide(totals, counts, out=np.zeros(admin_count), where=counts > 0)


def _validate_nbs_category_totals(metrics: pd.DataFrame) -> None:
    additive_suffixes = (
        "planting_cost_total_usd_2020",
        "regeneration_cost_total_usd_2020",
        "carbon_benefit_total_tonnes",
    )
    categories_by_prefix = {
        "nbs_slope_vegetation": tuple(SLOPE_CLASS_NAMES.values()),
        "nbs_mangrove": tuple(MANGROVE_CLASS_NAMES.values()),
    }
    for prefix, categories in categories_by_prefix.items():
        for suffix in additive_suffixes:
            total_column = f"{prefix}_{suffix}"
            category_columns = [
                f"{prefix}_{category}_{suffix}" for category in categories
            ]
            if not np.allclose(
                metrics[total_column],
                metrics[category_columns].sum(axis=1),
                rtol=0,
                atol=1e-6,
            ):
                raise ValueError(
                    f"NbS category metrics do not reconcile to {total_column}"
                )


def _line_parts(geometry: BaseGeometry) -> Iterator[LineString]:
    if isinstance(geometry, LineString):
        if not geometry.is_empty and geometry.length > 0:
            yield geometry
        return
    if isinstance(geometry, (MultiLineString, GeometryCollection)):
        for part in geometry.geoms:
            yield from _line_parts(part)


def _grid_crossing_parameters(
    start: float,
    stop: float,
) -> list[float]:
    """Return segment parameters where a raster-space coordinate is integral."""
    delta = stop - start
    if np.isclose(delta, 0):
        return []
    lower = min(start, stop)
    upper = max(start, stop)
    first_boundary = floor(lower) + 1
    last_boundary = ceil(upper) - 1
    return [
        (boundary - start) / delta
        for boundary in range(first_boundary, last_boundary + 1)
        if 0 < (boundary - start) / delta < 1
    ]


def _segment_length_m(
    start: tuple[float, float],
    stop: tuple[float, float],
    geod: Geod | None,
    projected_unit_factor: float | None,
) -> float:
    if geod is not None:
        return abs(geod.inv(start[0], start[1], stop[0], stop[1])[2])
    if projected_unit_factor is None:
        raise ValueError("River length measurement has no unit conversion")
    return float(
        np.hypot(stop[0] - start[0], stop[1] - start[1])
        * projected_unit_factor
    )


def _raster_cell_size_m(
    transform: Affine,
    shape: tuple[int, int],
    crs: PyprojCRS,
) -> float:
    centre_col = shape[1] / 2
    centre_row = shape[0] / 2
    centre_x, centre_y = transform * (centre_col, centre_row)
    next_x, _ = transform * (centre_col + 1, centre_row)
    _, next_y = transform * (centre_col, centre_row + 1)
    if crs.is_geographic:
        geod = crs.get_geod()
        horizontal = abs(geod.inv(centre_x, centre_y, next_x, centre_y)[2])
        vertical = abs(geod.inv(centre_x, centre_y, centre_x, next_y)[2])
    elif crs.is_projected and crs.axis_info:
        unit_factor = crs.axis_info[0].unit_conversion_factor
        horizontal = abs(next_x - centre_x) * unit_factor
        vertical = abs(next_y - centre_y) * unit_factor
    else:
        raise ValueError(f"Cannot calculate raster cell size in CRS {crs}")
    return min(horizontal, vertical)


def _nearest_valid_urbanisation_class(
    values: np.ndarray,
    row: int,
    col: int,
    valid_classes: set[int],
    max_distance_cells: float,
    cache: dict[tuple[int, int], int],
) -> int:
    key = (row, col)
    if key in cache:
        return cache[key]
    radius = ceil(max_distance_cells)
    row_start = max(0, row - radius)
    row_stop = min(values.shape[0], row + radius + 1)
    col_start = max(0, col - radius)
    col_stop = min(values.shape[1], col + radius + 1)
    window = values[row_start:row_stop, col_start:col_stop]
    candidate_rows, candidate_cols = np.nonzero(
        np.isin(window, list(valid_classes))
    )
    if candidate_rows.size:
        candidate_rows = candidate_rows + row_start
        candidate_cols = candidate_cols + col_start
        distances_squared = (
            (candidate_rows - row) ** 2 + (candidate_cols - col) ** 2
        )
        eligible = distances_squared <= max_distance_cells**2
        if eligible.any():
            candidate_rows = candidate_rows[eligible]
            candidate_cols = candidate_cols[eligible]
            distances_squared = distances_squared[eligible]
            candidate_values = values[candidate_rows, candidate_cols].astype(int)
            order = np.lexsort((candidate_values, distances_squared))
            selected = int(candidate_values[order[0]])
            cache[key] = selected
            return selected
    raise ValueError(
        "No valid urbanisation class was found near a no-data river cell"
    )


def _classify_line_lengths(
    line: LineString,
    values: np.ndarray,
    transform: Affine,
    crs: PyprojCRS,
    nodata: float | None,
    class_to_group: dict[int, str],
    max_nodata_distance_cells: float | None = None,
    nodata_class_cache: dict[tuple[int, int], int] | None = None,
) -> dict[str, float]:
    """Split a line at raster-cell edges and total its length by cell class."""
    totals = {group: 0.0 for group in set(class_to_group.values())}
    inverse = ~transform
    if crs.is_geographic:
        geod = crs.get_geod()
        projected_unit_factor = None
    elif crs.is_projected and crs.axis_info:
        geod = None
        projected_unit_factor = crs.axis_info[0].unit_conversion_factor
    else:
        raise ValueError(f"Cannot calculate river length in CRS {crs}")
    coordinates = list(line.coords)
    for start_coordinate, stop_coordinate in zip(
        coordinates,
        coordinates[1:],
    ):
        start = (float(start_coordinate[0]), float(start_coordinate[1]))
        stop = (float(stop_coordinate[0]), float(stop_coordinate[1]))
        if start == stop:
            continue
        start_col, start_row = inverse * start
        stop_col, stop_row = inverse * stop
        parameters = {
            0.0,
            1.0,
            *_grid_crossing_parameters(start_col, stop_col),
            *_grid_crossing_parameters(start_row, stop_row),
        }
        ordered = sorted(parameters)
        for first, last in zip(ordered, ordered[1:]):
            midpoint = (first + last) / 2
            midpoint_x = start[0] + midpoint * (stop[0] - start[0])
            midpoint_y = start[1] + midpoint * (stop[1] - start[1])
            col_value, row_value = inverse * (midpoint_x, midpoint_y)
            col = floor(col_value)
            row = floor(row_value)
            if not (0 <= row < values.shape[0] and 0 <= col < values.shape[1]):
                raise ValueError("River geometry extends beyond the urbanisation raster")

            urbanisation_class = int(values[row, col])
            if nodata is not None and urbanisation_class == int(nodata):
                if (
                    max_nodata_distance_cells is None
                    or nodata_class_cache is None
                ):
                    raise ValueError(
                        "River geometry intersects no-data urbanisation cells"
                    )
                urbanisation_class = _nearest_valid_urbanisation_class(
                    values,
                    row,
                    col,
                    set(class_to_group),
                    max_nodata_distance_cells,
                    nodata_class_cache,
                )
            try:
                group = class_to_group[urbanisation_class]
            except KeyError as error:
                raise ValueError(
                    "River geometry intersects unexpected urbanisation class "
                    f"{urbanisation_class}"
                ) from error

            segment_start = (
                start[0] + first * (stop[0] - start[0]),
                start[1] + first * (stop[1] - start[1]),
            )
            segment_stop = (
                start[0] + last * (stop[0] - start[0]),
                start[1] + last * (stop[1] - start[1]),
            )
            totals[group] += _segment_length_m(
                segment_start,
                segment_stop,
                geod,
                projected_unit_factor,
            )
    return totals


def build_flopros_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """Calculate the modal positive FLOPROS return period in each region."""
    validate_spatial_admin_regions(admin_regions)
    filename = str(
        config.parameters.get(
            "flopros_filename",
            f"{config.country.iso3}_flopros.tif",
        )
    )
    path = _require_raster(config.source("adaptation_potential_dir"), filename)
    with rasterio.open(path) as source:
        if source.crs is None:
            raise ValueError(f"FLOPROS raster has no CRS: {path}")
        regions = admin_regions.to_crs(source.crs)
        statistics = zonal_stats(
            regions,
            str(path),
            categorical=True,
            nodata=0,
            all_touched=False,
        )

    modes: list[float] = []
    for adm_id, counts in zip(admin_regions["adm_id"], statistics, strict=True):
        positive = {
            float(value): int(count)
            for value, count in counts.items()
            if float(value) > 0 and int(count) > 0
        }
        if not positive:
            modes.append(np.nan)
            continue
        maximum = max(positive.values())
        modes.append(min(value for value, count in positive.items() if count == maximum))

    return pd.DataFrame(
        {
            "adm_id": admin_regions["adm_id"].astype("string"),
            "flopros_protection_standard_mode_rp": modes,
        }
    )


def build_nbs_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """Summarize opportunity area, cost, carbon, and biodiversity by region."""
    validate_spatial_admin_regions(admin_regions)
    directory = config.source("nature_based_solutions_dir")
    nominal_cell_area_ha = float(config.parameters["nbs_nominal_cell_area_ha"])
    max_distance_m = float(config.parameters["max_coastal_assignment_distance_m"])
    if nominal_cell_area_ha <= 0 or max_distance_m < 0:
        raise ValueError("NbS area must be positive and assignment distance nonnegative")

    slope_path = _require_raster(directory, SLOPE_FILENAME)
    with rasterio.open(slope_path) as source:
        grid = _grid_from_source(source, admin_regions, max_distance_m)
        slope_values = source.read(1, window=grid.window)
        slope_nodata = source.nodata
    admin_codes = _rasterized_admin_codes(admin_regions, grid)
    slope_mask = _validate_categories(
        slope_values, slope_nodata, {1, 2, 3}, "Slope vegetation opportunity raster"
    )
    slope = _build_inside_assignment(
        "slope_vegetation", slope_values, slope_mask, admin_codes
    )

    river_values, river_nodata = _read_window(
        _require_raster(directory, RIVER_FILENAME), grid
    )
    river_mask = _validate_categories(
        river_values, river_nodata, {1}, "River catchment opportunity raster"
    )
    river = _build_inside_assignment(
        "river_catchment_restoration", river_values, river_mask, admin_codes
    )

    mangrove_values, mangrove_nodata = _read_window(
        _require_raster(directory, MANGROVE_FILENAME), grid
    )
    mangrove_mask = _validate_categories(
        mangrove_values, mangrove_nodata, {1, 2, 3}, "Mangrove opportunity raster"
    )
    mangrove = _assign_mangrove_cells(
        mangrove_values,
        mangrove_mask,
        admin_codes,
        admin_regions,
        grid,
        max_distance_m,
    )

    metrics = admin_regions[["adm_id"]].copy()
    classes = {slope.name: SLOPE_CLASS_NAMES, mangrove.name: MANGROVE_CLASS_NAMES, river.name: {}}
    for assignment in (slope, mangrove, river):
        for class_value, category in ((None, "total"), *classes[assignment.name].items()):
            cells = _counts_by_admin(assignment, len(metrics), class_value)
            metrics[f"nbs_{assignment.name}_{category}_km2"] = cells * (nominal_cell_area_ha / 100)

    raster_specs = (
        (PLANTING_COST_FILENAME, (slope, river), "planting_cost_total_usd_2020", False),
        (REGENERATION_COST_FILENAME, (slope, river), "regeneration_cost_total_usd_2020", False),
        (MANGROVE_PLANTING_COST_FILENAME, (mangrove,), "planting_cost_total_usd_2020", False),
        (MANGROVE_REGENERATION_COST_FILENAME, (mangrove,), "regeneration_cost_total_usd_2020", False),
        (CARBON_FILENAME, (slope, mangrove, river), "carbon_benefit_total_tonnes", False),
        (BIODIVERSITY_FILENAME, (slope, mangrove, river), "biodiversity_benefit_mean", True),
    )
    for filename, assignments, suffix, mean in raster_specs:
        values, nodata = _read_window(_require_raster(directory, filename), grid)
        for assignment in assignments:
            for class_value, category in ((None, ""), *classes[assignment.name].items()):
                prefix = f"nbs_{assignment.name}_{category}" if category else f"nbs_{assignment.name}"
                metrics[f"{prefix}_{suffix}"] = _aggregate_continuous_values(
                    values, nodata, assignment, len(metrics), mean, nominal_cell_area_ha, class_value,
                )

    _validate_nbs_category_totals(metrics)
    return metrics


def build_river_network_context_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """Calculate river length by administrative region and urbanisation type."""
    validate_spatial_admin_regions(admin_regions)
    directory = config.source("adaptation_potential_dir")
    iso3 = config.country.iso3
    network_path = directory / f"{iso3}_river_network.gpkg"
    urbanisation_path = directory / f"{iso3}_ghs-mod.tif"
    if not network_path.is_file():
        raise FileNotFoundError(f"Required river network not found: {network_path}")
    if not urbanisation_path.is_file():
        raise FileNotFoundError(
            f"Required urbanisation raster not found: {urbanisation_path}"
        )

    with rasterio.open(urbanisation_path) as source:
        if source.crs is None:
            raise ValueError(
                f"Urbanisation raster has no CRS: {urbanisation_path}"
            )
        if source.transform.b != 0 or source.transform.d != 0:
            raise ValueError("Rotated urbanisation rasters are not supported")
        urbanisation_values = source.read(1)
        urbanisation_transform = source.transform
        urbanisation_crs = source.crs
        urbanisation_nodata = source.nodata

    rivers = gpd.read_file(network_path)
    if rivers.crs is None:
        raise ValueError(f"River network has no CRS: {network_path}")
    if rivers.empty:
        raise ValueError(f"River network contains no features: {network_path}")
    if rivers.geometry.isna().any() or rivers.geometry.is_empty.any():
        raise ValueError("River network contains missing or empty geometries")
    invalid_types = sorted(
        set(rivers.geom_type).difference({"LineString", "MultiLineString"})
    )
    if invalid_types:
        raise ValueError(
            f"River network contains unsupported geometry types: {invalid_types}"
        )

    rivers = rivers[["geometry"]].to_crs(urbanisation_crs)
    regions = admin_regions[["adm_id", "geometry"]].to_crs(
        urbanisation_crs
    )
    clipped = gpd.overlay(
        rivers,
        regions,
        how="intersection",
        keep_geom_type=False,
    )

    class_to_group = {
        urbanisation_class: group
        for group, classes in URBANISATION_GROUPS.items()
        for urbanisation_class in classes
    }
    max_nodata_distance_m = float(
        config.parameters.get(
            "max_urbanisation_nodata_distance_m",
            5000,
        )
    )
    if max_nodata_distance_m <= 0:
        raise ValueError(
            "Urbanisation no-data assignment distance must be positive"
        )
    admin_positions = {
        str(adm_id): position
        for position, adm_id in enumerate(admin_regions["adm_id"])
    }
    totals_m = {
        group: np.zeros(len(admin_regions), dtype="float64")
        for group in URBANISATION_GROUPS
    }
    raster_crs = PyprojCRS.from_user_input(urbanisation_crs)
    cell_size_m = _raster_cell_size_m(
        urbanisation_transform,
        urbanisation_values.shape,
        raster_crs,
    )
    max_nodata_distance_cells = max_nodata_distance_m / cell_size_m
    nodata_class_cache: dict[tuple[int, int], int] = {}
    for row in clipped.itertuples(index=False):
        position = admin_positions[str(row.adm_id)]
        for line in _line_parts(row.geometry):
            classified = _classify_line_lengths(
                line,
                urbanisation_values,
                urbanisation_transform,
                raster_crs,
                urbanisation_nodata,
                class_to_group,
                max_nodata_distance_cells,
                nodata_class_cache,
            )
            for group, length_m in classified.items():
                totals_m[group][position] += length_m

    metrics = admin_regions[["adm_id"]].copy()
    for group in ("rural", "town", "city"):
        metrics[f"river_length_{group}_km"] = totals_m[group] / 1000
    category_columns = [
        "river_length_rural_km",
        "river_length_town_km",
        "river_length_city_km",
    ]
    metrics["river_length_total_km"] = metrics[category_columns].sum(axis=1)
    metrics = metrics[
        [
            "adm_id",
            "river_length_total_km",
            *category_columns,
        ]
    ]
    values = metrics.drop(columns="adm_id").to_numpy(dtype="float64")
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("River network context metrics contain invalid lengths")
    if not np.allclose(
        metrics["river_length_total_km"],
        metrics[category_columns].sum(axis=1),
        rtol=0,
        atol=1e-9,
    ):
        raise ValueError("River urbanisation lengths do not reconcile to total")
    return metrics


def _nbs_source_column(
    opportunity: str,
    category: str,
    metric: str,
    implementation_approach: object,
) -> str:
    prefix = f"nbs_{opportunity}"
    if category != "total":
        prefix = f"{prefix}_{category}"
    if metric == "opportunity_area":
        return (
            f"{prefix}_total_km2"
            if category == "total"
            else f"{prefix}_km2"
        )
    if metric == "implementation_cost":
        source_approach = IMPLEMENTATION_APPROACH_SOURCE_TOKENS[
            str(implementation_approach)
        ]
        return f"{prefix}_{source_approach}_cost_total_usd_2020"
    if metric == "carbon_benefit":
        return f"{prefix}_carbon_benefit_total_tonnes"
    if metric == "biodiversity_benefit":
        return f"{prefix}_biodiversity_benefit_mean"
    raise ValueError(f"Unsupported nature-based solution metric: {metric}")


def _nbs_rows(
    metrics: pd.DataFrame,
    opportunity: str,
    categories: tuple[str, ...] = ("total",),
    category_column: str | None = None,
) -> pd.DataFrame:
    rows = []
    for category in categories:
        for metric, approach, unit in NBS_METRIC_ROWS:
            dimensions = dict(metric=metric, implementation_approach=approach, unit=unit)
            if category_column is not None:
                dimensions[category_column] = category
            rows.append((_nbs_source_column(opportunity, category, metric, approach), dimensions))
    return metric_rows(metrics, rows, adaptation_subsection="nature_based_solutions")


def assemble_adaptation_potential_card_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    flopros_metrics: pd.DataFrame,
    nbs_metrics: pd.DataFrame,
    river_network_context_metrics: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Reshape Adaptation Potential calculations into five card tables."""
    cards = {
        SLOPE_VEGETATION_CARD: _nbs_rows(
            nbs_metrics, "slope_vegetation", ("total", *SLOPE_CLASS_NAMES.values()), "land_use",
        ),
        MANGROVES_CARD: _nbs_rows(
            nbs_metrics, "mangrove", ("total", *MANGROVE_CLASS_NAMES.values()), "shoreline_condition",
        ),
        RIVER_CATCHMENT_RESTORATION_CARD: _nbs_rows(nbs_metrics, "river_catchment_restoration"),
        EXISTING_FLOOD_PROTECTION_CARD: metric_rows(
            flopros_metrics, [("flopros_protection_standard_mode_rp", {})],
            adaptation_subsection="flood_protection", metric="protection_standard_mode",
            unit="return_period_years",
        ),
        RIVER_NETWORK_CONTEXT_CARD: metric_rows(
            river_network_context_metrics,
            [(f"river_length_{area}_km", dict(urbanisation_class=area))
             for area in ("total", *URBANISATION_GROUPS)],
            adaptation_subsection="flood_protection", metric="river_length", unit="km",
        ),
    }
    return {
        card: finalize_card_output(
            rows, config, admin_regions, "adaptation_potential", card,
            ADAPTATION_POTENTIAL_CARD_DIMENSIONS[card],
            optional_dimensions=ADAPTATION_POTENTIAL_CARD_OPTIONAL_DIMENSIONS[card],
        )
        for card, rows in cards.items()
    }


def build_adaptation_potential_card_metrics(
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    """Calculate and build the five downloadable Adaptation Potential cards."""
    if admin_regions is None:
        admin_regions = load_admin_boundaries(config)
    return assemble_adaptation_potential_card_metrics(
        config,
        admin_regions,
        build_flopros_metrics(config, admin_regions),
        build_nbs_metrics(config, admin_regions),
        build_river_network_context_metrics(config, admin_regions),
    )
