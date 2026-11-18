# National Tool Metrics

The notebooks turn country datasets into downloadable CSVs for the national
tool. Kenya (`KEN`) and Mozambique (`MOZ`) are included as configuration
examples.

## Run a section

From the repository root, create the Conda environment and start Jupyter.

```sh
conda env create -f environment.yml
conda activate tooling
jupyter notebook
```

Pick a notebook below, set `COUNTRY` in its first code cell, and choose
**Run All**. The country config sets the administrative level and inherits
standard settings from [config/defaults.toml](config/defaults.toml). Each
section runs independently from its own inputs. The build cell
previews each card, and the export cell prints the CSV paths.

| Notebook | Metrics |
|---|---|
| [01 Hazard](notebooks/01_hazard_metrics.ipynb) | JRC river-flood extent and depth, and STORM tropical-cyclone wind-category area |
| [02 Exposure](notebooks/02_exposure_metrics.ipynb) | Population, capital stock, roads, rail, power, hospitals, and schools |
| [03 Vulnerability](notebooks/03_vulnerability_metrics.ipynb) | Relative Wealth Index and wealth distribution |
| [04 Risk](notebooks/04_risk_metrics.ipynb) | Socioeconomic river-flood risk and direct network damage |
| [05 Adaptation Potential](notebooks/05_adaptation_potential_metrics.ipynb) | Nature-based solutions, existing flood protection, and river network context |
| [06 Adaptation Outcomes](notebooks/06_adaptation_outcomes_metrics.ipynb) | Dry proofing, relocation, and flood-protection costs and benefits |
| [Concentration Curves](notebooks/concentration_curves.ipynb) | Validate, plot, and combine precomputed curves for the selected country |

## Add a country

Create `config/countries/<ISO3>.toml` with the country code, name, and
administrative level (`adm0`, `adm1`, or `adm2`). For Tanzania, save the
following as `config/countries/TZA.toml`.

```toml
[country]
iso3 = "TZA"
name = "Tanzania"
admin_level = "adm1"
```

Stage that country's boundaries and the inputs for the section you want to
run. The default boundary path is
`data/boundaries/<ISO3>/<admin-level>/<ISO3>_<admin-level>.shp`.
Precomputed summaries must match the selected administrative level.
[Input filenames and schemas](docs/data_layout.md) · [Dataset sources](docs/data_sources.md)

If a path, boundary field, processing parameter, or risk-run setting differs,
add that key to the country file under `[sources]`, `[boundaries]`,
`[parameters]`, or the relevant `[risk_runs...]` table. Relative paths start at
the repository root. For custom curve inputs, override the registry in the
country file. [Concentration curve registry](docs/concentration_curves.md)

Set `COUNTRY = "TZA"` in the notebook and run it.

Raw datasets, boundary files, and generated CSVs are kept out of Git. Your
colleague will need access to the inputs for the sections they want to run.

## Outputs

The six section notebooks write one tidy CSV per card under
`results/<ISO3>/<section>/` using
`<ISO3>_<admin-level>_<section>_<card>_metrics.csv`. The concentration-curve
notebook writes `results/<ISO3>/concentration_curves/<ISO3>_concentration_curves.csv`.
See the [card CSV contracts](docs/card_csv_contracts.md) for metric definitions,
units, and output schemas.

## Code and tests

Each workflow has one Python module under `src/national_tool_metrics/`.
`utils.py` contains shared configuration, boundary loading, geospatial
operations, and CSV export. The notebooks are the entry points for running
metrics.

Run the regression checks from the repository root in the `tooling`
environment. They use small fixtures and run without country datasets.

```sh
python -m unittest discover -s tests
```
