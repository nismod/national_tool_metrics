# Power Network

## Summary

This card shows the total length of the GridFinder power-transmission network
within each administrative area, reported in kilometres. It measures the
length of mapped transmission-line geometry and does not represent electricity
access, voltage, carrying capacity, reliability or service quality. GridFinder
also provides predicted distribution-network data, but that layer is not
included in this card.

## How it is calculated

Power-transmission length is calculated from the GridFinder global power-system
dataset and aggregated to each administrative area. GridFinder's transmission
network is principally derived from OpenStreetMap power-line data; its broader
research dataset also uses open data and predictive modelling to address gaps
in global power-system mapping.

1. Valid power-transmission line geometries are selected from the GridFinder
   network dataset.
2. Transmission lines are clipped to each administrative boundary, so a line
   crossing a boundary contributes only the length located within that area.
3. The clipped line segments are measured in a metric coordinate system and
   summed in kilometres for each administrative area.

The network is a global research dataset rather than a verified utility asset
register. Results depend on the completeness and accuracy of the underlying
open data and should be independently validated for detailed planning.

## Understanding the CSV download

| Item | Description |
|---|---|
| Filename | `<ISO3>_<admin-level>_exposure_power_metrics.csv` |
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
| `card` | Card represented by the file | `power` |
| `unit` | Unit of power-transmission network length | `km` |
| `value` | Total mapped transmission-line length within the administrative area | Kilometres, rounded to three decimal places; zero where no transmission lines are present |

The CSV already contains one row per administrative area, so no additional
metric filter is required. Join the rows to the matching boundary geometry
using `country_iso3`, `admin_level` and `adm_id`.

## Sources

| Dataset | Provider | Citation | Licence | Link |
|---|---|---|---|---|
| GridFinder global power-system data | World Bank Group and University of Oxford | Arderne, C., Nicolas, C., Zorn, C. and Koks, E. E. (2019). *Data from: Predictive mapping of the global power system using open data* [Dataset]. Zenodo. [https://doi.org/10.5281/zenodo.3538890](https://doi.org/10.5281/zenodo.3538890) | CC BY 4.0; OpenStreetMap attribution applies to OSM-derived data | [GridFinder](https://gridfinder.rdrn.me/) |
| GridFinder methodology | Scientific Data | Arderne, C., Zorn, C., Nicolas, C. and Koks, E. E. (2020). *Predictive mapping of the global power system using open data*. Scientific Data 7, 19. [https://doi.org/10.1038/s41597-019-0347-4](https://doi.org/10.1038/s41597-019-0347-4) | CC BY 4.0 | [Scientific Data](https://www.nature.com/articles/s41597-019-0347-4) |
| Administrative boundaries | geoBoundaries, William & Mary geoLab and community contributors | Runfola, D. et al. (2020). *geoBoundaries: A global database of political administrative boundaries*. PLoS ONE 15(4): e0231866. [https://doi.org/10.1371/journal.pone.0231866](https://doi.org/10.1371/journal.pone.0231866) | CC BY 4.0; attribution required | [geoBoundaries](https://www.geoboundaries.org/globalDownloads.html) |
