# River Network Context

## Summary

This card shows the length of the selected river network within each
administrative area, divided into rural, town and city settings. It provides
context on where river flood-protection measures might be considered and is
reported in kilometres.

The values describe river-network length, not the length currently protected
by flood defences. They do not measure flood hazard, exposure, risk or the
amount of protection required.

## How it is calculated

River-network lines are combined with the 2020 GHS-SMOD settlement
classification and aggregated to each administrative area.

1. The river network is derived from HydroRIVERS version 1. Rivers are clipped
   to the country boundary, and only reaches with an upstream drainage area of
   at least 500 km² are retained.
2. River lines are clipped to each administrative area and divided where they
   cross GHS-SMOD grid cells.
3. Each river section is classified as `rural`, `town` or `city`. GHS-SMOD
   classes 10–13 are grouped as rural, including water; classes 21–23 are
   grouped as town; and class 30 is grouped as city.
4. River-section lengths are measured geodesically and summed in kilometres.
   Where a river intersects a small no-data gap in the settlement raster, the
   nearest valid class within 5 km is used.
5. `total` is calculated as rural + town + city river length within the
   administrative area.

## Understanding the CSV download

| Item | Description |
|---|---|
| Filename | `<ISO3>_<admin-level>_adaptation_potential_river_network_context_metrics.csv` |
| One row represents | One administrative area × one urbanisation class |
| Rows per area | 4: total, rural, town and city |
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
| `section` | Section of the tool | `adaptation_potential` |
| `card` | Card represented by the file | `river_network_context` |
| `adaptation_subsection` | Adaptation-potential grouping within the tool | `flood_protection` |
| `urbanisation_class` | Settlement context assigned to the river sections | `total`, `rural`, `town`, `city` |
| `metric` | Quantity represented by the row | `river_length` |
| `unit` | Unit of river-network length | `km` |
| `value` | River-network length for the selected class and administrative area | Kilometres, rounded to three decimal places; zero where no selected river section is present |

For example, to compare river-network length through cities, filter to:

```text
urbanisation_class = city
metric = river_length
unit = km
```

This produces one row per administrative area. The `total` row already sums
the rural, town and city rows and should not be added to them. Because water
cells are included in `rural`, that category is broader than inhabited rural
settlements alone.

## Sources

| Dataset | Provider | Citation | Licence | Link |
|---|---|---|---|---|
| HydroRIVERS version 1 | HydroSHEDS | Lehner, B. and Grill, G. (2013). *Global river hydrography and network routing: baseline data and new approaches to study the world's large river systems*. Hydrological Processes, 27(15), 2171–2186. [https://doi.org/10.1002/hyp.9740](https://doi.org/10.1002/hyp.9740) | HydroSHEDS licence; free for scientific, educational and commercial use; attribution required | [HydroRIVERS](https://www.hydrosheds.org/products/hydrorivers) |
| GHS Settlement Model, 2020 | European Commission, Joint Research Centre | Schiavina, M., Melchiorri, M. and Pesaresi, M. (2023). *GHS-SMOD R2023A—GHS settlement layers, application of the Degree of Urbanisation methodology (stage I) to GHS-POP R2023A and GHS-BUILT-S R2023A, multitemporal (1975–2030)* [Dataset]. European Commission, Joint Research Centre. [https://doi.org/10.2905/A0DF7A6F-49DE-46EA-9BDE-563437A6E2BA](https://doi.org/10.2905/A0DF7A6F-49DE-46EA-9BDE-563437A6E2BA) | European Commission reuse notice; attribution required | [GHS-SMOD R2023A](https://human-settlement.emergency.copernicus.eu/ghs_smod2023.php) |
| Administrative boundaries | geoBoundaries, William & Mary geoLab and community contributors | Runfola, D. et al. (2020). *geoBoundaries: A global database of political administrative boundaries*. PLoS ONE 15(4): e0231866. [https://doi.org/10.1371/journal.pone.0231866](https://doi.org/10.1371/journal.pone.0231866) | CC BY 4.0; attribution required | [geoBoundaries](https://www.geoboundaries.org/globalDownloads.html) |
