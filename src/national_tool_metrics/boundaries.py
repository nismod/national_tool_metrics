from __future__ import annotations

import geopandas as gpd

from .config import PipelineConfig
from .tables import validate_columns


def load_admin_boundaries(config: PipelineConfig) -> gpd.GeoDataFrame:
    """Load boundaries and standardize their identifier columns."""
    boundary_path = config.boundaries.path
    if not boundary_path.is_file():
        raise FileNotFoundError(f"Boundary layer not found: {boundary_path}")

    boundaries = gpd.read_file(boundary_path)
    required_columns = {config.boundaries.name_field, "geometry"}
    validate_columns(boundaries, required_columns, "Boundary layer")

    if config.boundaries.id_field in boundaries.columns:
        admin_regions = boundaries[
            [
                config.boundaries.id_field,
                config.boundaries.name_field,
                "geometry",
            ]
        ].copy()
        admin_regions = admin_regions.rename(
            columns={config.boundaries.id_field: "adm_id"}
        )
    elif config.country.admin_level == "adm0" and len(boundaries) == 1:
        admin_regions = boundaries[
            [config.boundaries.name_field, "geometry"]
        ].copy()
        admin_regions.insert(0, "adm_id", config.country.iso3)
    else:
        validate_columns(
            boundaries,
            {config.boundaries.id_field},
            "Boundary layer",
        )
    admin_regions = admin_regions.rename(
        columns={config.boundaries.name_field: "adm_name"}
    )
    admin_regions["adm_id"] = admin_regions["adm_id"].astype("string")
    admin_regions["adm_name"] = admin_regions["adm_name"].astype("string")

    if admin_regions.crs is None:
        raise ValueError(f"Boundary layer has no CRS: {boundary_path}")
    if admin_regions["adm_id"].isna().any():
        raise ValueError("Boundary layer contains missing administrative IDs")
    if admin_regions["adm_id"].duplicated().any():
        raise ValueError("Boundary layer contains duplicate administrative IDs")
    if admin_regions.geometry.isna().any() or admin_regions.geometry.is_empty.any():
        raise ValueError("Boundary layer contains missing or empty geometries")

    return admin_regions
