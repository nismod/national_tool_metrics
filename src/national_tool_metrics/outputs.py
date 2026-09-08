from __future__ import annotations

from pathlib import Path
import re

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
]

CARD_IDENTIFIER_COLUMNS = [*IDENTIFIER_COLUMNS, "card"]

OUTPUT_UNIQUE_KEY = [
    "country_iso3",
    "admin_level",
    "adm_id",
    "section",
]

REMOVED_OUTPUT_DIMENSIONS = {"hazard", "scenario", "model_run"}
METRIC_NAMESPACE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def build_identifier_frame(
    admin_regions: gpd.GeoDataFrame,
    config: PipelineConfig,
    section: str,
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
    return identifiers[IDENTIFIER_COLUMNS]


def build_card_identifier_frame(
    admin_regions: gpd.GeoDataFrame,
    config: PipelineConfig,
    section: str,
    card: str,
) -> pd.DataFrame:
    """Create the standard identifiers repeated in one card CSV."""
    identifiers = build_identifier_frame(admin_regions, config, section)
    identifiers["card"] = card
    return identifiers[CARD_IDENTIFIER_COLUMNS]


def namespace_metric_table(
    metrics: pd.DataFrame,
    namespace: str,
) -> pd.DataFrame:
    """Prefix a one-row-per-admin metric table with a stable run namespace."""
    validate_columns(metrics, {"adm_id"}, "Metric table")
    validate_unique(metrics, ["adm_id"], "Metric table")
    if not METRIC_NAMESPACE_PATTERN.fullmatch(namespace):
        raise ValueError(
            "Metric namespace must start with a lowercase letter and contain "
            f"only lowercase letters, numbers, and underscores: {namespace!r}"
        )
    metric_columns = [column for column in metrics.columns if column != "adm_id"]
    if not metric_columns:
        raise ValueError("Metric table contains no metric columns to namespace")
    return metrics.rename(
        columns={column: f"{namespace}_{column}" for column in metric_columns}
    )


def merge_metric_tables(
    identifiers: pd.DataFrame,
    metric_tables: list[pd.DataFrame],
    *,
    fill_missing_numeric: bool = True,
) -> pd.DataFrame:
    """Merge one or more one-row-per-admin metric tables.

    By default, missing numeric values introduced by metric tables are treated
    as zero. Set ``fill_missing_numeric`` to ``False`` for metrics where missing
    values represent genuine no-data rather than zero.
    """
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
    if fill_missing_numeric:
        output[numeric_columns] = output[numeric_columns].fillna(0)
    output[numeric_columns] = output[numeric_columns].round(3)
    return output


def validate_section_output(
    frame: pd.DataFrame,
    expected_section: str,
    require_metrics: bool = True,
) -> None:
    """Validate identifiers, row grain, and the CSV-safe output schema."""
    validate_columns(frame, set(IDENTIFIER_COLUMNS), "Section output")
    removed_dimensions = sorted(
        REMOVED_OUTPUT_DIMENSIONS.intersection(frame.columns)
    )
    if removed_dimensions:
        raise ValueError(
            "Section output contains removed dimensions; encode them in metric "
            f"column names instead: {removed_dimensions}"
        )
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


def validate_card_output(
    frame: pd.DataFrame,
    expected_section: str,
    expected_card: str,
    dimension_columns: list[str] | tuple[str, ...],
    identifier_columns: list[str] | tuple[str, ...] = CARD_IDENTIFIER_COLUMNS,
    optional_dimension_columns: list[str] | tuple[str, ...] = (),
) -> None:
    """Validate a tidy, one-card CSV and its parameter dimensions."""
    dimensions = list(dimension_columns)
    identifiers = list(identifier_columns)
    optional_dimensions = list(optional_dimension_columns)
    if "adm_id" not in identifiers or "adm_name" not in identifiers:
        raise ValueError(
            "Card identifiers must include adm_id and adm_name"
        )
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Card output contains duplicate identifier columns")
    if not dimensions:
        raise ValueError("Card output must define at least one dimension column")
    if len(dimensions) != len(set(dimensions)):
        raise ValueError("Card output contains duplicate dimension columns")
    unknown_optional_dimensions = sorted(
        set(optional_dimensions).difference(dimensions)
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
        if column not in optional_dimensions
    ]
    if frame[required_dimensions].isna().any().any():
        raise ValueError("Card output contains missing parameter values")
    if "section" in frame and set(frame["section"].unique()) != {
        expected_section
    }:
        raise ValueError(
            f"Expected section {expected_section!r}, found "
            f"{sorted(frame['section'].unique())}"
        )
    if "card" in frame and set(frame["card"].unique()) != {expected_card}:
        raise ValueError(
            f"Expected card {expected_card!r}, found "
            f"{sorted(frame['card'].unique())}"
        )
    if not pd.api.types.is_numeric_dtype(frame["value"]):
        raise ValueError("Card output value column must be numeric")
    if frame["value"].isna().all():
        raise ValueError("Card output value column is entirely empty")

    unique_key = [
        column
        for column in (
            "country_iso3",
            "admin_level",
            "adm_id",
            "section",
            "card",
        )
        if column in identifiers
    ]
    unique_key.extend(dimensions)
    validate_unique(frame, unique_key, "Card output")


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


def write_card_output(
    frame: pd.DataFrame,
    config: PipelineConfig,
    section: str,
    card: str,
    dimension_columns: list[str] | tuple[str, ...],
    identifier_columns: list[str] | tuple[str, ...] = CARD_IDENTIFIER_COLUMNS,
    optional_dimension_columns: list[str] | tuple[str, ...] = (),
) -> Path:
    """Validate and write the canonical downloadable CSV for one tool card."""
    validate_card_output(
        frame,
        section,
        card,
        dimension_columns,
        identifier_columns,
        optional_dimension_columns,
    )
    output_path = config.card_output_path(section, card)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    return output_path
