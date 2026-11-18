# Data-Source Manifest

This manifest records the source identity and local role of datasets used by
the workflows. Raw files are not tracked by Git. Update this document whenever
a source, version, population epoch, model run, or preprocessing method changes.

Fields marked **confirmation required** must be completed from the original
download record or upstream workflow before public release. They are left
explicitly unresolved rather than inferred from filenames.

## Country and global inputs

| Section | Dataset | Local files | Known metadata and use | Provenance status |
|---|---|---|---|---|
| Shared | geoBoundaries administrative boundaries | `data/boundaries/<ISO3>/<admin-level>/<ISO3>_<admin-level>.shp` | ADM0, ADM1, and ADM2 boundaries using `shapeID` and `shapeName`; downloaded from the geoBoundaries platform | CC BY 4.0 with attribution required; exact geoBoundaries release, product variant, download date, and any local conversion or renaming: **confirmation required** |
| Hazard | Global river flood hazard maps | `data/raw/<ISO3>/hazard/river_flooding/<ISO3>_jrc-flood_RP*.tif` | JRC global inundation-depth maps in metres for RP10, RP20, RP50, RP75, RP100, RP200, and RP500; river flow modelled with LISFLOOD and inundation with LISFLOOD-FP | European Commission, Joint Research Centre; DOI `10.2905/JRC.VD32YWG`; catalogue record issued 14 March 2024 and modified 20 March 2024; CC BY 4.0; local download date and preprocessing: **confirmation required** |
| Hazard | STORM tropical-cyclone wind hazard | `data/raw/global/tropical_cyclone/STORM_FIXED_RETURN_PERIODS_constant_*_YR_RP.tif` | Present-climate maximum 10-metre, 10-minute sustained wind speed in m/s at 10 km resolution for RP10, RP20, RP50, RP100, RP200, RP500, and RP1000 | STORM global GeoTIFF release v2, DOI `10.5281/zenodo.10931452`; derived from Bloemendaal et al. STORM v4 present-climate data, which the release identifies as CC0; download date: **confirmation required** |
| Exposure | WorldPop demographics | `data/raw/KEN/exposure/population/worldpop/KEN_worldpop_*.tif` | Pre-aggregated 90 m population rasters | Population reference year, WorldPop release, preprocessing workflow, and licence: **confirmation required** |
| Exposure | Capital stock | `data/raw/KEN/exposure/capital_stock/KEN_*_capstock.tif` | Residential, non-residential, and infrastructure capital stock | Provider, valuation year, currency basis, preprocessing, and licence: **confirmation required** |
| Exposure | Government facilities | `data/raw/KEN/exposure/facilities/building_*_gov_summary_*.csv` | Precomputed hospital and school counts by administrative region | Facility source, extraction date, and licence: **confirmation required** |
| Exposure / Risk | Road and rail networks | `data/raw/KEN/risk/infrastructure_networks/direct/river_flood/river-jrc_*_damages.gpkg` | Network geometries plus JRC river-flood expected annual damage | Upstream network source, damage-model version, currency year, and licence: **confirmation required** |
| Exposure / Risk | Power network | `data/raw/KEN/risk/infrastructure_networks/direct/tropical_cyclone/power.gpkg` | Power geometry plus STORM baseline 2020 expected annual damage | Upstream network source, STORM model version, currency year, and licence: **confirmation required** |
| Vulnerability | Relative Wealth Index summaries | `data/raw/KEN/vulnerability/relative_wealth_index/KEN_rwi_summary_<ADMIN-LEVEL>.gpkg` | Precomputed regional mean and population-weighted RWI | Original RWI release, population weighting input, processing method, and licence: **confirmation required** |
| Vulnerability | Wealth-quintile summaries | `data/raw/KEN/vulnerability/wealth_distribution/KEN_pop_wealth_summary_<ADMIN-LEVEL>.gpkg` | Population totals for national wealth quintiles; current population basis is 2025 | Source RWI, quintile construction, processing workflow, and licence: **confirmation required** |
| Vulnerability | Baseline accessibility | `data/raw/KEN/vulnerability/accessibility/access_*.csv` | Hospital and school travel-time summaries for two modes and eight population groups | Routing inputs, travel assumptions, production date, and licence: **confirmation required** |
| Risk | Population river-flood risk | `data/raw/KEN/risk/socioeconomic/river_flood/KEN_<ADMIN-LEVEL>_jrc_population_risk_metrics.gpkg` | Protected average annual exposure and RP10–RP500 exposure summaries for 2024 WorldPop demographic groups and national population-weighted RWI quintiles; JRC Global Surface Water occurrence above 50% is excluded | Traced to `flood-risk-inequality` commit `76ed21f` (MIT); uses JRC flood hazard, FLOPROS protection standards, WorldPop R2025A v1 constrained 2024 estimates, Meta RWI, GHS-POP R2023A as the reference grid, and geoBoundaries |
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

Update the [card CSV contracts](card_csv_contracts.md) when a change in source
data affects a published metric's definition or units.

## Confirmed source citations

### Administrative boundaries

The administrative boundaries are sourced from
[geoBoundaries](https://www.geoboundaries.org/globalDownloads.html), an open
database of political administrative boundaries maintained by the William &
Mary geoLab and community contributors. geoBoundaries data are licensed under
[Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/)
and require acknowledgement. The recommended written citation is:

> Runfola, D. et al. (2020). geoBoundaries: A global database of political
> administrative boundaries. *PLOS ONE*, 15(4), e0231866.
> https://doi.org/10.1371/journal.pone.0231866

The local filenames do not establish which geoBoundaries release or product
variant was downloaded. Record the release identifier and whether the files
came from the individual-country, Comprehensive Global Administrative Zones,
or another published package before the card documentation is approved.

### River-flood hazard

The river-flood rasters are sourced from the European Commission Joint
Research Centre dataset
[Global river flood hazard maps](https://data.jrc.ec.europa.eu/dataset/jrc-floods-floodmapgl_rp50y-tif).
The catalogue describes global gridded inundation maps for seven return periods
from 10 to 500 years, with cell values representing water depth in metres.
River flow is produced using LISFLOOD and inundation is simulated using
LISFLOOD-FP. The catalogue states that the dataset is not an official flood
hazard map.

The catalogue's requested dataset citation is:

> Baugh, Calum; Colonese, Juan; D'Angelo, Claudia; Dottori, Francesco; Neal,
> Jeffrey; Prudhomme, Christel; Salamon, Peter (2024). Global river flood
> hazard maps. European Commission, Joint Research Centre (JRC) [Dataset].
> Available online at:
> http://data.europa.eu/89h/jrc-floods-floodmapgl_rp50y-tif

The dataset is licensed under
[Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/)
with no access limitations. The catalogue record was issued on 14 March 2024
and modified on 20 March 2024. These catalogue dates should not be treated as
the hydrological reference period; that period and any local clipping or
preprocessing still require confirmation.
