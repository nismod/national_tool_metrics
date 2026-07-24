from __future__ import annotations

from pathlib import Path
import re

import geopandas as gpd
import numpy as np
import pandas as pd

from .tables import validate_columns


def normalize_metric_token(value: object) -> str:
    """Convert a category label into a metric-safe token."""
    token = str(value).lower().strip()
    token = re.sub(r"^(road|rail|power)_", "", token)
    token = re.sub(r"[^a-z0-9]+", "_", token).strip("_")
    return token or "unknown"


def _metric_crs(polygons: gpd.GeoDataFrame) -> object:
    if polygons.crs is None:
        raise ValueError("Administrative polygons must have a CRS")
    return polygons.estimate_utm_crs() or "EPSG:3857"


def network_length_by_admin(
    network_path: Path,
    polygons: gpd.GeoDataFrame,
    group_column: str | None = None,
    metric_prefix: str = "network_length",
) -> pd.DataFrame:
    """Clip network lines to administrative regions and summarize length."""
    if not network_path.is_file():
        raise FileNotFoundError(f"Network layer not found: {network_path}")

    lines = gpd.read_file(network_path)
    required_columns = {"geometry"}
    if group_column:
        required_columns.add(group_column)
    validate_columns(lines, required_columns, network_path.name)

    lines = lines[lines.geometry.notna() & ~lines.geometry.is_empty].copy()
    if lines.empty:
        raise ValueError(f"No valid line geometries found in {network_path}")

    metric_crs = _metric_crs(polygons)
    admin_for_overlay = polygons[["adm_id", "geometry"]].to_crs(metric_crs)
    lines_for_overlay = lines.to_crs(metric_crs)
    selected_columns = (
        [group_column, "geometry"] if group_column else ["geometry"]
    )
    intersections = gpd.overlay(
        lines_for_overlay[selected_columns],
        admin_for_overlay,
        how="intersection",
        keep_geom_type=True,
    )
    intersections = intersections[
        intersections.geometry.notna() & ~intersections.geometry.is_empty
    ].copy()
    intersections["length_km"] = intersections.geometry.length / 1_000

    result = polygons[["adm_id"]].copy()
    if intersections.empty:
        result[f"{metric_prefix}_km"] = 0.0
        return result

    if group_column:
        intersections[group_column] = intersections[group_column].fillna(
            "unknown"
        )
        grouped = (
            intersections.groupby(["adm_id", group_column])["length_km"]
            .sum()
            .reset_index()
        )
        grouped["metric_name"] = grouped[group_column].map(
            lambda value: (
                f"{metric_prefix}_{normalize_metric_token(value)}_km"
            )
        )
        metrics = grouped.pivot_table(
            index="adm_id",
            columns="metric_name",
            values="length_km",
            fill_value=0,
        )
    else:
        metrics = (
            intersections.groupby("adm_id")["length_km"]
            .sum()
            .to_frame(f"{metric_prefix}_km")
        )

    metrics.columns.name = None
    return result.merge(
        metrics.reset_index(),
        on="adm_id",
        how="left",
        validate="one_to_one",
    ).fillna(0)


def line_ead_by_admin(
    asset_path: Path,
    polygons: gpd.GeoDataFrame,
    ead_column: str,
    total_metric_name: str,
    group_column: str | None = None,
    group_metric_prefix: str | None = None,
) -> pd.DataFrame:
    """Allocate line-asset EAD by each line's intersected length."""
    if not asset_path.is_file():
        raise FileNotFoundError(f"Asset damage layer not found: {asset_path}")

    assets = gpd.read_file(asset_path)
    required_columns = {ead_column, "geometry"}
    if group_column:
        required_columns.add(group_column)
    validate_columns(assets, required_columns, asset_path.name)

    assets = assets[
        assets.geometry.notna() & ~assets.geometry.is_empty
    ].copy()
    if assets.empty:
        raise ValueError(f"No valid line geometries found in {asset_path}")

    assets[ead_column] = pd.to_numeric(
        assets[ead_column], errors="coerce"
    ).fillna(0)
    if group_column:
        assets[group_column] = assets[group_column].fillna("unknown")

    metric_crs = _metric_crs(polygons)
    admin_for_overlay = polygons[["adm_id", "geometry"]].to_crs(metric_crs)
    assets_for_overlay = assets.to_crs(metric_crs).copy()
    assets_for_overlay["_asset_row_id"] = np.arange(len(assets_for_overlay))
    assets_for_overlay["_asset_length_m"] = (
        assets_for_overlay.geometry.length
    )
    assets_for_overlay = assets_for_overlay[
        assets_for_overlay["_asset_length_m"] > 0
    ].copy()

    keep_columns = [
        "_asset_row_id",
        "_asset_length_m",
        ead_column,
        "geometry",
    ]
    if group_column:
        keep_columns.insert(3, group_column)

    intersections = gpd.overlay(
        assets_for_overlay[keep_columns],
        admin_for_overlay,
        how="intersection",
        keep_geom_type=True,
    )
    result = polygons[["adm_id"]].copy()
    if intersections.empty:
        result[total_metric_name] = 0.0
        return result

    intersections = intersections[
        intersections.geometry.notna() & ~intersections.geometry.is_empty
    ].copy()
    intersections["_intersection_length_m"] = intersections.geometry.length
    intersections["_length_weight"] = (
        intersections["_intersection_length_m"]
        / intersections["_asset_length_m"]
    )
    intersections["_ead_apportioned"] = (
        intersections[ead_column] * intersections["_length_weight"]
    )

    totals = (
        intersections.groupby("adm_id")["_ead_apportioned"]
        .sum()
        .rename(total_metric_name)
    )
    result = result.merge(
        totals.reset_index(),
        on="adm_id",
        how="left",
        validate="one_to_one",
    )
    result[total_metric_name] = result[total_metric_name].fillna(0)

    if group_column:
        prefix = group_metric_prefix or total_metric_name
        grouped = (
            intersections.groupby(["adm_id", group_column])[
                "_ead_apportioned"
            ]
            .sum()
            .reset_index()
        )
        grouped["metric_name"] = grouped[group_column].map(
            lambda value: f"{prefix}_{normalize_metric_token(value)}"
        )
        group_metrics = grouped.pivot_table(
            index="adm_id",
            columns="metric_name",
            values="_ead_apportioned",
            fill_value=0,
        )
        group_metrics.columns.name = None
        result = result.merge(
            group_metrics.reset_index(),
            on="adm_id",
            how="left",
            validate="one_to_one",
        )
        group_columns = [
            column
            for column in result.columns
            if column.startswith(f"{prefix}_")
        ]
        result[group_columns] = result[group_columns].fillna(0)

    return result
