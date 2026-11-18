# Population Risk

## Summary

This card shows the modelled population exposed to river flooding within each
administrative area, split by demographic group and national wealth quintile.
It reports protection-adjusted average annual exposure in people per year,
alongside the population exposed at return periods of 10, 20, 50, 75, 100, 200
and 500 years. Average annual exposure is the number of people expected to be
exposed in a given year, obtained by integrating exposure across the modelled
return periods; a return-period value is a single point on that curve — the
population exposed by a flood with that annual chance of occurring (a 100-year
flood has a 1% chance in any given year). "Protection-adjusted" means exposure
from events more frequent than the local flood protection standard has been
removed. Higher values indicate more people exposed, not deeper flooding or
greater economic damage.

## How it is calculated

Risk is calculated at the grid-cell level using flood hazard, population,
relative wealth, flood-protection and surface-water raster datasets. The
grid-cell results are then summed for each administrative area.

1. WorldPop 2024 age-sex data are combined into the demographic groups shown in
   the card. The Relative Wealth Index (RWI) and total population are used to
   create national population wealth quintiles, from Q1 (least wealthy) to Q5
   (wealthiest).
2. For each design return period, a grid cell is treated as exposed where the
   JRC raster shows a positive flood depth. The population in exposed cells is
   summed for each demographic group and wealth quintile.
3. Protection-adjusted average annual exposure is calculated by integrating
   across each grid cell's return-period exposure values, assuming no risk at
   the 2-year return period (bankfull). FLOPROS protection standards are applied
   before integration.
4. Permanent-water cells and cells without valid flood or population data are
   excluded.
5. Grid-cell results are aggregated to each administrative area. `bottom_40`
   is calculated as Q1 + Q2.

## Understanding the CSV download

| Item | Description |
|---|---|
| Filename | `<ISO3>_<admin-level>_risk_population_metrics.csv` |
| One row represents | One administrative area × one population group × one risk metric |
| Rows per area | 112: fourteen displayed groups × eight risk metrics |
| Value column | `value` |
| Boundary join | `country_iso3` + `admin_level` + `adm_id` |

| Field | Meaning | Values |
|---|---|---|
| `country_iso3` | Three-letter ISO country code | `KEN`, `MOZ` |
| `country_name` | Country name | `Kenya`, `Mozambique` |
| `admin_level` | Administrative level used for the calculation | `ADM0`, `ADM1`, `ADM2` |
| `adm_id` | geoBoundaries `shapeID`; used to link the CSV row to the matching boundary geometry | Identifier from the selected geoBoundaries layer |
| `adm_name` | geoBoundaries `shapeName` for the administrative area | Area name from the selected boundary layer |
| `section` | Section of the tool | `risk` |
| `card` | Card represented by the file | `population` |
| `risk_subsection` | Risk grouping within the tool | `socioeconomic` |
| `hazard` | Hazard represented | `river_flood` |
| `model` | Model or source family | `jrc` |
| `scenario` | Model scenario | `baseline` |
| `population_layer` | Type of population grouping | `demographics`, `wealth` |
| `population_group` | Group represented by the row | Demographics: `total`, `female`, `male`, `infant`, `schoolage`, `working`, `childbearing`, `elderly`; wealth: `q1`–`q5`, `bottom_40` |
| `risk_metric` | Annualised exposure or design return period | `average_annual_exposure_protected`, `rp10`, `rp20`, `rp50`, `rp75`, `rp100`, `rp200`, `rp500` |
| `unit` | Unit for the selected risk metric | `people_per_year` for average annual exposure; `people` for return-period exposure |
| `value` | Numeric population exposure described by the other fields | Rounded to three decimal places |

For example, to reproduce protection-adjusted average annual exposure for the
bottom 40% of the national wealth distribution, filter to:

```text
population_layer = wealth
population_group = bottom_40
risk_metric = average_annual_exposure_protected
unit = people_per_year
```

This produces one row per administrative area. `bottom_40` overlaps Q1 and Q2,
and several demographic groups overlap one another; do not sum all displayed
groups. Do not combine `people` and `people_per_year` values.

## Sources

| Dataset | Provider | Citation | Licence | Link |
|---|---|---|---|---|
| Global river flood hazard maps | European Commission, Joint Research Centre | Baugh, Calum; Colonese, Juan; D'Angelo, Claudia; Dottori, Francesco; Neal, Jeffrey; Prudhomme, Christel; Salamon, Peter (2024). *Global river flood hazard maps*. European Commission, Joint Research Centre (JRC) [Dataset]. Available online at: [data.europa.eu/89h/jrc-floods-floodmapgl_rp50y-tif](http://data.europa.eu/89h/jrc-floods-floodmapgl_rp50y-tif). | CC BY 4.0 | [JRC Data Catalogue](https://data.jrc.ec.europa.eu/dataset/jrc-floods-floodmapgl_rp50y-tif) |
| Age- and sex-structured population | WorldPop, University of Southampton | Bondarenko, M. et al. (2025). *Estimates of 2015–2030 total number of people per grid square broken down by gender and age groupings at a resolution of 3 arc (approximately 100 m at the equator), R2025A version v1*. WorldPop. [https://doi.org/10.5258/SOTON/WP00841](https://doi.org/10.5258/SOTON/WP00841). | CC BY 4.0 | [WorldPop catalogue](https://hub.worldpop.org/project/categories?id=8) |
| Relative Wealth Index | Meta Data for Good | Chi, G., Fang, H., Chatterjee, S. and Blumenstock, J.E. (2022). *Microestimates of wealth for all low- and middle-income countries*. Proceedings of the National Academy of Sciences, 119(3), e2113658119. [https://doi.org/10.1073/pnas.2113658119](https://doi.org/10.1073/pnas.2113658119). | CC BY-NC 4.0 | [Humanitarian Data Exchange](https://data.humdata.org/dataset/relative-wealth-index) |
| FLOPROS flood-protection standards | Vrije Universiteit Amsterdam and collaborators | Scussolini, P. et al. (2016). *FLOPROS: an evolving global database of flood protection standards*. Natural Hazards and Earth System Sciences, 16, 1049–1061. [https://doi.org/10.5194/nhess-16-1049-2016](https://doi.org/10.5194/nhess-16-1049-2016). | CC BY 3.0 | [FLOPROS paper and supplement](https://nhess.copernicus.org/articles/16/1049/2016/) |
| Global Surface Water occurrence | European Commission, Joint Research Centre and Google | Pekel, J.-F., Cottam, A., Gorelick, N. and Belward, A.S. (2016). *High-resolution mapping of global surface water and its long-term changes*. Nature, 540, 418–422. [https://doi.org/10.1038/nature20584](https://doi.org/10.1038/nature20584). | Copernicus data; attribution required | [Global Surface Water](https://global-surface-water.appspot.com/download) |
| Administrative boundaries | geoBoundaries, William & Mary geoLab and community contributors | Runfola, D. et al. (2020). *geoBoundaries: A global database of political administrative boundaries*. PLoS ONE 15(4): e0231866. [https://doi.org/10.1371/journal.pone.0231866](https://doi.org/10.1371/journal.pone.0231866) | CC BY 4.0; attribution required | [geoBoundaries](https://www.geoboundaries.org/globalDownloads.html) |
