from dataclasses import replace
from pathlib import Path
import unittest

from national_tool_metrics.config import (
    default_boundary_path,
    load_country_config,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class CountryConfigTests(unittest.TestCase):
    def test_loads_mozambique_country_and_source_settings(self) -> None:
        config = load_country_config("MOZ", repo_root=REPO_ROOT)

        self.assertEqual(config.country.iso3, "MOZ")
        self.assertEqual(config.country.name, "Mozambique")
        self.assertEqual(config.country.admin_level, "adm1")
        self.assertEqual(
            config.boundaries.path,
            REPO_ROOT
            / "data"
            / "boundaries"
            / "MOZ"
            / "adm1"
            / "MOZ_adm1.shp",
        )
        self.assertEqual(
            config.source("worldpop_dir"),
            REPO_ROOT
            / "data"
            / "raw"
            / "MOZ"
            / "exposure"
            / "population"
            / "worldpop",
        )
        self.assertEqual(
            config.risk_run("river_flood_jrc_baseline").inputs[
                "population_risk_dir"
            ],
            REPO_ROOT
            / "data"
            / "raw"
            / "MOZ"
            / "risk"
            / "socioeconomic"
            / "river_flood",
        )
        self.assertEqual(
            config.risk_run(
                "tropical_cyclone_storm_baseline_2020"
            ).inputs["power_damage"],
            REPO_ROOT
            / "data"
            / "raw"
            / "MOZ"
            / "risk"
            / "infrastructure_networks"
            / "direct"
            / "tropical_cyclone"
            / "power.gpkg",
        )

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

        flood_run = config.risk_run("river_flood_jrc_baseline")
        cyclone_run = config.risk_run(
            "tropical_cyclone_storm_baseline_2020"
        )

        self.assertEqual(flood_run.name, "river_flood_jrc_baseline")
        self.assertIn("population_risk_dir", flood_run.inputs)
        self.assertEqual(
            cyclone_run.name,
            "tropical_cyclone_storm_baseline_2020",
        )
        self.assertIn("power_damage", cyclone_run.inputs)

    def test_loads_canonical_section_sources(self) -> None:
        config = load_country_config("KEN", repo_root=REPO_ROOT)

        flood_run = config.risk_run("river_flood_jrc_baseline")

        self.assertEqual(
            config.source("worldpop_dir"),
            REPO_ROOT
            / "data"
            / "raw"
            / "KEN"
            / "exposure"
            / "population"
            / "worldpop",
        )
        self.assertEqual(
            flood_run.inputs["population_risk_dir"],
            REPO_ROOT
            / "data"
            / "raw"
            / "KEN"
            / "risk"
            / "socioeconomic"
            / "river_flood",
        )

    def test_risk_summary_directories_support_future_admin_levels(
        self,
    ) -> None:
        config = load_country_config("KEN", repo_root=REPO_ROOT)
        flood_run = config.risk_run("river_flood_jrc_baseline")

        self.assertTrue(
            flood_run.inputs["population_risk_dir"].is_dir()
        )
        self.assertTrue(
            flood_run.inputs["capital_stock_risk_dir"].is_dir()
        )

    def test_builds_canonical_section_output_path(self) -> None:
        config = load_country_config("KEN", repo_root=REPO_ROOT)

        output_path = config.output_path("adaptation_potential")

        self.assertEqual(
            output_path,
            REPO_ROOT
            / "results"
            / "KEN"
            / "adaptation_potential"
            / "KEN_adm1_adaptation_potential_metrics.csv",
        )

    def test_loads_adaptation_potential_sources_and_parameters(self) -> None:
        config = load_country_config("KEN", repo_root=REPO_ROOT)

        self.assertEqual(
            config.source("adaptation_potential_dir"),
            REPO_ROOT / "data" / "raw" / "KEN" / "adaptation_potential",
        )
        self.assertEqual(
            config.source("nature_based_solutions_dir"),
            REPO_ROOT / "data" / "raw" / "global" / "nature_based_solutions",
        )
        self.assertEqual(config.parameters["nbs_nominal_cell_area_ha"], 6.25)
        self.assertEqual(
            config.parameters["max_urbanisation_nodata_distance_m"],
            5000,
        )

    def test_loads_river_flood_hazard_source(self) -> None:
        config = load_country_config("KEN", repo_root=REPO_ROOT)

        self.assertEqual(
            config.source("river_flood_hazard_dir"),
            REPO_ROOT
            / "data"
            / "raw"
            / "KEN"
            / "hazard"
            / "river_flooding",
        )
        self.assertEqual(
            config.source("tropical_cyclone_hazard_dir"),
            REPO_ROOT
            / "data"
            / "raw"
            / "global"
            / "tropical_cyclone",
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
