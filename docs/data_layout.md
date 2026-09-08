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

      concentration_curves/

    global/
      nature_based_solutions/
      tropical_cyclone/
```

Adaptation Analysis inputs will be added after that section's scope is agreed.
The empty tropical-cyclone, indirect-risk, and social-infrastructure directories
reserve canonical locations for planned inputs.

Concentration curves are country-level inputs shared by socioeconomic,
adaptation-analysis, accessibility, and other tool areas. Their detailed input,
registry, and output contract is defined in
[`concentration_curves.md`](concentration_curves.md).

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

### STORM tropical-cyclone wind

```text
data/raw/global/tropical_cyclone/
  STORM_FIXED_RETURN_PERIODS_constant_10_YR_RP.tif
  STORM_FIXED_RETURN_PERIODS_constant_20_YR_RP.tif
  STORM_FIXED_RETURN_PERIODS_constant_50_YR_RP.tif
  STORM_FIXED_RETURN_PERIODS_constant_100_YR_RP.tif
  STORM_FIXED_RETURN_PERIODS_constant_200_YR_RP.tif
  STORM_FIXED_RETURN_PERIODS_constant_500_YR_RP.tif
  STORM_FIXED_RETURN_PERIODS_constant_1000_YR_RP.tif
```

The rasters must share a CRS, transform, shape, and extent. Values represent
10-metre, 10-minute sustained maximum wind speed in metres per second. For each
return period, the workflow calculates area and administrative-area share at
or above the tropical-storm threshold and converted Saffir-Simpson Category
1–5 thresholds: 18.0, 29.0, 37.6, 43.4, 51.1, and 61.6 m/s. Zero is no-data.
Areas must not increase with category severity or decrease with return period.
Raster cells crossing administrative boundaries are weighted by their exact
intersection area so coarse coastal cells are not assigned wholly to one region.

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
Blank baseline travel times are preserved as no-data when an administrative
region falls outside the upstream routing calculation; they are not converted
to zero-minute access. Observed travel times must be finite and nonnegative.

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
to the lower return period. Regions without positive FLOPROS cells retain a
blank no-data value; they are not assigned a zero-year protection standard.

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

## Adaptation Outcomes inputs

Dry proofing uses five administrative summaries at the configured level:

```text
data/raw/<ISO3>/adaptation_outcomes/
  <ISO3>_adaptation-cost_dp_m-jrc_<ADMIN-LEVEL>.gpkg
  <ISO3>_<ADMIN-LEVEL>_metrics_jrc-flood_AALs_adapted_dp_capstock.gpkg
  <ISO3>_<ADMIN-LEVEL>_metrics_jrc-flood_protected_AAR_baseline_capstock.gpkg
  <ISO3>_<ADMIN-LEVEL>_metrics_jrc-flood_adapted_AAR_V-EXP_S-rwi_dp.gpkg
  <ISO3>_<ADMIN-LEVEL>_metrics_jrc-flood_protected_AAR_V-EXP_S-rwi.gpkg
```

Relocation uses the same baseline summaries and three threshold-specific inputs
for each `<DUC>` code in `11`, `12`, `13`, `21`, `22`, `23`, and `30`:

```text
data/raw/<ISO3>/adaptation_outcomes/
  <ISO3>_adaptation-cost_rl_m-jrc_duc<DUC>_<ADMIN-LEVEL>.gpkg
  <ISO3>_<ADMIN-LEVEL>_metrics_jrc-flood_AALs_adapted_rl_duc<DUC>_capstock.gpkg
  <ISO3>_<ADMIN-LEVEL>_metrics_jrc-flood_adapted_AAR_V-EXP_S-rwi_rl_duc<DUC>.gpkg
```

Flood protection uses three inputs for every combination of `<DUC>` and design
return period `<RP>` in `10`, `20`, `50`, `100`, and `200`:

```text
data/raw/<ISO3>/adaptation_outcomes/
  <ISO3>_adaptation-cost_fp_rp<RP>_duc<DUC>_<ADMIN-LEVEL>.gpkg
  <ISO3>_<ADMIN-LEVEL>_metrics_jrc-flood_AALs_adapted_fp_rp<RP>_duc<DUC>_capstock.gpkg
  <ISO3>_<ADMIN-LEVEL>_metrics_jrc-flood_adapted_AAR_V-EXP_S-rwi_fp_rp<RP>_duc<DUC>.gpkg
```

The cost source supplies `area_dry-proofed` in square metres. Economic sources
supply residential, non-residential, infrastructure, and total average annual
capital-stock loss.
Social sources supply total and quintile average annual flood exposure plus
the concentration index. Avoided values are baseline minus adapted; negative
values are retained. Population and coverage fields are checked as contextual
quality indicators but are not published in the card CSV. The relocation cost
source supplies `capstock_relocated` in USD.
Flood-protection costs use `adaptation_cost`, `min_adaptation_cost`, and
`max_adaptation_cost` in millions of USD. `adj_adaptation_cost` is ignored.
Jointly missing cost estimates remain missing; partial cost ranges and ranges
that do not satisfy lower <= estimate <= upper are rejected.

ADM1 and ADM2 summaries must contain `shapeID`. The one-row ADM0 boundary and
summaries may omit it; the workflow assigns the country ISO3 code as the stable
ADM0 `adm_id` after verifying that both the boundary and each summary contain
exactly one country row. The standard output identifiers are therefore retained
at every administrative level.

## Results

Download outputs are migrating from section-wide CSVs to one tidy CSV per
sidebar card. Hazard writes:

```text
results/<ISO3>/hazard/<ISO3>_<admin-level>_hazard_river_flooding_metrics.csv
results/<ISO3>/hazard/<ISO3>_<admin-level>_hazard_tropical_cyclone_wind_metrics.csv
```

Every card CSV begins with seven standard identifiers:

```text
country_iso3, country_name, admin_level, adm_id, adm_name, section, card
```

Card-specific adjustable parameters follow the identifiers, and the plotted
number is stored in `value`. See
[`card_csv_contracts.md`](card_csv_contracts.md) for the exact schemas, row
grains, and permitted values.

Exposure writes seven card CSVs under `results/<ISO3>/exposure/`.
Vulnerability currently writes the two approved card outputs below;
Accessibility is supplied through a separate workflow.

```text
results/<ISO3>/vulnerability/<ISO3>_<admin-level>_vulnerability_relative_wealth_index_metrics.csv
results/<ISO3>/vulnerability/<ISO3>_<admin-level>_vulnerability_wealth_distribution_metrics.csv
```

Risk writes the three supported card outputs below. Each file includes a
`risk_subsection` column for the sidebar hierarchy. Population and Capital
Stock are river-flood-only; Direct Damage represents its supported hazards as
rows rather than separate files.

```text
results/<ISO3>/risk/<ISO3>_<admin-level>_risk_population_metrics.csv
results/<ISO3>/risk/<ISO3>_<admin-level>_risk_capital_stock_metrics.csv
results/<ISO3>/risk/<ISO3>_<admin-level>_risk_direct_damage_metrics.csv
```

Adaptation Potential writes five card outputs. Each file includes
`adaptation_subsection`; nature-based solution parameters are tidy columns
rather than parts of metric names.

```text
results/<ISO3>/adaptation_potential/<ISO3>_<admin-level>_adaptation_potential_slope_vegetation_metrics.csv
results/<ISO3>/adaptation_potential/<ISO3>_<admin-level>_adaptation_potential_mangroves_metrics.csv
results/<ISO3>/adaptation_potential/<ISO3>_<admin-level>_adaptation_potential_river_catchment_restoration_metrics.csv
results/<ISO3>/adaptation_potential/<ISO3>_<admin-level>_adaptation_potential_existing_flood_protection_metrics.csv
results/<ISO3>/adaptation_potential/<ISO3>_<admin-level>_adaptation_potential_river_network_context_metrics.csv
```

Adaptation Outcomes writes Dry Proofing, Relocation, and Flood Protection cards:

```text
results/<ISO3>/adaptation_outcomes/<ISO3>_<admin-level>_adaptation_outcomes_dry_proofing_metrics.csv
results/<ISO3>/adaptation_outcomes/<ISO3>_<admin-level>_adaptation_outcomes_relocation_metrics.csv
results/<ISO3>/adaptation_outcomes/<ISO3>_<admin-level>_adaptation_outcomes_flood_protection_metrics.csv
```

Sections not yet migrated continue to write:

```text
results/<ISO3>/<section>/<ISO3>_<admin-level>_<section>_metrics.csv
```

These legacy-wide files have one row per administrative region and encode run
dimensions in metric column names. The shared section writer remains in place
until all applicable sections have approved card contracts.

Concentration curves use a separate country-level output because their rows are
cumulative population shares rather than administrative regions:

```text
results/<ISO3>/concentration_curves/<ISO3>_concentration_curves.csv
```

## Adding another country or administrative level

1. Add `config/countries/<ISO3>.toml` with canonical source paths.
2. Add the required boundary layer under `data/boundaries/<ISO3>/`.
3. Populate each implemented section's input contract for the selected level.
4. Record source provenance in `docs/data_sources.md`.
5. Run the automated tests and then execute each applicable notebook.
6. Check row coverage, metric names, units, and reconciliation rules before
   publishing the CSVs.
