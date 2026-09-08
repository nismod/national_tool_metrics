from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import LineString, box

from national_tool_metrics.config import load_country_config
from national_tool_metrics.outputs import CARD_IDENTIFIER_COLUMNS
from national_tool_metrics.sections.adaptation_potential import (
    ADAPTATION_POTENTIAL_CARD_DIMENSIONS,
    BIODIVERSITY_FILENAME,
    CARBON_FILENAME,
    EXISTING_FLOOD_PROTECTION_CARD,
    MANGROVE_FILENAME,
    MANGROVE_PLANTING_COST_FILENAME,
    MANGROVE_REGENERATION_COST_FILENAME,
    MANGROVES_CARD,
    PLANTING_COST_FILENAME,
    REGENERATION_COST_FILENAME,
    RIVER_CATCHMENT_RESTORATION_CARD,
    RIVER_FILENAME,
    RIVER_NETWORK_CONTEXT_CARD,
    SLOPE_FILENAME,
    SLOPE_VEGETATION_CARD,
    assemble_adaptation_potential_card_metrics,
    assemble_adaptation_potential_metrics,
    build_flopros_metrics,
    build_nbs_metrics,
    build_river_network_context_metrics,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class AdaptationPotentialMetricTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory(dir=REPO_ROOT / "tests")
        self.addCleanup(self.temporary_directory.cleanup)
        self.temp_path = Path(self.temporary_directory.name)
        self.local_directory = self.temp_path / "adaptation_potential"
        self.global_directory = self.temp_path / "nature_based_solutions"
        self.local_directory.mkdir()
        self.global_directory.mkdir()

        base_config = load_country_config("KEN", repo_root=REPO_ROOT)
        self.config = replace(
            base_config,
            sources={
                **base_config.sources,
                "adaptation_potential_dir": self.local_directory,
                "nature_based_solutions_dir": self.global_directory,
            },
            parameters={
                **base_config.parameters,
                "nbs_nominal_cell_area_ha": 6.25,
                "max_coastal_assignment_distance_m": 5000,
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
        self.transform = from_origin(0, 5000, 1000, 1000)

    def _write_raster(self, path: Path, values: np.ndarray) -> None:
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            height=values.shape[0],
            width=values.shape[1],
            count=1,
            dtype=values.dtype,
            crs="EPSG:3857",
            transform=self.transform,
            nodata=-9999,
        ) as target:
            target.write(values, 1)

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
        self._write_raster(self.local_directory / "KEN_flopros.tif", values)

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
        self._write_raster(self.local_directory / "KEN_flopros.tif", values)

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

    def test_nbs_metrics_use_nominal_area_and_nearest_mangrove_assignment(
        self,
    ) -> None:
        zeros = np.zeros((5, 5), dtype="float32")
        slope = zeros.copy()
        slope[0] = [1, 2, 3, 0, 0]
        slope[1] = [0, 3, 1, 2, 0]
        river = zeros.copy()
        river[2] = [1, 0, 1, 1, 0]
        mangrove = zeros.copy()
        mangrove[3] = [0, 0, 1, 2, 3]

        self._write_raster(self.global_directory / SLOPE_FILENAME, slope)
        self._write_raster(self.global_directory / RIVER_FILENAME, river)
        self._write_raster(self.global_directory / MANGROVE_FILENAME, mangrove)
        for filename, value in (
            (PLANTING_COST_FILENAME, 10),
            (REGENERATION_COST_FILENAME, 2),
            (MANGROVE_PLANTING_COST_FILENAME, 20),
            (MANGROVE_REGENERATION_COST_FILENAME, 4),
            (CARBON_FILENAME, 3),
            (BIODIVERSITY_FILENAME, 5),
        ):
            self._write_raster(
                self.global_directory / filename,
                np.full((5, 5), value, dtype="float32"),
            )

        metrics = build_nbs_metrics(self.config, self.admin_regions)
        first = metrics.set_index("adm_id").loc["KEN-1"]
        second = metrics.set_index("adm_id").loc["KEN-2"]

        self.assertEqual(len(metrics.columns), 46)
        self.assertAlmostEqual(first["nbs_slope_vegetation_total_km2"], 0.1875)
        self.assertAlmostEqual(second["nbs_slope_vegetation_total_km2"], 0.1875)
        self.assertAlmostEqual(
            second["nbs_mangrove_total_km2"],
            0.1875,
        )
        self.assertAlmostEqual(
            second["nbs_mangrove_fast_retreat_km2"],
            0.0625,
        )
        self.assertAlmostEqual(
            first["nbs_river_catchment_restoration_total_km2"],
            0.0625,
        )
        self.assertAlmostEqual(
            second["nbs_river_catchment_restoration_total_km2"],
            0.125,
        )
        self.assertAlmostEqual(
            first["nbs_slope_vegetation_planting_cost_total_usd_2020"],
            187.5,
        )
        self.assertAlmostEqual(
            second["nbs_mangrove_planting_cost_total_usd_2020"],
            375.0,
        )
        self.assertAlmostEqual(
            second["nbs_mangrove_carbon_benefit_total_tonnes"],
            56.25,
        )
        self.assertAlmostEqual(
            second["nbs_mangrove_biodiversity_benefit_mean"],
            5.0,
        )
        self.assertAlmostEqual(
            first[
                "nbs_slope_vegetation_crops_planting_cost_total_usd_2020"
            ],
            62.5,
        )
        self.assertAlmostEqual(
            first[
                "nbs_slope_vegetation_crops_regeneration_cost_total_usd_2020"
            ],
            12.5,
        )
        self.assertAlmostEqual(
            first[
                "nbs_slope_vegetation_crops_carbon_benefit_total_tonnes"
            ],
            18.75,
        )
        self.assertAlmostEqual(
            first[
                "nbs_slope_vegetation_crops_biodiversity_benefit_mean"
            ],
            5.0,
        )
        self.assertAlmostEqual(
            second[
                "nbs_mangrove_fast_retreat_planting_cost_total_usd_2020"
            ],
            125.0,
        )
        self.assertAlmostEqual(
            second[
                "nbs_mangrove_fast_retreat_regeneration_cost_total_usd_2020"
            ],
            25.0,
        )
        self.assertAlmostEqual(
            second[
                "nbs_mangrove_fast_retreat_carbon_benefit_total_tonnes"
            ],
            18.75,
        )
        self.assertAlmostEqual(
            second[
                "nbs_mangrove_fast_retreat_biodiversity_benefit_mean"
            ],
            5.0,
        )

        for prefix, categories in {
            "nbs_slope_vegetation": ("other", "crops", "bare_ground"),
            "nbs_mangrove": (
                "accreting",
                "static_moderate_retreat",
                "fast_retreat",
            ),
        }.items():
            for suffix in (
                "planting_cost_total_usd_2020",
                "regeneration_cost_total_usd_2020",
                "carbon_benefit_total_tonnes",
            ):
                category_columns = [
                    f"{prefix}_{category}_{suffix}" for category in categories
                ]
                np.testing.assert_allclose(
                    metrics[f"{prefix}_{suffix}"],
                    metrics[category_columns].sum(axis=1),
                )

    def test_assembled_output_uses_adaptation_potential_identifiers(self) -> None:
        flopros = pd.DataFrame(
            {
                "adm_id": ["KEN-1", "KEN-2"],
                "flopros_protection_standard_mode_rp": [2, float("nan")],
            }
        )
        nbs = pd.DataFrame(
            {
                "adm_id": ["KEN-1", "KEN-2"],
                "nbs_slope_vegetation_total_km2": [1.0, 2.0],
            }
        )
        river_context = pd.DataFrame(
            {
                "adm_id": ["KEN-1", "KEN-2"],
                "river_length_total_km": [3.0, 4.0],
            }
        )

        output = assemble_adaptation_potential_metrics(
            self.config,
            self.admin_regions,
            flopros,
            nbs,
            river_context,
        )

        self.assertEqual(set(output["section"]), {"adaptation_potential"})
        self.assertTrue(
            {"hazard", "scenario", "model_run"}.isdisjoint(output.columns)
        )
        self.assertTrue(
            pd.isna(
                output.loc[1, "flopros_protection_standard_mode_rp"]
            )
        )

    def test_builds_five_tidy_adaptation_potential_card_tables(self) -> None:
        flopros = pd.DataFrame(
            {
                "adm_id": ["KEN-1", "KEN-2"],
                "flopros_protection_standard_mode_rp": [20.0, np.nan],
            }
        )
        nbs_columns: dict[str, list[float] | list[str]] = {
            "adm_id": ["KEN-1", "KEN-2"]
        }
        for opportunity, categories in {
            "slope_vegetation": ("total", "other", "crops", "bare_ground"),
            "mangrove": (
                "total",
                "accreting",
                "static_moderate_retreat",
                "fast_retreat",
            ),
            "river_catchment_restoration": ("total",),
        }.items():
            for category_order, category in enumerate(categories, start=1):
                prefix = f"nbs_{opportunity}"
                if category != "total":
                    prefix = f"{prefix}_{category}"
                area_column = (
                    f"{prefix}_total_km2"
                    if category == "total"
                    else f"{prefix}_km2"
                )
                base = float(category_order * 10)
                nbs_columns[area_column] = [base, base * 2]
                nbs_columns[
                    f"{prefix}_planting_cost_total_usd_2020"
                ] = [base + 1, (base + 1) * 2]
                nbs_columns[
                    f"{prefix}_regeneration_cost_total_usd_2020"
                ] = [base + 2, (base + 2) * 2]
                nbs_columns[
                    f"{prefix}_carbon_benefit_total_tonnes"
                ] = [base + 3, (base + 3) * 2]
                nbs_columns[
                    f"{prefix}_biodiversity_benefit_mean"
                ] = [base + 4, (base + 4) * 2]
        nbs = pd.DataFrame(nbs_columns)
        river_context = pd.DataFrame(
            {
                "adm_id": ["KEN-1", "KEN-2"],
                "river_length_total_km": [6.0, 10.0],
                "river_length_rural_km": [3.0, 4.0],
                "river_length_town_km": [2.0, 3.0],
                "river_length_city_km": [1.0, 3.0],
            }
        )

        cards = assemble_adaptation_potential_card_metrics(
            self.config,
            self.admin_regions,
            flopros,
            nbs,
            river_context,
        )

        self.assertEqual(
            set(cards),
            {
                SLOPE_VEGETATION_CARD,
                MANGROVES_CARD,
                RIVER_CATCHMENT_RESTORATION_CARD,
                EXISTING_FLOOD_PROTECTION_CARD,
                RIVER_NETWORK_CONTEXT_CARD,
            },
        )
        for card, output in cards.items():
            self.assertEqual(
                list(output.columns),
                [
                    *CARD_IDENTIFIER_COLUMNS,
                    *ADAPTATION_POTENTIAL_CARD_DIMENSIONS[card],
                    "value",
                ],
            )
            self.assertEqual(set(output["section"]), {"adaptation_potential"})
            self.assertEqual(set(output["card"]), {card})

        slope = cards[SLOPE_VEGETATION_CARD]
        self.assertEqual(len(slope), 2 * 20)
        self.assertNotIn("hazard", slope.columns)
        self.assertEqual(
            set(slope["land_use"]),
            {"total", "other", "crops", "bare_ground"},
        )
        native_cost = slope.loc[
            (slope["adm_id"] == "KEN-1")
            & (slope["land_use"] == "total")
            & (slope["metric"] == "implementation_cost")
            & (slope["implementation_approach"] == "native_planting"),
            "value",
        ].item()
        self.assertEqual(native_cost, 11.0)
        self.assertTrue(
            slope.loc[
                slope["metric"] == "opportunity_area",
                "implementation_approach",
            ].isna().all()
        )

        mangroves = cards[MANGROVES_CARD]
        self.assertEqual(len(mangroves), 2 * 20)
        self.assertNotIn("hazard", mangroves.columns)
        self.assertEqual(
            set(mangroves["shoreline_condition"]),
            {
                "total",
                "accreting",
                "static_moderate_retreat",
                "fast_retreat",
            },
        )

        restoration = cards[RIVER_CATCHMENT_RESTORATION_CARD]
        self.assertEqual(len(restoration), 2 * 5)
        self.assertEqual(
            set(restoration["adaptation_subsection"]),
            {"nature_based_solutions"},
        )

        protection = cards[EXISTING_FLOOD_PROTECTION_CARD]
        self.assertEqual(len(protection), 2)
        self.assertEqual(set(protection["unit"]), {"return_period_years"})
        self.assertTrue(
            protection.loc[protection["adm_id"] == "KEN-2", "value"].isna().all()
        )

        river = cards[RIVER_NETWORK_CONTEXT_CARD]
        self.assertEqual(len(river), 2 * 4)
        self.assertEqual(
            set(river["urbanisation_class"]),
            {"total", "rural", "town", "city"},
        )
        self.assertEqual(set(river["metric"]), {"river_length"})

    def test_river_context_groups_water_with_rural_and_fills_nearby_nodata(
        self,
    ) -> None:
        urbanisation = np.zeros((5, 5), dtype="int16")
        urbanisation[0] = [-9999, 10, 22, 30, 13]
        self._write_raster(
            self.local_directory / "KEN_ghs-mod.tif",
            urbanisation,
        )
        rivers = gpd.GeoDataFrame(
            {"HYRIV_ID": [1]},
            geometry=[LineString([(0, 4500), (4000, 4500)])],
            crs="EPSG:3857",
        )
        rivers.to_file(
            self.local_directory / "KEN_river_network.gpkg",
            layer="KEN_river_network",
            driver="GPKG",
        )

        metrics = build_river_network_context_metrics(
            self.config,
            self.admin_regions,
        ).set_index("adm_id")

        self.assertAlmostEqual(metrics.loc["KEN-1", "river_length_total_km"], 2)
        self.assertAlmostEqual(metrics.loc["KEN-1", "river_length_rural_km"], 2)
        self.assertAlmostEqual(metrics.loc["KEN-1", "river_length_town_km"], 0)
        self.assertAlmostEqual(metrics.loc["KEN-1", "river_length_city_km"], 0)
        self.assertAlmostEqual(metrics.loc["KEN-2", "river_length_total_km"], 2)
        self.assertAlmostEqual(metrics.loc["KEN-2", "river_length_rural_km"], 0)
        self.assertAlmostEqual(metrics.loc["KEN-2", "river_length_town_km"], 1)
        self.assertAlmostEqual(metrics.loc["KEN-2", "river_length_city_km"], 1)


if __name__ == "__main__":
    unittest.main()
