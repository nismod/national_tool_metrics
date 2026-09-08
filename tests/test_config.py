from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from national_tool_metrics.config import (
    default_boundary_path,
    load_country_config,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class CountryConfigTests(unittest.TestCase):
    @staticmethod
    def _load_temporary_config(
        repo_root: Path,
        concentration_config: str,
    ):
        config_path = repo_root / "country.toml"
        config_path.write_text(
            """
[country]
iso3 = "KEN"
name = "Kenya"
admin_level = "adm1"

[boundaries]
id_field = "shapeID"
name_field = "shapeName"

[sources]
"""
            + concentration_config,
            encoding="utf-8",
        )
        return load_country_config(config_path, repo_root=repo_root)

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
        self.assertIn(config.country.admin_level, {"adm0", "adm1", "adm2"})
        self.assertEqual(config.boundaries.id_field, "shapeID")
        self.assertEqual(config.boundaries.name_field, "shapeName")
        self.assertEqual(
            config.boundaries.path,
            default_boundary_path(
                REPO_ROOT,
                "KEN",
                config.country.admin_level,
            ),
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
            / (
                f"KEN_{config.country.admin_level}_"
                "adaptation_potential_metrics.csv"
            ),
        )

    def test_builds_canonical_card_output_path(self) -> None:
        config = load_country_config("KEN", repo_root=REPO_ROOT)

        output_path = config.card_output_path(
            "hazard",
            "river_flooding",
        )

        self.assertEqual(
            output_path,
            REPO_ROOT
            / "results"
            / "KEN"
            / "hazard"
            / (
                f"KEN_{config.country.admin_level}_"
                "hazard_river_flooding_metrics.csv"
            ),
        )

        with self.assertRaisesRegex(ValueError, "Invalid card slug"):
            config.card_output_path("hazard", "River Flooding")

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
        self.assertEqual(
            config.source("adaptation_outcomes_dir"),
            REPO_ROOT / "data" / "raw" / "KEN" / "adaptation_outcomes",
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
        target_level = "adm2" if config.country.admin_level == "adm1" else "adm1"
        alternate_config = replace(
            config,
            country=replace(config.country, admin_level=target_level),
            boundaries=replace(
                config.boundaries,
                path=default_boundary_path(REPO_ROOT, "KEN", target_level),
            ),
        )

        self.assertEqual(alternate_config.country.admin_level, target_level)
        self.assertEqual(
            alternate_config.boundaries.path,
            default_boundary_path(REPO_ROOT, "KEN", target_level),
        )
        self.assertEqual(
            alternate_config.output_path("exposure"),
            REPO_ROOT
            / "results"
            / "KEN"
            / "exposure"
            / f"KEN_{target_level}_exposure_metrics.csv",
        )
        self.assertEqual(
            alternate_config.card_output_path(
                "hazard",
                "tropical_cyclone_wind",
            ),
            REPO_ROOT
            / "results"
            / "KEN"
            / "hazard"
            / f"KEN_{target_level}_hazard_tropical_cyclone_wind_metrics.csv",
        )

    def test_expands_a_concentration_curve_set_in_filename_order(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)
            curve_directory = (
                repo_root / "data" / "raw" / "KEN" / "concentration_curves"
            )
            curve_directory.mkdir(parents=True)
            for duc in ("duc11", "duc2"):
                (curve_directory / (
                    f"KEN_jrc_adapted_rl_{duc}_V-EXP_"
                    "concentration_curve.csv"
                )).write_text("frac_pop,frac_flood\n", encoding="utf-8")

            config = self._load_temporary_config(
                repo_root,
                r'''
[[concentration_curve_sets]]
glob = "data/raw/KEN/concentration_curves/KEN_jrc_adapted_rl_duc*_V-EXP_concentration_curve.csv"
filename_regex = '^KEN_jrc_adapted_rl_(?P<duc>duc\d+)_V-EXP_concentration_curve\.csv$'
curve_id_template = "flood_risk__jrc__relocation_{duc}"
x_column = "frac_pop"
y_column = "frac_flood"
ranked_by = "relative_wealth"
rank_direction = "lowest_to_highest"
description_template = "Relocation option {duc}."
expected_count = 2
''',
            )

            self.assertEqual(
                list(config.concentration_curves),
                [
                    "flood_risk__jrc__relocation_duc2",
                    "flood_risk__jrc__relocation_duc11",
                ],
            )
            curve = config.concentration_curve(
                "flood_risk__jrc__relocation_duc2"
            )
            self.assertEqual(
                curve.path,
                curve_directory
                / "KEN_jrc_adapted_rl_duc2_V-EXP_concentration_curve.csv",
            )
            self.assertEqual(curve.description, "Relocation option duc2.")
            self.assertEqual(curve.x_column, "frac_pop")
            self.assertEqual(curve.ranked_by, "relative_wealth")

    def test_rejects_a_concentration_curve_set_with_no_files(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)

            with self.assertRaisesRegex(ValueError, "matched no files"):
                self._load_temporary_config(
                    repo_root,
                    r'''
[[concentration_curve_sets]]
glob = "data/raw/KEN/concentration_curves/*.csv"
filename_regex = '^(?P<scenario>.+)\.csv$'
curve_id_template = "flood_risk__jrc__{scenario}"
x_column = "frac_pop"
y_column = "frac_flood"
ranked_by = "relative_wealth"
rank_direction = "lowest_to_highest"
description = "Test curve."
''',
                )

    def test_rejects_an_unexpected_concentration_curve_set_count(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)
            curve_directory = (
                repo_root / "data" / "raw" / "KEN" / "concentration_curves"
            )
            curve_directory.mkdir(parents=True)
            (curve_directory / "one.csv").write_text(
                "frac_pop,frac_flood\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError,
                "expected 2 files but matched 1",
            ):
                self._load_temporary_config(
                    repo_root,
                    r'''
[[concentration_curve_sets]]
glob = "data/raw/KEN/concentration_curves/*.csv"
filename_regex = '^(?P<scenario>.+)\.csv$'
curve_id_template = "flood_risk__jrc__{scenario}"
x_column = "frac_pop"
y_column = "frac_flood"
ranked_by = "relative_wealth"
rank_direction = "lowest_to_highest"
description = "Test curve."
expected_count = 2
''',
                )

    def test_rejects_a_globbed_filename_that_does_not_match(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)
            curve_directory = (
                repo_root / "data" / "raw" / "KEN" / "concentration_curves"
            )
            curve_directory.mkdir(parents=True)
            (curve_directory / "KEN_jrc_adapted_rl_unknown.csv").write_text(
                "frac_pop,frac_flood\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError,
                "filename_regex does not match",
            ):
                self._load_temporary_config(
                    repo_root,
                    r'''
[[concentration_curve_sets]]
glob = "data/raw/KEN/concentration_curves/KEN_jrc_adapted_rl_*.csv"
filename_regex = '^KEN_jrc_adapted_rl_(?P<duc>duc\d+)\.csv$'
curve_id_template = "flood_risk__jrc__relocation_{duc}"
x_column = "frac_pop"
y_column = "frac_flood"
ranked_by = "relative_wealth"
rank_direction = "lowest_to_highest"
description_template = "Relocation option {duc}."
''',
                )

    def test_rejects_duplicate_batch_curve_identifiers(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)
            curve_directory = (
                repo_root / "data" / "raw" / "KEN" / "concentration_curves"
            )
            curve_directory.mkdir(parents=True)
            for filename in ("curve_a.csv", "curve_b.csv"):
                (curve_directory / filename).write_text(
                    "frac_pop,frac_flood\n",
                    encoding="utf-8",
                )

            with self.assertRaisesRegex(
                ValueError,
                "Duplicate concentration-curve identifier",
            ):
                self._load_temporary_config(
                    repo_root,
                    r'''
[[concentration_curve_sets]]
glob = "data/raw/KEN/concentration_curves/curve_*.csv"
filename_regex = '^curve_(?P<variant>[a-z])\.csv$'
curve_id_template = "flood_risk__jrc__relocation"
x_column = "frac_pop"
y_column = "frac_flood"
ranked_by = "relative_wealth"
rank_direction = "lowest_to_highest"
description_template = "Relocation option {variant}."
''',
                )


if __name__ == "__main__":
    unittest.main()
