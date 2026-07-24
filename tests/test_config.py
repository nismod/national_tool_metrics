from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

from national_tool_metrics.config import (
    _select_path_candidate,
    default_boundary_path,
    load_country_config,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class CountryConfigTests(unittest.TestCase):
    def test_loads_kenya_country_and_boundary_settings(self) -> None:
        config = load_country_config("KEN", repo_root=REPO_ROOT)

        self.assertEqual(config.country.iso3, "KEN")
        self.assertEqual(config.country.name, "Kenya")
        self.assertEqual(config.country.admin_level, "adm1")
        self.assertEqual(config.boundaries.id_field, "shapeID")
        self.assertEqual(config.boundaries.name_field, "shapeName")
        self.assertEqual(
            config.boundaries.path,
            REPO_ROOT / "data" / "boundaries" / "KEN" / "adm1" / "KEN_adm1.shp",
        )

    def test_loads_agreed_risk_run_bundles(self) -> None:
        config = load_country_config("KEN", repo_root=REPO_ROOT)

        flood_run = config.risk_run("jrc_river_flood_baseline")
        cyclone_run = config.risk_run(
            "storm_tropical_cyclone_baseline_2020"
        )

        self.assertEqual(flood_run.hazard, "river_flood")
        self.assertEqual(flood_run.scenario, "baseline")
        self.assertIn("population_risk", flood_run.inputs)
        self.assertEqual(cyclone_run.hazard, "tropical_cyclone")
        self.assertIn("power_damage", cyclone_run.inputs)

    def test_loads_new_first_migration_candidates(self) -> None:
        config = load_country_config("KEN", repo_root=REPO_ROOT)

        worldpop_candidates = config.source_candidates["worldpop_dir"]
        flood_run = config.risk_run("jrc_river_flood_baseline")
        population_risk_candidates = flood_run.input_candidates[
            "population_risk"
        ]

        self.assertEqual(
            worldpop_candidates[0],
            REPO_ROOT
            / "data"
            / "raw"
            / "KEN"
            / "exposure"
            / "population"
            / "worldpop",
        )
        self.assertEqual(
            worldpop_candidates[1],
            REPO_ROOT / "data" / "raw" / "KEN" / "context" / "worldpop",
        )
        self.assertEqual(
            population_risk_candidates[0].parent,
            REPO_ROOT
            / "data"
            / "raw"
            / "KEN"
            / "risk"
            / "socioeconomic"
            / "river_flood",
        )

    def test_empty_new_skeleton_falls_back_to_populated_legacy_path(
        self,
    ) -> None:
        new_path = Path("new/source")
        legacy_path = Path("legacy/source")

        with patch(
            "national_tool_metrics.config._path_contains_data",
            side_effect=lambda path: path == legacy_path,
        ):
            selected = _select_path_candidate((new_path, legacy_path))

        self.assertEqual(selected, legacy_path)

    def test_builds_canonical_section_output_path(self) -> None:
        config = load_country_config("KEN", repo_root=REPO_ROOT)

        output_path = config.output_path("adaptation_options")

        self.assertEqual(
            output_path,
            REPO_ROOT
            / "results"
            / "KEN"
            / "adaptation_options"
            / "KEN_adm1_adaptation_options_metrics.csv",
        )

    def test_admin_level_alone_changes_standard_boundary_and_output_paths(
        self,
    ) -> None:
        config = load_country_config("KEN", repo_root=REPO_ROOT)
        adm2_config = replace(
            config,
            country=replace(config.country, admin_level="adm2"),
            boundaries=replace(
                config.boundaries,
                path=default_boundary_path(REPO_ROOT, "KEN", "adm2"),
            ),
        )

        self.assertEqual(adm2_config.country.admin_level, "adm2")
        self.assertEqual(
            adm2_config.boundaries.path,
            REPO_ROOT / "data" / "boundaries" / "KEN" / "adm2" / "KEN_adm2.shp",
        )
        self.assertEqual(
            adm2_config.output_path("exposure"),
            REPO_ROOT
            / "results"
            / "KEN"
            / "exposure"
            / "KEN_adm2_exposure_metrics.csv",
        )


if __name__ == "__main__":
    unittest.main()
