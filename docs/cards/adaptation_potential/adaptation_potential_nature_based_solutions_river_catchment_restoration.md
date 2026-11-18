# River Catchment Restoration Potential

## Summary

This card shows modelled areas where restoring trees within river catchments
may be suitable as a nature-based solution for reducing river-flood risk. It
reports the opportunity area, estimated implementation cost for native
planting and natural regeneration, potential carbon benefit, and a relative
biodiversity-benefit index within each administrative area.

Catchment restoration generally requires planting across a substantial area
to influence flooding. The results are intended for broad screening; they do
not confirm site-level feasibility or quantify the change in downstream flood
risk that restoration would achieve.

## How it is calculated

The metrics are calculated from global river-catchment restoration
opportunity, cost and benefit rasters and aggregated to each administrative
area.

1. Sub-basins with river-flood risk are identified. Within these sub-basins,
   potential restoration areas are currently non-woodland, non-cropped land
   away from the coast that could be restored to woodland.
2. Opportunity area is calculated by counting eligible cells and assuming a
   nominal area of 0.0625 km² (6.25 hectares) per cell.
3. Native-planting and natural-regeneration costs are calculated by applying
   the corresponding cost per hectare to each opportunity cell and summing
   the results. Costs are reported in 2020 US dollars.
4. Potential carbon benefit is calculated from the estimated additional
   carbon per hectare of mature forest after a nominal 50 years and is
   reported in tonnes. Biodiversity benefit is the mean relative
   biodiversity-benefit index across opportunity cells rather than a total
   that accumulates with area.
5. Results are aggregated to each administrative area. No-data and
   non-opportunity cells are excluded.

The source assessment considers restoration opportunities within the
immediate catchment only. It does not model downstream effects outside that
catchment.

## Understanding the CSV download

| Item | Description |
|---|---|
| Filename | `<ISO3>_<admin-level>_adaptation_potential_river_catchment_restoration_metrics.csv` |
| One row represents | One administrative area × one metric and, for cost rows, one implementation approach |
| Rows per area | 5: opportunity area, two implementation-cost approaches, carbon benefit and biodiversity benefit |
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
| `card` | Card represented by the file | `river_catchment_restoration` |
| `adaptation_subsection` | Adaptation-potential grouping within the tool | `nature_based_solutions` |
| `metric` | Quantity represented by the row | `opportunity_area`, `implementation_cost`, `carbon_benefit`, `biodiversity_benefit` |
| `implementation_approach` | Restoration approach used for cost estimates; blank for other metrics | `native_planting`, `natural_regeneration`, or blank |
| `unit` | Unit for the selected metric | `km2`, `usd_2020`, `tonnes`, `index` |
| `value` | Numeric result described by the other fields | Rounded to three decimal places; zero where no eligible cell contributes |

For example, to compare the estimated cost of river-catchment restoration
through natural regeneration, filter to:

```text
metric = implementation_cost
implementation_approach = natural_regeneration
unit = usd_2020
```

This produces one row per administrative area. Native planting and natural
regeneration are alternative cost estimates, not components to sum. The
biodiversity index is a mean and should not be added across administrative
areas.

## Sources

| Dataset | Provider | Citation | Licence | Link |
|---|---|---|---|---|
| Global nature-based-solution opportunity areas, planting costs and benefits | University of Oxford | Harwood, T. and Russell, T. (2025). *Global opportunity areas for nature-based solutions to reduce risks to infrastructure* [Dataset]. Zenodo. [https://doi.org/10.5281/zenodo.15001764](https://doi.org/10.5281/zenodo.15001764) | See Zenodo record | [Zenodo](https://zenodo.org/records/15001764) |
| Administrative boundaries | geoBoundaries, William & Mary geoLab and community contributors | Runfola, D. et al. (2020). *geoBoundaries: A global database of political administrative boundaries*. PLoS ONE 15(4): e0231866. [https://doi.org/10.1371/journal.pone.0231866](https://doi.org/10.1371/journal.pone.0231866) | CC BY 4.0; attribution required | [geoBoundaries](https://www.geoboundaries.org/globalDownloads.html) |
