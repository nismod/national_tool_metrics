from __future__ import annotations

from dataclasses import dataclass
import glob as glob_module
from pathlib import Path
import re
import tomllib
from typing import Any


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


def _validate_concentration_curve_id(curve_id: str) -> None:
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
    _validate_concentration_curve_id(curve_name)
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
    """One reporting bundle whose name is its output metric namespace."""

    name: str
    inputs: dict[str, Path]
    layers: dict[str, str]
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

    def output_path(self, section: str) -> Path:
        section_slug = section.strip().lower()
        if not re.fullmatch(r"[a-z][a-z0-9_]*", section_slug):
            raise ValueError(f"Invalid section slug: {section!r}")
        return (
            self.repo_root
            / "results"
            / self.country.iso3
            / section_slug
            / (
                f"{self.country.iso3}_{self.country.admin_level}_"
                f"{section_slug}_metrics.csv"
            )
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


def load_country_config(
    country: str | Path = "KEN",
    repo_root: Path | None = None,
) -> PipelineConfig:
    """Load and validate a country TOML configuration."""
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
        layers_table = run_values.get("layers", {})
        columns_table = run_values.get("columns", {})
        if not all(
            isinstance(table, dict)
            for table in (inputs_table, layers_table, columns_table)
        ):
            raise ValueError(
                f"inputs, layers, and columns for risk run {run_name} "
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
            layers={
                str(name): str(value)
                for name, value in layers_table.items()
            },
            columns={
                str(name): str(value)
                for name, value in columns_table.items()
            },
        )

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
