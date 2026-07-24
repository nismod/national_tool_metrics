from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import tomllib
from typing import Any


_ADMIN_LEVEL_PATTERN = re.compile(r"^adm\d+$", re.IGNORECASE)


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


def _path_candidates(
    repo_root: Path,
    value: object,
    label: str,
) -> tuple[Path, ...]:
    """Parse one path or an ordered list of migration-compatible paths."""
    if isinstance(value, str) and value.strip():
        raw_paths = [value.strip()]
    elif (
        isinstance(value, list)
        and value
        and all(isinstance(item, str) and item.strip() for item in value)
    ):
        raw_paths = [item.strip() for item in value]
    else:
        raise ValueError(
            f"{label} must be a path string or a non-empty list of path strings"
        )
    return tuple(_resolve_path(repo_root, item) for item in raw_paths)


def _path_contains_data(path: Path) -> bool:
    """Distinguish a populated source from an empty tracked skeleton."""
    if path.is_file():
        return True
    if not path.is_dir():
        return False
    return any(
        item.is_file() and item.name != ".gitkeep"
        for item in path.rglob("*")
    )


def _select_path_candidate(candidates: tuple[Path, ...]) -> Path:
    """Select the first populated candidate, falling back to the first path."""
    return next(
        (path for path in candidates if _path_contains_data(path)),
        candidates[0],
    )


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
    """One reporting bundle of compatible metrics for a hazard and scenario."""

    name: str
    hazard: str
    scenario: str
    inputs: dict[str, Path]
    input_candidates: dict[str, tuple[Path, ...]]
    layers: dict[str, str]
    columns: dict[str, str]


@dataclass(frozen=True)
class PipelineConfig:
    repo_root: Path
    config_path: Path
    country: CountryConfig
    boundaries: BoundaryConfig
    sources: dict[str, Path]
    source_candidates: dict[str, tuple[Path, ...]]
    parameters: dict[str, int | float | str | bool]
    risk_runs: dict[str, RiskRunConfig]

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
    source_candidates = {
        name: _path_candidates(root, value, f"[sources].{name}")
        for name, value in source_table.items()
    }
    sources = {
        name: _select_path_candidate(candidates)
        for name, candidates in source_candidates.items()
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

        input_candidates = {
            name: _path_candidates(
                root,
                value,
                f"[risk_runs.{run_name}.inputs].{name}",
            )
            for name, value in inputs_table.items()
        }
        risk_runs[run_name] = RiskRunConfig(
            name=run_name,
            hazard=_require_string(
                run_values, "hazard", f"risk_runs.{run_name}"
            ),
            scenario=_require_string(
                run_values, "scenario", f"risk_runs.{run_name}"
            ),
            inputs={
                name: _select_path_candidate(candidates)
                for name, candidates in input_candidates.items()
            },
            input_candidates=input_candidates,
            layers={
                str(name): str(value)
                for name, value in layers_table.items()
            },
            columns={
                str(name): str(value)
                for name, value in columns_table.items()
            },
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
        source_candidates=source_candidates,
        parameters=parameters,
        risk_runs=risk_runs,
    )
