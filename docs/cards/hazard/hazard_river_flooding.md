# River Flooding

## Summary

This card shows the modelled extent and depth of river flooding within each
administrative area. It reports flooded area (km²), percentage of the area
flooded, mean flood depth and 90th-percentile flood depth for return periods of
10, 20, 50, 75, 100, 200 and 500 years. Depth statistics describe flooded
cells only, so they may decrease when a rarer flood expands into shallower
areas.

These are **design return periods**. A 100-year design return period describes
a flood with a 1% annual probability of being equalled or exceeded under the
model assumptions. 

## How it is calculated

1. Administrative boundaries are overlaid on JRC flood-depth rasters for each 
 design return period. No-data, non-finite and non-positive depth values are excluded.
2. Flooded cell areas are summed. Cell area is also used to calculate the
   area-weighted mean and 90th-percentile flood depths.
3. Flooded percentage is calculated as
   `flooded area ÷ administrative area × 100`.

## Understanding the CSV download

| Item | Description |
|---|---|
| Filename | `<ISO3>_<admin-level>_hazard_river_flooding_metrics.csv` |
| One row represents | One administrative area × one return period × one metric |
| Rows per area | 28: seven return periods × four metrics |
| Value column | `value` |
| Boundary join | `country_iso3` + `admin_level` + `adm_id` |

| Field | Meaning | Values |
|---|---|---|
| `country_iso3` | Three-letter ISO country code | `KEN`, `MOZ` |
| `country_name` | Country name | `Kenya`, `Mozambique` |
| `admin_level` | Administrative level used for the calculation | `ADM0`, `ADM1`, `ADM2` |
| `adm_id` | geoBoundaries `shapeID`; used to link the CSV row to the matching boundary geometry | Identifier from the selected geoBoundaries layer |
| `adm_name` | geoBoundaries `shapeName` for the administrative area | Area name from the selected boundary layer |
| `section` | Section of the tool | `hazard` |
| `card` | Card represented by the file | `river_flooding` |
| `hazard` | Hazard represented | `river_flood` |
| `model` | Model or source family | `jrc` |
| `scenario` | Model scenario | `baseline` |
| `return_period_years` | Design return period for the modelled flood | `10`, `20`, `50`, `75`, `100`, `200`, `500` |
| `metric` | Quantity stored in `value` | `flooded_area`, `area_flooded_percentage`, `mean_flood_depth`, `p90_flood_depth` |
| `unit` | Unit for the selected metric | `km2`, `percent`, `m` |
| `value` | Numeric result described by the other fields in the row | Rounded to three decimal places; zero when no valid positive-depth cells are included |

For example, to reproduce a map of the percentage area flooded for the
100-year design return period, filter to:

```text
return_period_years = 100
metric = area_flooded_percentage
unit = percent
```

This produces one row per administrative area. Do not sum rows across metrics
or return periods: they represent different measures or design flood
probabilities.

## Sources

| Dataset | Provider | Citation | Licence | Link |
|---|---|---|---|---|
| Global river flood hazard maps | European Commission, Joint Research Centre | Baugh, Calum; Colonese, Juan; D'Angelo, Claudia; Dottori, Francesco; Neal, Jeffrey; Prudhomme, Christel; Salamon, Peter (2024). *Global river flood hazard maps*. European Commission, Joint Research Centre (JRC) [Dataset]. Available online at: [data.europa.eu/89h/jrc-floods-floodmapgl_rp50y-tif](http://data.europa.eu/89h/jrc-floods-floodmapgl_rp50y-tif). | CC BY 4.0 | [JRC Data Catalogue](https://data.jrc.ec.europa.eu/dataset/jrc-floods-floodmapgl_rp50y-tif) |
| Administrative boundaries | geoBoundaries, William & Mary geoLab and community contributors | Runfola, D. et al. (2020). *geoBoundaries: A global database of political administrative boundaries*. PLoS ONE 15(4): e0231866. [https://doi.org/10.1371/journal.pone.0231866](https://doi.org/10.1371/journal.pone.0231866) | CC BY 4.0; attribution required | [geoBoundaries](https://www.geoboundaries.org/globalDownloads.html) |
