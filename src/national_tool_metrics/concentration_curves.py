from __future__ import annotations

from pathlib import Path
import re

import numpy as np
import pandas as pd

from .config import ConcentrationCurveConfig, PipelineConfig
from .tables import validate_columns


SHARED_X_COLUMN = "cumulative_population_share"
CURVE_ID_PATTERN = re.compile(
    r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*"
    r"__[a-z][a-z0-9]*(?:_[a-z0-9]+)*"
    r"__[a-z][a-z0-9]*(?:_[a-z0-9]+)*$"
)
NUMERIC_TOLERANCE = 1e-9


def validate_curve_id(curve_id: str) -> None:
    """Require ``indicator__model-or-source__scenario`` identifiers."""
    if not CURVE_ID_PATTERN.fullmatch(curve_id):
        raise ValueError(
            "Concentration-curve identifiers must contain three lowercase "
            "double-underscore-separated components: "
            f"<indicator>__<model-or-source>__<scenario>; found {curve_id!r}"
        )


def load_concentration_curve(
    curve: ConcentrationCurveConfig,
) -> pd.DataFrame:
    """Load and normalize one registered two-column concentration curve."""
    validate_curve_id(curve.name)
    if curve.x_column == curve.y_column:
        raise ValueError(
            f"Concentration curve {curve.name!r} uses the same X and Y column"
        )
    if not curve.path.is_file():
        raise FileNotFoundError(
            f"Concentration-curve input not found: {curve.path}"
        )

    frame = pd.read_csv(curve.path)
    validate_columns(
        frame,
        {curve.x_column, curve.y_column},
        f"Concentration curve {curve.name!r}",
    )
    normalized = frame[[curve.x_column, curve.y_column]].copy()
    normalized.columns = [SHARED_X_COLUMN, curve.name]
    for column in normalized.columns:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    validate_concentration_curve(normalized, curve.name)
    return normalized


def validate_concentration_curve(
    frame: pd.DataFrame,
    curve_id: str,
) -> None:
    """Validate bounds, order, monotonicity, and endpoints for one curve."""
    validate_curve_id(curve_id)
    validate_columns(
        frame,
        {SHARED_X_COLUMN, curve_id},
        f"Concentration curve {curve_id!r}",
    )
    if frame.empty:
        raise ValueError(f"Concentration curve {curve_id!r} contains no rows")

    values = frame[[SHARED_X_COLUMN, curve_id]].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError(
            f"Concentration curve {curve_id!r} contains blank or non-finite values"
        )

    x_values = values[:, 0]
    y_values = values[:, 1]
    if np.any(x_values < -NUMERIC_TOLERANCE) or np.any(
        x_values > 1 + NUMERIC_TOLERANCE
    ):
        raise ValueError(
            f"Concentration curve {curve_id!r} has X values outside [0, 1]"
        )
    if np.any(y_values < -NUMERIC_TOLERANCE) or np.any(
        y_values > 1 + NUMERIC_TOLERANCE
    ):
        raise ValueError(
            f"Concentration curve {curve_id!r} has Y values outside [0, 1]"
        )
    if np.any(np.diff(x_values) <= 0):
        raise ValueError(
            f"Concentration curve {curve_id!r} X values must be unique and "
            "strictly increasing"
        )
    if np.any(np.diff(y_values) < -NUMERIC_TOLERANCE):
        raise ValueError(
            f"Concentration curve {curve_id!r} Y values must be non-decreasing"
        )
    if not np.allclose(
        values[[0, -1]],
        np.array([[0.0, 0.0], [1.0, 1.0]]),
        atol=NUMERIC_TOLERANCE,
        rtol=0,
    ):
        raise ValueError(
            f"Concentration curve {curve_id!r} must start at (0, 0) and end "
            "at (1, 1)"
        )


def build_concentration_curve_output(config: PipelineConfig) -> pd.DataFrame:
    """Combine all registered curves on one identical population-share grid."""
    if not config.concentration_curves:
        raise ValueError("No concentration curves are registered")

    combined: pd.DataFrame | None = None
    for curve in config.concentration_curves.values():
        frame = load_concentration_curve(curve)
        if combined is None:
            combined = frame
            continue

        if len(frame) != len(combined) or not np.allclose(
            frame[SHARED_X_COLUMN].to_numpy(),
            combined[SHARED_X_COLUMN].to_numpy(),
            atol=NUMERIC_TOLERANCE,
            rtol=0,
        ):
            raise ValueError(
                f"Concentration curve {curve.name!r} does not use the shared "
                "population-share grid"
            )
        combined[curve.name] = frame[curve.name].to_numpy()

    if combined is None:  # pragma: no cover - guarded above
        raise ValueError("No concentration curves are registered")
    return combined


def concentration_curve_registry_frame(config: PipelineConfig) -> pd.DataFrame:
    """Return registry metadata as a reviewable table for the notebook."""
    rows = []
    for curve in config.concentration_curves.values():
        try:
            display_path = curve.path.relative_to(config.repo_root)
        except ValueError:
            display_path = curve.path
        rows.append(
            {
                "curve_id": curve.name,
                "input_path": display_path,
                "x_column": curve.x_column,
                "y_column": curve.y_column,
                "ranked_by": curve.ranked_by,
                "rank_direction": curve.rank_direction,
                "description": curve.description,
            }
        )
    return pd.DataFrame(rows)


def write_concentration_curve_output(
    frame: pd.DataFrame,
    config: PipelineConfig,
) -> Path:
    """Validate and write the canonical country concentration-curve CSV."""
    expected_columns = [SHARED_X_COLUMN, *config.concentration_curves]
    if list(frame.columns) != expected_columns:
        raise ValueError(
            "Concentration-curve output columns do not match the registry: "
            f"expected {expected_columns}, found {list(frame.columns)}"
        )
    for curve_id in config.concentration_curves:
        validate_concentration_curve(
            frame[[SHARED_X_COLUMN, curve_id]],
            curve_id,
        )

    output_path = config.concentration_curve_output_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    return output_path
