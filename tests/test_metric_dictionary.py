from pathlib import Path
import csv
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
DICTIONARY_PATH = REPO_ROOT / "docs" / "metric_dictionary.csv"


class MetricDictionaryTests(unittest.TestCase):
    def setUp(self) -> None:
        with DICTIONARY_PATH.open(encoding="utf-8", newline="") as source:
            self.rows = list(csv.DictReader(source))

    def test_uses_section_aligned_modules_and_hazards(self) -> None:
        self.assertEqual(
            {row["module"] for row in self.rows},
            {
                "hazard",
                "exposure",
                "vulnerability",
                "risk",
                "adaptation_potential",
            },
        )
        self.assertEqual(
            {row["hazard"] for row in self.rows},
            {"none", "river_flood", "tropical_cyclone"},
        )

    def test_preserves_unique_metric_entries_by_section(self) -> None:
        metric_names = [row["metric_name"] for row in self.rows]
        self.assertEqual(len(metric_names), len(set(metric_names)))

        counts = {
            section: sum(row["module"] == section for row in self.rows)
            for section in {
                "exposure",
                "hazard",
                "vulnerability",
                "risk",
                "adaptation_potential",
            }
        }
        self.assertEqual(
            counts,
            {
                "hazard": 4,
                "exposure": 20,
                "vulnerability": 8,
                "risk": 11,
                "adaptation_potential": 22,
            },
        )

    def test_population_sources_document_90m_inputs(self) -> None:
        population_rows = [
            row
            for row in self.rows
            if row["module"] == "exposure"
            and row["metric_name"].startswith("pop_")
        ]
        self.assertEqual(len(population_rows), 8)
        self.assertTrue(
            all("90 m" in row["source_notes"] for row in population_rows)
        )
        self.assertTrue(
            all("1km" not in row["source_notes"] for row in self.rows)
        )

    def test_accessibility_pattern_covers_all_metric_variants(self) -> None:
        accessibility_rows = [
            row
            for row in self.rows
            if row["metric_name"].startswith("access_")
        ]
        self.assertEqual(len(accessibility_rows), 1)
        self.assertEqual(
            accessibility_rows[0]["metric_name"],
            (
                "access_<accessibility_type>_<access_mode>_"
                "<population_metric_label>_travel_time_avg_baseline"
            ),
        )

    def test_risk_dictionary_uses_selected_protected_population_map(
        self,
    ) -> None:
        risk_metrics = {
            row["metric_name"]
            for row in self.rows
            if row["module"] == "risk"
        }
        self.assertIn(
            (
                "river_flood_jrc_baseline_"
                "flooded_pop_ea_protected_<population_group>"
            ),
            risk_metrics,
        )
        self.assertNotIn(
            "river_flood_jrc_baseline_flooded_pop_ea_<population_group>",
            risk_metrics,
        )
        self.assertIn(
            (
                "river_flood_jrc_baseline_"
                "flooded_pop_rp<return_period>_<population_group>"
            ),
            risk_metrics,
        )
        self.assertIn(
            (
                "river_flood_jrc_baseline_"
                "capstock_rp<return_period>_<asset_type>"
            ),
            risk_metrics,
        )
        self.assertIn(
            "tropical_cyclone_storm_baseline_2020_power_ead_total",
            risk_metrics,
        )

    def test_river_context_documents_water_as_rural(self) -> None:
        river_rows = {
            row["metric_name"]: row
            for row in self.rows
            if row["module"] == "adaptation_potential"
            and row["metric_name"].startswith("river_length_")
        }

        self.assertEqual(
            set(river_rows),
            {
                "river_length_total_km",
                "river_length_rural_km",
                "river_length_town_km",
                "river_length_city_km",
            },
        )
        self.assertIn(
            "class 10 water is grouped with rural",
            river_rows["river_length_rural_km"]["aggregation_method"],
        )

    def test_nbs_dictionary_documents_category_costs_and_benefits(self) -> None:
        category_patterns = {
            row["metric_name"]
            for row in self.rows
            if row["module"] == "adaptation_potential"
            and "<opportunity_category>" in row["metric_name"]
        }
        self.assertEqual(
            category_patterns,
            {
                (
                    "nbs_<categorized_nbs_class>_<opportunity_category>_"
                    "planting_cost_total_usd_2020"
                ),
                (
                    "nbs_<categorized_nbs_class>_<opportunity_category>_"
                    "regeneration_cost_total_usd_2020"
                ),
                (
                    "nbs_<categorized_nbs_class>_<opportunity_category>_"
                    "carbon_benefit_total_tonnes"
                ),
                (
                    "nbs_<categorized_nbs_class>_<opportunity_category>_"
                    "biodiversity_benefit_mean"
                ),
            },
        )

    def test_hazard_dictionary_documents_four_return_period_patterns(
        self,
    ) -> None:
        hazard_metrics = {
            row["metric_name"]
            for row in self.rows
            if row["module"] == "hazard"
        }

        self.assertEqual(
            hazard_metrics,
            {
                (
                    "river_flood_jrc_baseline_"
                    "flooded_area_rp<return_period>_km2"
                ),
                (
                    "river_flood_jrc_baseline_"
                    "flooded_area_rp<return_period>_pct_admin"
                ),
                (
                    "river_flood_jrc_baseline_"
                    "flood_depth_mean_rp<return_period>_m"
                ),
                (
                    "river_flood_jrc_baseline_"
                    "flood_depth_p90_rp<return_period>_m"
                ),
            },
        )

    def test_hazard_and_risk_metrics_encode_run_dimensions(self) -> None:
        for row in self.rows:
            if row["module"] == "hazard":
                self.assertTrue(
                    row["metric_name"].startswith(
                        "river_flood_jrc_baseline_"
                    )
                )
            if row["module"] == "risk" and row["hazard"] == "river_flood":
                self.assertTrue(
                    row["metric_name"].startswith(
                        "river_flood_jrc_baseline_"
                    )
                )
            if (
                row["module"] == "risk"
                and row["hazard"] == "tropical_cyclone"
            ):
                self.assertTrue(
                    row["metric_name"].startswith(
                        "tropical_cyclone_storm_baseline_2020_"
                    )
                )


if __name__ == "__main__":
    unittest.main()
