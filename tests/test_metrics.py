"""Regression checks using small, local fixtures."""

from dataclasses import replace
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
import warnings
from unittest.mock import patch


import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import Point, box


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from national_tool_metrics.adaptation_outcomes import (
    build_dry_proofing_metrics,
    build_flood_protection_metrics,
)
from national_tool_metrics.adaptation_potential import build_flopros_metrics
from national_tool_metrics.concentration_curves import (
    build_concentration_curve_output,
    SHARED_X_COLUMN,
)
from national_tool_metrics.exposure import (
    assemble_exposure_card_metrics,
    build_facility_metrics,
    DEMOGRAPHIC_GROUP_METRICS,
    EDUCATIONAL_FACILITIES_CARD,
    EXPOSURE_CARD_DIMENSIONS,
    FACILITY_CARDS,
    HEALTHCARE_FACILITIES_CARD,
)
from national_tool_metrics.hazard import (
    build_hazard_card_metrics,
    RIVER_FLOOD_CARD,
    RIVER_FLOOD_CARD_DIMENSIONS,
    RIVER_FLOOD_RETURN_PERIODS,
    TROPICAL_CYCLONE_CARD,
    TROPICAL_CYCLONE_CARD_DIMENSIONS,
    TROPICAL_CYCLONE_CATEGORY_THRESHOLDS_MS,
    TROPICAL_CYCLONE_RETURN_PERIODS,
)
from national_tool_metrics.risk import (
    build_capital_stock_risk_metrics,
    build_population_risk_metrics,
)
from national_tool_metrics.utils import (
    build_card_identifier_frame,
    CARD_IDENTIFIER_COLUMNS,
    load_admin_boundaries,
    load_country_config,
    validate_card_output,
    write_card_outputs,
)
from national_tool_metrics.vulnerability import (
    build_relative_wealth_index_metrics,
    build_vulnerability_card_metrics,
)


def example_config(level=None):
    config = load_country_config("KEN", repo_root=REPO_ROOT, load_curves=False)
    return replace(config, country=replace(config.country, admin_level=level)) if level else config


def example_regions():
    return gpd.GeoDataFrame(
        {"adm_id": ["KEN-1", "KEN-2"], "adm_name": ["Region One", "Region Two"]},
        geometry=[Point(0, 0), Point(1, 1)], crs="EPSG:4326",
    )


def write_raster(path, values, north, *, nodata=-9999):
    with rasterio.open(
        path, "w", driver="GTiff", height=values.shape[0], width=values.shape[1], count=1,
        dtype=values.dtype, crs="EPSG:3857", transform=from_origin(0, north, 1000, 1000),
        nodata=nodata,
    ) as raster:
        raster.write(values, 1)


class CountryWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        config_dir = self.root / "config" / "countries"
        config_dir.mkdir(parents=True)
        defaults = (REPO_ROOT / "config" / "defaults.toml").read_bytes()
        (config_dir.parent / "defaults.toml").write_bytes(defaults)
        self.country_file = config_dir / "TZA.toml"
        self.country_file.write_text(
            r"""
[country]
iso3 = "TZA"
name = "Tanzania"
admin_level = "adm0"

[boundaries]
path = "boundaries.gpkg"

[sources]
rwi_dir = "alternate/rwi"

[[concentration_curve_sets]]
glob = "curve_*.csv"
filename_regex = '^curve_(?P<scenario>\w+)\.csv$'
curve_id_template = "flood_risk__jrc__{scenario}"
x_column = "frac_pop"
y_column = "frac_flood"
ranked_by = "relative_wealth"
rank_direction = "lowest_to_highest"
description = "Example curve"
expected_count = 2
""",
            encoding="utf-8",
        )

    def test_section_loads_new_country_without_curve_inputs(self) -> None:
        boundaries = gpd.GeoDataFrame(
            {"shapeName": ["Tanzania"]}, geometry=[box(0, 0, 1, 1)], crs="EPSG:4326",
        )
        boundaries.to_file(self.root / "boundaries.gpkg", index=False)

        config = load_country_config("TZA", repo_root=self.root, load_curves=False)
        admin_regions = load_admin_boundaries(config)
        self.assertEqual(admin_regions["adm_id"].tolist(), ["TZA"])
        self.assertEqual(config.concentration_curves, {})
        self.assertEqual(config.source("rwi_dir"), self.root / "alternate" / "rwi")
        self.assertEqual(
            config.source("worldpop_dir"),
            self.root / "data/raw/TZA/exposure/population/worldpop",
        )
        self.assertEqual(
            config.card_output_path("hazard", "river_flooding").relative_to(self.root),
            Path("results/TZA/hazard/TZA_adm0_hazard_river_flooding_metrics.csv"),
        )

        self.country_file.write_text(
            '[country]\niso3 = "TZA"\nname = "Tanzania"\nadmin_level = "adm1"\n',
            encoding="utf-8",
        )
        minimal = load_country_config("TZA", repo_root=self.root, load_curves=False)
        self.assertEqual(minimal.boundaries.path, self.root / "data/boundaries/TZA/adm1/TZA_adm1.shp")
        run = minimal.risk_run("river_flood_jrc_baseline")
        self.assertEqual(
            run.inputs["population_risk_dir"],
            self.root / "data/raw/TZA/risk/socioeconomic/river_flood",
        )

    def test_curves_require_files_and_a_shared_grid(self) -> None:
        with self.assertRaisesRegex(ValueError, "matched no files"):
            load_country_config("TZA", repo_root=self.root)

        first = self.root / "curve_baseline.csv"
        second = self.root / "curve_adapted.csv"
        first.write_text("frac_pop,frac_flood\n0,0\n0.5,0.4\n1,1\n", encoding="utf-8")
        second.write_text("frac_pop,frac_flood\n0,0\n0.5,0.6\n1,1\n", encoding="utf-8")
        config = load_country_config("TZA", repo_root=self.root)
        combined = build_concentration_curve_output(config)
        self.assertEqual(combined[SHARED_X_COLUMN].tolist(), [0.0, 0.5, 1.0])
        self.assertEqual(combined["flood_risk__jrc__adapted"].tolist(), [0.0, 0.6, 1.0])

        second.write_text("frac_pop,frac_flood\n0,0\n0.25,0.6\n1,1\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "shared population-share"):
            build_concentration_curve_output(config)


class HazardMetricTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        temporary_root = Path(self.temporary_directory.name)
        self.flood_directory = temporary_root
        self.cyclone_directory = temporary_root
        base_config = example_config()
        self.config = replace(
            base_config,
            sources={
                **base_config.sources,
                "river_flood_hazard_dir": self.flood_directory,
                "tropical_cyclone_hazard_dir": self.cyclone_directory,
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
            path = self.flood_directory / (
                f"KEN_jrc-flood_RP{return_period}.tif"
            )
            write_raster(path, values, 2000)

    def _write_tropical_cyclone_rasters(self) -> None:
        values = np.array(
            [
                [18.1, 29.1, 37.7, 43.5],
                [51.2, 61.7, 70.0, 0.0],
            ],
            dtype="float32",
        )
        for return_period in TROPICAL_CYCLONE_RETURN_PERIODS:
            path = self.cyclone_directory / (
                "STORM_FIXED_RETURN_PERIODS_constant_"
                f"{return_period}_YR_RP.tif"
            )
            write_raster(path, values, 2000, nodata=0)

    def test_builds_one_tidy_csv_table_per_hazard_card(self) -> None:
        self._write_return_period_rasters()
        self._write_tropical_cyclone_rasters()

        cards = build_hazard_card_metrics(self.config, self.admin_regions)

        self.assertEqual(
            set(cards),
            {RIVER_FLOOD_CARD, TROPICAL_CYCLONE_CARD},
        )
        river = cards[RIVER_FLOOD_CARD]
        cyclone = cards[TROPICAL_CYCLONE_CARD]
        self.assertEqual(
            list(river.columns),
            [
                *CARD_IDENTIFIER_COLUMNS,
                *RIVER_FLOOD_CARD_DIMENSIONS,
                "value",
            ],
        )
        self.assertEqual(
            list(cyclone.columns),
            [
                *CARD_IDENTIFIER_COLUMNS,
                *TROPICAL_CYCLONE_CARD_DIMENSIONS,
                "value",
            ],
        )
        self.assertEqual(
            len(river),
            len(self.admin_regions) * len(RIVER_FLOOD_RETURN_PERIODS) * 4,
        )
        self.assertEqual(
            len(cyclone),
            len(self.admin_regions)
            * len(TROPICAL_CYCLONE_RETURN_PERIODS)
            * len(TROPICAL_CYCLONE_CATEGORY_THRESHOLDS_MS)
            * 2,
        )
        self.assertEqual(
            set(river["metric"]),
            {
                "flooded_area",
                "area_flooded_percentage",
                "mean_flood_depth",
                "p90_flood_depth",
            },
        )
        self.assertEqual(
            set(cyclone["return_period_years"]),
            set(TROPICAL_CYCLONE_RETURN_PERIODS),
        )
        self.assertNotIn(75, set(cyclone["return_period_years"]))

        river_value = river.loc[
            (river["adm_id"] == "KEN-1")
            & (river["return_period_years"] == 10)
            & (river["metric"] == "mean_flood_depth"),
            "value",
        ].item()
        cyclone_value = cyclone.loc[
            (cyclone["adm_id"] == "KEN-1")
            & (cyclone["return_period_years"] == 10)
            & (cyclone["wind_threshold"] == "cat1plus")
            & (cyclone["display_mode"] == "area"),
            "value",
        ].item()
        self.assertAlmostEqual(river_value, 1.25, places=3)
        self.assertAlmostEqual(cyclone_value, 3.0, places=3)


class ExposureMetricTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = example_config("adm1")
        self.admin_regions = example_regions()

    def test_missing_facilities_keep_csv_rows_and_populate_when_files_arrive(self):
        population = self.admin_regions[["adm_id"]].assign(
            **{column: 100_000.0 for column in DEMOGRAPHIC_GROUP_METRICS.values()}
        )
        capital = self.admin_regions[["adm_id"]].assign(
            capstock_residential=1.0,
            capstock_non_residential=2.0,
            capstock_infrastructure=3.0,
        )
        networks = self.admin_regions[["adm_id"]].assign(
            road_length_primary_km=1.0,
            rail_length_km=1.0,
            power_transmission_length_km=1.0,
        )
        with TemporaryDirectory() as directory:
            config = replace(
                self.config,
                repo_root=Path(directory),
                sources={**self.config.sources, "facility_dir": Path(directory)},
            )
            for available_count in range(3):
                with self.subTest(available_files=available_count):
                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter("always")
                        facilities = build_facility_metrics(config, self.admin_regions)
                    self.assertEqual(len(caught), 2 - available_count)
                    self.assertTrue(all("no data" in str(w.message) for w in caught))
                    cards = assemble_exposure_card_metrics(
                        config, self.admin_regions, population, capital,
                        networks, facilities,
                    )
                    for index, card in enumerate((
                        HEALTHCARE_FACILITIES_CARD, EDUCATIONAL_FACILITIES_CARD,
                    )):
                        output = cards[card]
                        dimensions = EXPOSURE_CARD_DIMENSIONS[card]
                        self.assertEqual(len(output), 18)
                        self.assertEqual(output.groupby("adm_id").size().tolist(), [9, 9])
                        if index >= available_count:
                            self.assertTrue(output["value"].isna().all())
                            with self.assertRaisesRegex(ValueError, "entirely empty"):
                                validate_card_output(output, "exposure", card, dimensions)
                        else:
                            # The supplied region has five facilities; the unmatched
                            # region retains the existing zero-fill behavior.
                            self.assertEqual(output["value"].tolist(), [5.0] * 9 + [0.0] * 9)
                        paths = write_card_outputs(
                            {card: output}, config, "exposure", EXPOSURE_CARD_DIMENSIONS,
                            allow_empty_value_cards=FACILITY_CARDS,
                        )
                        path = paths[card]
                        saved = pd.read_csv(path)
                        self.assertEqual(list(saved.columns), list(output.columns))
                        self.assertEqual(len(saved), len(output))
                        self.assertEqual(saved["value"].isna().tolist(), output["value"].isna().tolist())
                        if index >= available_count:
                            self.assertTrue(all(line.endswith(",") for line in path.read_text().splitlines()[1:]))

                    if available_count < 2:
                        source = ("hospitals", "schools")[available_count]
                        path = Path(directory) / f"building_{source}_gov_summary_ADM1__KEN.csv"
                        path.write_text("adm_id,n_buildings\nKEN-1,5\n")

    def test_existing_invalid_facility_summary_still_raises(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "building_hospitals_gov_summary_ADM1__KEN.csv"
            path.write_text("adm_id,wrong_column\nKEN-1,5\n")
            config = replace(
                self.config,
                sources={**self.config.sources, "facility_dir": Path(directory)},
            )
            with self.assertRaisesRegex(ValueError, "missing required columns"):
                build_facility_metrics(config, self.admin_regions)


class VulnerabilityMetricTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = example_config("adm1")
        self.admin_regions = example_regions()

    @patch(
        "national_tool_metrics.vulnerability."
        "read_gpkg_attributes"
    )
    def test_adm0_synthesizes_iso3_when_summaries_omit_shape_id(
        self,
        read_mock,
    ) -> None:
        adm0_config = replace(
            self.config,
            country=replace(self.config.country, admin_level="adm0"),
        )
        adm0_regions = self.admin_regions.iloc[[0]].assign(adm_id="KEN", adm_name="Kenya")
        read_mock.return_value = pd.DataFrame(
            {
                "shapeName": ["Kenya"],
                "average_rwi": [-0.5],
                "population_weighted_rwi": [-0.3],
            }
        )

        metrics = build_relative_wealth_index_metrics(
            adm0_config,
            adm0_regions,
        )

        self.assertEqual(metrics["adm_id"].tolist(), ["KEN"])
        self.assertEqual(metrics["raw_rwi"].tolist(), [-0.5])

    @patch(
        "national_tool_metrics.vulnerability."
        "read_gpkg_attributes"
    )
    def test_non_adm0_still_requires_shape_id(self, read_mock) -> None:
        read_mock.return_value = pd.DataFrame(
            {
                "shapeName": ["Region One"],
                "average_rwi": [-0.5],
                "population_weighted_rwi": [-0.3],
            }
        )

        with self.assertRaisesRegex(ValueError, "shapeID"):
            build_relative_wealth_index_metrics(
                self.config,
                self.admin_regions.iloc[[0]],
            )

    def test_card_builder_produces_both_wealth_cards(self) -> None:
        rwi = pd.DataFrame(
            {
                "adm_id": ["KEN-1", "KEN-2"],
                "raw_rwi": [-0.5, 0.2],
                "pop_weighted_rwi": [-0.3, 0.4],
            }
        )
        wealth = pd.DataFrame(
            {
                "adm_id": ["KEN-1", "KEN-2"],
                **{
                    f"pop_rwi_q{quintile}": [10.0, 20.0]
                    for quintile in range(1, 6)
                },
            }
        )

        with (
            patch(
                "national_tool_metrics.vulnerability."
                "build_relative_wealth_index_metrics",
                return_value=rwi,
            ),
            patch(
                "national_tool_metrics.vulnerability."
                "build_wealth_distribution_metrics",
                return_value=wealth,
            ),
        ):
            cards = build_vulnerability_card_metrics(
                self.config,
                self.admin_regions,
            )

        self.assertEqual(set(cards), {"relative_wealth_index", "wealth_distribution"})


class RiskMetricTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = example_config("adm1")
        self.admin_regions = example_regions()
        self.river_run = self.config.risk_run(
            "river_flood_jrc_baseline"
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
        "national_tool_metrics.risk.read_gpkg_attributes"
    )
    def test_adm0_population_synthesizes_iso3_when_shape_id_is_absent(
        self,
        read_mock,
    ) -> None:
        adm0_config = replace(
            self.config,
            country=replace(self.config.country, admin_level="adm0"),
        )
        adm0_regions = self.admin_regions.iloc[[0]].assign(adm_id="KEN", adm_name="Kenya")
        source = self._population_source()
        source = source[source["shapeID"] == "KEN-1"].copy()
        source["shapeName"] = "Kenya"
        source["admin_level"] = "ADM0"
        read_mock.return_value = source.drop(columns="shapeID")

        metrics = build_population_risk_metrics(
            adm0_config,
            adm0_regions,
            self.river_run,
        )

        self.assertEqual(metrics["adm_id"].tolist(), ["KEN"])
        self.assertEqual(
            metrics["flooded_pop_ea_protected_total"].tolist(),
            [100.0],
        )

    @patch(
        "national_tool_metrics.risk.read_gpkg_attributes"
    )
    def test_non_adm0_population_still_requires_shape_id(
        self,
        read_mock,
    ) -> None:
        read_mock.return_value = self._population_source().drop(
            columns="shapeID"
        )

        with self.assertRaisesRegex(ValueError, "shapeID"):
            build_population_risk_metrics(
                self.config,
                self.admin_regions,
                self.river_run,
            )

    @patch(
        "national_tool_metrics.risk.read_gpkg_attributes"
    )
    def test_adm0_capital_stock_synthesizes_iso3_without_shape_id(
        self,
        read_mock,
    ) -> None:
        adm0_config = replace(
            self.config,
            country=replace(self.config.country, admin_level="adm0"),
        )
        adm0_regions = self.admin_regions.iloc[[0]].assign(adm_id="KEN", adm_name="Kenya")
        read_mock.return_value = pd.DataFrame(
            {
                "shapeName": ["Kenya"],
                "res_losses": [10.0],
                "nres_losses": [20.0],
                "infr_losses": [30.0],
                "total_losses": [60.0],
            }
        )

        metrics = build_capital_stock_risk_metrics(
            adm0_config,
            adm0_regions,
            self.river_run,
        )

        self.assertEqual(metrics["adm_id"].tolist(), ["KEN"])
        self.assertEqual(metrics["capstock_aal_total"].tolist(), [60.0])


class AdaptationPotentialMetricTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.temp_path = Path(self.temporary_directory.name)
        self.local_directory = self.temp_path / "adaptation_potential"
        self.local_directory.mkdir()

        base_config = example_config()
        self.config = replace(
            base_config,
            sources={
                **base_config.sources,
                "adaptation_potential_dir": self.local_directory,
            },
        )
        self.admin_regions = gpd.GeoDataFrame(
            {
                "adm_id": ["KEN-1", "KEN-2"],
                "adm_name": ["Region One", "Region Two"],
            },
            geometry=[box(0, 0, 2000, 5000), box(2000, 0, 4000, 5000)],
            crs="EPSG:3857",
        )

    def test_flopros_mode_excludes_zero_and_resolves_ties_downward(self) -> None:
        values = np.array(
            [
                [0, 2, 3, 4, 0],
                [0, 2, 3, 4, 0],
                [2, 2, 3, 4, 0],
                [0, 5, 3, 4, 0],
                [0, 5, 3, 4, 0],
            ],
            dtype="float32",
        )
        write_raster(self.local_directory / "KEN_flopros.tif", values, 5000)

        metrics = build_flopros_metrics(self.config, self.admin_regions)

        self.assertEqual(
            metrics["flopros_protection_standard_mode_rp"].tolist(),
            [2.0, 3.0],
        )

    def test_flopros_preserves_region_without_positive_cells_as_no_data(
        self,
    ) -> None:
        values = np.array(
            [
                [2, 2, 0, 0, 0],
                [2, 2, 0, 0, 0],
                [2, 2, 0, 0, 0],
                [2, 2, 0, 0, 0],
                [2, 2, 0, 0, 0],
            ],
            dtype="float32",
        )
        write_raster(self.local_directory / "KEN_flopros.tif", values, 5000)

        metrics = build_flopros_metrics(self.config, self.admin_regions)

        self.assertEqual(
            metrics.loc[0, "flopros_protection_standard_mode_rp"],
            2.0,
        )
        self.assertTrue(
            pd.isna(
                metrics.loc[1, "flopros_protection_standard_mode_rp"]
            )
        )


class AdaptationOutcomesMetricTests(unittest.TestCase):
    def setUp(self) -> None:
        base_config = example_config()
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
        self.flood_costs = pd.DataFrame({
            **identifiers,
            "adaptation_cost": [100_000.0, 200_000.0],
            "min_adaptation_cost": [50_000.0, 100_000.0],
            "max_adaptation_cost": [300_000.0, 600_000.0],
        })
        self.missing_cost_scenario = None

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

    def _read_source(self, _path: Path, layer_name: str) -> pd.DataFrame:
        if "adaptation-cost_fp" in layer_name:
            cost = self.flood_costs.copy()
            if self.missing_cost_scenario and self.missing_cost_scenario in layer_name:
                cost.loc[0, ["adaptation_cost", "min_adaptation_cost", "max_adaptation_cost"]] = np.nan
            return cost

        for token, source in (
            ("adaptation-cost_dp", "cost"),
            ("AALs_adapted_", "economic_adapted"),
            ("protected_AAR_baseline_capstock", "economic_baseline"),
            ("adapted_AAR_V-EXP_S-rwi_", "social_adapted"),
            ("protected_AAR_V-EXP_S-rwi", "social_baseline"),
        ):
            if token in layer_name:
                return self.sources[source].copy()
        raise AssertionError(f"Unexpected layer: {layer_name}")

    @patch(
        "national_tool_metrics.adaptation_outcomes."
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
        "national_tool_metrics.adaptation_outcomes."
        "read_gpkg_attributes"
    )
    def test_preserves_jointly_missing_flood_protection_costs(
        self,
        read_gpkg_attributes,
    ) -> None:
        self.missing_cost_scenario = "_rp10_duc11_"
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


class OutputContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = example_config()
        self.admin_regions = example_regions()

    def test_rejects_duplicate_card_parameter_combinations(self) -> None:
        identifiers = build_card_identifier_frame(
            self.admin_regions.iloc[[0]],
            self.config,
            section="hazard",
            card="river_flooding",
        )
        output = pd.concat([identifiers, identifiers], ignore_index=True)
        output["return_period_years"] = 100
        output["metric"] = "flooded_area"
        output["unit"] = "km2"
        output["value"] = [1.0, 2.0]

        with self.assertRaisesRegex(ValueError, "duplicate key rows"):
            validate_card_output(
                output,
                "hazard",
                "river_flooding",
                ("return_period_years", "metric", "unit"),
            )

    def test_allows_declared_optional_card_dimensions(self) -> None:
        output = build_card_identifier_frame(
            self.admin_regions,
            self.config,
            section="risk",
            card="population",
        )
        output["epoch"] = pd.NA
        output["metric"] = "exposed_population"
        output["unit"] = "people"
        output["value"] = [10.0, 20.0]
        dimensions = ("epoch", "metric", "unit")

        validate_card_output(
            output,
            "risk",
            "population",
            dimensions,
            optional_dimension_columns=("epoch",),
        )

        output.loc[0, "metric"] = pd.NA
        with self.assertRaisesRegex(ValueError, "missing parameter values"):
            validate_card_output(
                output,
                "risk",
                "population",
                dimensions,
                optional_dimension_columns=("epoch",),
            )
