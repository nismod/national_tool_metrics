from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

from national_tool_metrics.concentration_curves import (
    SHARED_X_COLUMN,
    build_concentration_curve_output,
    validate_concentration_curve,
    validate_curve_id,
)
from national_tool_metrics.config import (
    ConcentrationCurveConfig,
    load_country_config,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class ConcentrationCurveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base_config = load_country_config("KEN", repo_root=REPO_ROOT)

    @staticmethod
    def _curve(
        name: str,
        path: Path,
        *,
        y_column: str = "outcome_share",
    ) -> ConcentrationCurveConfig:
        return ConcentrationCurveConfig(
            name=name,
            path=path,
            x_column="population_share",
            y_column=y_column,
            ranked_by="relative_wealth",
            rank_direction="lowest_to_highest",
            description="Test concentration curve.",
        )

    def test_loads_registered_kenya_curve_metadata(self) -> None:
        curve = self.base_config.concentration_curve(
            "flood_risk__jrc__baseline_protected"
        )

        self.assertEqual(curve.x_column, "frac_pop")
        self.assertEqual(curve.y_column, "frac_flood")
        self.assertEqual(curve.rank_direction, "lowest_to_highest")
        self.assertEqual(
            self.base_config.concentration_curve_output_path(),
            REPO_ROOT
            / "results"
            / "KEN"
            / "concentration_curves"
            / "KEN_concentration_curves.csv",
        )

    def test_combines_registered_curves_on_one_shared_grid(self) -> None:
        first = self._curve(
            "flood_risk__jrc__baseline_protected",
            Path("first.csv"),
        )
        second = self._curve(
            "flood_risk__jrc__adaptation_option",
            Path("second.csv"),
        )
        config = replace(
            self.base_config,
            concentration_curves={first.name: first, second.name: second},
        )
        loaded_curves = [
            pd.DataFrame(
                {
                    SHARED_X_COLUMN: [0.0, 0.5, 1.0],
                    first.name: [0.0, 0.4, 1.0],
                }
            ),
            pd.DataFrame(
                {
                    SHARED_X_COLUMN: [0.0, 0.5, 1.0],
                    second.name: [0.0, 0.6, 1.0],
                }
            ),
        ]
        with patch(
            "national_tool_metrics.concentration_curves.load_concentration_curve",
            side_effect=loaded_curves,
        ):
            output = build_concentration_curve_output(config)

        self.assertEqual(
            list(output.columns),
            [SHARED_X_COLUMN, first.name, second.name],
        )
        self.assertEqual(output[SHARED_X_COLUMN].tolist(), [0.0, 0.5, 1.0])
        self.assertEqual(output[second.name].tolist(), [0.0, 0.6, 1.0])

    def test_rejects_a_mismatched_population_share_grid(self) -> None:
        first = self._curve(
            "flood_risk__jrc__baseline_protected",
            Path("first.csv"),
        )
        second = self._curve(
            "flood_risk__jrc__adaptation_option",
            Path("second.csv"),
        )
        config = replace(
            self.base_config,
            concentration_curves={first.name: first, second.name: second},
        )
        loaded_curves = [
            pd.DataFrame(
                {
                    SHARED_X_COLUMN: [0.0, 0.5, 1.0],
                    first.name: [0.0, 0.4, 1.0],
                }
            ),
            pd.DataFrame(
                {
                    SHARED_X_COLUMN: [0.0, 0.25, 1.0],
                    second.name: [0.0, 0.3, 1.0],
                }
            ),
        ]
        with patch(
            "national_tool_metrics.concentration_curves.load_concentration_curve",
            side_effect=loaded_curves,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "shared population-share",
            ):
                build_concentration_curve_output(config)

    def test_rejects_non_monotonic_outcome_values(self) -> None:
        curve_id = "flood_risk__jrc__baseline_protected"
        frame = pd.DataFrame(
            {
                SHARED_X_COLUMN: [0.0, 0.5, 0.75, 1.0],
                curve_id: [0.0, 0.6, 0.5, 1.0],
            }
        )

        with self.assertRaisesRegex(ValueError, "non-decreasing"):
            validate_concentration_curve(frame, curve_id)

    def test_requires_three_component_curve_identifiers(self) -> None:
        validate_curve_id("flood_risk__jrc__baseline_protected")

        with self.assertRaisesRegex(ValueError, "three lowercase"):
            validate_curve_id("socioeconomic__flood_risk__jrc__baseline")


if __name__ == "__main__":
    unittest.main()
