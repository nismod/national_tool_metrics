from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from .config import PipelineConfig
from .tables import validate_columns, validate_unique


IDENTIFIER_COLUMNS = [
    "country_iso3",
    "country_name",
    "admin_level",
    "adm_id",
    "adm_name",
    "section",
    "hazard",
    "scenario",
    "model_run",
]

OUTPUT_UNIQUE_KEY = [
    "country_iso3",
    "admin_level",
    "adm_id",
    "section",
    "hazard",
    "scenario",
    "model_run",
]


def build_identifier_frame(
    admin_regions: gpd.GeoDataFrame,
    config: PipelineConfig,
    section: str,
    hazard: str = "none",
    scenario: str = "baseline",
    model_run: str = "baseline_inputs",
) -> pd.DataFrame:
    """Create the standard one-row-per-admin output identifiers."""
    validate_columns(
        admin_regions,
        {"adm_id", "adm_name"},
        "Administrative regions",
    )
    validate_unique(admin_regions, ["adm_id"], "Administrative regions")

    identifiers = admin_regions[["adm_id", "adm_name"]].copy()
    identifiers.insert(0, "admin_level", config.country.admin_level.upper())
    identifiers.insert(0, "country_name", config.country.name)
    identifiers.insert(0, "country_iso3", config.country.iso3)
    identifiers["section"] = section
    identifiers["hazard"] = hazard
    identifiers["scenario"] = scenario
    identifiers["model_run"] = model_run
    return identifiers[IDENTIFIER_COLUMNS]


def merge_metric_tables(
    identifiers: pd.DataFrame,
    metric_tables: list[pd.DataFrame],
) -> pd.DataFrame:
    """Merge one or more one-row-per-admin metric tables."""
    output = identifiers.copy()
    for index, metrics in enumerate(metric_tables, start=1):
        label = f"Metric table {index}"
        validate_columns(metrics, {"adm_id"}, label)
        validate_unique(metrics, ["adm_id"], label)

        overlapping_metrics = (
            set(output.columns)
            .intersection(metrics.columns)
            .difference({"adm_id"})
        )
        if overlapping_metrics:
            raise ValueError(
                f"{label} would overwrite existing columns: "
                f"{sorted(overlapping_metrics)}"
            )

        output = output.merge(
            metrics,
            on="adm_id",
            how="left",
            validate="one_to_one",
        )

    numeric_columns = output.select_dtypes(include="number").columns
    output[numeric_columns] = output[numeric_columns].fillna(0).round(3)
    return output


def validate_section_output(
    frame: pd.DataFrame,
    expected_section: str,
    require_metrics: bool = True,
) -> None:
    """Validate identifiers, row grain, and the CSV-safe output schema."""
    validate_columns(frame, set(IDENTIFIER_COLUMNS), "Section output")
    if frame.empty:
        raise ValueError("Section output contains no rows")
    if frame["section"].isna().any():
        raise ValueError("Section output contains missing section values")
    if set(frame["section"].unique()) != {expected_section}:
        raise ValueError(
            f"Expected section {expected_section!r}, found "
            f"{sorted(frame['section'].unique())}"
        )
    if isinstance(frame, gpd.GeoDataFrame) or "geometry" in frame.columns:
        raise ValueError("Section CSV output must not contain geometry")

    validate_unique(frame, OUTPUT_UNIQUE_KEY, "Section output")
    if frame[IDENTIFIER_COLUMNS].isna().any().any():
        raise ValueError("Section output contains missing identifier values")

    metric_columns = [
        column for column in frame.columns if column not in IDENTIFIER_COLUMNS
    ]
    if require_metrics and not metric_columns:
        raise ValueError("Section output contains no metric columns")
    empty_metrics = [
        column for column in metric_columns if frame[column].isna().all()
    ]
    if empty_metrics:
        raise ValueError(
            f"Section output contains entirely empty metrics: {empty_metrics}"
        )


def write_section_output(
    frame: pd.DataFrame,
    config: PipelineConfig,
    section: str,
) -> Path:
    """Validate and write the canonical CSV for one tool section."""
    validate_section_output(frame, section)
    output_path = config.output_path(section)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    return output_path
