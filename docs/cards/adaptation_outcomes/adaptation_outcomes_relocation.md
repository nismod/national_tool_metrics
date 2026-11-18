# Relocation

## Summary

This scenario allows users to explore how river-flood impacts might change if
people and residential buildings were relocated from places exposed to
frequent, deep flooding. Users can choose an urbanisation threshold to
determine which settlement classes are included. Results are presented as
three complementary types of benefit:

- **Economic benefits:** modelled residential capital-stock losses avoided
  each year.
- **Social benefits:** modelled population exposure avoided each year, shown
  for five national wealth quintiles.
- **Inequality benefits:** how the distribution of remaining exposure across
  the wealth distribution changes after relocation.

The tool also estimates relocation cost from the value of residential capital
stock moved and lets users test a cost multiplier, discount rate and appraisal
period.

This is an exploratory scenario, not a resettlement plan or project appraisal.
It does not identify destinations, replacement land or housing, or account for
housing availability, tenure and consent, livelihoods, access to services,
social and cultural disruption, compensation, environmental impacts or future
changes in flood hazard, population and assets.

## Exploring the results

The scenario is applied consistently across the whole country using the
selected assumptions. The map shows results for individual administrative
areas, while the charts in the right-hand sidebar summarise national outcomes.

Use **Relocation Urbanisation Threshold** to choose the most urbanised
settlement class eligible for relocation. The selected class and all less
urbanised classes are included. For example, selecting **Rural settlement**
includes rural settlements, low-density rural areas and remote areas, while
selecting **Urban centre** includes every settlement class. This direction is
the reverse of the flood-protection threshold, which includes the selected
class and more urbanised areas.

Only cells meeting the flood-depth and existing-protection criteria described
below are relocated; the urbanisation threshold does not mean that every
person or building in the selected settlement classes is moved.

Under **Plot Subnational Metrics**, select adaptation cost or one of the
benefit measures to compare administrative areas. Economic and social
benefits can be viewed separately; for social benefits, select a wealth
quintile to map where avoided exposure for that group is greatest. Selecting
an area on the map shows its value.

The cost-benefit controls let users explore alternative assumptions:

- **Relocation Cost Multiplier** multiplies the residential capital-stock
  value in relocated cells to produce a simplified relocation-cost estimate.
  A multiplier of 2, for example, estimates cost as twice the value of the
  residential capital stock relocated.
- **Discount rate** determines how strongly benefits occurring in later years
  are reduced when expressed in present-value terms.
- **Appraisal period** determines how many years of annual benefits are
  included in the economic comparison.

These controls change the cost or cost-benefit interpretation; they do not
change which cells are eligible or the modelled annual avoided loss and
exposure. Compare the one-off relocation cost with the present value of annual
benefits, rather than directly comparing cost in USD with benefits in
USD/year.

### Economic benefits

The economic chart compares annual capital-stock loss after relocation with
the loss avoided. Together, these make up the baseline annual loss:

`baseline loss = loss after adaptation + avoided loss`

Only residential buildings are relocated. The model therefore assigns avoided
loss to residential capital stock, while non-residential and infrastructure
losses remain unchanged. Larger avoided loss indicates a larger modelled
economic benefit, but it should be considered alongside the amount and value
of residential capital stock relocated and the selected cost multiplier.

Where cost-benefit metrics are displayed, a higher benefit-cost ratio or a
positive net present value indicates a stronger economic case under the
selected assumptions. These are scenario comparisons, not project budgets or
investment recommendations.

### Social benefits

The social chart compares annual population exposure remaining after
relocation with avoided exposure for each wealth quintile:

`baseline exposure = exposure after adaptation + avoided exposure`

Q1 is the lowest-wealth 20% of the national population and Q5 is the
highest-wealth 20%. Compare both the total avoided exposure and its
distribution across quintiles. A scenario can produce a large overall benefit
while directing relatively little of that benefit to lower-wealth groups.

The model removes relocated people from flood exposure at their original
location and assumes that they retain the same national wealth quintile. It
does not place them at a destination or estimate any flood risk at that
destination. Avoided exposure should therefore be interpreted as a potential
benefit under the scenario assumptions, not as a count of people guaranteed
to be safely and successfully relocated.

### Flood-risk inequality

The concentration chart compares the distribution of population exposure
before and after relocation. People are ordered from lower to higher relative
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
a change in distribution does not by itself show the size of the benefit or
the wider distributional effects of relocation.

## How it is calculated

The analysis is performed at grid-cell level using river-flood depth, existing
flood protection, settlement class, residential capital stock, population and
relative wealth data. Results are then aggregated to each administrative
area.

1. Settlement class is taken from the 2020 GHS Settlement Model. Cells in the
   selected class and all less urbanised classes are considered for
   relocation.
2. Within those settlement classes, a cell is eligible where the 10-year
   design flood has a depth of at least one metre and the FLOPROS existing
   protection estimate is below the 10-year standard. A 10-year design flood
   has a 10% chance of being exceeded in any given year; it does not occur on
   a regular ten-year schedule.
3. Relocation is represented by removing modelled river-flood risk from the
   eligible cells. For the calculation, these cells are assigned a protection
   level above the largest flood return period analysed. The population and
   residential assets are treated as having no remaining river-flood exposure
   or loss, but their destination is not modelled.
4. Residential capital-stock loss and population exposure are recalculated
   and integrated across the JRC flood return periods, assuming no risk at the
   2-year return period (bankfull). Non-residential and infrastructure losses
   remain at their baseline values because those assets are not relocated.
5. Avoided residential loss and population exposure equal the baseline result
   minus the adapted result. The concentration index measures how annual
   population exposure is distributed across people ranked from lower to
   higher relative wealth. Negative values indicate greater concentration
   among lower-wealth people, positive values indicate greater concentration
   among higher-wealth people, and zero indicates no wealth-related
   concentration.
6. Residential capital stock in eligible cells is summed for each
   administrative area. The tool multiplies this value by the user-selected
   relocation cost multiplier to estimate the one-off adaptation cost.
7. Permanent-water cells and cells without the required hazard, exposure or
   vulnerability data are excluded before the results are aggregated.

The scenario deliberately simplifies relocation to test its possible effects
on modelled flood loss, exposure and inequality. It should therefore be used
to compare possible outcomes, not to identify households for relocation or to
estimate the full financial, social or ethical implications of resettlement.

## Sources

| Dataset | Provider | Citation | Licence | Link |
|---|---|---|---|---|
| Global river flood hazard maps | European Commission, Joint Research Centre | Baugh, Calum; Colonese, Juan; D'Angelo, Claudia; Dottori, Francesco; Neal, Jeffrey; Prudhomme, Christel; Salamon, Peter (2024). *Global river flood hazard maps*. European Commission, Joint Research Centre (JRC) [Dataset]. Available online at: [data.europa.eu/89h/jrc-floods-floodmapgl_rp50y-tif](http://data.europa.eu/89h/jrc-floods-floodmapgl_rp50y-tif). | CC BY 4.0 | [JRC Data Catalogue](https://data.jrc.ec.europa.eu/dataset/jrc-floods-floodmapgl_rp50y-tif) |
| GHS Settlement Model, 2020 | European Commission, Joint Research Centre | Schiavina, M., Melchiorri, M. and Pesaresi, M. (2023). *GHS-SMOD R2023A—GHS settlement layers, application of the Degree of Urbanisation methodology (stage I) to GHS-POP R2023A and GHS-BUILT-S R2023A, multitemporal (1975–2030)* [Dataset]. European Commission, Joint Research Centre. [https://doi.org/10.2905/A0DF7A6F-49DE-46EA-9BDE-563437A6E2BA](https://doi.org/10.2905/A0DF7A6F-49DE-46EA-9BDE-563437A6E2BA) | European Commission reuse notice; attribution required | [GHS-SMOD R2023A](https://human-settlement.emergency.copernicus.eu/ghs_smod2023.php) |
| FLOPROS flood-protection standards | Vrije Universiteit Amsterdam and collaborators | Scussolini, P. et al. (2016). *FLOPROS: an evolving global database of flood protection standards*. Natural Hazards and Earth System Sciences, 16, 1049–1061. [https://doi.org/10.5194/nhess-16-1049-2016](https://doi.org/10.5194/nhess-16-1049-2016) | CC BY 3.0 | [FLOPROS paper and supplement](https://nhess.copernicus.org/articles/16/1049/2016/) |
| National building and infrastructure capital-stock estimates | Global Infrastructure Risk Model and Resilience Index (GIRI); Coalition for Disaster Resilient Infrastructure and partners | Coalition for Disaster Resilient Infrastructure (2023). *Global Infrastructure Resilience: Capturing the resilience dividend—A Biennial Report from the Coalition for Disaster Resilient Infrastructure*. New Delhi. | CC BY 3.0 IGO; registration and acceptance of the source terms are required for download | [GIRI data download](https://giri.unepgrid.ch/form/subscribe-for-download-data) |
| Residential built-up volume, 2020 | European Commission, Joint Research Centre | Pesaresi, M. and Politis, P. (2023). *GHS-BUILT-V R2023A—GHS built-up volume grids derived from joint assessment of Sentinel-2, Landsat and global DEM data, multitemporal (1975–2030)* [Dataset]. European Commission, Joint Research Centre. [https://doi.org/10.2905/AB2F107A-03CD-47A3-85E5-139D8EC63283](https://doi.org/10.2905/AB2F107A-03CD-47A3-85E5-139D8EC63283) | European Commission reuse notice; attribution required | [JRC Data Catalogue](https://data.jrc.ec.europa.eu/dataset/ab2f107a-03cd-47a3-85e5-139d8ec63283) |
| Global flood depth-damage curves | European Commission, Joint Research Centre | Huizinga, J., de Moel, H. and Szewczyk, W. (2017). *Global flood depth-damage functions: Methodology and the database with guidelines*. EUR 28552 EN. Publications Office of the European Union. [https://doi.org/10.2760/16510](https://doi.org/10.2760/16510) | European Commission reuse notice; attribution required | [JRC Publications Repository](https://publications.jrc.ec.europa.eu/repository/handle/JRC105688) |
| Age- and sex-structured population | WorldPop, University of Southampton | Bondarenko, M. et al. (2025). *Estimates of 2015–2030 total number of people per grid square broken down by gender and age groupings at a resolution of 3 arc (approximately 100 m at the equator), R2025A version v1*. WorldPop. [https://doi.org/10.5258/SOTON/WP00841](https://doi.org/10.5258/SOTON/WP00841) | CC BY 4.0 | [WorldPop catalogue](https://hub.worldpop.org/project/categories?id=8) |
| Relative Wealth Index | Meta Data for Good | Chi, G., Fang, H., Chatterjee, S. and Blumenstock, J. E. (2022). *Microestimates of wealth for all low- and middle-income countries*. Proceedings of the National Academy of Sciences, 119(3), e2113658119. [https://doi.org/10.1073/pnas.2113658119](https://doi.org/10.1073/pnas.2113658119) | CC BY-NC 4.0 | [Humanitarian Data Exchange](https://data.humdata.org/dataset/relative-wealth-index) |
| Global Surface Water occurrence | European Commission, Joint Research Centre and Google | Pekel, J.-F., Cottam, A., Gorelick, N. and Belward, A. S. (2016). *High-resolution mapping of global surface water and its long-term changes*. Nature, 540, 418–422. [https://doi.org/10.1038/nature20584](https://doi.org/10.1038/nature20584) | Copernicus data; attribution required | [Global Surface Water](https://global-surface-water.appspot.com/download) |
| Administrative boundaries | geoBoundaries, William & Mary geoLab and community contributors | Runfola, D. et al. (2020). *geoBoundaries: A global database of political administrative boundaries*. PLoS ONE 15(4): e0231866. [https://doi.org/10.1371/journal.pone.0231866](https://doi.org/10.1371/journal.pone.0231866) | CC BY 4.0; attribution required | [geoBoundaries](https://www.geoboundaries.org/globalDownloads.html) |
