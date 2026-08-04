# Section-Aligned Data Layout

The repository is migrating from the legacy `context`, `socioeconomic`,
`infrastructure`, and `service_disruption` layout to the six sections used by
the national tool:

1. Hazard
2. Exposure
3. Vulnerability
4. Risk
5. Adaptation Options
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

    global/
      adaptation_options/
        nature_based_solutions/
```

Hazard and Adaptation Analysis input folders will be added once their inputs
and analytical scope have been agreed.

## Target results structure

Each tool section has one canonical output directory:

```text
results/<ISO3>/
  hazard/
  exposure/
  vulnerability/
  risk/
  adaptation_options/
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
| Adaptation Options | Nature-based solutions | `global` | `global/adaptation_options/nature_based_solutions` |

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
