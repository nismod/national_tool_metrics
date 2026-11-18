# Rail

## Summary

This card shows the total length of the mapped rail network within each
administrative area, reported in kilometres. It measures rail-line geometry
derived from OpenStreetMap and does not represent the number of routes,
stations, services, passengers, operational status or network capacity.

## How it is calculated

Rail length is calculated from OpenStreetMap-derived line data and aggregated
to each administrative area.

1. Valid rail-line geometries are selected from the network dataset.
2. Rail lines are clipped to each administrative boundary, so a line crossing
   a boundary contributes only the length located within that area.
3. The clipped rail segments are measured in a metric coordinate system and
   summed in kilometres for each administrative area.

Results depend on the completeness and classification of the OpenStreetMap
network and should not be interpreted as a complete inventory of operational
rail infrastructure.

## Understanding the CSV download

| Item | Description |
|---|---|
| Filename | `<ISO3>_<admin-level>_exposure_rail_metrics.csv` |
| One row represents | One administrative area |
| Rows per area | 1 |
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
| `section` | Section of the tool | `exposure` |
| `card` | Card represented by the file | `rail` |
| `unit` | Unit of rail-network length | `km` |
| `value` | Total mapped rail length within the administrative area | Kilometres, rounded to three decimal places; zero where no rail lines are present |

The CSV already contains one row per administrative area, so no additional
metric filter is required. Join the rows to the matching boundary geometry
using `country_iso3`, `admin_level` and `adm_id`.

## Sources

| Dataset | Provider | Citation | Licence | Link |
|---|---|---|---|---|
| Rail network | OpenStreetMap contributors | OpenStreetMap contributors. *OpenStreetMap data*. | Open Data Commons Open Database License (ODbL) | [OpenStreetMap copyright and licence](https://www.openstreetmap.org/copyright) |
| Administrative boundaries | geoBoundaries, William & Mary geoLab and community contributors | Runfola, D. et al. (2020). *geoBoundaries: A global database of political administrative boundaries*. PLoS ONE 15(4): e0231866. [https://doi.org/10.1371/journal.pone.0231866](https://doi.org/10.1371/journal.pone.0231866) | CC BY 4.0; attribution required | [geoBoundaries](https://www.geoboundaries.org/globalDownloads.html) |
