# Roads

## Summary

This card shows the length of the mapped road network within each
administrative area, reported in kilometres for motorway, trunk, primary,
secondary and tertiary roads. It uses the actual road-line network from
OpenStreetMap rather than a modelled road-density surface. The `all` value is
the sum of these five classes only; it does not include residential, service,
unclassified or other lower-class roads.

## How it is calculated

Road lengths are calculated from OpenStreetMap line data and aggregated to
each administrative area.

1. Roads are classified as motorway, trunk, primary, secondary or tertiary.
   Other road classes are excluded from the card.
2. Road lines are clipped to each administrative boundary, so a road crossing
   a boundary contributes only the length located within that area.
3. The clipped road segments are measured in a metric coordinate system and
   summed in kilometres for each road class.
4. `all` is calculated as the sum of the five displayed road classes.

Results depend on the completeness and classification of the OpenStreetMap
network and should not be interpreted as a complete inventory of every road.

## Understanding the CSV download

| Item | Description |
|---|---|
| Filename | `<ISO3>_<admin-level>_exposure_roads_metrics.csv` |
| One row represents | One administrative area × one road class |
| Rows per area | 6: all included roads and five component classes |
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
| `card` | Card represented by the file | `roads` |
| `road_class` | Road class represented by the row | `all`, `motorway`, `trunk`, `primary`, `secondary`, `tertiary` |
| `unit` | Unit of road length | `km` |
| `value` | Total mapped road length for the selected class and administrative area | Kilometres, rounded to three decimal places; zero where the class is absent |

For example, to reproduce a map of primary-road length, filter to:

```text
road_class = primary
unit = km
```

This produces one row per administrative area. The `all` row already sums the
five component classes, so it should not be added to the individual class
rows. It does not include road classes outside the five listed above.

## Sources

| Dataset | Provider | Citation | Licence | Link |
|---|---|---|---|---|
| Road network | OpenStreetMap contributors | OpenStreetMap contributors. *OpenStreetMap data*. | Open Data Commons Open Database License (ODbL) | [OpenStreetMap copyright and licence](https://www.openstreetmap.org/copyright) |
| Administrative boundaries | geoBoundaries, William & Mary geoLab and community contributors | Runfola, D. et al. (2020). *geoBoundaries: A global database of political administrative boundaries*. PLoS ONE 15(4): e0231866. [https://doi.org/10.1371/journal.pone.0231866](https://doi.org/10.1371/journal.pone.0231866) | CC BY 4.0; attribution required | [geoBoundaries](https://www.geoboundaries.org/globalDownloads.html) |
