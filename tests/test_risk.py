from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from national_tool_metrics.config import load_country_config
from national_tool_metrics.outputs import CARD_IDENTIFIER_COLUMNS
from national_tool_metrics.sections.risk import (
    CAPITAL_STOCK_CARD,
    CAPITAL_STOCK_COMPONENT_TOKENS,
    CAPITAL_STOCK_RISK_MAP_PREFIXES,
    DIRECT_DAMAGE_CARD,
    POPULATION_CARD,
    POPULATION_GROUP_TOKENS,
    POPULATION_RISK_MAP_PREFIXES,
    RISK_CARD_DIMENSIONS,
    RETURN_PERIOD_RISK_MAPS,
    assemble_risk_card_metrics,
    assemble_risk_run_metrics,
    build_capital_stock_risk_metrics,
    build_direct_network_risk_metrics,
    build_population_risk_metrics,
    combine_risk_run_outputs,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class RiskMetricTests(unittest.TestCase):
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
        self.river_run = self.config.risk_run(
            "river_flood_jrc_baseline"
        )
        self.cyclone_run = self.config.risk_run(
            "tropical_cyclone_storm_baseline_2020"
        )

    def _population_source(self) -> pd.DataFrame:
        group_values = {
            "total": (100.0, 200.0),
            "female": (50.0, 100.0),
            "male": (50.0, 100.0),
            "children_under5": (10.0, 20.0),
            "school_age_5_14": (20.0, 40.0),
            "working_age_15_64": (60.0, 120.0),
            "older_65plus": (10.0, 20.0),
            "female_15_49": (30.0, 60.0),
            "wealth_q1": (20.0, 40.0),
            "wealth_q2": (20.0, 40.0),
            "wealth_q3": (20.0, 40.0),
            "wealth_q4": (20.0, 40.0),
            "wealth_q5": (20.0, 40.0),
        }
        risk_map_multipliers = {
            "AAR_protected": 1.0,
            "RP10": 1.1,
            "RP20": 1.2,
            "RP50": 1.3,
            "RP75": 1.4,
            "RP100": 1.5,
            "RP200": 1.6,
            "RP500": 1.7,
        }
        records = []
        for risk_map, multiplier in risk_map_multipliers.items():
            for group, values in group_values.items():
                for adm_id, adm_name, value in zip(
                    ["KEN-1", "KEN-2"],
                    ["Region One", "Region Two"],
                    values,
                ):
                    records.append(
                        {
                            "shapeID": adm_id,
                            "shapeName": adm_name,
                            "ISO3": "KEN",
                            "admin_level": "ADM1",
                            "risk_map": risk_map,
                            "population_group": group,
                            "exposed_population": value * multiplier,
                        }
                    )
        return pd.DataFrame(records)

    @patch(
        "national_tool_metrics.sections.risk.read_gpkg_attributes"
    )
    def test_population_includes_protected_aar_and_return_periods(
        self,
        read_mock,
    ) -> None:
        read_mock.return_value = self._population_source()
        self.assertEqual(
            RETURN_PERIOD_RISK_MAPS,
            ("RP10", "RP20", "RP50", "RP75", "RP100", "RP200", "RP500"),
        )

        metrics = build_population_risk_metrics(
            self.config,
            self.admin_regions,
            self.river_run,
        )

        self.assertEqual(len(metrics.columns) - 1, 104)
        self.assertEqual(
            set(metrics.columns).difference({"adm_id"}),
            {
                f"{prefix}_{token}"
                for prefix in POPULATION_RISK_MAP_PREFIXES.values()
                for token in POPULATION_GROUP_TOKENS.values()
            },
        )
        self.assertEqual(
            metrics["flooded_pop_ea_protected_total"].tolist(),
            [100.0, 200.0],
        )
        source_path, source_layer = read_mock.call_args.args
        self.assertEqual(
            source_path.name,
            "KEN_ADM1_jrc_population_risk_metrics.gpkg",
        )
        self.assertEqual(
            source_layer,
            "KEN_ADM1_jrc_population_risk_metrics",
        )
        self.assertEqual(
            metrics["flooded_pop_rp500_total"].tolist(),
            [170.0, 340.0],
        )

    @patch(
        "national_tool_metrics.sections.risk.read_gpkg_attributes"
    )
    def test_population_filename_follows_admin_level(
        self,
        read_mock,
    ) -> None:
        read_mock.return_value = self._population_source().assign(
            admin_level="ADM2"
        )
        adm2_config = replace(
            self.config,
            country=replace(self.config.country, admin_level="adm2"),
        )

        build_population_risk_metrics(
            adm2_config,
            self.admin_regions,
            self.river_run,
        )

        source_path, source_layer = read_mock.call_args.args
        self.assertEqual(
            source_path.name,
            "KEN_ADM2_jrc_population_risk_metrics.gpkg",
        )
        self.assertEqual(
            source_layer,
            "KEN_ADM2_jrc_population_risk_metrics",
        )

    @patch(
        "national_tool_metrics.sections.risk.read_gpkg_attributes"
    )
    def test_population_rejects_missing_group(
        self,
        read_mock,
    ) -> None:
        source = self._population_source()
        read_mock.return_value = source[
            source["population_group"] != "wealth_q5"
        ]

        with self.assertRaisesRegex(ValueError, "Missing"):
            build_population_risk_metrics(
                self.config,
                self.admin_regions,
                self.river_run,
            )

    @patch(
        "national_tool_metrics.sections.risk.read_gpkg_attributes"
    )
    def test_population_rejects_non_monotonic_return_periods(
        self,
        read_mock,
    ) -> None:
        source = self._population_source()
        rp20_rows = source["risk_map"] == "RP20"
        source.loc[rp20_rows, "exposed_population"] *= 0.5
        read_mock.return_value = source

        with self.assertRaisesRegex(ValueError, "not monotonic"):
            build_population_risk_metrics(
                self.config,
                self.admin_regions,
                self.river_run,
            )

    @patch(
        "national_tool_metrics.sections.risk.read_gpkg_attributes"
    )
    def test_capital_stock_components_reconcile(
        self,
        read_mock,
    ) -> None:
        multipliers = {
            "protected_AAR": 1.0,
            "RP10": 2.0,
            "RP20": 3.0,
            "RP50": 4.0,
            "RP75": 5.0,
            "RP100": 6.0,
            "RP200": 7.0,
            "RP500": 8.0,
        }

        def read_source(path, layer):
            risk_map = next(
                key for key in multipliers if f"_{key}_" in path.name
            )
            multiplier = multipliers[risk_map]
            self.assertEqual(path.stem, layer)
            return pd.DataFrame(
                {
                    "shapeID": ["KEN-1", "KEN-2"],
                    "shapeName": ["Region One", "Region Two"],
                    "res_losses": [10.0, 20.0],
                    "nres_losses": [20.0, 30.0],
                    "infr_losses": [30.0, 40.0],
                    "total_losses": [60.0, 90.0],
                }
            ).assign(
                **{
                    column: lambda frame, column=column: (
                        frame[column] * multiplier
                    )
                    for column in CAPITAL_STOCK_COMPONENT_TOKENS
                }
            )

        read_mock.side_effect = read_source

        metrics = build_capital_stock_risk_metrics(
            self.config,
            self.admin_regions,
            self.river_run,
        )

        self.assertEqual(
            metrics["capstock_aal_total"].tolist(),
            [60.0, 90.0],
        )
        self.assertEqual(len(metrics.columns) - 1, 32)
        self.assertEqual(
            set(metrics.columns).difference({"adm_id"}),
            {
                f"{prefix}_{component}"
                for prefix in CAPITAL_STOCK_RISK_MAP_PREFIXES.values()
                for component in CAPITAL_STOCK_COMPONENT_TOKENS.values()
            },
        )
        self.assertEqual(
            metrics["capstock_rp500_total"].tolist(),
            [480.0, 720.0],
        )
        self.assertEqual(read_mock.call_count, 8)

    @patch(
        "national_tool_metrics.sections.risk.read_gpkg_attributes"
    )
    def test_capital_stock_rejects_non_monotonic_national_totals(
        self,
        read_mock,
    ) -> None:
        multipliers = {
            "protected_AAR": 1.0,
            "RP10": 3.0,
            "RP20": 2.0,
            "RP50": 4.0,
            "RP75": 5.0,
            "RP100": 6.0,
            "RP200": 7.0,
            "RP500": 8.0,
        }

        def read_source(path, _layer):
            risk_map = next(
                key for key in multipliers if f"_{key}_" in path.name
            )
            multiplier = multipliers[risk_map]
            return pd.DataFrame(
                {
                    "shapeID": ["KEN-1", "KEN-2"],
                    "shapeName": ["Region One", "Region Two"],
                    "res_losses": [10.0, 20.0],
                    "nres_losses": [20.0, 30.0],
                    "infr_losses": [30.0, 40.0],
                    "total_losses": [60.0, 90.0],
                }
            ).assign(
                **{
                    column: lambda frame, column=column: (
                        frame[column] * multiplier
                    )
                    for column in CAPITAL_STOCK_COMPONENT_TOKENS
                }
            )

        read_mock.side_effect = read_source

        with self.assertRaisesRegex(ValueError, "not monotonic"):
            build_capital_stock_risk_metrics(
                self.config,
                self.admin_regions,
                self.river_run,
            )

    @patch(
        "national_tool_metrics.sections.risk.line_ead_by_admin"
    )
    def test_direct_networks_include_jrc_roads_and_rail(
        self,
        line_ead_mock,
    ) -> None:
        line_ead_mock.side_effect = [
            pd.DataFrame(
                {
                    "adm_id": ["KEN-1", "KEN-2"],
                    "road_ead_total": [30.0, 70.0],
                    "road_ead_primary": [10.0, 20.0],
                    "road_ead_secondary": [20.0, 50.0],
                }
            ),
            pd.DataFrame(
                {
                    "adm_id": ["KEN-1", "KEN-2"],
                    "rail_ead_total": [5.0, 10.0],
                }
            ),
        ]

        metrics = build_direct_network_risk_metrics(
            self.config,
            self.admin_regions,
            self.river_run,
        )

        self.assertEqual(line_ead_mock.call_count, 2)
        self.assertIn("road_ead_total", metrics.columns)
        self.assertIn("rail_ead_total", metrics.columns)

    @patch(
        "national_tool_metrics.sections.risk.line_ead_by_admin"
    )
    def test_all_zero_cyclone_power_risk_is_valid(
        self,
        line_ead_mock,
    ) -> None:
        line_ead_mock.return_value = pd.DataFrame(
            {
                "adm_id": ["KEN-1", "KEN-2"],
                "power_ead_total": [0.0, 0.0],
            }
        )

        metrics = build_direct_network_risk_metrics(
            self.config,
            self.admin_regions,
            self.cyclone_run,
        )

        self.assertEqual(metrics["power_ead_total"].tolist(), [0.0, 0.0])

    def test_combined_output_merges_namespaced_runs_horizontally(
        self,
    ) -> None:
        river = assemble_risk_run_metrics(
            self.config,
            self.admin_regions,
            self.river_run,
            [
                pd.DataFrame(
                    {
                        "adm_id": ["KEN-1", "KEN-2"],
                        "flooded_pop_ea_protected_total": [10.0, 20.0],
                    }
                )
            ],
        )
        cyclone = assemble_risk_run_metrics(
            self.config,
            self.admin_regions,
            self.cyclone_run,
            [
                pd.DataFrame(
                    {
                        "adm_id": ["KEN-1", "KEN-2"],
                        "power_ead_total": [0.0, 0.0],
                    }
                )
            ],
        )

        combined = combine_risk_run_outputs([river, cyclone])

        self.assertEqual(len(combined), 2)
        self.assertTrue(
            {"hazard", "scenario", "model_run"}.isdisjoint(combined.columns)
        )
        self.assertEqual(
            combined[
                "river_flood_jrc_baseline_"
                "flooded_pop_ea_protected_total"
            ].tolist(),
            [10.0, 20.0],
        )
        self.assertEqual(
            combined[
                "tropical_cyclone_storm_baseline_2020_power_ead_total"
            ].tolist(),
            [0.0, 0.0],
        )

    def test_builds_three_tidy_risk_card_tables(self) -> None:
        population_columns = {"adm_id": ["KEN-1", "KEN-2"]}
        for risk_order, prefix in enumerate(
            POPULATION_RISK_MAP_PREFIXES.values(),
            start=1,
        ):
            for token in POPULATION_GROUP_TOKENS.values():
                population_columns[f"{prefix}_{token}"] = [
                    risk_order * 10.0,
                    risk_order * 20.0,
                ]
        population = pd.DataFrame(population_columns)

        capital = self.admin_regions[["adm_id"]].copy()
        for risk_order, prefix in enumerate(
            CAPITAL_STOCK_RISK_MAP_PREFIXES.values(),
            start=1,
        ):
            for sector in (
                "total",
                "residential",
                "non_residential",
                "infrastructure",
            ):
                capital[f"{prefix}_{sector}"] = [
                    risk_order * 100.0,
                    risk_order * 200.0,
                ]

        river_direct = pd.DataFrame(
            {
                "adm_id": ["KEN-1", "KEN-2"],
                "road_ead_total": [100.0, 200.0],
                "road_ead_trunk": [10.0, 20.0],
                "road_ead_primary": [20.0, 40.0],
                "road_ead_secondary": [30.0, 60.0],
                "road_ead_tertiary": [40.0, 80.0],
                "rail_ead_total": [5.0, 10.0],
            }
        )
        cyclone_direct = pd.DataFrame(
            {
                "adm_id": ["KEN-1", "KEN-2"],
                "power_ead_total": [7.0, 14.0],
            }
        )

        cards = assemble_risk_card_metrics(
            self.config,
            self.admin_regions,
            population,
            capital,
            river_direct,
            cyclone_direct,
        )

        self.assertEqual(
            set(cards),
            {POPULATION_CARD, CAPITAL_STOCK_CARD, DIRECT_DAMAGE_CARD},
        )
        for card, output in cards.items():
            self.assertEqual(
                list(output.columns),
                [
                    *CARD_IDENTIFIER_COLUMNS,
                    *RISK_CARD_DIMENSIONS[card],
                    "value",
                ],
            )
            self.assertEqual(set(output["section"]), {"risk"})
            self.assertEqual(set(output["card"]), {card})

        population_card = cards[POPULATION_CARD]
        self.assertEqual(len(population_card), 2 * 14 * 8)
        bottom_40 = population_card.loc[
            (population_card["adm_id"] == "KEN-1")
            & (population_card["population_group"] == "bottom_40")
            & (
                population_card["risk_metric"]
                == "average_annual_exposure_protected"
            ),
            "value",
        ].item()
        self.assertEqual(bottom_40, 20.0)
        self.assertEqual(
            set(population_card["population_group"]),
            {
                "total",
                "female",
                "male",
                "infant",
                "schoolage",
                "working",
                "childbearing",
                "elderly",
                "q1",
                "q2",
                "q3",
                "q4",
                "q5",
                "bottom_40",
            },
        )
        self.assertEqual(
            set(
                population_card.loc[
                    population_card["risk_metric"]
                    == "average_annual_exposure_protected",
                    "unit",
                ]
            ),
            {"people_per_year"},
        )
        self.assertEqual(
            set(population_card["risk_subsection"]),
            {"socioeconomic"},
        )
        self.assertEqual(set(population_card["hazard"]), {"river_flood"})
        self.assertNotIn("metric", population_card.columns)
        self.assertNotIn("epoch", population_card.columns)

        capital_card = cards[CAPITAL_STOCK_CARD]
        self.assertEqual(len(capital_card), 2 * 4 * 8)
        self.assertEqual(
            set(
                capital_card.loc[
                    capital_card["risk_metric"].str.startswith("rp"),
                    "unit",
                ]
            ),
            {"usd"},
        )
        self.assertEqual(
            set(capital_card["risk_subsection"]),
            {"socioeconomic"},
        )
        self.assertEqual(
            set(capital_card["risk_metric"]),
            {
                "average_annual_loss_protected",
                "rp10",
                "rp20",
                "rp50",
                "rp75",
                "rp100",
                "rp200",
                "rp500",
            },
        )

        direct_card = cards[DIRECT_DAMAGE_CARD]
        self.assertEqual(len(direct_card), 2 * 8)
        self.assertEqual(
            set(direct_card["risk_subsection"]),
            {"infrastructure_networks"},
        )
        missing_motorway = direct_card.loc[
            (direct_card["infrastructure_type"] == "road")
            & (direct_card["asset_class"] == "motorway"),
            "value",
        ]
        self.assertEqual(missing_motorway.tolist(), [0.0, 0.0])
        cyclone = direct_card.loc[
            direct_card["hazard"] == "tropical_cyclone"
        ]
        self.assertEqual(set(cyclone["model"]), {"storm"})
        self.assertEqual(set(cyclone["epoch"]), {2020})
        self.assertEqual(set(cyclone["infrastructure_type"]), {"power"})


if __name__ == "__main__":
    unittest.main()
