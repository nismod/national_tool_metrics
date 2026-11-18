# Tropical Cyclone Wind

## Summary

This card shows the modelled area exposed to tropical-cyclone wind speeds
within each administrative area. It reports exposed area (km²) and percentage
of the administrative area for tropical-storm and Saffir–Simpson Category 1–5
wind thresholds, using design return periods of 10, 20, 50, 100, 200, 500 and
1,000 years. The thresholds are cumulative: for example, `cat3plus` includes
all areas reaching Category 3 or higher wind speeds.

These are **design return periods**. A 100-year design return period describes
wind speeds with a 1% annual probability of being equalled or exceeded under
the model assumptions. It is not a forecast or a cyclone expected to occur
once every 100 years.

## How it is calculated

Wind exposure is calculated from STORM wind-speed rasters and then aggregated
to each administrative area.

1. The wind-speed return-period maps are derived from STORM's synthetic
   catalogue of tropical-cyclone tracks. Return-period wind speeds are
   estimated empirically from this catalogue and provided as present-day
   rasters of modelled maximum 10-metre, 10-minute sustained wind speed.
2. Wind speeds are compared with thresholds for tropical storm and
   Saffir–Simpson Categories 1–5. The area meeting or exceeding each threshold
   is summed within each administrative area.
3. Exposed percentage is calculated as
   `area meeting or exceeding the threshold ÷ administrative area × 100`.
   No-data and non-finite wind-speed values are excluded.

## Understanding the CSV download

| Item | Description |
|---|---|
| Filename | `<ISO3>_<admin-level>_hazard_tropical_cyclone_wind_metrics.csv` |
| One row represents | One administrative area × one return period × one wind threshold × one display mode |
| Rows per area | 84: seven return periods × six wind thresholds × two display modes |
| Value column | `value` |
| Boundary join | `country_iso3` + `admin_level` + `adm_id` |
| Geometry | Not included |

| Field | Meaning | Values |
|---|---|---|
| `country_iso3` | Three-letter ISO country code | `KEN`, `MOZ` |
| `country_name` | Country name | `Kenya`, `Mozambique` |
| `admin_level` | Administrative level used for the calculation | `ADM0`, `ADM1`, `ADM2` |
| `adm_id` | geoBoundaries `shapeID`; used to link the CSV row to the matching boundary geometry | Identifier from the selected geoBoundaries layer |
| `adm_name` | geoBoundaries `shapeName` for the administrative area | Area name from the selected boundary layer |
| `section` | Section of the tool | `hazard` |
| `card` | Card represented by the file | `tropical_cyclone_wind` |
| `hazard` | Hazard represented | `tropical_cyclone` |
| `model` | Model or source family | `storm` |
| `scenario` | Model scenario | `baseline` |
| `epoch` | Reference epoch assigned to the baseline scenario | `2020` |
| `return_period_years` | Design return period for the modelled wind speed | `10`, `20`, `50`, `100`, `200`, `500`, `1000` |
| `wind_threshold` | Minimum wind category included in the result | `tropical_storm_plus`, `cat1plus`, `cat2plus`, `cat3plus`, `cat4plus`, `cat5plus` |
| `wind_threshold_ms` | Minimum sustained wind speed for the selected threshold | `18.0`, `29.0`, `37.6`, `43.4`, `51.1`, `61.6` metres per second |
| `display_mode` | Whether `value` reports area or percentage | `area`, `percentage` |
| `metric` | Quantity represented | `wind_area` |
| `unit` | Unit for the selected display mode | `km2`, `percent` |
| `value` | Area or percentage described by the other fields | Rounded to three decimal places; zero where no valid cells meet the threshold |

For example, to reproduce a map of the percentage area exposed to Category 3
or higher wind speeds for the 100-year design return period, filter to:

```text
return_period_years = 100
wind_threshold = cat3plus
display_mode = percentage
unit = percent
```

This produces one row per administrative area. Wind thresholds overlap, so do
not sum category rows. Return periods also represent separate design wind
conditions and should not be summed.

## Sources

| Dataset | Provider | Citation | Licence | Link |
|---|---|---|---|---|
| STORM wind-speed return-period methodology paper | Scientific Data | Bloemendaal, N.; de Moel, H.; Muis, S.; Haigh, I. D.; Aerts, J. C. J. H. (2020). *Estimation of global tropical cyclone wind speed probabilities using the STORM dataset*. Scientific Data 7, 377. [https://doi.org/10.1038/s41597-020-00720-x](https://doi.org/10.1038/s41597-020-00720-x) | CC BY 4.0 | [Scientific Data](https://www.nature.com/articles/s41597-020-00720-x) |
| STORM baseline wind-speed return periods | 4TU.ResearchData | Bloemendaal, N.; de Moel, H.; Muis, S.; Haigh, I. D.; Aerts, J. C. J. H. (2023). *STORM tropical cyclone wind speed return periods* (Version 4) [Dataset]. 4TU.ResearchData. [https://doi.org/10.4121/12705164.v4](https://doi.org/10.4121/12705164.v4) | CC0 | [4TU.ResearchData](https://doi.org/10.4121/12705164.v4) |
| Derived STORM wind-speed GeoTIFFs | University of Oxford | Russell, T. (2024). *STORM tropical cyclone wind speed return periods as global GeoTIFFs* (Version v2) [Dataset]. Zenodo. [https://doi.org/10.5281/zenodo.10931452](https://doi.org/10.5281/zenodo.10931452) | Derived from CC0 STORM v4 datasets | [Zenodo](https://zenodo.org/records/10931452) |
| Administrative boundaries | geoBoundaries, William & Mary geoLab and community contributors | Runfola, D. et al. (2020). *geoBoundaries: A global database of political administrative boundaries*. PLoS ONE 15(4): e0231866. [https://doi.org/10.1371/journal.pone.0231866](https://doi.org/10.1371/journal.pone.0231866) | CC BY 4.0; attribution required | [geoBoundaries](https://www.geoboundaries.org/globalDownloads.html) |

