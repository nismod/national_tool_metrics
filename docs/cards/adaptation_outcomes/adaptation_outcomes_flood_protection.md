# Flood Protection

## Summary

This scenario allows users to explore how river-flood impacts might change if
protection were increased to a selected design standard in areas meeting a
chosen minimum urbanisation threshold. Results are presented as three
complementary types of benefit:

- **Economic benefits:** modelled capital-stock losses avoided each year for
  residential buildings, non-residential buildings and infrastructure.
- **Social benefits:** modelled population exposure avoided each year, shown
  for five national wealth quintiles.
- **Inequality benefits:** how the distribution of remaining exposure across
  the wealth distribution changes after adaptation.

The tool also estimates the cost of increasing protection and lets users test
lower, central and upper cost assumptions, discount rates and appraisal
periods.

This is an exploratory scenario, not a design for specific flood defences or
a project appraisal. It assumes that protection is effective against floods
more frequent than the selected design standard. It does not model the type,
location or condition of individual defences; overtopping or structural
failure; maintenance; environmental and social impacts; indirect losses; or
future changes in flood hazard, population and assets.

## Exploring the results

The scenario is applied consistently across the whole country using the
selected assumptions. The map shows results for individual administrative
areas, while the charts in the right-hand sidebar summarise national outcomes.

Use the two adaptation controls to define the scenario:

- **Minimum Urbanisation Protection Threshold** determines which settlements
  are included. The selected class and all more urbanised classes are
  protected. For example, selecting **Urban centre** restricts the scenario
  to urban centres, while selecting a lower-density class includes a wider
  set of settlements.
- **Design Flood Protection** sets the target protection standard: 10, 20,
  50, 100 or 200 years. A 100-year design standard refers to a flood with a
  1% chance of being exceeded in any given year; it does not mean that such a
  flood occurs once every 100 years. Less frequent, more severe floods can
  still exceed the protection.

Under **Plot Subnational Metrics**, select adaptation cost or one of the
benefit measures to compare administrative areas. Economic and social
benefits can be viewed separately; for social benefits, select a wealth
quintile to map where avoided exposure for that group is greatest. Selecting
an area on the map shows its value.

The cost-benefit controls let users explore alternative assumptions:

- **Flood Protection Cost** switches between lower, central and upper
  construction-cost estimates.
- **Discount rate** determines how strongly benefits occurring in later years
  are reduced when expressed in present-value terms.
- **Appraisal period** determines how many years of annual benefits are
  included in the economic comparison.

The discount rate and appraisal period change the cost-benefit interpretation;
they do not change the areas protected or the modelled annual avoided loss and
exposure. Compare the one-off adaptation cost with the present value of annual
benefits, rather than directly comparing cost in USD with benefits in
USD/year.

### Economic benefits

The economic chart compares annual capital-stock loss after adaptation with
the loss avoided through increased flood protection. Together, these make up
the baseline annual loss:

`baseline loss = loss after adaptation + avoided loss`

Results are separated into residential, non-residential and infrastructure
capital stock. Larger avoided loss indicates a larger modelled economic
benefit, but it should be considered alongside the estimated protection cost.
Where cost-benefit metrics are displayed, a higher benefit-cost ratio or a
positive net present value indicates a stronger economic case under the
selected assumptions. These are scenario comparisons, not project budgets or
investment recommendations.

### Social benefits

The social chart compares annual population exposure remaining after
adaptation with avoided exposure for each wealth quintile:

`baseline exposure = exposure after adaptation + avoided exposure`

Q1 is the lowest-wealth 20% of the national population and Q5 is the
highest-wealth 20%. Compare both the total avoided exposure and its
distribution across quintiles. A scenario can produce a large overall benefit
while directing relatively little of that benefit to lower-wealth groups.

Avoided exposure represents the modelled reduction associated with the higher
protection standard. It is not a count of people guaranteed to be safe: floods
can exceed the design standard, and the model does not represent defence
failure, evacuation, disruption or other consequences of flooding.

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

The analysis is performed at grid-cell level using river-flood hazard,
existing flood protection, capital stock, population and relative wealth data.
Results are then aggregated to each administrative area.

1. Settlements are classified using the 2020 GHS Degree of Urbanisation
   dataset. The selected minimum class and all more urbanised classes are
   included in the scenario.
2. A target protection standard of 10, 20, 50, 100 or 200 years is assigned
   to eligible areas. Existing protection is taken from FLOPROS. Protection
   is only increased where the selected target is higher than the existing
   estimate; it is never reduced, and areas without valid FLOPROS data are not
   changed.
3. Baseline and adapted average annual impacts are calculated by integrating
   across JRC river-flood return periods, assuming no risk at the 2-year
   return period (bankfull). In the adapted scenario, impacts from floods more
   frequent than the revised protection standard are excluded, while impacts
   from rarer floods remain.
4. Economic impacts are calculated by applying flood depth-damage curves to
   residential, non-residential and infrastructure capital stock. Social
   impacts are calculated from the population exposed in each grid cell,
   including national Relative Wealth Index quintiles.
5. Avoided loss and avoided exposure equal the baseline result minus the
   adapted result. The concentration index measures how annual population
   exposure is distributed across people ranked from lower to higher relative
   wealth. Negative values indicate greater concentration among lower-wealth
   people, positive values indicate greater concentration among higher-wealth
   people, and zero indicates no wealth-related concentration.
6. Adaptation cost is estimated from the length of the selected HydroRIVERS
   network passing through eligible settlements, the increase from existing
   to target protection, and lower, central and upper unit-cost assumptions
   from Boulange et al. (2023). The method increases cost with both river
   length and the size of the protection upgrade. Costs are aggregated to the
   administrative areas shown in the tool.
7. Permanent-water cells and cells without the required hazard, exposure or
   vulnerability data are excluded before the results are aggregated.

The scenario simplifies flood protection as a change in design standard. It
does not identify suitable defence alignments or account for local hydraulic,
geotechnical, environmental, financial or governance constraints. It should
therefore be used to compare possible outcomes, not as an engineering design
or investment appraisal.

## Sources

| Dataset or method | Provider | Citation | Licence | Link |
|---|---|---|---|---|
| Flood-protection cost methodology | The University of Tokyo and collaborators | Boulange, J., Hirabayashi, Y., Tanoue, M. and Yamada, T. (2023). *Quantitative evaluation of flood damage methodologies under a portfolio of adaptation scenarios*. Natural Hazards, 118, 1855–1879. [https://doi.org/10.1007/s11069-023-06017-7](https://doi.org/10.1007/s11069-023-06017-7) | CC BY 4.0 | [Natural Hazards](https://link.springer.com/article/10.1007/s11069-023-06017-7) |
| Global river flood hazard maps | European Commission, Joint Research Centre | Baugh, Calum; Colonese, Juan; D'Angelo, Claudia; Dottori, Francesco; Neal, Jeffrey; Prudhomme, Christel; Salamon, Peter (2024). *Global river flood hazard maps*. European Commission, Joint Research Centre (JRC) [Dataset]. Available online at: [data.europa.eu/89h/jrc-floods-floodmapgl_rp50y-tif](http://data.europa.eu/89h/jrc-floods-floodmapgl_rp50y-tif). | CC BY 4.0 | [JRC Data Catalogue](https://data.jrc.ec.europa.eu/dataset/jrc-floods-floodmapgl_rp50y-tif) |
| FLOPROS flood-protection standards | Vrije Universiteit Amsterdam and collaborators | Scussolini, P. et al. (2016). *FLOPROS: an evolving global database of flood protection standards*. Natural Hazards and Earth System Sciences, 16, 1049–1061. [https://doi.org/10.5194/nhess-16-1049-2016](https://doi.org/10.5194/nhess-16-1049-2016) | CC BY 3.0 | [FLOPROS paper and supplement](https://nhess.copernicus.org/articles/16/1049/2016/) |
| Degree of Urbanisation, 2020 | European Commission, Joint Research Centre | Schiavina, M., Melchiorri, M. and Freire, S. (2023). *GHS-DUC R2023A—GHS Degree of Urbanisation Classification, application of the Degree of Urbanisation methodology (stage II) to GADM 4.1 layer, multitemporal (1975–2030)* [Dataset]. European Commission, Joint Research Centre. [https://doi.org/10.2905/DC0EB21D-472C-4F5A-8846-823C50836305](https://doi.org/10.2905/DC0EB21D-472C-4F5A-8846-823C50836305) | European Commission reuse notice; attribution required | [GHS-DUC R2023A](https://human-settlement.emergency.copernicus.eu/ghs_duc2023.php) |
| HydroRIVERS version 1 | HydroSHEDS | Lehner, B. and Grill, G. (2013). *Global river hydrography and network routing: baseline data and new approaches to study the world's large river systems*. Hydrological Processes, 27(15), 2171–2186. [https://doi.org/10.1002/hyp.9740](https://doi.org/10.1002/hyp.9740) | HydroSHEDS licence; free for scientific, educational and commercial use; attribution required | [HydroRIVERS](https://www.hydrosheds.org/products/hydrorivers) |
| National building and infrastructure capital-stock estimates | Global Infrastructure Risk Model and Resilience Index (GIRI); Coalition for Disaster Resilient Infrastructure and partners | Coalition for Disaster Resilient Infrastructure (2023). *Global Infrastructure Resilience: Capturing the resilience dividend—A Biennial Report from the Coalition for Disaster Resilient Infrastructure*. New Delhi. | CC BY 3.0 IGO; registration and acceptance of the source terms are required for download | [GIRI data download](https://giri.unepgrid.ch/form/subscribe-for-download-data) |
| Residential and non-residential built-up volume, 2020 | European Commission, Joint Research Centre | Pesaresi, M. and Politis, P. (2023). *GHS-BUILT-V R2023A—GHS built-up volume grids derived from joint assessment of Sentinel-2, Landsat and global DEM data, multitemporal (1975–2030)* [Dataset]. European Commission, Joint Research Centre. [https://doi.org/10.2905/AB2F107A-03CD-47A3-85E5-139D8EC63283](https://doi.org/10.2905/AB2F107A-03CD-47A3-85E5-139D8EC63283) | European Commission reuse notice; attribution required | [JRC Data Catalogue](https://data.jrc.ec.europa.eu/dataset/ab2f107a-03cd-47a3-85e5-139d8ec63283) |
| Road network used as the infrastructure-density proxy | OpenStreetMap contributors | OpenStreetMap contributors. *OpenStreetMap data*. | Open Data Commons Open Database License (ODbL) | [OpenStreetMap copyright and licence](https://www.openstreetmap.org/copyright) |
| Global flood depth-damage curves | European Commission, Joint Research Centre | Huizinga, J., de Moel, H. and Szewczyk, W. (2017). *Global flood depth-damage functions: Methodology and the database with guidelines*. EUR 28552 EN. Publications Office of the European Union. [https://doi.org/10.2760/16510](https://doi.org/10.2760/16510) | European Commission reuse notice; attribution required | [JRC Publications Repository](https://publications.jrc.ec.europa.eu/repository/handle/JRC105688) |
| Age- and sex-structured population | WorldPop, University of Southampton | Bondarenko, M. et al. (2025). *Estimates of 2015–2030 total number of people per grid square broken down by gender and age groupings at a resolution of 3 arc (approximately 100 m at the equator), R2025A version v1*. WorldPop. [https://doi.org/10.5258/SOTON/WP00841](https://doi.org/10.5258/SOTON/WP00841) | CC BY 4.0 | [WorldPop catalogue](https://hub.worldpop.org/project/categories?id=8) |
| Relative Wealth Index | Meta Data for Good | Chi, G., Fang, H., Chatterjee, S. and Blumenstock, J. E. (2022). *Microestimates of wealth for all low- and middle-income countries*. Proceedings of the National Academy of Sciences, 119(3), e2113658119. [https://doi.org/10.1073/pnas.2113658119](https://doi.org/10.1073/pnas.2113658119) | CC BY-NC 4.0 | [Humanitarian Data Exchange](https://data.humdata.org/dataset/relative-wealth-index) |
| Global Surface Water occurrence | European Commission, Joint Research Centre and Google | Pekel, J.-F., Cottam, A., Gorelick, N. and Belward, A. S. (2016). *High-resolution mapping of global surface water and its long-term changes*. Nature, 540, 418–422. [https://doi.org/10.1038/nature20584](https://doi.org/10.1038/nature20584) | Copernicus data; attribution required | [Global Surface Water](https://global-surface-water.appspot.com/download) |
| Administrative boundaries | geoBoundaries, William & Mary geoLab and community contributors | Runfola, D. et al. (2020). *geoBoundaries: A global database of political administrative boundaries*. PLoS ONE 15(4): e0231866. [https://doi.org/10.1371/journal.pone.0231866](https://doi.org/10.1371/journal.pone.0231866) | CC BY 4.0; attribution required | [geoBoundaries](https://www.geoboundaries.org/globalDownloads.html) |
