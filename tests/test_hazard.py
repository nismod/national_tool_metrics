from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box

from national_tool_metrics.config import load_country_config
from national_tool_metrics.outputs import CARD_IDENTIFIER_COLUMNS
from national_tool_metrics.sections.hazard import (
    RIVER_FLOOD_CARD,
    RIVER_FLOOD_CARD_DIMENSIONS,
    RIVER_FLOOD_RETURN_PERIODS,
    TROPICAL_CYCLONE_CARD,
    TROPICAL_CYCLONE_CARD_DIMENSIONS,
    TROPICAL_CYCLONE_CATEGORY_THRESHOLDS_MS,
    TROPICAL_CYCLONE_RETURN_PERIODS,
    build_hazard_card_metrics,
    build_hazard_metrics,
    build_tropical_cyclone_metrics,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class HazardMetricTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory(dir=REPO_ROOT / "tests")
        self.addCleanup(self.temporary_directory.cleanup)
        temporary_root = Path(self.temporary_directory.name)
        self.flood_directory = temporary_root
        self.cyclone_directory = temporary_root
        base_config = load_country_config("KEN", repo_root=REPO_ROOT)
        self.config = replace(
            base_config,
            sources={
                **base_config.sources,
                "river_flood_hazard_dir": self.flood_directory,
                "tropical_cyclone_hazard_dir": self.cyclone_directory,
            },
        )
        self.admin_regions = gpd.GeoDataFrame(
            {
                "adm_id": ["KEN-1", "KEN-2"],
                "adm_name": ["Region One", "Region Two"],
            },
            geometry=[box(0, 0, 2000, 2000), box(2000, 0, 4000, 2000)],
            crs="EPSG:3857",
        )

    def _write_return_period_rasters(self) -> None:
        values = np.array(
            [
                [0.5, 2.0, 1.0, -9999.0],
                [-9999.0, -9999.0, 3.0, 4.0],
            ],
            dtype="float32",
        )
        for return_period in RIVER_FLOOD_RETURN_PERIODS:
            path = self.flood_directory / (
                f"KEN_jrc-flood_RP{return_period}.tif"
            )
            with rasterio.open(
                path,
                "w",
                driver="GTiff",
                height=2,
                width=4,
                count=1,
                dtype="float32",
                crs="EPSG:3857",
                transform=from_origin(0, 2000, 1000, 1000),
                nodata=-9999,
            ) as target:
                target.write(values, 1)

    def _write_tropical_cyclone_rasters(self) -> None:
        values = np.array(
            [
                [18.1, 29.1, 37.7, 43.5],
                [51.2, 61.7, 70.0, 0.0],
            ],
            dtype="float32",
        )
        for return_period in TROPICAL_CYCLONE_RETURN_PERIODS:
            path = self.cyclone_directory / (
                "STORM_FIXED_RETURN_PERIODS_constant_"
                f"{return_period}_YR_RP.tif"
            )
            with rasterio.open(
                path,
                "w",
                driver="GTiff",
                height=2,
                width=4,
                count=1,
                dtype="float32",
                crs="EPSG:3857",
                transform=from_origin(0, 2000, 1000, 1000),
                nodata=0,
            ) as target:
                target.write(values, 1)

    def test_builds_category_threshold_areas_for_all_return_periods(
        self,
    ) -> None:
        self._write_tropical_cyclone_rasters()

        output = build_tropical_cyclone_metrics(
            self.config,
            self.admin_regions,
        ).set_index("adm_id")

        expected_areas = {
            "KEN-1": {
                "tropical_storm_plus": 4.0,
                "cat1plus": 3.0,
                "cat2plus": 2.0,
                "cat3plus": 2.0,
                "cat4plus": 2.0,
                "cat5plus": 1.0,
            },
            "KEN-2": {
                "tropical_storm_plus": 3.0,
                "cat1plus": 3.0,
                "cat2plus": 3.0,
                "cat3plus": 2.0,
                "cat4plus": 1.0,
                "cat5plus": 1.0,
            },
        }
        self.assertEqual(
            tuple(TROPICAL_CYCLONE_CATEGORY_THRESHOLDS_MS.values()),
            (18.0, 29.0, 37.6, 43.4, 51.1, 61.6),
        )
        for return_period in TROPICAL_CYCLONE_RETURN_PERIODS:
            for adm_id, category_areas in expected_areas.items():
                for category, expected_area in category_areas.items():
                    self.assertAlmostEqual(
                        output.loc[
                            adm_id,
                            f"wind_area_{category}_rp{return_period}_km2",
                        ],
                        expected_area,
                        places=3,
                    )
                    self.assertAlmostEqual(
                        output.loc[
                            adm_id,
                            "wind_area_"
                            f"{category}_rp{return_period}_pct_admin",
                        ],
                        expected_area / 4.0 * 100,
                        places=2,
                    )

    def test_weights_cyclone_cells_by_admin_boundary_intersection(self) -> None:
        self._write_tropical_cyclone_rasters()
        partial_region = gpd.GeoDataFrame(
            {
                "adm_id": ["KEN-PARTIAL"],
                "adm_name": ["Partial Region"],
            },
            geometry=[box(0, 0, 1500, 2000)],
            crs="EPSG:3857",
        )

        output = build_tropical_cyclone_metrics(
            self.config,
            partial_region,
        ).set_index("adm_id")

        self.assertAlmostEqual(
            output.loc[
                "KEN-PARTIAL",
                "wind_area_tropical_storm_plus_rp10_km2",
            ],
            3.0,
            places=3,
        )
        self.assertAlmostEqual(
            output.loc[
                "KEN-PARTIAL",
                "wind_area_cat5plus_rp10_km2",
            ],
            0.5,
            places=3,
        )
        self.assertAlmostEqual(
            output.loc[
                "KEN-PARTIAL",
                "wind_area_tropical_storm_plus_rp10_pct_admin",
            ],
            100.0,
            places=3,
        )

    def test_builds_extent_and_depth_metrics_for_all_return_periods(self) -> None:
        self._write_return_period_rasters()
        self._write_tropical_cyclone_rasters()

        output = build_hazard_metrics(self.config, self.admin_regions)
        metrics = output.set_index("adm_id")

        expected_cyclone_metrics = (
            len(TROPICAL_CYCLONE_RETURN_PERIODS)
            * len(TROPICAL_CYCLONE_CATEGORY_THRESHOLDS_MS)
            * 2
        )
        self.assertEqual(output.shape, (2, 34 + expected_cyclone_metrics))
        self.assertEqual(set(output["section"]), {"hazard"})
        self.assertTrue(
            {"hazard", "scenario", "model_run"}.isdisjoint(output.columns)
        )
        for return_period in RIVER_FLOOD_RETURN_PERIODS:
            self.assertAlmostEqual(
                metrics.loc[
                    "KEN-1",
                    "river_flood_jrc_baseline_"
                    f"flooded_area_rp{return_period}_km2",
                ],
                2.0,
                places=3,
            )
            self.assertAlmostEqual(
                metrics.loc[
                    "KEN-1",
                    "river_flood_jrc_baseline_"
                    f"flooded_area_rp{return_period}_pct_admin",
                ],
                50.0,
                places=2,
            )
            self.assertAlmostEqual(
                metrics.loc[
                    "KEN-1",
                    "river_flood_jrc_baseline_"
                    f"flood_depth_mean_rp{return_period}_m",
                ],
                1.25,
                places=3,
            )
            self.assertAlmostEqual(
                metrics.loc[
                    "KEN-1",
                    "river_flood_jrc_baseline_"
                    f"flood_depth_p90_rp{return_period}_m",
                ],
                2.0,
                places=3,
            )
            self.assertAlmostEqual(
                metrics.loc[
                    "KEN-2",
                    "river_flood_jrc_baseline_"
                    f"flooded_area_rp{return_period}_km2",
                ],
                3.0,
                places=3,
            )
            self.assertAlmostEqual(
                metrics.loc[
                    "KEN-2",
                    "river_flood_jrc_baseline_"
                    f"flood_depth_p90_rp{return_period}_m",
                ],
                4.0,
                places=3,
            )

    def test_builds_one_tidy_csv_table_per_hazard_card(self) -> None:
        self._write_return_period_rasters()
        self._write_tropical_cyclone_rasters()

        cards = build_hazard_card_metrics(self.config, self.admin_regions)

        self.assertEqual(
            set(cards),
            {RIVER_FLOOD_CARD, TROPICAL_CYCLONE_CARD},
        )
        river = cards[RIVER_FLOOD_CARD]
        cyclone = cards[TROPICAL_CYCLONE_CARD]
        self.assertEqual(
            list(river.columns),
            [
                *CARD_IDENTIFIER_COLUMNS,
                *RIVER_FLOOD_CARD_DIMENSIONS,
                "value",
            ],
        )
        self.assertEqual(
            list(cyclone.columns),
            [
                *CARD_IDENTIFIER_COLUMNS,
                *TROPICAL_CYCLONE_CARD_DIMENSIONS,
                "value",
            ],
        )
        self.assertEqual(
            len(river),
            len(self.admin_regions) * len(RIVER_FLOOD_RETURN_PERIODS) * 4,
        )
        self.assertEqual(
            len(cyclone),
            len(self.admin_regions)
            * len(TROPICAL_CYCLONE_RETURN_PERIODS)
            * len(TROPICAL_CYCLONE_CATEGORY_THRESHOLDS_MS)
            * 2,
        )
        self.assertEqual(
            set(river["metric"]),
            {
                "flooded_area",
                "area_flooded_percentage",
                "mean_flood_depth",
                "p90_flood_depth",
            },
        )
        self.assertEqual(
            set(cyclone["return_period_years"]),
            set(TROPICAL_CYCLONE_RETURN_PERIODS),
        )
        self.assertNotIn(75, set(cyclone["return_period_years"]))

        river_value = river.loc[
            (river["adm_id"] == "KEN-1")
            & (river["return_period_years"] == 10)
            & (river["metric"] == "mean_flood_depth"),
            "value",
        ].item()
        cyclone_value = cyclone.loc[
            (cyclone["adm_id"] == "KEN-1")
            & (cyclone["return_period_years"] == 10)
            & (cyclone["wind_threshold"] == "cat1plus")
            & (cyclone["display_mode"] == "area"),
            "value",
        ].item()
        self.assertAlmostEqual(river_value, 1.25, places=3)
        self.assertAlmostEqual(cyclone_value, 3.0, places=3)


if __name__ == "__main__":
    unittest.main()
