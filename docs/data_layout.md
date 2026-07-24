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

## Precomputed wealth distribution

The precomputed administrative wealth-distribution input should be added to:

```text
data/raw/KEN/vulnerability/wealth_distribution/
```

Its filename and schema will be added to the country configuration when the
dataset is available.
