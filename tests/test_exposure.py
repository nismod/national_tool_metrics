from pathlib import Path
import unittest
from unittest.mock import patch

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from national_tool_metrics.config import load_country_config
from national_tool_metrics.outputs import CARD_IDENTIFIER_COLUMNS
from national_tool_metrics.sections.exposure import (
    CAPITAL_STOCK_CARD,
    DEMOGRAPHIC_GROUP_METRICS,
    EDUCATIONAL_FACILITIES_CARD,
    EXPOSURE_CARD_DIMENSIONS,
    HEALTHCARE_FACILITIES_CARD,
    POPULATION_CARD,
    POWER_CARD,
    RAIL_CARD,
    ROADS_CARD,
    build_exposure_card_metrics,
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
    def test_population_uses_90m_aggregated_demographic_rasters(
        self,
        zonal_sum_mock,
    ) -> None:
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
        raster_names = {
            call.args[0].name for call in zonal_sum_mock.call_args_list
        }
        self.assertEqual(
            raster_names,
            {
                "KEN_worldpop_total.tif",
                "KEN_worldpop_female.tif",
                "KEN_worldpop_male.tif",
                "KEN_worldpop_children_under5.tif",
                "KEN_worldpop_school-age_5-14.tif",
                "KEN_worldpop_working-age_15-64.tif",
                "KEN_worldpop_older_65plus.tif",
                "KEN_worldpop_female_15-49.tif",
            },
        )

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
        self.assertTrue(
            {"hazard", "scenario", "model_run"}.isdisjoint(output.columns)
        )
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

    def test_builds_seven_tidy_exposure_card_tables(self) -> None:
        population = pd.DataFrame(
            {
                "adm_id": ["KEN-1", "KEN-2"],
                "pop_total": [100.0, 0.0],
                "pop_female": [60.0, 0.0],
                "pop_male": [40.0, 0.0],
                "pop_under_5": [10.0, 0.0],
                "pop_school_children_5_14": [15.0, 0.0],
                "pop_working_age_15_64": [70.0, 0.0],
                "pop_female_childbearing_15_49": [20.0, 0.0],
                "pop_older_65_plus": [5.0, 0.0],
            }
        )
        capital_stock = pd.DataFrame(
            {
                "adm_id": ["KEN-1", "KEN-2"],
                "capstock_residential": [100.0, 200.0],
                "capstock_non_residential": [200.0, 300.0],
                "capstock_infrastructure": [300.0, 400.0],
            }
        )
        networks = pd.DataFrame(
            {
                "adm_id": ["KEN-1", "KEN-2"],
                "road_length_trunk_km": [10.0, 1.0],
                "road_length_primary_km": [20.0, 2.0],
                "road_length_secondary_km": [30.0, 3.0],
                "road_length_tertiary_km": [40.0, 4.0],
                "rail_length_km": [5.0, 6.0],
                "power_transmission_length_km": [7.0, 8.0],
            }
        )
        facilities = pd.DataFrame(
            {
                "adm_id": ["KEN-1", "KEN-2"],
                "gov_hospitals_count": [5.0, 1.0],
                "gov_schools_count": [10.0, 2.0],
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
            cards = build_exposure_card_metrics(
                self.config,
                self.admin_regions,
            )

        expected_cards = {
            POPULATION_CARD,
            CAPITAL_STOCK_CARD,
            ROADS_CARD,
            RAIL_CARD,
            POWER_CARD,
            HEALTHCARE_FACILITIES_CARD,
            EDUCATIONAL_FACILITIES_CARD,
        }
        self.assertEqual(set(cards), expected_cards)
        for card, output in cards.items():
            self.assertEqual(
                list(output.columns),
                [
                    *CARD_IDENTIFIER_COLUMNS,
                    *EXPOSURE_CARD_DIMENSIONS[card],
                    "value",
                ],
            )

        self.assertEqual(len(cards[POPULATION_CARD]), 2 * 8 * 2)
        self.assertEqual(len(cards[CAPITAL_STOCK_CARD]), 2 * 4)
        self.assertEqual(len(cards[ROADS_CARD]), 2 * 6)
        self.assertEqual(len(cards[RAIL_CARD]), 2)
        self.assertEqual(len(cards[POWER_CARD]), 2)
        self.assertEqual(len(cards[HEALTHCARE_FACILITIES_CARD]), 2 * 9)
        self.assertEqual(len(cards[EDUCATIONAL_FACILITIES_CARD]), 2 * 9)
        self.assertEqual(
            list(DEMOGRAPHIC_GROUP_METRICS),
            [
                "total",
                "female",
                "male",
                "infant",
                "schoolage",
                "working",
                "childbearing",
                "elderly",
            ],
        )

        population_card = cards[POPULATION_CARD]
        childbearing_percentage = population_card.loc[
            (population_card["adm_id"] == "KEN-1")
            & (population_card["demographic_group"] == "childbearing")
            & (population_card["display_mode"] == "percentage"),
            "value",
        ].item()
        self.assertEqual(childbearing_percentage, 20.0)
        self.assertTrue(
            pd.isna(
                population_card.loc[
                    (population_card["adm_id"] == "KEN-2")
                    & (population_card["demographic_group"] == "total")
                    & (population_card["display_mode"] == "percentage"),
                    "value",
                ].item()
            )
        )

        capital_card = cards[CAPITAL_STOCK_CARD]
        self.assertEqual(
            capital_card.loc[
                (capital_card["adm_id"] == "KEN-1")
                & (capital_card["sector"] == "total"),
                "value",
            ].item(),
            600.0,
        )
        roads_card = cards[ROADS_CARD]
        self.assertEqual(
            roads_card.loc[
                (roads_card["adm_id"] == "KEN-1")
                & (roads_card["road_class"] == "all"),
                "value",
            ].item(),
            100.0,
        )
        self.assertEqual(
            roads_card.loc[
                (roads_card["adm_id"] == "KEN-1")
                & (roads_card["road_class"] == "motorway"),
                "value",
            ].item(),
            0.0,
        )

        healthcare = cards[HEALTHCARE_FACILITIES_CARD]
        female_rate = healthcare.loc[
            (healthcare["adm_id"] == "KEN-1")
            & (healthcare["metric"] == "per_100k")
            & (healthcare["demographic_group"] == "female"),
            "value",
        ].item()
        self.assertAlmostEqual(female_rate, 8333.333, places=3)
        self.assertTrue(
            pd.isna(
                healthcare.loc[
                    (healthcare["adm_id"] == "KEN-2")
                    & (healthcare["metric"] == "per_100k")
                    & (healthcare["demographic_group"] == "total"),
                    "value",
                ].item()
            )
        )


if __name__ == "__main__":
    unittest.main()
