# Population

## Summary

This card shows the estimated population within each administrative area,
reported as both the number of people and percentage of the total population.
Results are available for the total population and by sex and age group.

## How it is calculated

Population is calculated from 2024 WorldPop gridded age- and sex-structured
estimates and aggregated to each administrative area.

1. WorldPop age and sex layers are combined into the eight demographic groups
   shown in the card: total, female, male, children under 5, children aged
   5–14, people aged 15–64, women aged 15–49 and people aged 65 and over.
2. Population counts in valid grid cells are summed within each administrative
   area.
3. Each group's percentage is calculated as
   `group population ÷ total population × 100`. Percentage values are left
   blank where the total population is zero.

## Understanding the CSV download

| Item | Description |
|---|---|
| Filename | `<ISO3>_<admin-level>_exposure_population_metrics.csv` |
| One row represents | One administrative area × one demographic group × one display mode |
| Rows per area | 16: eight demographic groups × two display modes |
| Value column | `value` |
| Boundary join | `country_iso3` + `admin_level` + `adm_id` |

| Field | Meaning | Values |
|---|---|---|
| `country_iso3` | Three-letter ISO country code | `KEN`, `MOZ` |
| `country_name` | Country name | `Kenya`, `Mozambique` |
| `admin_level` | Administrative level used for the calculation | `ADM0`, `ADM1`, `ADM2` |
| `adm_id` | geoBoundaries `shapeID`; used to link the CSV row to the matching boundary geometry | Identifier from the selected geoBoundaries layer |
| `adm_name` | geoBoundaries `shapeName` for the administrative area | Area name from the selected boundary layer |
| `section` | Section of the tool | `exposure` |
| `card` | Card represented by the file | `population` |
| `demographic_group` | Population group represented by the row | `total`, `female`, `male`, `infant`, `schoolage`, `working`, `childbearing`, `elderly` |
| `display_mode` | Whether `value` reports a population count or percentage | `absolute`, `percentage` |
| `unit` | Unit for the selected display mode | `people`, `percent` |
| `value` | Population count or percentage described by the other fields | Rounded to three decimal places; percentage is blank where total population is zero |

The demographic-group labels correspond to:

| Value | Population group |
|---|---|
| `total` | Total population |
| `female` | Female population of all ages |
| `male` | Male population of all ages |
| `infant` | Children under 5 |
| `schoolage` | Children aged 5–14 |
| `working` | People aged 15–64 |
| `childbearing` | Women aged 15–49 |
| `elderly` | People aged 65 and over |

For example, to reproduce a map showing children aged 5–14 as a percentage of
the total population, filter to:

```text
demographic_group = schoolage
display_mode = percentage
unit = percent
```

This produces one row per administrative area. Do not sum all demographic
groups because several groups overlap. Do not combine `people` and `percent`
values.

## Sources

| Dataset | Provider | Citation | Licence | Link |
|---|---|---|---|---|
| Age- and sex-structured population | WorldPop, University of Southampton | Bondarenko, M. et al. (2025). *Estimates of 2015–2030 total number of people per grid square broken down by gender and age groupings at a resolution of 3 arc (approximately 100 m at the equator), R2025A version v1*. WorldPop. [https://doi.org/10.5258/SOTON/WP00841](https://doi.org/10.5258/SOTON/WP00841). | CC BY 4.0 | [WorldPop catalogue](https://hub.worldpop.org/project/categories?id=8) |
| Administrative boundaries | geoBoundaries, William & Mary geoLab and community contributors | Runfola, D. et al. (2020). *geoBoundaries: A global database of political administrative boundaries*. PLoS ONE 15(4): e0231866. [https://doi.org/10.1371/journal.pone.0231866](https://doi.org/10.1371/journal.pone.0231866) | CC BY 4.0; attribution required | [geoBoundaries](https://www.geoboundaries.org/globalDownloads.html) |
