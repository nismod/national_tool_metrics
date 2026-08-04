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
from national_tool_metrics.sections.hazard import (
    RIVER_FLOOD_RETURN_PERIODS,
    build_hazard_metrics,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class HazardMetricTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory(dir=REPO_ROOT / "tests")
        self.addCleanup(self.temporary_directory.cleanup)
        self.hazard_directory = Path(self.temporary_directory.name)
        base_config = load_country_config("KEN", repo_root=REPO_ROOT)
        self.config = replace(
            base_config,
            sources={
                **base_config.sources,
                "river_flood_hazard_dir": self.hazard_directory,
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
            path = self.hazard_directory / (
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

    def test_builds_extent_and_depth_metrics_for_all_return_periods(self) -> None:
        self._write_return_period_rasters()

        output = build_hazard_metrics(self.config, self.admin_regions)
        metrics = output.set_index("adm_id")

        self.assertEqual(output.shape, (2, 37))
        self.assertEqual(set(output["section"]), {"hazard"})
        self.assertEqual(set(output["hazard"]), {"river_flood"})
        self.assertEqual(set(output["scenario"]), {"baseline"})
        self.assertEqual(
            set(output["model_run"]),
            {"jrc_river_flood_baseline"},
        )
        for return_period in RIVER_FLOOD_RETURN_PERIODS:
            self.assertAlmostEqual(
                metrics.loc["KEN-1", f"flooded_area_rp{return_period}_km2"],
                2.0,
                places=3,
            )
            self.assertAlmostEqual(
                metrics.loc[
                    "KEN-1",
                    f"flooded_area_rp{return_period}_pct_admin",
                ],
                50.0,
                places=2,
            )
            self.assertAlmostEqual(
                metrics.loc[
                    "KEN-1",
                    f"flood_depth_mean_rp{return_period}_m",
                ],
                1.25,
                places=3,
            )
            self.assertAlmostEqual(
                metrics.loc[
                    "KEN-1",
                    f"flood_depth_p90_rp{return_period}_m",
                ],
                2.0,
                places=3,
            )
            self.assertAlmostEqual(
                metrics.loc["KEN-2", f"flooded_area_rp{return_period}_km2"],
                3.0,
                places=3,
            )
            self.assertAlmostEqual(
                metrics.loc[
                    "KEN-2",
                    f"flood_depth_p90_rp{return_period}_m",
                ],
                4.0,
                places=3,
            )


if __name__ == "__main__":
    unittest.main()
