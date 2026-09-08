from dataclasses import replace
from pathlib import Path
import re
import unittest
from unittest.mock import patch

import pandas as pd

from national_tool_metrics.config import load_country_config
from national_tool_metrics.outputs import CARD_IDENTIFIER_COLUMNS
from national_tool_metrics.sections.adaptation_outcomes import (
    ADAPTATION_OUTCOMES_CARD_DIMENSIONS,
    DRY_PROOFING_CARD,
    FLOOD_PROTECTION_CARD,
    FLOOD_PROTECTION_RETURN_PERIODS,
    RELOCATION_CARD,
    URBANISATION_THRESHOLDS,
    assemble_adaptation_outcomes_card_metrics,
    build_adaptation_outcomes_card_metrics,
    build_dry_proofing_metrics,
    build_flood_protection_metrics,
    build_relocation_metrics,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class AdaptationOutcomesMetricTests(unittest.TestCase):
    def setUp(self) -> None:
        base_config = load_country_config("KEN", repo_root=REPO_ROOT)
        self.config = replace(
            base_config,
            sources={
                **base_config.sources,
                "adaptation_outcomes_dir": REPO_ROOT / "unused-test-data",
            },
        )
        self.admin_regions = pd.DataFrame(
            {
                "adm_id": ["KEN-1", "KEN-2"],
                "adm_name": ["Region One", "Region Two"],
            }
        )
        identifiers = {
            "shapeID": ["KEN-1", "KEN-2"],
            "shapeName": ["Region One", "Region Two"],
        }
        self.sources = {
            "cost": pd.DataFrame(
                {
                    **identifiers,
                    "area_dry-proofed": [2_000_000, 4_000_000],
                }
            ),
            "economic_baseline": pd.DataFrame(
                {
                    **identifiers,
                    "res_losses": [100.0, 200.0],
                    "nres_losses": [20.0, 40.0],
                    "infr_losses": [30.0, 60.0],
                    "total_losses": [150.0, 300.0],
                }
            ),
            "economic_adapted": pd.DataFrame(
                {
                    **identifiers,
                    "res_losses": [80.0, 220.0],
                    "nres_losses": [20.0, 40.0],
                    "infr_losses": [25.0, 60.0],
                    "total_losses": [125.0, 320.0],
                }
            ),
            "social_baseline": self._social_source(
                identifiers,
                total=[100.0, 200.0],
                quintiles=[
                    [10.0, 30.0],
                    [15.0, 35.0],
                    [20.0, 40.0],
                    [25.0, 45.0],
                    [30.0, 50.0],
                ],
                concentration_index=[0.2, -0.1],
            ),
            "social_adapted": self._social_source(
                identifiers,
                total=[80.0, 220.0],
                quintiles=[
                    [5.0, 40.0],
                    [10.0, 40.0],
                    [15.0, 40.0],
                    [20.0, 50.0],
                    [30.0, 50.0],
                ],
                concentration_index=[0.1, -0.2],
            ),
        }
        self.relocation_costs = {
            code: pd.DataFrame(
                {
                    **identifiers,
                    "capstock_relocated": [code * 1_000.0, code * 2_000.0],
                }
            )
            for code in URBANISATION_THRESHOLDS
        }
        self.relocation_economic_adapted = {
            code: self.sources["economic_adapted"].copy()
            for code in URBANISATION_THRESHOLDS
        }
        self.relocation_social_adapted = {
            code: self.sources["social_adapted"].copy()
            for code in URBANISATION_THRESHOLDS
        }
        self.flood_protection_costs = {
            (return_period, code): pd.DataFrame(
                {
                    **identifiers,
                    "adaptation_cost": [
                        return_period * code * 100.0,
                        return_period * code * 200.0,
                    ],
                    "adj_adaptation_cost": [1.0, 2.0],
                    "min_adaptation_cost": [
                        return_period * code * 50.0,
                        return_period * code * 100.0,
                    ],
                    "max_adaptation_cost": [
                        return_period * code * 300.0,
                        return_period * code * 600.0,
                    ],
                }
            )
            for return_period in FLOOD_PROTECTION_RETURN_PERIODS
            for code in URBANISATION_THRESHOLDS
        }
        self.flood_protection_economic_adapted = {
            (return_period, code): self.sources["economic_adapted"].copy()
            for return_period in FLOOD_PROTECTION_RETURN_PERIODS
            for code in URBANISATION_THRESHOLDS
        }
        self.flood_protection_social_adapted = {
            (return_period, code): self.sources["social_adapted"].copy()
            for return_period in FLOOD_PROTECTION_RETURN_PERIODS
            for code in URBANISATION_THRESHOLDS
        }

    @staticmethod
    def _social_source(
        identifiers: dict[str, list[str]],
        *,
        total: list[float],
        quintiles: list[list[float]],
        concentration_index: list[float],
    ) -> pd.DataFrame:
        return pd.DataFrame(
            {
                **identifiers,
                "CI": concentration_index,
                "QR": [1.0, 1.0],
                "Population": [1_000.0, 2_000.0],
                "Population Coverage (%)": [100.0, 100.0],
                "Total Flood Risk": total,
                **{
                    f"Q{index} Flood Risk": values
                    for index, values in enumerate(quintiles, start=1)
                },
            }
        )

    def _read_source(self, path: Path, layer_name: str) -> pd.DataFrame:
        del path
        threshold_match = re.search(r"duc(\d+)", layer_name)
        threshold_code = (
            int(threshold_match.group(1)) if threshold_match else None
        )
        return_period_match = re.search(r"rp(\d+)", layer_name)
        return_period = (
            int(return_period_match.group(1))
            if return_period_match
            else None
        )
        scenario = (return_period, threshold_code)
        if "adaptation-cost_fp" in layer_name:
            return self.flood_protection_costs[scenario].copy()
        if "AALs_adapted_fp" in layer_name:
            return self.flood_protection_economic_adapted[scenario].copy()
        if "adapted_AAR_V-EXP_S-rwi_fp" in layer_name:
            return self.flood_protection_social_adapted[scenario].copy()
        if "adaptation-cost_rl" in layer_name:
            return self.relocation_costs[threshold_code].copy()
        if "AALs_adapted_rl" in layer_name:
            return self.relocation_economic_adapted[threshold_code].copy()
        if "adapted_AAR_V-EXP_S-rwi_rl" in layer_name:
            return self.relocation_social_adapted[threshold_code].copy()
        if "adaptation-cost" in layer_name:
            return self.sources["cost"].copy()
        if "AALs_adapted_dp_capstock" in layer_name:
            return self.sources["economic_adapted"].copy()
        if "protected_AAR_baseline_capstock" in layer_name:
            return self.sources["economic_baseline"].copy()
        if "adapted_AAR_V-EXP_S-rwi_dp" in layer_name:
            return self.sources["social_adapted"].copy()
        if "protected_AAR_V-EXP_S-rwi" in layer_name:
            return self.sources["social_baseline"].copy()
        raise AssertionError(f"Unexpected layer: {layer_name}")

    @patch(
        "national_tool_metrics.sections.adaptation_outcomes."
        "read_gpkg_attributes"
    )
    def test_builds_dry_proofing_metrics_and_retains_negative_avoided_values(
        self,
        read_gpkg_attributes,
    ) -> None:
        read_gpkg_attributes.side_effect = self._read_source

        metrics = build_dry_proofing_metrics(
            self.config,
            self.admin_regions,
        ).set_index("adm_id")

        self.assertEqual(
            metrics.loc["KEN-1", "cost_area_dry_proofed_m2"],
            2_000_000,
        )
        self.assertEqual(
            metrics.loc["KEN-1", "economic_avoided_residential"],
            20,
        )
        self.assertEqual(
            metrics.loc["KEN-2", "economic_avoided_residential"],
            -20,
        )
        self.assertEqual(metrics.loc["KEN-2", "social_avoided_q1"], -10)
        self.assertAlmostEqual(metrics.loc["KEN-1", "social_change_ci"], -0.1)

    @patch(
        "national_tool_metrics.sections.adaptation_outcomes."
        "read_gpkg_attributes"
    )
    def test_card_has_approved_rows_without_percentages_or_quintile_ratio(
        self,
        read_gpkg_attributes,
    ) -> None:
        read_gpkg_attributes.side_effect = self._read_source
        metrics = build_dry_proofing_metrics(self.config, self.admin_regions)

        cards = assemble_adaptation_outcomes_card_metrics(
            self.config,
            self.admin_regions,
            metrics,
        )
        card = cards[DRY_PROOFING_CARD]

        self.assertEqual(len(card), 68)
        self.assertEqual(
            list(card.columns),
            [
                *CARD_IDENTIFIER_COLUMNS,
                *ADAPTATION_OUTCOMES_CARD_DIMENSIONS[DRY_PROOFING_CARD],
                "value",
            ],
        )
        self.assertEqual(set(card["card"]), {"dry_proofing"})
        self.assertNotIn("reduction_percent", set(card["statistic"]))
        self.assertNotIn("quintile_ratio", set(card["metric"]))
        area = card[card["metric"] == "area_dry_proofed"].iloc[0]
        self.assertEqual(area["unit"], "m2")
        self.assertEqual(area["value"], 2_000_000)
        self.assertEqual(
            set(card.loc[card["metric"] == "concentration_index", "statistic"]),
            {"baseline", "adapted", "change"},
        )
        duplicate_key = [
            *CARD_IDENTIFIER_COLUMNS,
            *ADAPTATION_OUTCOMES_CARD_DIMENSIONS[DRY_PROOFING_CARD],
        ]
        self.assertFalse(card.duplicated(duplicate_key).any())

    @patch(
        "national_tool_metrics.sections.adaptation_outcomes."
        "read_gpkg_attributes"
    )
    def test_builds_card_end_to_end(self, read_gpkg_attributes) -> None:
        read_gpkg_attributes.side_effect = self._read_source

        cards = build_adaptation_outcomes_card_metrics(
            self.config,
            self.admin_regions,
        )

        self.assertEqual(
            set(cards),
            {
                DRY_PROOFING_CARD,
                RELOCATION_CARD,
                FLOOD_PROTECTION_CARD,
            },
        )
        self.assertEqual(len(cards[RELOCATION_CARD]), 476)
        self.assertEqual(len(cards[FLOOD_PROTECTION_CARD]), 2_520)

    @patch(
        "national_tool_metrics.sections.adaptation_outcomes."
        "read_gpkg_attributes"
    )
    def test_builds_relocation_metrics_for_every_threshold(
        self,
        read_gpkg_attributes,
    ) -> None:
        read_gpkg_attributes.side_effect = self._read_source

        metrics = build_relocation_metrics(self.config, self.admin_regions)

        self.assertEqual(len(metrics), 14)
        self.assertEqual(
            list(metrics["urbanisation_threshold_code"].drop_duplicates()),
            list(URBANISATION_THRESHOLDS),
        )
        first = metrics[
            (metrics["adm_id"] == "KEN-1")
            & (metrics["urbanisation_threshold_code"] == 11)
        ].iloc[0]
        self.assertEqual(first["urbanisation_threshold"], "remote_area")
        self.assertEqual(first["cost_capstock_relocated"], 11_000)
        self.assertEqual(first["economic_avoided_residential"], 20)
        self.assertAlmostEqual(first["social_change_ci"], -0.1)

    @patch(
        "national_tool_metrics.sections.adaptation_outcomes."
        "read_gpkg_attributes"
    )
    def test_relocation_card_matches_dry_proofing_contract(
        self,
        read_gpkg_attributes,
    ) -> None:
        read_gpkg_attributes.side_effect = self._read_source
        dry_metrics = build_dry_proofing_metrics(
            self.config,
            self.admin_regions,
        )
        relocation_metrics = build_relocation_metrics(
            self.config,
            self.admin_regions,
        )

        card = assemble_adaptation_outcomes_card_metrics(
            self.config,
            self.admin_regions,
            dry_metrics,
            relocation_metrics,
        )[RELOCATION_CARD]

        self.assertEqual(len(card), 476)
        self.assertEqual(
            list(card.columns),
            [
                *CARD_IDENTIFIER_COLUMNS,
                *ADAPTATION_OUTCOMES_CARD_DIMENSIONS[RELOCATION_CARD],
                "value",
            ],
        )
        self.assertNotIn("reduction_percent", set(card["statistic"]))
        self.assertNotIn("quintile_ratio", set(card["metric"]))
        cost = card[card["metric"] == "capstock_relocated"]
        self.assertEqual(set(cost["unit"]), {"usd"})
        self.assertEqual(len(cost), 14)
        concentration_index = card[
            card["metric"] == "concentration_index"
        ]
        self.assertEqual(
            set(concentration_index["statistic"]),
            {"baseline", "adapted", "change"},
        )
        threshold_pairs = card[
            ["urbanisation_threshold_code", "urbanisation_threshold"]
        ].drop_duplicates()
        self.assertEqual(
            threshold_pairs.set_index("urbanisation_threshold_code")[
                "urbanisation_threshold"
            ].to_dict(),
            URBANISATION_THRESHOLDS,
        )
        duplicate_key = [
            *CARD_IDENTIFIER_COLUMNS,
            *ADAPTATION_OUTCOMES_CARD_DIMENSIONS[RELOCATION_CARD],
        ]
        self.assertFalse(card.duplicated(duplicate_key).any())

    @patch(
        "national_tool_metrics.sections.adaptation_outcomes."
        "read_gpkg_attributes"
    )
    def test_builds_flood_protection_metrics_for_every_scenario(
        self,
        read_gpkg_attributes,
    ) -> None:
        read_gpkg_attributes.side_effect = self._read_source

        metrics = build_flood_protection_metrics(
            self.config,
            self.admin_regions,
        )

        self.assertEqual(len(metrics), 70)
        self.assertEqual(
            set(metrics["design_return_period_years"]),
            set(FLOOD_PROTECTION_RETURN_PERIODS),
        )
        scenario = metrics[
            (metrics["adm_id"] == "KEN-1")
            & (metrics["urbanisation_threshold_code"] == 11)
            & (metrics["design_return_period_years"] == 10)
        ].iloc[0]
        self.assertEqual(scenario["urbanisation_threshold"], "remote_area")
        self.assertEqual(scenario["cost_adaptation_cost"], 11_000)
        self.assertEqual(scenario["cost_min_adaptation_cost"], 5_500)
        self.assertEqual(scenario["cost_max_adaptation_cost"], 33_000)
        self.assertEqual(scenario["economic_avoided_residential"], 20)
        self.assertAlmostEqual(scenario["social_change_ci"], -0.1)

    @patch(
        "national_tool_metrics.sections.adaptation_outcomes."
        "read_gpkg_attributes"
    )
    def test_flood_protection_card_has_three_cost_estimates(
        self,
        read_gpkg_attributes,
    ) -> None:
        read_gpkg_attributes.side_effect = self._read_source
        dry_metrics = build_dry_proofing_metrics(
            self.config,
            self.admin_regions,
        )
        flood_protection_metrics = build_flood_protection_metrics(
            self.config,
            self.admin_regions,
        )

        card = assemble_adaptation_outcomes_card_metrics(
            self.config,
            self.admin_regions,
            dry_metrics,
            flood_protection_metrics=flood_protection_metrics,
        )[FLOOD_PROTECTION_CARD]

        self.assertEqual(len(card), 2_520)
        self.assertEqual(
            list(card.columns),
            [
                *CARD_IDENTIFIER_COLUMNS,
                *ADAPTATION_OUTCOMES_CARD_DIMENSIONS[
                    FLOOD_PROTECTION_CARD
                ],
                "value",
            ],
        )
        cost = card[card["metric"] == "adaptation_cost"]
        self.assertEqual(set(cost["statistic"]), {"estimate", "lower", "upper"})
        self.assertEqual(set(cost["unit"]), {"million_usd"})
        self.assertEqual(len(cost), 210)
        self.assertNotIn("adj_adaptation_cost", set(card["metric"]))
        self.assertNotIn("reduction_percent", set(card["statistic"]))
        self.assertNotIn("quintile_ratio", set(card["metric"]))
        duplicate_key = [
            *CARD_IDENTIFIER_COLUMNS,
            *ADAPTATION_OUTCOMES_CARD_DIMENSIONS[FLOOD_PROTECTION_CARD],
        ]
        self.assertFalse(card.duplicated(duplicate_key).any())

    @patch(
        "national_tool_metrics.sections.adaptation_outcomes."
        "read_gpkg_attributes"
    )
    def test_rejects_invalid_flood_protection_cost_order(
        self,
        read_gpkg_attributes,
    ) -> None:
        self.flood_protection_costs[(10, 11)].loc[
            0,
            "min_adaptation_cost",
        ] = 12_000
        read_gpkg_attributes.side_effect = self._read_source

        with self.assertRaisesRegex(ValueError, "lower <= estimate <= upper"):
            build_flood_protection_metrics(self.config, self.admin_regions)

    @patch(
        "national_tool_metrics.sections.adaptation_outcomes."
        "read_gpkg_attributes"
    )
    def test_preserves_jointly_missing_flood_protection_costs(
        self,
        read_gpkg_attributes,
    ) -> None:
        cost = self.flood_protection_costs[(10, 11)]
        cost.loc[
            0,
            [
                "adaptation_cost",
                "min_adaptation_cost",
                "max_adaptation_cost",
            ],
        ] = None
        read_gpkg_attributes.side_effect = self._read_source

        metrics = build_flood_protection_metrics(
            self.config,
            self.admin_regions,
        )
        scenario = metrics[
            (metrics["adm_id"] == "KEN-1")
            & (metrics["urbanisation_threshold_code"] == 11)
            & (metrics["design_return_period_years"] == 10)
        ].iloc[0]

        self.assertTrue(
            scenario[
                [
                    "cost_adaptation_cost",
                    "cost_min_adaptation_cost",
                    "cost_max_adaptation_cost",
                ]
            ].isna().all()
        )

    @patch(
        "national_tool_metrics.sections.adaptation_outcomes."
        "read_gpkg_attributes"
    )
    def test_adm0_synthesizes_iso3_when_sources_omit_shape_id(
        self,
        read_gpkg_attributes,
    ) -> None:
        adm0_config = replace(
            self.config,
            country=replace(self.config.country, admin_level="adm0"),
        )
        adm0_regions = pd.DataFrame(
            {"adm_id": ["KEN"], "adm_name": ["Kenya"]}
        )
        for source_name, source in self.sources.items():
            adm0_source = source.iloc[[0]].copy()
            adm0_source["shapeName"] = "Kenya"
            self.sources[source_name] = adm0_source.drop(columns="shapeID")
        read_gpkg_attributes.side_effect = self._read_source

        metrics = build_dry_proofing_metrics(adm0_config, adm0_regions)
        cards = assemble_adaptation_outcomes_card_metrics(
            adm0_config,
            adm0_regions,
            metrics,
        )
        card = cards[DRY_PROOFING_CARD]

        self.assertEqual(len(card), 34)
        self.assertEqual(set(card["adm_id"]), {"KEN"})

    @patch(
        "national_tool_metrics.sections.adaptation_outcomes."
        "read_gpkg_attributes"
    )
    def test_rejects_economic_components_that_do_not_reconcile(
        self,
        read_gpkg_attributes,
    ) -> None:
        self.sources["economic_baseline"].loc[0, "total_losses"] = 151.0
        read_gpkg_attributes.side_effect = self._read_source

        with self.assertRaisesRegex(ValueError, "do not reconcile"):
            build_dry_proofing_metrics(self.config, self.admin_regions)

    @patch(
        "national_tool_metrics.sections.adaptation_outcomes."
        "read_gpkg_attributes"
    )
    def test_warns_when_social_population_context_differs(
        self,
        read_gpkg_attributes,
    ) -> None:
        self.sources["social_adapted"].loc[0, "Population"] = 999.0
        read_gpkg_attributes.side_effect = self._read_source

        with self.assertWarnsRegex(RuntimeWarning, "Population"):
            build_dry_proofing_metrics(self.config, self.admin_regions)

    @patch(
        "national_tool_metrics.sections.adaptation_outcomes."
        "read_gpkg_attributes"
    )
    def test_preserves_undefined_ci_when_flood_exposure_is_zero(
        self,
        read_gpkg_attributes,
    ) -> None:
        for source_name in ("social_baseline", "social_adapted"):
            source = self.sources[source_name]
            source.loc[0, "CI"] = None
            source.loc[0, "Total Flood Risk"] = 0.0
            for quintile in range(1, 6):
                source.loc[0, f"Q{quintile} Flood Risk"] = 0.0
        read_gpkg_attributes.side_effect = self._read_source

        metrics = build_dry_proofing_metrics(self.config, self.admin_regions)
        cards = assemble_adaptation_outcomes_card_metrics(
            self.config,
            self.admin_regions,
            metrics,
        )
        card = cards[DRY_PROOFING_CARD]
        region_ci = card[
            (card["adm_id"] == "KEN-1")
            & (card["metric"] == "concentration_index")
        ]

        self.assertTrue(region_ci["value"].isna().all())


if __name__ == "__main__":
    unittest.main()
