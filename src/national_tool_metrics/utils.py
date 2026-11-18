"""Country configuration and shared geospatial and CSV helpers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import glob as glob_module
from math import ceil, floor
from pathlib import Path
import re
import sqlite3
import tomllib
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import Geod
import rasterio
from rasterio.windows import Window
from rasterstats import zonal_stats


# Country configuration

_ADMIN_LEVEL_PATTERN = re.compile(r"^adm\d+$", re.IGNORECASE)
_CONCENTRATION_CURVE_ID_PATTERN = re.compile(
    r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*"
    r"__[a-z][a-z0-9]*(?:_[a-z0-9]+)*"
    r"__[a-z][a-z0-9]*(?:_[a-z0-9]+)*$"
)


def find_repo_root(start: Path | None = None) -> Path:
    """Find the repository root from the root, a notebook, or a subdirectory."""
    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if (
            (candidate / "README.md").is_file()
            and (candidate / "notebooks").is_dir()
            and (candidate / "src").is_dir()
        ):
            return candidate

    raise FileNotFoundError(
        f"Could not identify the national_tool_metrics repository from {current}"
    )


def _resolve_path(repo_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo_root / path


def _configured_path(repo_root: Path, value: object, label: str) -> Path:
    """Parse one required configuration path relative to the repository."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty path string")
    return _resolve_path(repo_root, value.strip())


def default_boundary_path(
    repo_root: Path,
    country_iso3: str,
    admin_level: str,
) -> Path:
    """Build the standard boundary path from country and admin level."""
    iso3 = country_iso3.upper()
    level = admin_level.lower()
    return (
        repo_root
        / "data"
        / "boundaries"
        / iso3
        / level
        / f"{iso3}_{level}.shp"
    )


def _require_table(config: dict[str, Any], name: str) -> dict[str, Any]:
    value = config.get(name)
    if not isinstance(value, dict):
        raise ValueError(f"Configuration must contain a [{name}] table")
    return value


def _require_string(table: dict[str, Any], key: str, table_name: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"[{table_name}].{key} must be a non-empty string")
    return value.strip()


def validate_curve_id(curve_id: str) -> None:
    """Require ``indicator__model-or-source__scenario`` identifiers."""
    if not _CONCENTRATION_CURVE_ID_PATTERN.fullmatch(curve_id):
        raise ValueError(
            "Concentration-curve identifiers must contain three lowercase "
            "double-underscore-separated components: "
            f"<indicator>__<model-or-source>__<scenario>; found {curve_id!r}"
        )


def _render_curve_template(
    template: str,
    captures: dict[str, str],
    label: str,
) -> str:
    missing_captures = [
        name for name, value in captures.items() if value is None
    ]
    if missing_captures:
        raise ValueError(
            f"{label} has unmatched optional capture groups: "
            f"{missing_captures}"
        )
    try:
        rendered = template.format_map(captures).strip()
    except (KeyError, ValueError) as error:
        raise ValueError(
            f"{label} could not be rendered from filename captures: {error}"
        ) from error
    if not rendered:
        raise ValueError(f"{label} must not render to an empty string")
    return rendered


def _natural_path_sort_key(
    path: Path,
) -> tuple[tuple[int, str | int], ...]:
    return tuple(
        (1, int(part)) if part.isdigit() else (0, part.casefold())
        for part in re.split(r"(\d+)", path.name)
    )


def _concentration_curve_config(
    curve_name: str,
    path: Path,
    values: dict[str, Any],
    table_name: str,
    *,
    description: str | None = None,
) -> ConcentrationCurveConfig:
    validate_curve_id(curve_name)
    return ConcentrationCurveConfig(
        name=curve_name,
        path=path,
        x_column=_require_string(values, "x_column", table_name),
        y_column=_require_string(values, "y_column", table_name),
        ranked_by=_require_string(values, "ranked_by", table_name),
        rank_direction=_require_string(
            values,
            "rank_direction",
            table_name,
        ),
        description=(
            description
            if description is not None
            else _require_string(values, "description", table_name)
        ),
    )


@dataclass(frozen=True)
class CountryConfig:
    iso3: str
    name: str
    admin_level: str


@dataclass(frozen=True)
class BoundaryConfig:
    path: Path
    id_field: str
    name_field: str


@dataclass(frozen=True)
class RiskRunConfig:
    """Input paths and value columns for a configured risk model run."""

    name: str
    inputs: dict[str, Path]
    columns: dict[str, str]


@dataclass(frozen=True)
class ConcentrationCurveConfig:
    """One precomputed concentration curve and its interpretation metadata."""

    name: str
    path: Path
    x_column: str
    y_column: str
    ranked_by: str
    rank_direction: str
    description: str


@dataclass(frozen=True)
class PipelineConfig:
    repo_root: Path
    config_path: Path
    country: CountryConfig
    boundaries: BoundaryConfig
    sources: dict[str, Path]
    parameters: dict[str, int | float | str | bool]
    risk_runs: dict[str, RiskRunConfig]
    concentration_curves: dict[str, ConcentrationCurveConfig]

    def source(self, name: str) -> Path:
        try:
            return self.sources[name]
        except KeyError as error:
            raise KeyError(f"Unknown configured source: {name}") from error

    def risk_run(self, name: str) -> RiskRunConfig:
        try:
            return self.risk_runs[name]
        except KeyError as error:
            raise KeyError(f"Unknown configured risk run: {name}") from error

    def concentration_curve(self, name: str) -> ConcentrationCurveConfig:
        try:
            return self.concentration_curves[name]
        except KeyError as error:
            raise KeyError(
                f"Unknown configured concentration curve: {name}"
            ) from error

    def concentration_curve_output_path(self) -> Path:
        return (
            self.repo_root
            / "results"
            / self.country.iso3
            / "concentration_curves"
            / f"{self.country.iso3}_concentration_curves.csv"
        )

    def card_output_path(self, section: str, card: str) -> Path:
        """Return the canonical downloadable CSV path for one tool card."""
        section_slug = section.strip().lower()
        card_slug = card.strip().lower()
        slug_pattern = r"[a-z][a-z0-9_]*"
        if not re.fullmatch(slug_pattern, section_slug):
            raise ValueError(f"Invalid section slug: {section!r}")
        if not re.fullmatch(slug_pattern, card_slug):
            raise ValueError(f"Invalid card slug: {card!r}")
        return (
            self.repo_root
            / "results"
            / self.country.iso3
            / section_slug
            / (
                f"{self.country.iso3}_{self.country.admin_level}_"
                f"{section_slug}_{card_slug}_metrics.csv"
            )
        )


def _merge_config(defaults: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = defaults.copy()
    for key, value in overrides.items():
        default = defaults.get(key)
        merged[key] = (
            _merge_config(default, value)
            if isinstance(default, dict) and isinstance(value, dict)
            else value
        )
    return merged


def load_country_config(
    country: str | Path = "KEN",
    repo_root: Path | None = None,
    *,
    load_curves: bool = True,
) -> PipelineConfig:
    """Load country settings and, if requested, resolve registered curve files."""
    root = (repo_root or find_repo_root()).resolve()
    requested_path = Path(country)
    if requested_path.suffix.lower() == ".toml":
        config_path = (
            requested_path
            if requested_path.is_absolute()
            else root / requested_path
        )
    else:
        config_path = root / "config" / "countries" / (
            f"{str(country).upper()}.toml"
        )

    if not config_path.is_file():
        raise FileNotFoundError(f"Country configuration not found: {config_path}")

    with config_path.open("rb") as config_file:
        raw = tomllib.load(config_file)

    country_table = _require_table(raw, "country")
    iso3 = _require_string(country_table, "iso3", "country").upper()
    country_name = _require_string(country_table, "name", "country")
    admin_level = _require_string(
        country_table, "admin_level", "country"
    ).lower()
    if len(iso3) != 3 or not iso3.isalpha():
        raise ValueError("[country].iso3 must contain exactly three letters")
    if not _ADMIN_LEVEL_PATTERN.fullmatch(admin_level):
        raise ValueError("[country].admin_level must look like 'adm1'")

    defaults_path = root / "config" / "defaults.toml"
    if defaults_path.is_file():
        defaults_text = defaults_path.read_text(encoding="utf-8")
        defaults = tomllib.loads(defaults_text.replace("{iso3}", iso3))
        curve_keys = ("concentration_curves", "concentration_curve_sets")
        if any(key in raw for key in curve_keys):
            for key in curve_keys:
                defaults.pop(key, None)
        raw = _merge_config(defaults, raw)

    boundary_table = _require_table(raw, "boundaries")
    boundary_path_value = boundary_table.get("path")
    if boundary_path_value is None:
        boundary_path = default_boundary_path(root, iso3, admin_level)
    elif isinstance(boundary_path_value, str) and boundary_path_value.strip():
        boundary_path = _resolve_path(root, boundary_path_value.strip())
    else:
        raise ValueError(
            "[boundaries].path must be a non-empty path string when provided"
        )

    boundaries = BoundaryConfig(
        path=boundary_path,
        id_field=_require_string(boundary_table, "id_field", "boundaries"),
        name_field=_require_string(
            boundary_table, "name_field", "boundaries"
        ),
    )

    source_table = _require_table(raw, "sources")
    sources = {
        name: _configured_path(root, value, f"[sources].{name}")
        for name, value in source_table.items()
    }

    parameters = raw.get("parameters", {})
    if not isinstance(parameters, dict):
        raise ValueError("[parameters] must be a TOML table")

    risk_run_table = raw.get("risk_runs", {})
    if not isinstance(risk_run_table, dict):
        raise ValueError("[risk_runs] must be a TOML table")

    risk_runs: dict[str, RiskRunConfig] = {}
    for run_name, run_values in risk_run_table.items():
        if not isinstance(run_values, dict):
            raise ValueError(f"[risk_runs.{run_name}] must be a TOML table")

        inputs_table = run_values.get("inputs", {})
        columns_table = run_values.get("columns", {})
        if not isinstance(inputs_table, dict) or not isinstance(columns_table, dict):
            raise ValueError(
                f"inputs and columns for risk run {run_name} "
                "must be TOML tables"
            )

        inputs = {
            name: _configured_path(
                root,
                value,
                f"[risk_runs.{run_name}.inputs].{name}",
            )
            for name, value in inputs_table.items()
        }
        risk_runs[run_name] = RiskRunConfig(
            name=run_name,
            inputs=inputs,
            columns={
                str(name): str(value)
                for name, value in columns_table.items()
            },
        )

    concentration_curves = (
        _load_concentration_curve_registry(root, raw) if load_curves else {}
    )
    return PipelineConfig(
        repo_root=root,
        config_path=config_path,
        country=CountryConfig(
            iso3=iso3,
            name=country_name,
            admin_level=admin_level,
        ),
        boundaries=boundaries,
        sources=sources,
        parameters=parameters,
        risk_runs=risk_runs,
        concentration_curves=concentration_curves,
    )


def _load_concentration_curve_registry(
    root: Path,
    raw: dict[str, Any],
) -> dict[str, ConcentrationCurveConfig]:
    concentration_curve_table = raw.get("concentration_curves", {})
    if not isinstance(concentration_curve_table, dict):
        raise ValueError("[concentration_curves] must be a TOML table")

    concentration_curves: dict[str, ConcentrationCurveConfig] = {}
    curve_sources: dict[str, str] = {}
    registered_curve_paths: dict[Path, str] = {}

    def register_curve(
        curve: ConcentrationCurveConfig,
        source_label: str,
    ) -> None:
        existing_source = curve_sources.get(curve.name)
        if existing_source is not None:
            raise ValueError(
                f"Duplicate concentration-curve identifier {curve.name!r}: "
                f"registered by {existing_source} and {source_label}"
            )
        normalized_path = curve.path.resolve()
        existing_curve = registered_curve_paths.get(normalized_path)
        if existing_curve is not None:
            raise ValueError(
                f"Concentration-curve input {curve.path} is registered more "
                f"than once: as {existing_curve!r} and {curve.name!r}"
            )
        concentration_curves[curve.name] = curve
        curve_sources[curve.name] = source_label
        registered_curve_paths[normalized_path] = curve.name

    for curve_name, curve_values in concentration_curve_table.items():
        table_name = f"concentration_curves.{curve_name}"
        if not isinstance(curve_values, dict):
            raise ValueError(f"[{table_name}] must be a TOML table")
        register_curve(
            _concentration_curve_config(
                curve_name,
                _configured_path(
                    root,
                    curve_values.get("path"),
                    f"[{table_name}].path",
                ),
                curve_values,
                table_name,
            ),
            f"[{table_name}]",
        )

    concentration_curve_sets = raw.get("concentration_curve_sets", [])
    if not isinstance(concentration_curve_sets, list):
        raise ValueError(
            "[[concentration_curve_sets]] must be a TOML array of tables"
        )

    for set_index, set_values in enumerate(concentration_curve_sets):
        table_name = f"concentration_curve_sets[{set_index}]"
        if not isinstance(set_values, dict):
            raise ValueError(
                f"[[{table_name}]] must be a TOML table"
            )

        glob_pattern = _require_string(set_values, "glob", table_name)
        filename_regex = _require_string(
            set_values,
            "filename_regex",
            table_name,
        )
        curve_id_template = _require_string(
            set_values,
            "curve_id_template",
            table_name,
        )
        try:
            compiled_filename_regex = re.compile(filename_regex)
        except re.error as error:
            raise ValueError(
                f"[{table_name}].filename_regex is invalid: {error}"
            ) from error

        description = set_values.get("description")
        description_template = set_values.get("description_template")
        if description is not None and description_template is not None:
            raise ValueError(
                f"[{table_name}] must use either description or "
                "description_template, not both"
            )
        description_key = (
            "description_template"
            if description_template is not None
            else "description"
        )
        description_template = _require_string(
            set_values,
            description_key,
            table_name,
        )

        expected_count = set_values.get("expected_count")
        if expected_count is not None and (
            isinstance(expected_count, bool)
            or not isinstance(expected_count, int)
            or expected_count < 1
        ):
            raise ValueError(
                f"[{table_name}].expected_count must be a positive integer"
            )

        resolved_glob = _resolve_path(root, glob_pattern)
        matched_paths = sorted(
            (
                Path(match)
                for match in glob_module.glob(
                    str(resolved_glob),
                    recursive=True,
                )
                if Path(match).is_file()
            ),
            key=_natural_path_sort_key,
        )
        if not matched_paths:
            raise ValueError(
                f"[{table_name}].glob matched no files: {glob_pattern!r}"
            )
        if (
            expected_count is not None
            and len(matched_paths) != expected_count
        ):
            raise ValueError(
                f"[{table_name}].glob expected {expected_count} files but "
                f"matched {len(matched_paths)}: {glob_pattern!r}"
            )

        for matched_path in matched_paths:
            filename_match = compiled_filename_regex.fullmatch(
                matched_path.name
            )
            if filename_match is None:
                raise ValueError(
                    f"[{table_name}].filename_regex does not match "
                    f"globbed file {matched_path.name!r}"
                )
            captures = filename_match.groupdict()
            curve_name = _render_curve_template(
                curve_id_template,
                captures,
                f"[{table_name}].curve_id_template",
            )
            curve_description = _render_curve_template(
                description_template,
                captures,
                f"[{table_name}].{description_key}",
            )
            register_curve(
                _concentration_curve_config(
                    curve_name,
                    matched_path,
                    set_values,
                    table_name,
                    description=curve_description,
                ),
                f"[[{table_name}]] file {matched_path.name!r}",
            )

    return concentration_curves


# Table input and validation

def validate_columns(
    frame: pd.DataFrame,
    required_columns: set[str],
    label: str,
) -> None:
    """Raise a useful error when required fields are absent."""
    missing_columns = required_columns.difference(frame.columns)
    if missing_columns:
        raise ValueError(
            f"{label} is missing required columns: {sorted(missing_columns)}"
        )


def validate_unique(
    frame: pd.DataFrame,
    key_columns: list[str],
    label: str,
) -> None:
    """Require one row per supplied key."""
    validate_columns(frame, set(key_columns), label)
    duplicate_rows = frame.duplicated(key_columns, keep=False)
    if duplicate_rows.any():
        example = frame.loc[duplicate_rows, key_columns].head()
        raise ValueError(
            f"{label} contains duplicate key rows. Example:\n{example}"
        )


def validate_admin_reference(
    source: pd.DataFrame,
    admin_regions: pd.DataFrame,
    label: str,
    *,
    allow_single_admin_id: bool = False,
    repeated_ids: bool = False,
) -> pd.DataFrame:
    """Match input names and IDs to boundaries, including ADM0 summaries without IDs."""
    validate_columns(source, {"shapeName"}, label)
    if "shapeID" not in source:
        if not allow_single_admin_id or len(admin_regions) != 1 or (not repeated_ids and len(source) != 1):
            validate_columns(source, {"shapeID"}, label)
        source = source.assign(shapeID=admin_regions.iloc[0]["adm_id"])
    source = source.astype({"shapeID": "string", "shapeName": "string"})
    reference = source[["shapeID", "shapeName"]]
    if repeated_ids:
        reference = reference.drop_duplicates()
    validate_unique(reference, ["shapeID"], label)

    expected = admin_regions[["adm_id", "adm_name"]].astype("string")
    expected_ids = set(expected["adm_id"].astype(str))
    observed_ids = set(reference["shapeID"].astype(str))
    if expected_ids != observed_ids:
        raise ValueError(
            f"{label} administrative coverage does not match the boundaries. "
            f"Missing IDs: {sorted(expected_ids - observed_ids)[:5]}; "
            f"extra IDs: {sorted(observed_ids - expected_ids)[:5]}"
        )
    names = expected.merge(reference, left_on="adm_id", right_on="shapeID", validate="one_to_one")
    mismatches = names.loc[names["adm_name"].astype(str) != names["shapeName"].astype(str)]
    if not mismatches.empty:
        raise ValueError(
            f"{label} administrative names do not match the boundaries. Example:\n"
            f"{mismatches[['adm_id', 'adm_name', 'shapeName']].head()}"
        )
    return source


def require_reconciliation(
    frame: pd.DataFrame,
    total_column: str,
    component_columns: list[str],
    label: str,
) -> None:
    component_total = frame[component_columns].sum(axis=1)
    if not np.allclose(
        frame[total_column],
        component_total,
        rtol=1e-6,
        atol=0.01,
    ):
        maximum_difference = (component_total - frame[total_column]).abs().max()
        raise ValueError(
            f"{label} components do not reconcile with {total_column}. "
            f"Maximum absolute difference: {maximum_difference}"
        )


def quote_sqlite_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def read_gpkg_attributes(
    gpkg_path: Path,
    layer_name: str,
) -> pd.DataFrame:
    """Read a GeoPackage feature layer without decoding its geometry."""
    if not gpkg_path.is_file():
        raise FileNotFoundError(f"GeoPackage not found: {gpkg_path}")

    quoted_layer = quote_sqlite_identifier(layer_name)
    with sqlite3.connect(gpkg_path) as connection:
        layer_exists = connection.execute(
            """
            SELECT 1
            FROM gpkg_contents
            WHERE table_name = ?
            """,
            [layer_name],
        ).fetchone()
        if layer_exists is None:
            raise ValueError(
                f"Layer {layer_name!r} not found in GeoPackage: {gpkg_path}"
            )

        geometry_columns = {
            row[0]
            for row in connection.execute(
                """
                SELECT column_name
                FROM gpkg_geometry_columns
                WHERE table_name = ?
                """,
                [layer_name],
            )
        }
        column_info = connection.execute(
            f"PRAGMA table_info({quoted_layer})"
        ).fetchall()
        attribute_columns = [
            row[1]
            for row in column_info
            if row[1] not in geometry_columns and row[1] != "fid"
        ]
        if not attribute_columns:
            raise ValueError(
                f"Layer {layer_name!r} contains no attribute columns"
            )

        select_columns = ", ".join(
            quote_sqlite_identifier(column) for column in attribute_columns
        )
        query = f"SELECT {select_columns} FROM {quoted_layer}"
        return pd.read_sql_query(query, connection)


def read_admin_summary_csv(
    csv_path: Path,
    value_columns: list[str],
    adm_id_column: str = "adm_id",
) -> pd.DataFrame:
    """Load and validate a pre-aggregated administrative summary CSV."""
    if not csv_path.is_file():
        raise FileNotFoundError(f"Administrative summary not found: {csv_path}")

    frame = pd.read_csv(csv_path, dtype={adm_id_column: "string"})
    required_columns = {adm_id_column, *value_columns}
    validate_columns(frame, required_columns, csv_path.name)
    validate_unique(frame, [adm_id_column], csv_path.name)
    return frame[[adm_id_column, *value_columns]].copy()


# Administrative boundaries

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


def validate_spatial_admin_regions(admin_regions: gpd.GeoDataFrame) -> None:
    if admin_regions.crs is None:
        raise ValueError("Administrative regions must have a CRS")
    if admin_regions.empty:
        raise ValueError("Administrative regions contain no rows")
    if admin_regions["adm_id"].duplicated().any():
        raise ValueError("Administrative regions contain duplicate IDs")
    if admin_regions.geometry.isna().any() or admin_regions.geometry.is_empty.any():
        raise ValueError("Administrative regions contain empty geometries")


# Raster calculations

_GEOD = Geod(ellps="WGS84")


def clipped_raster_window(
    source: rasterio.io.DatasetReader,
    bounds: tuple[float, float, float, float],
) -> Window:
    """Find the raster cells inside the requested bounds, clipped to the dataset."""
    if source.transform.b != 0 or source.transform.d != 0:
        raise ValueError(f"Rotated rasters are not supported: {source.name}")
    left, bottom, right, top = bounds
    inverse = ~source.transform
    first_col, first_row = inverse * (left, top)
    last_col, last_row = inverse * (right, bottom)
    col_start = max(0, floor(min(first_col, last_col)))
    row_start = max(0, floor(min(first_row, last_row)))
    col_stop = min(source.width, ceil(max(first_col, last_col)))
    row_stop = min(source.height, ceil(max(first_row, last_row)))
    if col_stop <= col_start or row_stop <= row_start:
        raise ValueError(f"Administrative boundaries do not overlap {source.name}")
    return Window(
        col_off=col_start,
        row_off=row_start,
        width=col_stop - col_start,
        height=row_stop - row_start,
    )


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


# Network calculations

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


def _network_metrics(
    path: Path,
    polygons: gpd.GeoDataFrame,
    total_name: str,
    group_column: str | None,
    group_prefix: str,
    *,
    ead_column: str | None = None,
) -> pd.DataFrame:
    if not path.is_file():
        label = "Asset damage" if ead_column else "Network"
        raise FileNotFoundError(f"{label} layer not found: {path}")

    assets = gpd.read_file(path)
    columns = [name for name in (group_column, ead_column, "geometry") if name]
    validate_columns(assets, set(columns), path.name)
    assets = assets.loc[
        assets.geometry.notna() & ~assets.geometry.is_empty, columns
    ].copy()
    if assets.empty:
        raise ValueError(f"No valid line geometries found in {path}")

    metric_crs = _metric_crs(polygons)
    assets = assets.to_crs(metric_crs)
    if ead_column:
        assets[ead_column] = pd.to_numeric(assets[ead_column], errors="coerce").fillna(0)
        assets["_asset_length_m"] = assets.geometry.length
        assets = assets.loc[assets["_asset_length_m"] > 0]

    intersections = gpd.overlay(
        assets, polygons[["adm_id", "geometry"]].to_crs(metric_crs),
        how="intersection", keep_geom_type=True,
    )
    intersections = intersections.loc[
        intersections.geometry.notna() & ~intersections.geometry.is_empty
    ].copy()
    result = polygons[["adm_id"]].copy()
    if intersections.empty:
        return result.assign(**{total_name: 0.0})

    length = intersections.geometry.length
    if ead_column:
        weight = length / intersections["_asset_length_m"]
        intersections["value"] = intersections[ead_column] * weight
    else:
        intersections["value"] = length / 1_000

    pieces = []
    if ead_column or group_column is None:
        pieces.append(intersections.groupby("adm_id")["value"].sum().rename(total_name))
    if group_column:
        intersections[group_column] = intersections[group_column].fillna("unknown")
        grouped = intersections.groupby(["adm_id", group_column])["value"].sum().reset_index()
        suffix = "" if ead_column else "_km"
        grouped["metric_name"] = grouped[group_column].map(
            lambda value: f"{group_prefix}_{normalize_metric_token(value)}{suffix}"
        )
        groups = grouped.pivot_table(index="adm_id", columns="metric_name", values="value", fill_value=0)
        groups.columns.name = None
        pieces.append(groups)

    metrics = pd.concat(pieces, axis=1)
    output = result.merge(metrics, on="adm_id", how="left", validate="one_to_one")
    output[metrics.columns] = output[metrics.columns].fillna(0)
    return output


def network_length_by_admin(
    network_path: Path,
    polygons: gpd.GeoDataFrame,
    group_column: str | None = None,
    metric_prefix: str = "network_length",
) -> pd.DataFrame:
    """Clip network lines to administrative regions and summarize length."""
    return _network_metrics(
        network_path, polygons, f"{metric_prefix}_km", group_column, metric_prefix,
    )


def line_ead_by_admin(
    asset_path: Path,
    polygons: gpd.GeoDataFrame,
    ead_column: str,
    total_metric_name: str,
    group_column: str | None = None,
    group_metric_prefix: str | None = None,
) -> pd.DataFrame:
    """Allocate each asset's expected annual damage by its intersected length."""
    return _network_metrics(
        asset_path, polygons, total_metric_name, group_column,
        group_metric_prefix or total_metric_name, ead_column=ead_column,
    )


# CSV output

IDENTIFIER_COLUMNS = [
    "country_iso3",
    "country_name",
    "admin_level",
    "adm_id",
    "adm_name",
    "section",
]

CARD_IDENTIFIER_COLUMNS = [*IDENTIFIER_COLUMNS, "card"]


def metric_rows(
    metrics: pd.DataFrame,
    measures: Iterable[tuple[str | pd.Series | float, dict[str, object]]],
    *,
    id_columns: tuple[str, ...] = ("adm_id",),
    **shared_dimensions: object,
) -> pd.DataFrame:
    """Turn an ordered list of measures into tidy rows with their card dimensions."""
    ids = metrics[list(id_columns)]
    parts = []
    for order, (value, dimensions) in enumerate(measures):
        parts.append(ids.assign(
            **(shared_dimensions | dimensions),
            value=metrics[value] if isinstance(value, str) else value,
            _row_order=order,
        ))
    return pd.concat(parts, ignore_index=True)


def build_card_identifier_frame(
    admin_regions: gpd.GeoDataFrame,
    config: PipelineConfig,
    section: str,
    card: str,
) -> pd.DataFrame:
    """Create the standard identifiers repeated in one card CSV."""
    validate_columns(admin_regions, {"adm_id", "adm_name"}, "Administrative regions")
    validate_unique(admin_regions, ["adm_id"], "Administrative regions")
    identifiers = admin_regions[["adm_id", "adm_name"]].assign(
        country_iso3=config.country.iso3,
        country_name=config.country.name,
        admin_level=config.country.admin_level.upper(),
        section=section,
        card=card,
    )
    return identifiers[CARD_IDENTIFIER_COLUMNS]


def finalize_card_output(
    long_metrics: pd.DataFrame,
    config: PipelineConfig,
    admin_regions: gpd.GeoDataFrame,
    section: str,
    card: str,
    dimensions: tuple[str, ...],
    *,
    sort_columns: tuple[str, ...] = ("_row_order",),
    optional_dimensions: tuple[str, ...] = (),
    allow_empty_values: bool = False,
) -> pd.DataFrame:
    """Attach identifiers, order and round the rows, and validate a card table."""
    identifiers = build_card_identifier_frame(admin_regions, config, section, card)
    admin_order = {
        adm_id: order for order, adm_id in enumerate(identifiers["adm_id"])
    }
    output = identifiers.merge(
        long_metrics, on="adm_id", how="left", validate="one_to_many"
    )
    output["_admin_order"] = output["adm_id"].map(admin_order)
    output = output.sort_values(["_admin_order", *sort_columns], kind="stable")
    output = output[
        [*CARD_IDENTIFIER_COLUMNS, *dimensions, "value"]
    ].reset_index(drop=True)
    output["value"] = output["value"].round(3)
    validate_card_output(
        output,
        section,
        card,
        dimensions,
        optional_dimension_columns=optional_dimensions,
        allow_empty_values=allow_empty_values,
    )
    return output


def validate_card_output(
    frame: pd.DataFrame,
    expected_section: str,
    expected_card: str,
    dimension_columns: list[str] | tuple[str, ...],
    optional_dimension_columns: list[str] | tuple[str, ...] = (),
    *,
    allow_empty_values: bool = False,
) -> None:
    """Validate a card, optionally allowing an entirely no-data value column."""
    dimensions = list(dimension_columns)
    identifiers = CARD_IDENTIFIER_COLUMNS
    if not dimensions:
        raise ValueError("Card output must define at least one dimension column")
    if len(dimensions) != len(set(dimensions)):
        raise ValueError("Card output contains duplicate dimension columns")
    unknown_optional_dimensions = sorted(
        set(optional_dimension_columns).difference(dimensions)
    )
    if unknown_optional_dimensions:
        raise ValueError(
            "Optional card dimensions are not declared dimensions: "
            f"{unknown_optional_dimensions}"
        )
    reserved_dimensions = set(dimensions).intersection(
        {*identifiers, "value"}
    )
    if reserved_dimensions:
        raise ValueError(
            "Card dimensions overlap reserved output columns: "
            f"{sorted(reserved_dimensions)}"
        )

    expected_columns = [*identifiers, *dimensions, "value"]
    if list(frame.columns) != expected_columns:
        raise ValueError(
            "Card output columns do not match the declared schema. "
            f"Expected {expected_columns}, found {list(frame.columns)}"
        )
    if frame.empty:
        raise ValueError("Card output contains no rows")
    if isinstance(frame, gpd.GeoDataFrame) or "geometry" in frame.columns:
        raise ValueError("Card CSV output must not contain geometry")
    if frame[identifiers].isna().any().any():
        raise ValueError("Card output contains missing identifier values")
    required_dimensions = [
        column
        for column in dimensions
        if column not in optional_dimension_columns
    ]
    if frame[required_dimensions].isna().any().any():
        raise ValueError("Card output contains missing parameter values")
    if set(frame["section"].unique()) != {expected_section}:
        raise ValueError(
            f"Expected section {expected_section!r}, found "
            f"{sorted(frame['section'].unique())}"
        )
    if set(frame["card"].unique()) != {expected_card}:
        raise ValueError(
            f"Expected card {expected_card!r}, found "
            f"{sorted(frame['card'].unique())}"
        )
    if not pd.api.types.is_numeric_dtype(frame["value"]):
        raise ValueError("Card output value column must be numeric")
    if frame["value"].isna().all() and not allow_empty_values:
        raise ValueError("Card output value column is entirely empty")

    unique_key = ["country_iso3", "admin_level", "adm_id", "section", "card", *dimensions]
    validate_unique(frame, unique_key, "Card output")


def write_card_outputs(
    cards: dict[str, pd.DataFrame],
    config: PipelineConfig,
    section: str,
    dimensions: dict[str, tuple[str, ...]],
    *,
    optional_dimensions: dict[str, tuple[str, ...]] | None = None,
    allow_empty_value_cards: frozenset[str] = frozenset(),
) -> dict[str, Path]:
    """Write the card tables for a notebook and return their CSV paths."""
    optional_dimensions = optional_dimensions or {}
    paths = {}
    for card, frame in cards.items():
        validate_card_output(
            frame,
            section,
            card,
            dimensions[card],
            optional_dimension_columns=optional_dimensions.get(card, ()),
            allow_empty_values=card in allow_empty_value_cards,
        )
        paths[card] = config.card_output_path(section, card)

    for card, path in paths.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        cards[card].to_csv(path, index=False)
    return paths
