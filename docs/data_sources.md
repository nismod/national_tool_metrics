# Data-Source Manifest

This manifest records the source identity and local role of datasets used by
the workflows. Raw files are not tracked by Git. Update this document whenever
a source, version, population epoch, model run, or preprocessing method changes.

Fields marked **confirmation required** must be completed from the original
download record or upstream workflow before public release. They are left
explicitly unresolved rather than inferred from filenames.

## Kenya and global inputs

| Section | Dataset | Local files | Known metadata and use | Provenance status |
|---|---|---|---|---|
| Shared | Administrative boundaries | `data/boundaries/KEN/<admin-level>/KEN_<admin-level>.shp` | ADM0, ADM1, and ADM2 boundaries using `shapeID` and `shapeName` | Provider, release date, and licence: **confirmation required** |
| Hazard | JRC river-flood hazard | `data/raw/KEN/hazard/river_flooding/KEN_jrc-flood_RP*.tif` | Flood depth in metres for RP10, RP20, RP50, RP75, RP100, RP200, and RP500 | JRC product version, download location, and licence: **confirmation required** |
| Exposure | WorldPop demographics | `data/raw/KEN/exposure/population/worldpop/KEN_worldpop_*.tif` | Pre-aggregated 90 m population rasters; population epoch 2025 | Original WorldPop release, preprocessing workflow, and licence: **confirmation required** |
| Exposure | Capital stock | `data/raw/KEN/exposure/capital_stock/KEN_*_capstock.tif` | Residential, non-residential, and infrastructure capital stock | Provider, valuation year, currency basis, preprocessing, and licence: **confirmation required** |
| Exposure | Government facilities | `data/raw/KEN/exposure/facilities/building_*_gov_summary_*.csv` | Precomputed hospital and school counts by administrative region | Facility source, extraction date, and licence: **confirmation required** |
| Exposure / Risk | Road and rail networks | `data/raw/KEN/risk/infrastructure_networks/direct/river_flood/river-jrc_*_damages.gpkg` | Network geometries plus JRC river-flood expected annual damage | Upstream network source, damage-model version, currency year, and licence: **confirmation required** |
| Exposure / Risk | Power network | `data/raw/KEN/risk/infrastructure_networks/direct/tropical_cyclone/power.gpkg` | Power geometry plus STORM baseline 2020 expected annual damage | Upstream network source, STORM model version, currency year, and licence: **confirmation required** |
| Vulnerability | Relative Wealth Index summaries | `data/raw/KEN/vulnerability/relative_wealth_index/KEN_rwi_summary_<ADMIN-LEVEL>.gpkg` | Precomputed regional mean and population-weighted RWI | Original RWI release, population weighting input, processing method, and licence: **confirmation required** |
| Vulnerability | Wealth-quintile summaries | `data/raw/KEN/vulnerability/wealth_distribution/KEN_pop_wealth_summary_<ADMIN-LEVEL>.gpkg` | Population totals for national wealth quintiles; current population basis is 2025 | Source RWI, quintile construction, processing workflow, and licence: **confirmation required** |
| Vulnerability | Baseline accessibility | `data/raw/KEN/vulnerability/accessibility/access_*.csv` | Hospital and school travel-time summaries for two modes and eight population groups | Routing inputs, travel assumptions, production date, and licence: **confirmation required** |
| Risk | Population river-flood risk | `data/raw/KEN/risk/socioeconomic/river_flood/KEN_<ADMIN-LEVEL>_jrc_population_risk_metrics.gpkg` | Protected AAR and seven return-period exposure summaries for demographics and wealth quintiles | Upstream OPSIS workflow version, protection treatment, population epoch, and licence: **confirmation required** |
| Risk | Capital-stock river-flood risk | `data/raw/KEN/risk/socioeconomic/river_flood/KEN_<ADMIN-LEVEL>_metrics_jrc-flood_*.gpkg` | Protected AAR plus RP10–RP500 losses for three capital-stock classes and total | Upstream OPSIS workflow version, vulnerability curves, valuation year, and licence: **confirmation required** |
| Adaptation Potential | FLOPROS | `data/raw/KEN/adaptation_potential/KEN_flopros.tif` | Existing flood-protection standard represented as raw return periods; zero is treated as no-data | FLOPROS release/version, processing, and licence: **confirmation required** |
| Adaptation Potential | River network | `data/raw/KEN/adaptation_potential/KEN_river_network.gpkg` | River length by administrative region and urbanisation group | Provider, network selection criteria, extraction date, and licence: **confirmation required** |
| Adaptation Potential | GHS-SMOD | `data/raw/KEN/adaptation_potential/KEN_ghs-mod.tif` | Urbanisation classification grouped to rural, town, and city | GHS-SMOD release epoch, local raster modifications, and licence: **confirmation required** |
| Adaptation Potential | Global NbS opportunity, cost, carbon, and biodiversity layers | `data/raw/global/nature_based_solutions/*.tif` | Global 9-arcsecond layers with a nominal 6.25 ha restored cell | Dataset title and acknowledgement recorded below; release identifier, download location, and licence: **confirmation required** |
| Cross-section | Concentration curves | `data/raw/KEN/concentration_curves/*.csv` | Precomputed cumulative outcome shares by cumulative population share; individual curves and ranking metadata are registered in `config/countries/KEN.toml` | Upstream construction workflow, population basis, risk definition, processing date, and licence: **confirmation required** |

## Nature-based solutions metadata

The supplied documentation names the dataset **Global opportunity areas for
nature-based solutions to reduce risks to infrastructure**. It was produced by
the Environmental Change Institute, University of Oxford, through the project
“Global Tools to Unlock Capital for Investments in Nature-Based Solutions,”
funded by the Global Center on Adaptation.

The dataset is intended for broad screening rather than site-level project
design. It identifies:

- slope-vegetation opportunities for landslide-risk reduction;
- mangrove-restoration opportunities by shoreline condition; and
- catchment tree-restoration opportunities for river-flood reduction.

`G_PlantingCost_9s.tif` and `G_RegenCost_9s.tif` contain generic native planting
and natural-regeneration costs in 2020 USD per hectare. `ManPlantCost_9s.tif`
and `ManRegenCost_9s.tif` provide the corresponding mangrove costs.
`G_CarbonBenefit_9s.tif` describes additional mature-forest carbon after a
nominal 50 years in tonnes per hectare. `G_BioBenefit_9s.tif` is a relative
biodiversity-prioritisation measure and is summarized as a mean rather than an
additive total.

## Provenance checklist

Before distributing data or publishing derived metrics, record for every
source:

1. Provider and full dataset title.
2. Release/version and download date.
3. Stable download or catalogue URL.
4. Licence and redistribution constraints.
5. Spatial resolution, CRS, and geographic coverage.
6. Reference year, population epoch, model scenario, and currency year where
   applicable.
7. Any clipping, aggregation, reprojection, filtering, or renaming performed
   before the file entered this repository.
8. The upstream script, notebook, or workflow used to create precomputed
   summaries.

This information should be updated alongside `docs/metric_dictionary.csv` so
that source metadata and metric definitions remain synchronized.
