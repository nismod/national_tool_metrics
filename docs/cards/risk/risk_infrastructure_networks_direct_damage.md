# Infrastructure Network Direct Damage

## Summary

This card shows modelled expected annual direct damage to infrastructure
networks within each administrative area, reported in US dollars per year. It
covers river-flood damage to roads and railways and tropical-cyclone wind
damage to power-transmission lines. Road damage is reported for motorway,
trunk, primary, secondary and tertiary roads, as well as their total; rail and
power are reported as totals.

Expected annual damage is the long-run average loss per year obtained by
combining damage from floods or winds of different annual probabilities. It
does not mean that this amount of damage will occur every year. The values
represent modelled physical damage and rehabilitation costs, not disruption,
loss of service or wider economic impacts.

## How it is calculated

The calculation follows the open-gira infrastructure-risk approach. Damage is
estimated for individual network segments and then aggregated to each
administrative area.

1. Road and rail networks are derived from OpenStreetMap. The road analysis
   includes motorway, trunk, primary, secondary and tertiary roads. The power
   analysis uses GridFinder transmission lines.
2. Network lines are split where they cross hazard-grid cells. JRC flood depth
   is assigned to road and rail segments, while STORM wind speed is assigned
   to power-transmission segments for the baseline 2020 climate.
3. For roads and railways, flood depth is converted to a damage fraction using
   infrastructure-specific depth-damage curves. The damage fraction is
   combined with segment length and rehabilitation cost to estimate direct
   damage. For power lines, the open-gira wind-damage model combines STORM wind
   hazard with transmission-network vulnerability and cost assumptions.
4. Damage is integrated across the modelled annual probabilities to calculate
   expected annual damage for each network segment.
5. Where a segment crosses an administrative boundary, its expected annual
   damage is allocated in proportion to the length within each area and then
   summed. Road `all` is the sum of the five displayed road classes.

These estimates are intended for risk screening. They depend on the coverage
of the network data and on globally consistent vulnerability and cost
assumptions rather than detailed engineering assessments of individual assets.

## Understanding the CSV download

| Item | Description |
|---|---|
| Filename | `<ISO3>_<admin-level>_risk_direct_damage_metrics.csv` |
| One row represents | One administrative area × one infrastructure and asset class |
| Rows per area | 8: six road rows, one rail row and one power row |
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
| `section` | Section of the tool | `risk` |
| `card` | Card represented by the file | `direct_damage` |
| `risk_subsection` | Risk grouping within the tool | `infrastructure_networks` |
| `hazard` | Hazard used in the damage calculation | `river_flood` for roads and rail; `tropical_cyclone` for power |
| `model` | Hazard model or source family | `jrc` for river flooding; `storm` for tropical cyclones |
| `scenario` | Model scenario | `baseline` |
| `epoch` | Reference year for the hazard scenario | Blank for river-flood rows; `2020` for tropical-cyclone power damage |
| `infrastructure_type` | Type of network represented | `road`, `rail`, `power` |
| `asset_class` | Network class represented by the row | Roads: `all`, `motorway`, `trunk`, `primary`, `secondary`, `tertiary`; rail and power: `all` |
| `metric` | Quantity represented | `direct_damage` |
| `unit` | Unit of expected annual direct damage | `usd_per_year` |
| `value` | Modelled expected annual direct damage described by the other fields | US dollars per year, rounded to three decimal places; zero where no damage is estimated |

For example, to reproduce expected annual flood damage to primary roads,
filter to:

```text
hazard = river_flood
infrastructure_type = road
asset_class = primary
metric = direct_damage
unit = usd_per_year
```

This produces one row per administrative area. The road `all` row already
sums the five displayed road classes and should not be added to them. Rail and
power rows represent different hazards, so they should not be interpreted as
directly comparable components of a single hazard total.

## Sources

| Dataset | Provider | Citation | Licence | Link |
|---|---|---|---|---|
| Infrastructure direct-damage workflow | nismod/open-gira contributors | nismod/open-gira contributors. *Open Global Infrastructure Risk/Resilience Analysis (open-gira)* [Software]. | MIT | [open-gira repository](https://github.com/nismod/open-gira) |
| Global infrastructure damage risk estimates | University of Oxford, nismod/open-gira contributors and OpenStreetMap contributors | Russell, T.; Thomas, F.; nismod/open-gira contributors; OpenStreetMap contributors (2022). *Global Infrastructure Damage Risk Estimates* [Dataset]. | CC BY-SA; ODbL applies to OpenStreetMap-derived data | [Global Infrastructure Risk data sources](https://global.infrastructureresilience.org/data) |
| Road and rail network | OpenStreetMap contributors | OpenStreetMap contributors. *OpenStreetMap data*. | Open Data Commons Open Database License (ODbL) | [OpenStreetMap copyright and licence](https://www.openstreetmap.org/copyright) |
| GridFinder power-transmission network | World Bank Group and University of Oxford | Arderne, C., Nicolas, C., Zorn, C. and Koks, E. E. (2019). *Data from: Predictive mapping of the global power system using open data* [Dataset]. Zenodo. [https://doi.org/10.5281/zenodo.3538890](https://doi.org/10.5281/zenodo.3538890) | CC BY 4.0; OpenStreetMap attribution applies to OSM-derived data | [GridFinder](https://gridfinder.rdrn.me/) |
| Global river flood hazard maps | European Commission, Joint Research Centre | Baugh, Calum; Colonese, Juan; D'Angelo, Claudia; Dottori, Francesco; Neal, Jeffrey; Prudhomme, Christel; Salamon, Peter (2024). *Global river flood hazard maps*. European Commission, Joint Research Centre (JRC) [Dataset]. Available online at: [data.europa.eu/89h/jrc-floods-floodmapgl_rp50y-tif](http://data.europa.eu/89h/jrc-floods-floodmapgl_rp50y-tif). | CC BY 4.0 | [JRC Data Catalogue](https://data.jrc.ec.europa.eu/dataset/jrc-floods-floodmapgl_rp50y-tif) |
| Road and railway vulnerability and cost methodology | Nature Communications | Koks, E. E., Rozenberg, J., Zorn, C. et al. (2019). *A global multi-hazard risk analysis of road and railway infrastructure assets*. Nature Communications 10, 2677. [https://doi.org/10.1038/s41467-019-10442-3](https://doi.org/10.1038/s41467-019-10442-3) | CC BY 4.0 | [Nature Communications](https://www.nature.com/articles/s41467-019-10442-3) |
| STORM baseline wind-speed return periods | 4TU.ResearchData | Bloemendaal, N.; de Moel, H.; Muis, S.; Haigh, I. D.; Aerts, J. C. J. H. (2023). *STORM tropical cyclone wind speed return periods* (Version 4) [Dataset]. 4TU.ResearchData. [https://doi.org/10.4121/12705164.v4](https://doi.org/10.4121/12705164.v4) | CC0 | [4TU.ResearchData](https://doi.org/10.4121/12705164.v4) |
| Administrative boundaries | geoBoundaries, William & Mary geoLab and community contributors | Runfola, D. et al. (2020). *geoBoundaries: A global database of political administrative boundaries*. PLoS ONE 15(4): e0231866. [https://doi.org/10.1371/journal.pone.0231866](https://doi.org/10.1371/journal.pone.0231866) | CC BY 4.0; attribution required | [geoBoundaries](https://www.geoboundaries.org/globalDownloads.html) |
