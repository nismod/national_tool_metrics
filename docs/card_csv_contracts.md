# Downloadable Card CSV Contracts

The national tool publishes one CSV for each downloadable sidebar card. Card
CSVs use tidy rows: adjustable card controls are columns, and the plotted
number is stored in `value`. This makes the files straightforward to filter,
pivot, chart, and combine without parsing parameter values from metric names.

Sections are migrating to this contract one at a time. Hazard, Exposure, and
the approved Relative Wealth Index and Wealth Distribution cards use the card
contract now. Other outputs continue to use their existing contracts until
their card schemas are agreed.

## Standard identifiers

Every card CSV starts with:

```text
country_iso3,country_name,admin_level,adm_id,adm_name,section,card
```

These are followed by card parameter columns, then `value`. Rows must be unique
for the standard identifiers plus every declared parameter column. Geometry is
not included. Numeric values are rounded to three decimal places when the card
table is assembled.

The canonical path is:

```text
results/<ISO3>/<section>/<ISO3>_<admin-level>_<section>_<card>_metrics.csv
```

## Hazard

Hazard calculations remain wide internally. The downloadable tables reshape
the calculated values without changing the raster aggregation methods.

### River Flooding

File:

```text
<ISO3>_<admin-level>_hazard_river_flooding_metrics.csv
```

Columns after the shared identifiers:

```text
hazard,model,scenario,return_period_years,metric,unit,value
```

Constant provenance values are `river_flood`, `jrc`, and `baseline`.
`return_period_years` contains 10, 20, 50, 75, 100, 200, and 500.

| `metric` | `unit` | Internal calculated column |
|---|---|---|
| `flooded_area` | `km2` | `flooded_area_rp<return_period>_km2` |
| `area_flooded_percentage` | `percent` | `flooded_area_rp<return_period>_pct_admin` |
| `mean_flood_depth` | `m` | `flood_depth_mean_rp<return_period>_m` |
| `p90_flood_depth` | `m` | `flood_depth_p90_rp<return_period>_m` |

The row grain is administrative area x return period x metric: 28 rows per
administrative area.

### Tropical Cyclone Wind

File:

```text
<ISO3>_<admin-level>_hazard_tropical_cyclone_wind_metrics.csv
```

Columns after the shared identifiers:

```text
hazard,model,scenario,epoch,return_period_years,wind_threshold,
wind_threshold_ms,display_mode,metric,unit,value
```

Constant provenance values are `tropical_cyclone`, `storm`, `baseline`, and
epoch `2020`. `metric` is `wind_area`.

The calculated return periods are 10, 20, 50, 100, 200, 500, and 1000 years.
There is no 75-year STORM input in the current calculation contract.

| `wind_threshold` | `wind_threshold_ms` |
|---|---:|
| `tropical_storm_plus` | 18.0 |
| `cat1plus` | 29.0 |
| `cat2plus` | 37.6 |
| `cat3plus` | 43.4 |
| `cat4plus` | 51.1 |
| `cat5plus` | 61.6 |

`display_mode` is `area` with unit `km2`, or `percentage` with unit `percent`.
The row grain is administrative area x return period x wind threshold x
display mode: 84 rows per administrative area.

## Exposure

Exposure writes seven card CSVs:

```text
<ISO3>_<admin-level>_exposure_population_metrics.csv
<ISO3>_<admin-level>_exposure_capital_stock_metrics.csv
<ISO3>_<admin-level>_exposure_roads_metrics.csv
<ISO3>_<admin-level>_exposure_rail_metrics.csv
<ISO3>_<admin-level>_exposure_power_metrics.csv
<ISO3>_<admin-level>_exposure_healthcare_facilities_metrics.csv
<ISO3>_<admin-level>_exposure_educational_facilities_metrics.csv
```

### Population

Columns after the standard identifiers are:

```text
demographic_group,display_mode,unit,value
```

`demographic_group` is `total`, `female`, `male`, `infant`, `schoolage`,
`working`, `childbearing`, or `elderly`. `infant` means children under 5.
`display_mode` is `absolute` with unit `people`, or `percentage` with unit
`percent`. Every percentage uses total population as its denominator. A zero
total-population denominator produces a blank value.

### Capital Stock

Columns after the standard identifiers are:

```text
sector,unit,value
```

`sector` is `total`, `residential`, `non_residential`, or `infrastructure`, and
the unit is `usd`. Total is the sum of the three component sectors.

### Roads

Columns after the standard identifiers are:

```text
road_class,unit,value
```

`road_class` is `all`, `motorway`, `trunk`, `primary`, `secondary`, or
`tertiary`; unit is `km`. All is the sum of the five displayed classes, and a
class absent from the source is written as zero.

### Rail and Power

After the standard identifiers, each file has `unit` and `value`; unit is `km`.

### Healthcare and Educational Facilities

Columns after the standard identifiers are:

```text
metric,demographic_group,unit,value
```

`metric` is `count` with unit `facilities`, or `per_100k` with unit
`facilities_per_100k_people`. Count has one `total` row per administrative
area. Per-100,000 rows use each of the eight demographic groups above as the
denominator. A zero denominator produces a blank rate.

## Vulnerability

Vulnerability currently writes two card CSVs. Accessibility is produced by a
separate workflow and is not included in these files.

```text
<ISO3>_<admin-level>_vulnerability_relative_wealth_index_metrics.csv
<ISO3>_<admin-level>_vulnerability_wealth_distribution_metrics.csv
```

### Relative Wealth Index

Columns after the standard identifiers are:

```text
rwi_measure,unit,value
```

`rwi_measure` is `average` or `population_weighted`; unit is `index`. The row
grain is administrative area x RWI measure: two rows per administrative area.

### Wealth Distribution

Columns after the standard identifiers are:

```text
wealth_group,display_mode,unit,value
```

`wealth_group` is `q1`, `q2`, `q3`, `q4`, `q5`, or `bottom_40`.
`display_mode` is `absolute` with unit `people`, or `percentage` with unit
`percent`. `bottom_40` is the sum of `q1` and `q2`. Percentages use the sum of
the five quintiles as their denominator; a zero denominator produces a blank
value. The row grain is administrative area x wealth group x display mode: 12
rows per administrative area.

## Risk

Risk writes one CSV for each supported card:

```text
<ISO3>_<admin-level>_risk_population_metrics.csv
<ISO3>_<admin-level>_risk_capital_stock_metrics.csv
<ISO3>_<admin-level>_risk_direct_damage_metrics.csv
```

All three files begin their card-specific columns with:

```text
risk_subsection,hazard,model,scenario
```

`risk_subsection` preserves the sidebar hierarchy without lengthening the
filename. It is `socioeconomic` for Population and Capital Stock, and
`infrastructure_networks` for Direct Damage. `hazard`, `model`, and `scenario`
remain explicit so the source analytical run is clear.

### Population Risk

Columns after the standard identifiers are:

```text
risk_subsection,hazard,model,scenario,population_layer,population_group,
risk_metric,unit,value
```

`population_layer` is `demographics` or `wealth`. Demographic labels are
`total`, `female`, `male`, `infant`, `schoolage`, `working`, `childbearing`,
and `elderly`. Wealth labels are `q1` through `q5` and `bottom_40`;
`bottom_40` is the sum of `q1` and `q2`. `risk_metric` is
`average_annual_exposure_protected`, `rp10`, `rp20`, `rp50`, `rp75`, `rp100`,
`rp200`, or `rp500`. Average annual rows use `people_per_year`; return-period
rows use `people`. This card is limited to baseline JRC river flooding and has
112 rows per administrative area.

### Capital Stock Risk

Columns after the standard identifiers are:

```text
risk_subsection,hazard,model,scenario,sector,risk_metric,unit,value
```

`sector` is `total`, `residential`, `non_residential`, or `infrastructure`.
`risk_metric` is `average_annual_loss_protected`, `rp10`, `rp20`, `rp50`,
`rp75`, `rp100`, `rp200`, or `rp500`. Average annual rows use `usd_per_year`;
return-period rows use `usd`. This card is limited to baseline JRC river
flooding and has 32 rows per administrative area.

### Direct Damage

Columns after the standard identifiers are:

```text
risk_subsection,hazard,model,scenario,epoch,infrastructure_type,asset_class,
metric,unit,value
```

`infrastructure_type` is `road`, `rail`, or `power`. Road `asset_class` is
`all`, `motorway`, `trunk`, `primary`, `secondary`, or `tertiary`; rail and
power use `all`. A road class absent from a country source is written as zero.
`epoch` is blank for the river-flood rows and `2020` for the tropical-cyclone
row. `metric` is `direct_damage` and unit is `usd_per_year`. The current output
has eight rows per administrative area: six river-flood road rows, one
river-flood rail row, and one tropical-cyclone power row.

Indirect Impacts, Facilities, and Accessibility are supplied by deferred or
separate workflows and are not written by this Risk notebook.

## Adaptation Potential

Adaptation Potential writes one CSV for each supported sidebar card:

```text
<ISO3>_<admin-level>_adaptation_potential_slope_vegetation_metrics.csv
<ISO3>_<admin-level>_adaptation_potential_mangroves_metrics.csv
<ISO3>_<admin-level>_adaptation_potential_river_catchment_restoration_metrics.csv
<ISO3>_<admin-level>_adaptation_potential_existing_flood_protection_metrics.csv
<ISO3>_<admin-level>_adaptation_potential_river_network_context_metrics.csv
```

Every file includes `adaptation_subsection` after the standard identifiers. It
is `nature_based_solutions` or `flood_protection`.

### Slope Vegetation

Columns after the standard identifiers are:

```text
adaptation_subsection,land_use,metric,implementation_approach,
unit,value
```

`land_use` is `total`, `other`, `crops`, or `bare_ground`. `metric` is
`opportunity_area`, `implementation_cost`,
`carbon_benefit`, or `biodiversity_benefit`. Cost rows use
`implementation_approach` values `native_planting` and
`natural_regeneration`; it is blank for other metrics. Units are `km2`,
`usd_2020`, `tonnes`, and `index`, respectively. The row grain is
administrative area x land use x valid metric/approach combination: 20 rows
per administrative area.

### Mangroves

Columns after the standard identifiers are:

```text
adaptation_subsection,shoreline_condition,metric,
implementation_approach,unit,value
```

`shoreline_condition` is `total`, `accreting`, `static_moderate_retreat`, or
`fast_retreat`. Metric, approach, and unit values
match Slope Vegetation. The row grain is administrative area x shoreline
condition x valid metric/approach combination: 20 rows per administrative
area.

### River Catchment Restoration

Columns after the standard identifiers are:

```text
adaptation_subsection,metric,implementation_approach,unit,value
```

The card uses the same metric, approach, and unit values as the other
nature-based solution cards, but has no category dimension because its
opportunity raster is binary. The row grain is administrative area x valid
metric/approach combination: five rows per administrative area.

### Existing Flood Protection

Columns after the standard identifiers are:

```text
adaptation_subsection,metric,unit,value
```

`metric` is `protection_standard_mode` and unit is `return_period_years`.
Regions without positive FLOPROS cells retain a blank value. The row grain is
one row per administrative area.

### River Network Context

Columns after the standard identifiers are:

```text
adaptation_subsection,urbanisation_class,metric,unit,value
```

`urbanisation_class` is `total`, `rural`, `town`, or `city`; `metric` is
`river_length` and unit is `km`. The row grain is four rows per administrative
area. Rural, town, and city lengths reconcile to the total.

## Adaptation Outcomes

Adaptation Outcomes writes Dry Proofing, Relocation, and Flood Protection cards:

```text
<ISO3>_<admin-level>_adaptation_outcomes_dry_proofing_metrics.csv
<ISO3>_<admin-level>_adaptation_outcomes_relocation_metrics.csv
<ISO3>_<admin-level>_adaptation_outcomes_flood_protection_metrics.csv
```

Columns after the standard identifiers are:

```text
outcome_type,hazard,model,metric,statistic,sector,wealth_group,unit,value
```

`hazard` is `river_flood` and `model` is `jrc`. `sector` and `wealth_group`
are optional dimensions. The card contains 34 rows per administrative area:

- one `cost` row for `area_dry_proofed`, with statistic `estimate` and unit
  `m2`;
- 12 `economic_benefit` rows for `average_annual_loss`: four sectors
  (`residential`, `non_residential`, `infrastructure`, and `total`) crossed
  with `baseline`, `adapted`, and `avoided`, in `usd_per_year`;
- 18 `social_benefit` rows for `average_annual_flood_exposure`: `total` and
  wealth groups `q1` through `q5` crossed with `baseline`, `adapted`, and
  `avoided`, in `people_per_year`; and
- three `social_benefit` concentration-index rows with statistics `baseline`,
  `adapted`, and `change`, in `index` units.

Avoided values equal baseline minus adapted and may be negative. Concentration
index change equals adapted minus baseline. Reduction percentages and quintile
ratios are not included. Concentration-index values are blank when total flood
exposure is zero and the index is therefore undefined.

The Relocation card adds two dimensions after `model`:

```text
urbanisation_threshold,urbanisation_threshold_code
```

It contains the same 34-row outcome pattern for each of seven thresholds:
`remote_area` (11), `low_density_rural` (12), `rural_settlement` (13),
`suburban_area` (21), `semi_dense_urban_area` (22), `dense_urban` (23), and
`urban_centre` (30). Its cost row is `capstock_relocated`, with statistic
`estimate` and unit `usd`. Baseline rows are repeated within every threshold,
giving 238 rows per administrative area and a complete comparison when one
threshold is selected.

The Flood Protection card adds one more scenario dimension:

```text
urbanisation_threshold,urbanisation_threshold_code,design_return_period_years
```

`design_return_period_years` is 10, 20, 50, 100, or 200. Each of the 35 DUC
and return-period combinations contains three `adaptation_cost` rows with
statistics `estimate`, `lower`, and `upper`, in `million_usd`, followed by the
same 33 economic, social-exposure, and concentration-index rows used by the
other cards. `adj_adaptation_cost` is not published. This gives 36 rows per
scenario and 1,260 rows per administrative area. When all three raw cost
estimates are unavailable, their output values remain blank rather than being
treated as zero.
