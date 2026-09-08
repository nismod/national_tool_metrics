from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from national_tool_metrics.config import load_country_config
from national_tool_metrics.outputs import (
    CARD_IDENTIFIER_COLUMNS,
    IDENTIFIER_COLUMNS,
    build_card_identifier_frame,
    build_identifier_frame,
    merge_metric_tables,
    namespace_metric_table,
    validate_card_output,
    validate_section_output,
    write_card_output,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class OutputContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_country_config("KEN", repo_root=REPO_ROOT)
        self.admin_regions = gpd.GeoDataFrame(
            {
                "adm_id": ["KEN-1", "KEN-2"],
                "adm_name": ["Region One", "Region Two"],
            },
            geometry=[Point(0, 0), Point(1, 1)],
            crs="EPSG:4326",
        )

    def test_builds_and_validates_section_output(self) -> None:
        identifiers = build_identifier_frame(
            self.admin_regions,
            self.config,
            section="exposure",
        )
        metrics = pd.DataFrame(
            {
                "adm_id": ["KEN-1", "KEN-2"],
                "pop_total": [100.12345, 200.0],
            }
        )

        output = merge_metric_tables(identifiers, [metrics])
        validate_section_output(output, "exposure")

        self.assertEqual(
            list(output.columns[: len(IDENTIFIER_COLUMNS)]),
            IDENTIFIER_COLUMNS,
        )
        self.assertEqual(output["pop_total"].tolist(), [100.123, 200.0])
        self.assertNotIn("geometry", output.columns)

    def test_can_preserve_numeric_no_data(self) -> None:
        identifiers = build_identifier_frame(
            self.admin_regions,
            self.config,
            section="vulnerability",
        )
        metrics = pd.DataFrame(
            {
                "adm_id": ["KEN-1", "KEN-2"],
                "access_minutes": [10.0, float("nan")],
            }
        )

        output = merge_metric_tables(
            identifiers,
            [metrics],
            fill_missing_numeric=False,
        )

        self.assertEqual(output.loc[0, "access_minutes"], 10.0)
        self.assertTrue(pd.isna(output.loc[1, "access_minutes"]))
        validate_section_output(output, "vulnerability")

    def test_rejects_duplicate_output_grain(self) -> None:
        identifiers = build_identifier_frame(
            self.admin_regions,
            self.config,
            section="risk",
        )
        duplicated = pd.concat(
            [identifiers.assign(metric=1), identifiers.iloc[[0]].assign(metric=2)],
            ignore_index=True,
        )

        with self.assertRaisesRegex(ValueError, "duplicate key rows"):
            validate_section_output(duplicated, "risk")

    def test_namespaces_metric_columns_and_rejects_removed_dimensions(
        self,
    ) -> None:
        metrics = pd.DataFrame(
            {"adm_id": ["KEN-1", "KEN-2"], "loss_total": [1, 2]}
        )
        namespaced = namespace_metric_table(
            metrics,
            "river_flood_jrc_baseline",
        )
        self.assertEqual(
            list(namespaced.columns),
            ["adm_id", "river_flood_jrc_baseline_loss_total"],
        )

        identifiers = build_identifier_frame(
            self.admin_regions,
            self.config,
            section="risk",
        )
        invalid = merge_metric_tables(identifiers, [namespaced])
        invalid["hazard"] = "river_flood"
        with self.assertRaisesRegex(ValueError, "removed dimensions"):
            validate_section_output(invalid, "risk")

    def test_rejects_overlapping_metric_names(self) -> None:
        identifiers = build_identifier_frame(
            self.admin_regions,
            self.config,
            section="exposure",
        )
        first = pd.DataFrame(
            {"adm_id": ["KEN-1", "KEN-2"], "pop_total": [100, 200]}
        )
        second = pd.DataFrame(
            {"adm_id": ["KEN-1", "KEN-2"], "pop_total": [101, 201]}
        )

        with self.assertRaisesRegex(ValueError, "overwrite existing columns"):
            merge_metric_tables(identifiers, [first, second])

    def test_builds_validates_and_writes_tidy_card_output(self) -> None:
        identifiers = build_card_identifier_frame(
            self.admin_regions,
            self.config,
            section="hazard",
            card="river_flooding",
        )
        output = identifiers.loc[
            identifiers.index.repeat(2)
        ].reset_index(drop=True)
        output["hazard"] = "river_flood"
        output["return_period_years"] = [10, 20, 10, 20]
        output["metric"] = "flooded_area"
        output["unit"] = "km2"
        output["value"] = [1.0, 2.0, 3.0, 4.0]
        dimensions = (
            "hazard",
            "return_period_years",
            "metric",
            "unit",
        )

        self.assertEqual(
            list(output.columns[: len(CARD_IDENTIFIER_COLUMNS)]),
            CARD_IDENTIFIER_COLUMNS,
        )
        validate_card_output(
            output,
            "hazard",
            "river_flooding",
            dimensions,
        )

        with TemporaryDirectory(dir=REPO_ROOT / "tests") as directory:
            temporary_config = replace(
                self.config,
                repo_root=Path(directory),
            )
            output_path = write_card_output(
                output,
                temporary_config,
                "hazard",
                "river_flooding",
                dimensions,
            )
            self.assertEqual(
                output_path.name,
                "KEN_adm1_hazard_river_flooding_metrics.csv",
            )
            self.assertEqual(pd.read_csv(output_path).shape, output.shape)

    def test_rejects_duplicate_card_parameter_combinations(self) -> None:
        identifiers = build_card_identifier_frame(
            self.admin_regions.iloc[[0]],
            self.config,
            section="hazard",
            card="river_flooding",
        )
        output = pd.concat([identifiers, identifiers], ignore_index=True)
        output["return_period_years"] = 100
        output["metric"] = "flooded_area"
        output["unit"] = "km2"
        output["value"] = [1.0, 2.0]

        with self.assertRaisesRegex(ValueError, "duplicate key rows"):
            validate_card_output(
                output,
                "hazard",
                "river_flooding",
                ("return_period_years", "metric", "unit"),
            )

    def test_allows_declared_optional_card_dimensions(self) -> None:
        output = build_card_identifier_frame(
            self.admin_regions,
            self.config,
            section="risk",
            card="population",
        )
        output["epoch"] = pd.NA
        output["metric"] = "exposed_population"
        output["unit"] = "people"
        output["value"] = [10.0, 20.0]
        dimensions = ("epoch", "metric", "unit")

        validate_card_output(
            output,
            "risk",
            "population",
            dimensions,
            optional_dimension_columns=("epoch",),
        )

        output.loc[0, "metric"] = pd.NA
        with self.assertRaisesRegex(ValueError, "missing parameter values"):
            validate_card_output(
                output,
                "risk",
                "population",
                dimensions,
                optional_dimension_columns=("epoch",),
            )


if __name__ == "__main__":
    unittest.main()
