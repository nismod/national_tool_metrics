# Dry Proofing

## Summary

This scenario allows users to explore how river-flood impacts might change if
eligible residential buildings were dry-proofed against water depths below
one metre. Dry-proofing can include measures such as waterproofing walls,
sealing openings and raising vulnerable services. Results are presented as
three complementary types of benefit:

- **Economic benefits:** modelled residential capital-stock losses avoided
  each year.
- **Social benefits:** modelled population exposure avoided each year, shown
  for five national wealth quintiles.
- **Inequality benefits:** how the distribution of remaining exposure across
  the wealth distribution changes after adaptation.

The tool also lets users test unit cost, discount rate and appraisal-period
assumptions when comparing economic benefits with the estimated cost of
dry-proofing the eligible residential area.

This is an exploratory scenario, not a forecast of actual uptake or a project
appraisal. It assumes that dry-proofing is completely effective for modelled
depths below one metre and ineffective at greater depths. The selected unit
cost is a simplified implementation-cost assumption, not a detailed project
estimate. The analysis does not separately model maintenance costs, practical
constraints, building condition, warning and evacuation, indirect losses or
disruption.

## Exploring the results

The scenario is applied consistently across the whole country. The map shows
results for individual administrative areas, while the accompanying sidebar 
charts summarise national outcomes.

Use the map to compare outcomes across administrative areas. Under **Plot
Subnational Metrics**, select the metric to display and switch between
**Economic** and **Social** benefits. For social benefits, select a wealth
quintile to see where avoided exposure for that group is greatest. Selecting
an area on the map shows its value.

The cost-benefit controls let users explore alternative assumptions:

- **Unit cost (USD/m²)** changes the assumed cost of dry-proofing each square
  metre of eligible residential building area.
- **Discount rate** determines how strongly benefits occurring in later years
  are reduced when expressed in present-value terms.
- **Appraisal period** determines how many years of annual benefits are
  included in the economic comparison.

These controls change the cost-benefit interpretation; they do not change
which buildings are eligible or the modelled annual avoided loss and exposure.

### Economic benefits

The economic chart compares annual capital-stock loss after adaptation with
the loss avoided through dry-proofing. Together, these make up the baseline
annual loss:

`baseline loss = loss after adaptation + avoided loss`

Results are separated into residential, non-residential and infrastructure
capital stock. Dry-proofing is applied only to residential buildings, so the
model does not assign avoided loss to the other two sectors. Larger avoided
loss indicates a larger modelled economic benefit, but it should be considered
alongside the amount of residential area requiring treatment and the selected
unit-cost assumptions.

When comparing cost-benefit results, a higher benefit-cost ratio or positive
net present value indicates a stronger economic case under the selected unit
cost, discount rate and appraisal period. These are scenario comparisons, not
project budgets or investment recommendations.

### Social benefits

The social chart compares annual population exposure remaining after
adaptation with avoided exposure for each wealth quintile:

`baseline exposure = exposure after adaptation + avoided exposure`

Q1 is the lowest-wealth 20% of the national population and Q5 is the
highest-wealth 20%. Compare both the total avoided exposure and its
distribution across quintiles. A scenario can produce a large overall benefit
while directing relatively little of that benefit to lower-wealth groups.

Dry-proofing does not remove floodwater or eliminate risks to people. Avoided
exposure is therefore an exploratory proxy for people associated with
dry-proofed cells where modelled depth is below one metre, rather than a count
of people physically removed from the flood extent.

### Flood-risk inequality

The concentration chart compares the distribution of population exposure
before and after adaptation. People are ordered from lower to higher relative
wealth:

- the dashed diagonal represents an equal distribution of exposure across
  the population;
- a curve above the diagonal indicates that exposure is concentrated more
  heavily among lower-wealth people;
- a curve below the diagonal indicates greater concentration among
  higher-wealth people; and
- movement towards the diagonal indicates a more even distribution after
  adaptation.

Always interpret the inequality chart alongside the social-benefit chart. A
curve can move closer to equality even when substantial exposure remains, and
a change in distribution does not by itself show the size of the benefit.

## How it is calculated

The analysis is performed at grid-cell level using residential built-up area,
river-flood depth, capital stock, population and relative wealth data. Results
are then aggregated to each administrative area.

1. Residential buildings are considered eligible where the 500-year design
   flood has a positive depth and the 10-year design flood has a depth below
   one metre. These are modelled return periods: a 500-year flood has a 0.2%
   chance of being exceeded in any given year, not an expectation that it
   occurs once every 500 years.
2. The residential built-up area in eligible cells is summed to produce
   `area_dry_proofed`. The area comes from the 2020 GHS-BUILT-S residential
   surface layer.
3. For each modelled return period, flood depth in an eligible cell is set to
   zero for the impact calculation when it is below one metre. Depths of one
   metre or more are unchanged. The flood hazard itself is not altered; this
   is a simplified representation of reduced building vulnerability.
4. Residential capital-stock damage is recalculated using the adapted depths
   and the residential depth-damage curve. Non-residential and infrastructure
   losses are unchanged because this scenario applies only to residential
   buildings. Losses are integrated across flood probabilities, with FLOPROS
   protection standards applied, to estimate adapted average annual loss.
5. Population exposure is recalculated using the same below-one-metre rule
   for the total population and national Relative Wealth Index quintiles.
   Because dry-proofing does not physically prevent flooding, the resulting
   reduction should be interpreted as an exploratory proxy for people
   associated with protected cells, not as people removed from the flood
   extent or protected from every consequence of flooding.
6. The concentration index measures how population exposure is distributed
   across people ranked from lower to higher relative wealth within each
   administrative area. Negative values indicate greater concentration among
   lower-wealth people, positive values indicate greater concentration among
   higher-wealth people, and zero indicates no wealth-related concentration.
7. `avoided` equals baseline minus adapted for loss and exposure. Concentration
   index `change` equals adapted minus baseline. Permanent-water cells and
   cells without the required input data are excluded before aggregation.


Further methodological detail is provided in Bernhofen et al., Flood risk 
inequality in low- and middle-income countries and the benefits of adaptation 
(manuscript under review). The accompanying analysis code is available in the 
[flood-risk-inequality](https://github.com/mvbnffc/flood-risk-inequality) repository.

## Sources

| Dataset or method | Provider | Citation | Licence | Link |
|---|---|---|---|---|
| Global river flood hazard maps | European Commission, Joint Research Centre | Baugh, Calum; Colonese, Juan; D'Angelo, Claudia; Dottori, Francesco; Neal, Jeffrey; Prudhomme, Christel; Salamon, Peter (2024). *Global river flood hazard maps*. European Commission, Joint Research Centre (JRC) [Dataset]. Available online at: [data.europa.eu/89h/jrc-floods-floodmapgl_rp50y-tif](http://data.europa.eu/89h/jrc-floods-floodmapgl_rp50y-tif). | CC BY 4.0 | [JRC Data Catalogue](https://data.jrc.ec.europa.eu/dataset/jrc-floods-floodmapgl_rp50y-tif) |
| Residential built-up surface, 2020 | European Commission, Joint Research Centre | Pesaresi, M. and Politis, P. (2023). *GHS-BUILT-S R2023A—GHS built-up surface grid, derived from Sentinel-2 composite and Landsat, multitemporal (1975–2030)* [Dataset]. European Commission, Joint Research Centre. [https://doi.org/10.2905/9F06F36F-4B11-47EC-ABB0-4F8B7B1D72EA](https://doi.org/10.2905/9F06F36F-4B11-47EC-ABB0-4F8B7B1D72EA) | European Commission reuse notice; attribution required | [GHS-BUILT-S R2023A](https://human-settlement.emergency.copernicus.eu/ghs_buS2023.php) |
| National building and infrastructure capital-stock estimates | Global Infrastructure Risk Model and Resilience Index (GIRI); Coalition for Disaster Resilient Infrastructure and partners | Coalition for Disaster Resilient Infrastructure (2023). *Global Infrastructure Resilience: Capturing the resilience dividend—A Biennial Report from the Coalition for Disaster Resilient Infrastructure*. New Delhi. | CC BY 3.0 IGO; registration and acceptance of the source terms are required for download | [GIRI data download](https://giri.unepgrid.ch/form/subscribe-for-download-data) |
| Global flood depth-damage curves | European Commission, Joint Research Centre | Huizinga, J., de Moel, H. and Szewczyk, W. (2017). *Global flood depth-damage functions: Methodology and the database with guidelines*. EUR 28552 EN. Publications Office of the European Union. [https://doi.org/10.2760/16510](https://doi.org/10.2760/16510) | European Commission reuse notice; attribution required | [JRC Publications Repository](https://publications.jrc.ec.europa.eu/repository/handle/JRC105688) |
| Age- and sex-structured population | WorldPop, University of Southampton | Bondarenko, M. et al. (2025). *Estimates of 2015–2030 total number of people per grid square broken down by gender and age groupings at a resolution of 3 arc (approximately 100 m at the equator), R2025A version v1*. WorldPop. [https://doi.org/10.5258/SOTON/WP00841](https://doi.org/10.5258/SOTON/WP00841) | CC BY 4.0 | [WorldPop catalogue](https://hub.worldpop.org/project/categories?id=8) |
| Relative Wealth Index | Meta Data for Good | Chi, G., Fang, H., Chatterjee, S. and Blumenstock, J. E. (2022). *Microestimates of wealth for all low- and middle-income countries*. Proceedings of the National Academy of Sciences, 119(3), e2113658119. [https://doi.org/10.1073/pnas.2113658119](https://doi.org/10.1073/pnas.2113658119) | CC BY-NC 4.0 | [Humanitarian Data Exchange](https://data.humdata.org/dataset/relative-wealth-index) |
| FLOPROS flood-protection standards | Vrije Universiteit Amsterdam and collaborators | Scussolini, P. et al. (2016). *FLOPROS: an evolving global database of flood protection standards*. Natural Hazards and Earth System Sciences, 16, 1049–1061. [https://doi.org/10.5194/nhess-16-1049-2016](https://doi.org/10.5194/nhess-16-1049-2016) | CC BY 3.0 | [FLOPROS paper and supplement](https://nhess.copernicus.org/articles/16/1049/2016/) |
| Global Surface Water occurrence | European Commission, Joint Research Centre and Google | Pekel, J.-F., Cottam, A., Gorelick, N. and Belward, A. S. (2016). *High-resolution mapping of global surface water and its long-term changes*. Nature, 540, 418–422. [https://doi.org/10.1038/nature20584](https://doi.org/10.1038/nature20584) | Copernicus data; attribution required | [Global Surface Water](https://global-surface-water.appspot.com/download) |
| Administrative boundaries | geoBoundaries, William & Mary geoLab and community contributors | Runfola, D. et al. (2020). *geoBoundaries: A global database of political administrative boundaries*. PLoS ONE 15(4): e0231866. [https://doi.org/10.1371/journal.pone.0231866](https://doi.org/10.1371/journal.pone.0231866) | CC BY 4.0; attribution required | [geoBoundaries](https://www.geoboundaries.org/globalDownloads.html) |
