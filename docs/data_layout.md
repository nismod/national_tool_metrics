# Section-Aligned Data Layout

The repository is migrating from the legacy `context`, `socioeconomic`,
`infrastructure`, and `service_disruption` layout to the six sections used by
the national tool:

1. Hazard
2. Exposure
3. Vulnerability
4. Risk
5. Adaptation Potential
6. Adaptation Analysis

The migration is staged so that existing notebooks continue to work until
their replacement section notebooks have been implemented and validated.

## Target raw-data structure

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

Adaptation Analysis input folders will be added once their inputs and
analytical scope have been agreed.

## Target results structure

Each tool section has one canonical output directory:

```text
results/<ISO3>/
  hazard/
  exposure/
  vulnerability/
  risk/
  adaptation_potential/
  adaptation_analysis/
```

The standard output filename is:

```text
<ISO3>_<admin-level>_<section>_metrics.csv
```

## Staged source selection

`config/countries/KEN.toml` lists the new path first and the legacy path
second for sources that have not yet been moved. Configuration selects the
first candidate containing data. Empty `.gitkeep` directories therefore do
not override populated legacy locations.

Each source directory should be moved as a complete unit. Partially copying a
dataset into its new directory can make that incomplete directory the selected
source.

Raw and generated data are ignored by Git. GitHub records the directory
skeleton and configuration, but not the local datasets or generated CSVs.

## River-flood Hazard rasters

The initial Hazard workflow creates one baseline JRC river-flood row per
administrative region. Return periods are encoded in the metric column names,
preserving the standard one-row-per-region, hazard, scenario, and model-run
grain. Input rasters use:

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

Positive raster values are treated as flood depth in metres, and no-data or
nonpositive cells are treated as dry. For each return period, the workflow
reports flooded area in square kilometres, flooded area as a percentage of
the administrative region, area-weighted mean depth, and area-weighted 90th-
percentile depth. Geographic cell areas and administrative-region areas are
calculated geodesically. The workflow also validates aligned raster grids and
nondecreasing flood extent with increasing return period.

Tropical-cyclone Hazard inputs and metrics are reserved for a later phase.

## Exposure WorldPop rasters

The Exposure Population card uses pre-aggregated 90 m WorldPop rasters in:

```text
data/raw/<ISO3>/exposure/population/worldpop/
```

The required filenames are:

```text
<ISO3>_worldpop_total.tif
<ISO3>_worldpop_female.tif
<ISO3>_worldpop_male.tif
<ISO3>_worldpop_children_under5.tif
<ISO3>_worldpop_school-age_5-14.tif
<ISO3>_worldpop_working-age_15-64.tif
<ISO3>_worldpop_older_65plus.tif
<ISO3>_worldpop_female_15-49.tif
```

## Planned migration sequence

| Stage | Source | Legacy location | Target location |
|---|---|---|---|
| Hazard | JRC river-flood depth maps | New input | `KEN/hazard/river_flooding` |
| Exposure | WorldPop | `KEN/context/worldpop` | `KEN/exposure/population/worldpop` |
| Exposure | Capital stock | `KEN/context/capital_stock` | `KEN/exposure/capital_stock` |
| Exposure | Facility counts | `KEN/context/accessibility/building_*` | `KEN/exposure/facilities` |
| Vulnerability | RWI | `KEN/context/rwi` | `KEN/vulnerability/relative_wealth_index` |
| Vulnerability | Wealth distribution | New input | `KEN/vulnerability/wealth_distribution` |
| Vulnerability | Accessibility | `KEN/context/accessibility/access_*` | `KEN/vulnerability/accessibility` |
| Risk | Socioeconomic flood risk | `KEN/socioeconomic/flooding` | `KEN/risk/socioeconomic/river_flood` |
| Risk | Direct river-flood network risk | `KEN/infrastructure/flooding` | `KEN/risk/infrastructure_networks/direct/river_flood` |
| Risk | Direct cyclone network risk | `KEN/infrastructure/tc` | `KEN/risk/infrastructure_networks/direct/tropical_cyclone` |
| Risk | Indirect network risk | Existing source to be confirmed | `KEN/risk/infrastructure_networks/indirect/tropical_cyclone` |
| Adaptation Potential | FLOPROS protection standards | New input | `KEN/adaptation_potential` |
| Adaptation Potential | Nature-based solutions | `global` | `global/nature_based_solutions` |

The existing road, rail, and power risk files also provide the geometries used
by the Exposure workflow. They live under Risk in the target layout and are
referenced by Exposure through the country configuration, avoiding duplicate
copies.

## Precomputed Vulnerability summaries

Precomputed Relative Wealth Index summaries use:

```text
data/raw/KEN/vulnerability/relative_wealth_index/
  <ISO3>_rwi_summary_<ADMIN-LEVEL>.gpkg
```

with layer name `<ISO3>_rwi_summary_<ADMIN-LEVEL>` and columns:

```text
shapeID
shapeName
average_rwi
population_weighted_rwi
```

Precomputed wealth-distribution summaries use:

```text
data/raw/KEN/vulnerability/wealth_distribution/
  <ISO3>_pop_wealth_summary_<ADMIN-LEVEL>.gpkg
```

with layer name `<ISO3>_pop_wealth_summary_<ADMIN-LEVEL>` and columns
`shapeID`, `shapeName`, and `q1_total` through `q5_total`.

The pipeline requires complete administrative coverage, unique identifiers,
finite values, and nonnegative quintile populations. Small regional
differences between the sum of quintiles and the independently aggregated
Exposure population are accepted.

## Risk workflow inputs

The consolidated Risk workflow creates one output row per administrative
region, hazard, scenario, and model run. The initial Kenya runs are JRC
baseline river flooding and STORM baseline tropical cyclone.

JRC socioeconomic summaries use admin-level-aware filenames:

```text
data/raw/<ISO3>/risk/socioeconomic/river_flood/
  <ISO3>_<ADMIN-LEVEL>_jrc_population_risk_metrics.gpkg
  <ISO3>_<ADMIN-LEVEL>_metrics_jrc-flood_protected_AAR_baseline_capstock.gpkg
  <ISO3>_<ADMIN-LEVEL>_metrics_jrc-flood_RP<RETURN-PERIOD>_baseline_capstock.gpkg
```

The layer names match the corresponding filename stems. The Population Risk
card uses `risk_map = AAR_protected` as its protection-adjusted annual-average
metric and includes `RP10`, `RP20`, `RP50`, `RP75`, `RP100`, `RP200`, and
`RP500` event exposure metrics for all eight demographic groups and five
wealth quintiles. The risk map is encoded in each metric column name, so the
return periods do not introduce another output row dimension. Adding
consistently named ADM2 summaries is sufficient for the workflow to discover
them after `admin_level` is changed.

The Capital Stock Risk card uses the protection-adjusted AAR file plus
separate `RP10`, `RP20`, `RP50`, `RP75`, `RP100`, `RP200`, and `RP500` files.
Each file contains residential, non-residential, infrastructure, and total
losses. Return-period losses are encoded in metric column names and retain the
same output row grain. Each file must have complete administrative coverage,
nonnegative finite values, and exact component-to-total reconciliation.

Direct network risk uses:

```text
data/raw/<ISO3>/risk/infrastructure_networks/direct/river_flood/
  river-jrc_road_damages.gpkg
  river-jrc_rail_damages.gpkg

data/raw/<ISO3>/risk/infrastructure_networks/direct/tropical_cyclone/
  power.gpkg
```

Indirect infrastructure risk is reserved for tropical cyclone only and will
be added when its source schema is available. Social-infrastructure risk is
produced by a separate workflow and is not calculated by this repository
phase.

## Adaptation Potential workflow inputs

The Adaptation Potential workflow creates one baseline row per administrative
region. Existing flood protection is read from:

```text
data/raw/<ISO3>/adaptation_potential/<ISO3>_flopros.tif
```

FLOPROS is treated as a raw return period. Zero-valued cells are excluded as
no-data and the metric is the modal positive return period in each region;
ties are resolved to the lower return period.

Nature-based solution inputs are stored in:

```text
data/raw/global/nature_based_solutions/
```

The required opportunity rasters are `G_LandslideNbS_123_9s.tif` for slope
vegetation, `ManRestorClass_9s.tif` for mangroves, and
`G_PotentialNonCoastalTreeNBS_9s.tif` for river catchment restoration. Generic
planting and regeneration costs use `G_PlantingCost_9s.tif` and
`G_RegenCost_9s.tif`; mangroves use `ManPlantCost_9s.tif` and
`ManRegenCost_9s.tif`. Carbon and biodiversity co-benefits use
`G_CarbonBenefit_9s.tif` and `G_BioBenefit_9s.tif` for all three classes.

The source documentation's nominal 9-arcsecond cell assumption is retained:
each fully restored opportunity cell represents 6.25 hectares. Cost and
carbon totals multiply valid per-hectare values by this area. Biodiversity is
reported as a mean over valid opportunity cells. The cost, carbon, and
biodiversity metrics retain both headline totals and category-level results.
Slope vegetation is split into other land cover, crops, and bare ground;
mangroves are split into accreting, static or moderately retreating, and
fast-retreating shoreline conditions. Planting cost, regeneration cost, and
carbon category totals reconcile to their corresponding NbS-class totals.
River catchment restoration remains a total because its opportunity raster is
binary. Mangrove cells outside an administrative polygon are assigned to the
nearest region only when it is within 5 km; all other opportunity cells are
assigned by cell centre.

The River Network Context card uses:

```text
data/raw/<ISO3>/adaptation_potential/
  <ISO3>_river_network.gpkg
  <ISO3>_ghs-mod.tif
```

River geometries are clipped to administrative boundaries, divided at
urbanisation raster-cell edges, and measured geodesically. GHS-SMOD classes
10, 11, 12, and 13 are grouped as rural (including class 10 water); classes
21, 22, and 23 are grouped as town; and class 30 is grouped as city. Total,
rural, town, and city river lengths are reported in kilometres, and the three
grouped lengths must reconcile to the total. Where small boundary differences
place river geometry on raster no-data cells, the nearest valid urbanisation
class within 5 km is used.
