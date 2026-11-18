# Capital Stock Loss

## Summary

This card shows modelled direct river-flood damage to capital stock within each
administrative area, reported in US dollars for residential buildings,
non-residential buildings, infrastructure and their total. It reports
protection-adjusted average annual loss in US dollars per year, alongside the
loss from floods with design return periods of 10, 20, 50, 75, 100, 200 and
500 years. A return period describes an annual probability, not a regular
schedule: a 100-year flood has a 1% chance of occurring in any given year.
These are modelled direct physical losses, not observed losses, indirect
economic effects or recovery costs.

## How it is calculated

Risk is calculated at the grid-cell level using flood depth, capital-stock,
depth-damage, flood-protection and surface-water data. The grid-cell results
are then summed for each administrative area.

1. GIRI national capital-stock estimates are divided into residential,
   non-residential and infrastructure categories. Residential and
   non-residential values are spatially distributed using 2020 GHSL built-up
   volumes; infrastructure is distributed using an OpenStreetMap road-density
   proxy.
2. For each design return period, JRC flood depth is converted to a damage
   fraction using the global depth-damage curves developed by Huizinga et al.
   Separate curves are used for residential and infrastructure capital stock;
   the non-residential curve averages the commercial and industrial curves.
3. The damage fraction is multiplied by capital-stock value in each grid cell
   to estimate direct loss. Grid-cell losses are summed for each sector and
   administrative area, and `total` is calculated as the sum of the three
   sectors.
4. Protection-adjusted average annual loss is calculated by integrating across
   the grid-cell return-period losses, assuming no loss at the 2-year return
   period (bankfull). FLOPROS protection standards are applied before
   integration.
5. Permanent-water cells and cells without valid input data are excluded.

## Understanding the CSV download

| Item | Description |
|---|---|
| Filename | `<ISO3>_<admin-level>_risk_capital_stock_metrics.csv` |
| One row represents | One administrative area × one capital-stock sector × one risk metric |
| Rows per area | 32: four sectors × eight risk metrics |
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
| `card` | Card represented by the file | `capital_stock` |
| `risk_subsection` | Risk grouping within the tool | `socioeconomic` |
| `hazard` | Hazard represented | `river_flood` |
| `model` | Model or source family | `jrc` |
| `scenario` | Model scenario | `baseline` |
| `sector` | Capital-stock category represented by the row | `total`, `residential`, `non_residential`, `infrastructure` |
| `risk_metric` | Annualised loss or design return period | `average_annual_loss_protected`, `rp10`, `rp20`, `rp50`, `rp75`, `rp100`, `rp200`, `rp500` |
| `unit` | Unit for the selected risk metric | `usd_per_year` for average annual loss; `usd` for return-period loss |
| `value` | Modelled direct capital-stock loss described by the other fields | Rounded to three decimal places |

For example, to reproduce protection-adjusted average annual residential loss,
filter to:

```text
sector = residential
risk_metric = average_annual_loss_protected
unit = usd_per_year
```

This produces one row per administrative area. The `total` row already sums
the three component sectors, so it should not be added to the residential,
non-residential or infrastructure rows. Do not combine `usd` and
`usd_per_year` values.

## Sources

| Dataset | Provider | Citation | Licence | Link |
|---|---|---|---|---|
| Global river flood hazard maps | European Commission, Joint Research Centre | Baugh, Calum; Colonese, Juan; D'Angelo, Claudia; Dottori, Francesco; Neal, Jeffrey; Prudhomme, Christel; Salamon, Peter (2024). *Global river flood hazard maps*. European Commission, Joint Research Centre (JRC) [Dataset]. Available online at: [data.europa.eu/89h/jrc-floods-floodmapgl_rp50y-tif](http://data.europa.eu/89h/jrc-floods-floodmapgl_rp50y-tif). | CC BY 4.0 | [JRC Data Catalogue](https://data.jrc.ec.europa.eu/dataset/jrc-floods-floodmapgl_rp50y-tif) |
| Global flood depth-damage functions | European Commission, Joint Research Centre | Huizinga, J., de Moel, H. and Szewczyk, W. (2017). *Global flood depth-damage functions: Methodology and the database with guidelines*. EUR 28552 EN, Publications Office of the European Union. [https://doi.org/10.2760/16510](https://doi.org/10.2760/16510). | European Commission reuse policy; attribution required | [JRC Publications Repository](https://publications.jrc.ec.europa.eu/repository/handle/JRC105688) |
| National building and infrastructure capital-stock estimates | Global Infrastructure Risk Model and Resilience Index (GIRI); Coalition for Disaster Resilient Infrastructure and partners | Coalition for Disaster Resilient Infrastructure (2023). *Global Infrastructure Resilience: Capturing the resilience dividend—A Biennial Report from the Coalition for Disaster Resilient Infrastructure*. New Delhi. | CC BY 3.0 IGO; registration and acceptance of the source terms are required for download | [GIRI data download](https://giri.unepgrid.ch/form/subscribe-for-download-data) |
| GIRI Building Exposure Model methodology | University of Geneva and UNEP/GRID-Geneva | Piller, T., Benvenuti, A. and De Bono, A. (2023). *The GIRI global building exposure model (BEM)*. University of Geneva / UNEP/GRID-Geneva. | See source terms | [GIRI BEM report](https://giri.unepgrid.ch/sites/default/files/2023-09/GIRI_BEM_report_UNIGE.pdf) |
| Residential and non-residential built-up volume, 2020 | European Commission, Joint Research Centre | Pesaresi, M. and Politis, P. (2023). *GHS-BUILT-V R2023A—GHS built-up volume grids derived from joint assessment of Sentinel-2, Landsat and global DEM data, multitemporal (1975–2030)* [Dataset]. European Commission, Joint Research Centre. [https://doi.org/10.2905/AB2F107A-03CD-47A3-85E5-139D8EC63283](https://doi.org/10.2905/AB2F107A-03CD-47A3-85E5-139D8EC63283) | European Commission reuse notice; attribution required | [JRC Data Catalogue](https://data.jrc.ec.europa.eu/dataset/ab2f107a-03cd-47a3-85e5-139d8ec63283) |
| Road network used as the infrastructure-density proxy | OpenStreetMap contributors | OpenStreetMap contributors. *OpenStreetMap data*. | Open Data Commons Open Database License (ODbL) | [OpenStreetMap copyright and licence](https://www.openstreetmap.org/copyright) |
| FLOPROS flood-protection standards | Vrije Universiteit Amsterdam and collaborators | Scussolini, P. et al. (2016). *FLOPROS: an evolving global database of flood protection standards*. Natural Hazards and Earth System Sciences, 16, 1049–1061. [https://doi.org/10.5194/nhess-16-1049-2016](https://doi.org/10.5194/nhess-16-1049-2016). | CC BY 3.0 | [FLOPROS paper and supplement](https://nhess.copernicus.org/articles/16/1049/2016/) |
| Global Surface Water occurrence | European Commission, Joint Research Centre and Google | Pekel, J.-F., Cottam, A., Gorelick, N. and Belward, A.S. (2016). *High-resolution mapping of global surface water and its long-term changes*. Nature, 540, 418–422. [https://doi.org/10.1038/nature20584](https://doi.org/10.1038/nature20584). | Copernicus data; attribution required | [Global Surface Water](https://global-surface-water.appspot.com/download) |
| Administrative boundaries | geoBoundaries, William & Mary geoLab and community contributors | Runfola, D. et al. (2020). *geoBoundaries: A global database of political administrative boundaries*. PLoS ONE 15(4): e0231866. [https://doi.org/10.1371/journal.pone.0231866](https://doi.org/10.1371/journal.pone.0231866) | CC BY 4.0; attribution required | [geoBoundaries](https://www.geoboundaries.org/globalDownloads.html) |
