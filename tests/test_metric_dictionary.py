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
            {"exposure", "vulnerability", "risk", "adaptation_options"},
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
                "vulnerability",
                "risk",
                "adaptation_options",
            }
        }
        self.assertEqual(
            counts,
            {
                "exposure": 20,
                "vulnerability": 8,
                "risk": 10,
                "adaptation_options": 9,
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


if __name__ == "__main__":
    unittest.main()
