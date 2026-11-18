# Existing Flood Protection

## Summary

This card shows the most common estimated river-flood protection standard
within each administrative area, expressed as a design return period in
years. Higher values indicate protection against less frequent floods. For
example, a 50-year protection standard represents protection designed or
estimated for a flood with a 1-in-50, or 2%, chance of being exceeded in any
given year; it does not mean that such a flood occurs once every 50 years.

The value is a broad regional indicator from FLOPROS, not an inventory or
engineering assessment of individual flood defences. Protection can vary
within an administrative area, and the displayed value is the most common
standard rather than the highest, lowest or average standard.

## How it is calculated

The FLOPROS raster records river-flood protection standards as return periods.
FLOPROS combines available information on the design standard of existing
protection with policy-based and modelled estimates to improve global
coverage.

1. Administrative boundaries are overlaid on the FLOPROS protection-standard
   raster.
2. Zero values are treated as no-data and excluded. The most frequently
   occurring positive protection-standard value within each administrative
   area is selected.
3. If two or more values are equally frequent, the lower return period is
   selected. If an area contains no positive FLOPROS cells, the result is left
   blank rather than reported as zero.

## Understanding the CSV download

| Item | Description |
|---|---|
| Filename | `<ISO3>_<admin-level>_adaptation_potential_existing_flood_protection_metrics.csv` |
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
| `section` | Section of the tool | `adaptation_potential` |
| `card` | Card represented by the file | `existing_flood_protection` |
| `adaptation_subsection` | Adaptation-potential grouping within the tool | `flood_protection` |
| `metric` | Flood-protection summary represented by the row | `protection_standard_mode` |
| `unit` | Unit of the protection standard | `return_period_years` |
| `value` | Most common positive FLOPROS return period within the administrative area | Years, rounded to three decimal places; blank where no positive FLOPROS cell is available |

To reproduce the existing flood-protection view, filter to:

```text
metric = protection_standard_mode
unit = return_period_years
```

This produces one row per administrative area. The value should not be
interpreted as the average protection standard or as a guarantee that every
location in the area has that level of protection. Blank values represent
missing information, not a zero-year protection standard.

## Sources

| Dataset | Provider | Citation | Licence | Link |
|---|---|---|---|---|
| FLOPROS flood-protection standards | Vrije Universiteit Amsterdam and collaborators | Scussolini, P. et al. (2016). *FLOPROS: an evolving global database of flood protection standards*. Natural Hazards and Earth System Sciences, 16, 1049–1061. [https://doi.org/10.5194/nhess-16-1049-2016](https://doi.org/10.5194/nhess-16-1049-2016) | CC BY 3.0 | [FLOPROS paper and supplement](https://nhess.copernicus.org/articles/16/1049/2016/) |
| Administrative boundaries | geoBoundaries, William & Mary geoLab and community contributors | Runfola, D. et al. (2020). *geoBoundaries: A global database of political administrative boundaries*. PLoS ONE 15(4): e0231866. [https://doi.org/10.1371/journal.pone.0231866](https://doi.org/10.1371/journal.pone.0231866) | CC BY 4.0; attribution required | [geoBoundaries](https://www.geoboundaries.org/globalDownloads.html) |
