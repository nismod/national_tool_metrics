from pathlib import Path
import unittest
from unittest.mock import patch

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from national_tool_metrics.config import load_country_config
from national_tool_metrics.sections.exposure import (
    build_exposure_metrics,
    build_population_metrics,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class ExposureMetricTests(unittest.TestCase):
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

    @patch(
        "national_tool_metrics.sections.exposure.zonal_raster_sum"
    )
    @patch(
        "national_tool_metrics.sections.exposure.find_single_raster"
    )
    @patch(
        "national_tool_metrics.sections.exposure._worldpop_inventory"
    )
    def test_population_contains_agreed_demographics_without_youth(
        self,
        inventory_mock,
        total_raster_mock,
        zonal_sum_mock,
    ) -> None:
        ages = [0, 1, *range(5, 95, 5)]
        inventory_mock.return_value = pd.DataFrame(
            [
                {
                    "sex": sex,
                    "age_start": age,
                    "path": Path(f"{sex}_{age:02}.tif"),
                }
                for sex in ("f", "m", "t")
                for age in ages
            ]
        )
        total_raster_mock.return_value = Path("total_population.tif")
        zonal_sum_mock.return_value = pd.Series(
            [10.0, 20.0],
            index=self.admin_regions.index,
        )

        metrics = build_population_metrics(
            self.config,
            self.admin_regions,
        )

        expected_columns = {
            "adm_id",
            "pop_total",
            "pop_female",
            "pop_male",
            "pop_under_5",
            "pop_school_children_5_14",
            "pop_working_age_15_64",
            "pop_older_65_plus",
            "pop_female_childbearing_15_49",
        }
        self.assertEqual(set(metrics.columns), expected_columns)
        self.assertNotIn("pop_youth_15_24", metrics.columns)

    def test_complete_exposure_output_uses_seven_card_groups(self) -> None:
        population = pd.DataFrame(
            {"adm_id": ["KEN-1", "KEN-2"], "pop_total": [100, 200]}
        )
        capital_stock = pd.DataFrame(
            {
                "adm_id": ["KEN-1", "KEN-2"],
                "capstock_residential": [1_000, 2_000],
            }
        )
        networks = pd.DataFrame(
            {
                "adm_id": ["KEN-1", "KEN-2"],
                "road_length_primary_km": [10, 20],
                "rail_length_km": [1, 2],
                "power_transmission_length_km": [3, 4],
            }
        )
        facilities = pd.DataFrame(
            {
                "adm_id": ["KEN-1", "KEN-2"],
                "gov_hospitals_count": [5, 6],
                "gov_schools_count": [7, 8],
            }
        )

        with (
            patch(
                "national_tool_metrics.sections.exposure."
                "build_population_metrics",
                return_value=population,
            ),
            patch(
                "national_tool_metrics.sections.exposure."
                "build_capital_stock_metrics",
                return_value=capital_stock,
            ),
            patch(
                "national_tool_metrics.sections.exposure."
                "build_network_metrics",
                return_value=networks,
            ),
            patch(
                "national_tool_metrics.sections.exposure."
                "build_facility_metrics",
                return_value=facilities,
            ),
        ):
            output = build_exposure_metrics(
                self.config,
                self.admin_regions,
            )

        self.assertEqual(set(output["section"]), {"exposure"})
        self.assertEqual(set(output["hazard"]), {"none"})
        self.assertEqual(set(output["scenario"]), {"baseline"})
        self.assertEqual(set(output["model_run"]), {"baseline_inputs"})
        for metric_name in (
            "pop_total",
            "capstock_residential",
            "road_length_primary_km",
            "rail_length_km",
            "power_transmission_length_km",
            "gov_hospitals_count",
            "gov_schools_count",
        ):
            self.assertIn(metric_name, output.columns)


if __name__ == "__main__":
    unittest.main()
