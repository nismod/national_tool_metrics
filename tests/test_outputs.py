from pathlib import Path
import unittest

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from national_tool_metrics.config import load_country_config
from national_tool_metrics.outputs import (
    IDENTIFIER_COLUMNS,
    build_identifier_frame,
    merge_metric_tables,
    namespace_metric_table,
    validate_section_output,
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


if __name__ == "__main__":
    unittest.main()
