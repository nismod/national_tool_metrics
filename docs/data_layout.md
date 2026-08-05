# Data Layout and File Contracts

This document defines the canonical local-data structure used by the national
tool metrics workflows. Country directories use ISO3 codes and administrative
levels use lowercase directory names (`adm0`, `adm1`, and `adm2`).

## Canonical structure

```text
data/
  boundaries/
    <ISO3>/
      adm0/
      adm1/
      adm2/

  raw/
    <ISO3>/
      hazard/
        river_flooding/
        tropical_cyclones/

      exposure/
        population/
          worldpop/
        capital_stock/
        facilities/

      vulnerability/
        relative_wealth_index/
        wealth_distribution/
        accessibility/

      risk/
        socioeconomic/
          river_flood/
        infrastructure_networks/
          direct/
            river_flood/
            tropical_cyclone/
          indirect/
            tropical_cyclone/
        social_infrastructure/

      adaptation_potential/

    global/
      nature_based_solutions/
```

Adaptation Analysis inputs will be added after that section's scope is agreed.
The empty tropical-cyclone, indirect-risk, and social-infrastructure directories
reserve canonical locations for planned inputs.

## Data tracking

Raw data, boundary files, and generated results are ignored by Git. A checkout
therefore contains the folder skeleton but not the datasets needed to execute
the notebooks. Populate the documented paths locally and record dataset
provenance in `docs/data_sources.md`.

## Boundaries

The default boundary path is derived from the country and configured level:

```text
data/boundaries/<ISO3>/<admin-level>/<ISO3>_<admin-level>.shp
```

The Kenya configuration expects identifier and name fields called `shapeID` and
`shapeName`. The complete shapefile sidecar set must remain beside the `.shp`.

## Hazard inputs

### JRC river flooding

```text
data/raw/<ISO3>/hazard/river_flooding/
  <ISO3>_jrc-flood_RP10.tif
  <ISO3>_jrc-flood_RP20.tif
  <ISO3>_jrc-flood_RP50.tif
  <ISO3>_jrc-flood_RP75.tif
  <ISO3>_jrc-flood_RP100.tif
  <ISO3>_jrc-flood_RP200.tif
  <ISO3>_jrc-flood_RP500.tif
```

The rasters must share a CRS, transform, shape, and extent. Positive values are
treated as flood depth in metres; nonpositive and no-data cells are dry. The
workflow calculates flooded area, percentage of administrative area,
area-weighted mean depth, and area-weighted 90th-percentile depth for each
return period. Flood extent must not decrease as return period increases.

Tropical-cyclone Hazard inputs are reserved for a future workflow.

## Exposure inputs

### Population

The Population card reads eight pre-aggregated 90 m WorldPop rasters:

```text
data/raw/<ISO3>/exposure/population/worldpop/
  <ISO3>_worldpop_total.tif
  <ISO3>_worldpop_female.tif
  <ISO3>_worldpop_male.tif
  <ISO3>_worldpop_children_under5.tif
  <ISO3>_worldpop_school-age_5-14.tif
  <ISO3>_worldpop_working-age_15-64.tif
  <ISO3>_worldpop_older_65plus.tif
  <ISO3>_worldpop_female_15-49.tif
```

The current Kenya population epoch is configured as 2025.

### Capital stock

```text
data/raw/<ISO3>/exposure/capital_stock/
  <ISO3>_res_capstock.tif
  <ISO3>_nres_capstock.tif
  <ISO3>_inf_capstock.tif
```

These produce residential, non-residential, infrastructure, and total capital-
stock metrics.

### Networks and facilities

Exposure reuses the canonical road, rail, and power files stored under Risk,
avoiding duplicate geometry files. Government hospital and school counts use:

```text
data/raw/<ISO3>/exposure/facilities/
  building_hospitals_gov_summary_<ADMIN-LEVEL>__<ISO3>.csv
  building_schools_gov_summary_<ADMIN-LEVEL>__<ISO3>.csv
```

## Vulnerability inputs

### Relative Wealth Index

```text
data/raw/<ISO3>/vulnerability/relative_wealth_index/
  <ISO3>_rwi_summary_<ADMIN-LEVEL>.gpkg
```

The GeoPackage layer has the same name as the file stem and contains `shapeID`,
`shapeName`, `average_rwi`, and `population_weighted_rwi`.

### Wealth distribution

```text
data/raw/<ISO3>/vulnerability/wealth_distribution/
  <ISO3>_pop_wealth_summary_<ADMIN-LEVEL>.gpkg
```

The corresponding layer contains `shapeID`, `shapeName`, and `q1_total` through
`q5_total`. Quintile totals must be finite, nonnegative, and cover every selected
administrative region.

### Accessibility

```text
data/raw/<ISO3>/vulnerability/accessibility/
  access_<facility>_gov_<mode>_summary_<ADMIN-LEVEL>_<group>__<ISO3>.csv
```

The workflow expects hospitals and schools; walking and motorized modes; and
the total, female, male, infant, school-age, working-age, childbearing-age, and
elderly population groups. This produces 32 baseline travel-time metrics.

## Risk inputs

Risk produces one row per administrative region. The currently configured runs
are JRC baseline river flooding and STORM baseline tropical cyclone for epoch
2020. Metrics are namespaced with `river_flood_jrc_baseline_` and
`tropical_cyclone_storm_baseline_2020_`.

### Socioeconomic river-flood risk

```text
data/raw/<ISO3>/risk/socioeconomic/river_flood/
  <ISO3>_<ADMIN-LEVEL>_jrc_population_risk_metrics.gpkg
  <ISO3>_<ADMIN-LEVEL>_metrics_jrc-flood_protected_AAR_baseline_capstock.gpkg
  <ISO3>_<ADMIN-LEVEL>_metrics_jrc-flood_RP<RETURN-PERIOD>_baseline_capstock.gpkg
```

Return periods are 10, 20, 50, 75, 100, 200, and 500 years. GeoPackage layer
names match their file stems. Population risk includes the eight demographic
groups and five wealth quintiles. Capital-stock risk includes residential,
non-residential, infrastructure, and total losses. Administrative coverage and
component-to-total reconciliation are validated.

### Direct network risk

```text
data/raw/<ISO3>/risk/infrastructure_networks/direct/river_flood/
  river-jrc_road_damages.gpkg
  river-jrc_rail_damages.gpkg

data/raw/<ISO3>/risk/infrastructure_networks/direct/tropical_cyclone/
  power.gpkg
```

The road and rail files supply both Exposure geometries and JRC expected annual
damage attributes. The power file supplies Exposure geometry and STORM baseline
2020 expected annual damage. Indirect network risk is reserved for tropical
cyclone only. Social-infrastructure risk is supplied separately.

## Adaptation Potential inputs

### Existing flood protection and river context

```text
data/raw/<ISO3>/adaptation_potential/
  <ISO3>_flopros.tif
  <ISO3>_river_network.gpkg
  <ISO3>_ghs-mod.tif
```

FLOPROS values are raw protection return periods. Zero is excluded as no-data,
and the output reports the modal positive value in each region, resolving ties
to the lower return period.

River geometries are clipped to administrative boundaries and measured
geodesically. GHS-SMOD classes 10–13 are grouped as rural, including water;
classes 21–23 are town; and class 30 is city. The nearest valid urbanisation
class within 5 km may fill small raster no-data gaps.

### Nature-based solutions

```text
data/raw/global/nature_based_solutions/
  G_LandslideNbS_123_9s.tif
  G_PotentialNonCoastalTreeNBS_9s.tif
  ManRestorClass_9s.tif
  G_PlantingCost_9s.tif
  G_RegenCost_9s.tif
  ManPlantCost_9s.tif
  ManRegenCost_9s.tif
  G_CarbonBenefit_9s.tif
  G_BioBenefit_9s.tif
```

The three opportunity classes are slope vegetation, river-catchment
restoration, and mangroves. Slope vegetation is split by current land cover;
mangroves are split by shoreline condition. Planting and regeneration are
reported as separate cost options.

The source documentation describes the rasters as 9 arcseconds and applies a
nominal restored-cell area of 6.25 hectares. Cost and carbon values are scaled
by that area; biodiversity is averaged over valid opportunity cells. Mangrove
cells outside a polygon may be assigned to the nearest region within 5 km.

## Results

Each implemented notebook writes one canonical CSV:

```text
results/<ISO3>/<section>/<ISO3>_<admin-level>_<section>_metrics.csv
```

The six identifier columns are:

```text
country_iso3, country_name, admin_level, adm_id, adm_name, section
```

All other columns are metrics. Hazard, model, scenario, epoch, and return-
period distinctions are encoded in metric names. Each combination of country,
administrative level, administrative identifier, and section must be unique.

## Adding another country or administrative level

1. Add `config/countries/<ISO3>.toml` with canonical source paths.
2. Add the required boundary layer under `data/boundaries/<ISO3>/`.
3. Populate each implemented section's input contract for the selected level.
4. Record source provenance in `docs/data_sources.md`.
5. Run the automated tests and then execute each applicable notebook.
6. Check row coverage, metric names, units, and reconciliation rules before
   publishing the CSVs.
