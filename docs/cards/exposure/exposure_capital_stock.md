# Capital Stock

## Summary

This card shows the estimated value of capital stock within each
administrative area, reported in US dollars for residential buildings,
non-residential buildings and infrastructure. Total capital stock is the sum
of these three categories. The values represent estimated asset stock, not
annual economic output, flood damage or observed property-level valuations.

## How it is calculated

National capital-stock estimates are taken from the Global Infrastructure Risk
Model and Resilience Index (GIRI), classified into residential,
non-residential and infrastructure categories, and spatially disaggregated
before being aggregated to each administrative area.

1. Residential capital stock is distributed using the 2020 Global Human
   Settlement Layer (GHSL) residential built-up volume as a spatial weight.
2. Non-residential capital stock is distributed using the 2020 GHSL
   non-residential built-up volume as a spatial weight.
3. Infrastructure capital stock is distributed using an infrastructure-density
   map derived from OpenStreetMap roads as a proxy for the spatial distribution
   of infrastructure.
4. The allocated grid-cell values are summed within each administrative area.
   Total capital stock is calculated as residential + non-residential +
   infrastructure capital stock.

The spatial distribution therefore reflects the coverage and assumptions of
the GHSL and OpenStreetMap proxy layers; it should not be interpreted as a
survey of individual assets.

## Understanding the CSV download

| Item | Description |
|---|---|
| Filename | `<ISO3>_<admin-level>_exposure_capital_stock_metrics.csv` |
| One row represents | One administrative area × one capital-stock sector |
| Rows per area | 4: total and three component sectors |
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
| `card` | Card represented by the file | `capital_stock` |
| `sector` | Capital-stock category represented by the row | `total`, `residential`, `non_residential`, `infrastructure` |
| `unit` | Unit of the capital-stock value | `usd` |
| `value` | Estimated capital-stock value for the selected sector and administrative area | US dollars, rounded to three decimal places |

For example, to reproduce a map of residential capital stock, filter to:

```text
sector = residential
unit = usd
```

This produces one row per administrative area. The `total` row already sums
the three component sectors, so it should not be added to the residential,
non-residential or infrastructure rows.

## Sources

| Dataset | Provider | Citation | Licence | Link |
|---|---|---|---|---|
| National building and infrastructure capital-stock estimates | Global Infrastructure Risk Model and Resilience Index (GIRI); Coalition for Disaster Resilient Infrastructure and partners | Coalition for Disaster Resilient Infrastructure (2023). *Global Infrastructure Resilience: Capturing the resilience dividend—A Biennial Report from the Coalition for Disaster Resilient Infrastructure*. New Delhi. | CC BY 3.0 IGO; registration and acceptance of the source terms are required for download | [GIRI data download](https://giri.unepgrid.ch/form/subscribe-for-download-data) |
| GIRI Building Exposure Model methodology | University of Geneva and UNEP/GRID-Geneva | Piller, T., Benvenuti, A. and De Bono, A. (2023). *The GIRI global building exposure model (BEM)*. University of Geneva / UNEP/GRID-Geneva. | See source terms | [GIRI BEM report](https://giri.unepgrid.ch/sites/default/files/2023-09/GIRI_BEM_report_UNIGE.pdf) |
| Residential and non-residential built-up volume, 2020 | European Commission, Joint Research Centre | Pesaresi, M. and Politis, P. (2023). *GHS-BUILT-V R2023A—GHS built-up volume grids derived from joint assessment of Sentinel-2, Landsat and global DEM data, multitemporal (1975–2030)* [Dataset]. European Commission, Joint Research Centre. [https://doi.org/10.2905/AB2F107A-03CD-47A3-85E5-139D8EC63283](https://doi.org/10.2905/AB2F107A-03CD-47A3-85E5-139D8EC63283) | European Commission reuse notice; attribution required | [JRC Data Catalogue](https://data.jrc.ec.europa.eu/dataset/ab2f107a-03cd-47a3-85e5-139d8ec63283) |
| Road network used as the infrastructure-density proxy | OpenStreetMap contributors | OpenStreetMap contributors. *OpenStreetMap data*. | Open Data Commons Open Database License (ODbL) | [OpenStreetMap copyright and licence](https://www.openstreetmap.org/copyright) |
| Administrative boundaries | geoBoundaries, William & Mary geoLab and community contributors | Runfola, D. et al. (2020). *geoBoundaries: A global database of political administrative boundaries*. PLoS ONE 15(4): e0231866. [https://doi.org/10.1371/journal.pone.0231866](https://doi.org/10.1371/journal.pone.0231866) | CC BY 4.0; attribution required | [geoBoundaries](https://www.geoboundaries.org/globalDownloads.html) |
