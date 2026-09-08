# National Tool Metrics

This repository converts hazard, exposure, vulnerability, risk, and adaptation
datasets into standardized subnational metrics for an interactive national
tool. Kenya (`KEN`) is the implemented reference country.

Each implemented tool section has one notebook. Download outputs are migrating
from one wide CSV per section to one tidy CSV per sidebar card. Hazard,
Exposure, Relative Wealth Index, Wealth Distribution, Risk, Adaptation
Potential, and all three Adaptation Outcomes cards use
the card contract; the other outputs retain their existing contracts until
their card schemas are agreed.

## Implementation status

| Tool section | Current scope | Status |
|---|---|---|
| Hazard | JRC river-flood depth/extent and STORM tropical-cyclone wind-category area | Implemented |
| Exposure | Population, capital stock, roads, rail, power, hospitals, and schools | Implemented |
| Vulnerability | Relative Wealth Index, wealth distribution, and baseline accessibility | Implemented |
| Risk | Socioeconomic river-flood risk and direct infrastructure-network risk | Implemented |
| Adaptation Potential | FLOPROS, nature-based solutions, and river-network context | Implemented |
| Adaptation Outcomes | Dry proofing, relocation, and flood-protection costs and benefits | Implemented |

Indirect tropical-cyclone network risk and social-infrastructure risk are not
yet produced by this repository. The social-infrastructure risk component will
be supplied by a separate workflow.

## Repository structure

```text
national_tool_metrics/
  config/
    countries/
      KEN.toml
  data/
    boundaries/<ISO3>/<admin-level>/
    raw/
      <ISO3>/
        hazard/
        exposure/
        vulnerability/
        risk/
        adaptation_potential/
        adaptation_outcomes/
        concentration_curves/
      global/
        nature_based_solutions/
        tropical_cyclone/
  docs/
    concentration_curves.md
    data_layout.md
    data_sources.md
    metric_dictionary.csv
  notebooks/
    01_hazard_metrics.ipynb
    02_exposure_metrics.ipynb
    03_vulnerability_metrics.ipynb
    04_risk_metrics.ipynb
    05_adaptation_potential_metrics.ipynb
    06_adaptation_outcomes_metrics.ipynb
    concentration_curves.ipynb
  results/<ISO3>/
    <section>/
    concentration_curves/
  src/national_tool_metrics/
  tests/
```

See [the data-layout specification](docs/data_layout.md) for required paths and
filenames. Dataset provenance and metadata are recorded in
[the data-source manifest](docs/data_sources.md).

## Environment setup

Create and activate the Conda environment from the repository root:

```powershell
conda env create -f environment.yml
conda activate tooling
```

If the environment already exists, update it after dependency changes:

```powershell
conda env update -f environment.yml --prune
```

## Country configuration

Country settings and input paths are defined in
[`config/countries/KEN.toml`](config/countries/KEN.toml). The default output
level is controlled by one value:

```toml
[country]
admin_level = "adm1"
```

Change this to `adm0` or `adm2` to use another administrative level. The
matching boundary layer and all admin-level-specific input summaries must exist
before running a notebook. Kenya currently has both ADM1 and ADM2 boundaries,
but not every workflow input is available at both levels.

## Running the workflows

Start Jupyter from the repository root:

```powershell
jupyter notebook
```

Run the notebook for the section you want to rebuild:

1. `notebooks/01_hazard_metrics.ipynb`
2. `notebooks/02_exposure_metrics.ipynb`
3. `notebooks/03_vulnerability_metrics.ipynb`
4. `notebooks/04_risk_metrics.ipynb`
5. `notebooks/05_adaptation_potential_metrics.ipynb`
6. `notebooks/concentration_curves.ipynb`

The notebooks are section-specific and do not need to be run as one continuous
pipeline. Each notebook loads the country configuration, validates its inputs,
builds its metric tables, and writes the corresponding CSV files under
`results/`.

The unnumbered concentration-curve notebook is shared across multiple tool
sections. It validates the curves registered in the country configuration and
writes one country-level wide CSV. See
[`docs/concentration_curves.md`](docs/concentration_curves.md) for its distinct
file contract and naming convention.

## Output contract

Hazard, Exposure, the two approved Vulnerability cards, the three supported
Risk cards, and the five Adaptation Potential cards write one downloadable CSV
per card. Hazard writes:

```text
results/<ISO3>/hazard/<ISO3>_<admin-level>_hazard_river_flooding_metrics.csv
results/<ISO3>/hazard/<ISO3>_<admin-level>_hazard_tropical_cyclone_wind_metrics.csv
```

These files use tidy rows. Return period, hazard metric, wind threshold, and
display mode are explicit columns, and the plotted number is stored in
`value`. See [the card CSV contracts](docs/card_csv_contracts.md) for the exact
schemas and permitted parameter values.

Exposure writes Population, Capital Stock, Roads, Rail, Power, Healthcare
Facilities, and Educational Facilities card CSVs under
`results/<ISO3>/exposure/`. All card CSVs use the same standard identifier
prefix before their card-specific parameters and `value`.

Vulnerability writes:

```text
results/<ISO3>/vulnerability/<ISO3>_<admin-level>_vulnerability_relative_wealth_index_metrics.csv
results/<ISO3>/vulnerability/<ISO3>_<admin-level>_vulnerability_wealth_distribution_metrics.csv
```

Accessibility is supplied through a separate workflow and is not included in
these two files.

Risk writes Population, Capital Stock, and Direct Damage card CSVs under
`results/<ISO3>/risk/`. Every Risk CSV includes `risk_subsection`, `hazard`,
`model`, and `scenario`. Population and Capital Stock are limited to baseline
JRC river flooding; Direct Damage contains both river-flood and
tropical-cyclone rows. Indirect Impacts, Facilities, and Accessibility remain
deferred or separate workflows.

Adaptation Potential writes Slope Vegetation, Mangroves, River Catchment
Restoration, Existing Flood Protection, and River Network Context card CSVs
under `results/<ISO3>/adaptation_potential/`. Every file includes
`adaptation_subsection`; adjustable categories, metrics, and implementation
approaches are represented as columns.

Adaptation Outcomes writes Dry Proofing, Relocation, and Flood Protection cards
under `results/<ISO3>/adaptation_outcomes/`. They report adaptation cost metrics,
baseline, adapted, and avoided capital-stock losses and flood exposure, plus
baseline, adapted, and changed concentration-index values. Relocation includes
all seven degree-of-urbanisation thresholds as explicit CSV dimensions. Flood
Protection crosses those thresholds with five design return periods and three
adaptation-cost estimates.

Sections not yet migrated continue to use one wide section CSV with one row
per administrative region. Those CSVs start with:

```text
country_iso3
country_name
admin_level
adm_id
adm_name
section
```

Metric columns follow these identifiers. Where a metric varies by hazard,
model, scenario, epoch, or return period, those dimensions are included in the
column name. Examples include:

```text
river_flood_jrc_baseline_flooded_area_rp100_km2
tropical_cyclone_storm_baseline_2020_wind_area_cat3plus_rp100_pct_admin
tropical_cyclone_storm_baseline_2020_power_ead_total
```

Their standard output path is:

```text
results/<ISO3>/<section>/<ISO3>_<admin-level>_<section>_metrics.csv
```

Metric definitions, units, and aggregation methods are maintained in
[`docs/metric_dictionary.csv`](docs/metric_dictionary.csv). It remains the
calculation dictionary while sections migrate to card outputs.

## Data and Git

Raw data, boundary files, and generated results are intentionally ignored by
Git because they can be large or restricted. Git tracks the directory skeleton,
configuration, notebooks, reusable Python code, tests, and documentation.

Before running a workflow on a new checkout, populate the paths documented in
`docs/data_layout.md`. Do not commit local datasets or generated CSVs.

## Tests

From PowerShell in the repository root:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
```

The tests cover configuration parsing, output contracts, section assembly,
metric-dictionary coverage, and representative raster/vector calculations.
