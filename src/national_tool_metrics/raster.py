from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from pyproj import Geod
from rasterio.windows import Window
from rasterstats import zonal_stats


_GEOD = Geod(ellps="WGS84")


def zonal_raster_sum(
    raster_path: Path,
    polygons: gpd.GeoDataFrame,
    all_touched: bool = False,
) -> pd.Series:
    """Sum raster values within each polygon."""
    if not raster_path.is_file():
        raise FileNotFoundError(f"Raster not found: {raster_path}")
    if polygons.crs is None:
        raise ValueError("Polygons must have a CRS")

    with rasterio.open(raster_path) as source:
        if source.crs is None:
            raise ValueError(f"Raster has no CRS: {raster_path}")
        polygons_for_stats = (
            polygons
            if polygons.crs == source.crs
            else polygons.to_crs(source.crs)
        )
        statistics = zonal_stats(
            polygons_for_stats,
            str(raster_path),
            stats=["sum"],
            nodata=source.nodata,
            all_touched=all_touched,
        )

    return pd.Series(
        [item.get("sum", 0) or 0 for item in statistics],
        index=polygons.index,
        dtype="float64",
    )


def find_single_raster(directory: Path, pattern: str, label: str) -> Path:
    """Return the sole raster matching a glob pattern."""
    matches = sorted(directory.glob(pattern))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"Expected one {label}, found {len(matches)} in {directory} "
            f"matching {pattern!r}"
        )
    return matches[0]


def raster_window_cell_areas_km2(
    source: rasterio.io.DatasetReader,
    window: Window,
) -> np.ndarray:
    """Return the area of every cell in a raster window in square kilometres."""
    height = int(window.height)
    width = int(window.width)

    if source.crs is not None and source.crs.is_projected:
        cell_area_km2 = abs(source.transform.a * source.transform.e) / 1_000_000
        return np.full((height, width), cell_area_km2, dtype="float64")

    if source.crs is None or not source.crs.is_geographic:
        raise ValueError(f"Cannot calculate cell areas for CRS: {source.crs}")

    left = source.transform.c + window.col_off * source.transform.a
    right = left + source.transform.a
    row_areas = []
    for row in range(
        int(window.row_off),
        int(window.row_off + window.height),
    ):
        top = source.transform.f + row * source.transform.e
        bottom = top + source.transform.e
        area_m2, _ = _GEOD.polygon_area_perimeter(
            [left, right, right, left],
            [top, top, bottom, bottom],
        )
        row_areas.append(abs(area_m2) / 1_000_000)

    return np.repeat(
        np.asarray(row_areas, dtype="float64")[:, None],
        width,
        axis=1,
    )
