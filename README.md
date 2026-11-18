# National Tool Metrics

The notebooks produce the national tool's downloadable metric CSVs. The repo
includes country settings for Kenya (`KEN`) and Mozambique (`MOZ`).

## Run a notebook

From the repository root, create the Conda environment and start Jupyter.

```sh
conda env create -f environment.yml
conda activate tooling
jupyter notebook
```

1. Stage the raw inputs for the notebook you want to run using the paths below.
2. Set `COUNTRY` in the notebook's first code cell. Set the reporting level
   (`adm0`, `adm1`, or `adm2`) in `config/countries/<ISO3>.toml`.
3. Choose **Run All** in Jupyter. The build cell previews each card and the
   export cell prints the CSV paths.

Each notebook runs independently with its own inputs.

## Raw inputs by notebook

All six section notebooks use the administrative boundaries for the selected
country and level. By default, place the shapefile and its companion files at
`data/boundaries/<ISO3>/<admin-level>/<ISO3>_<admin-level>.shp`. Precomputed
summaries must match that level. Concentration Curves uses country-level CSVs.

| Notebook | Raw inputs and default locations |
|---|---|
| [01 Hazard](notebooks/01_hazard_metrics.ipynb) | Country JRC flood-depth GeoTIFFs in `data/raw/<ISO3>/hazard/river_flooding/` and global STORM wind-speed GeoTIFFs in `data/raw/global/tropical_cyclone/`. |
| [02 Exposure](notebooks/02_exposure_metrics.ipynb) | Eight WorldPop demographic rasters and three capital-stock rasters under `data/raw/<ISO3>/exposure/`. Roads, rail, and power use the same network GeoPackages as Risk. Hospital and school counts use summary CSVs in `data/raw/<ISO3>/exposure/facilities/` when available. |
| [03 Vulnerability](notebooks/03_vulnerability_metrics.ipynb) | Two precomputed GeoPackages under `data/raw/<ISO3>/vulnerability/`. One contains mean and population-weighted Relative Wealth Index. The other contains population totals by wealth quintile. |
| [04 Risk](notebooks/04_risk_metrics.ipynb) | JRC summaries of flooded population and capital-stock loss for protected average annual risk and return-period events in `data/raw/<ISO3>/risk/socioeconomic/river_flood/`. Direct damage uses JRC road and rail GeoPackages and a STORM power GeoPackage under `data/raw/<ISO3>/risk/infrastructure_networks/direct/`. |
| [05 Adaptation Potential](notebooks/05_adaptation_potential_metrics.ipynb) | FLOPROS protection raster, river network GeoPackage, and GHS-SMOD urbanisation raster in `data/raw/<ISO3>/adaptation_potential/`. Global rasters in `data/raw/global/nature_based_solutions/` supply opportunity areas, planting and regeneration costs, carbon, and biodiversity. |
| [06 Adaptation Outcomes](notebooks/06_adaptation_outcomes_metrics.ipynb) | Precomputed GeoPackages in `data/raw/<ISO3>/adaptation_outcomes/` covering adaptation costs, baseline and adapted capital-stock losses, and flood-exposure summaries. Include the required dry-proofing, relocation, and flood-protection scenarios. |
| [Concentration Curves](notebooks/concentration_curves.ipynb) | Precomputed curve CSVs in `data/raw/<ISO3>/concentration_curves/` containing cumulative population and outcome shares for baseline and registered adaptation scenarios. |

See [Data layout](docs/data_layout.md) for exact filenames, fields, and scenario
requirements. See [Data sources](docs/data_sources.md) for dataset provenance.

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

Each country inherits [config/defaults.toml](config/defaults.toml). If a path,
boundary field, processing parameter, or risk-run setting differs, add that
key to the country file under `[sources]`, `[boundaries]`,
`[parameters]`, or the relevant `[risk_runs...]` table. Relative paths start at
the repository root. For custom curve inputs, override the registry in the
country file. [Concentration curve registry](docs/concentration_curves.md)

Set `COUNTRY = "TZA"` in the notebook and run it.

### Run only available cards

Add a `[cards]` table to the country TOML when a section has data for only
some cards. This example selects one card in each of three sections.

```toml
[cards]
hazard = ["river_flooding"]
vulnerability = ["relative_wealth_index"]
adaptation_potential = ["existing_flood_protection"]
```

Omit a section from `[cards]` to build all its cards. Use an empty list, such
as `adaptation_outcomes = []`, to skip an entire section.

| Section key | Valid card names |
|---|---|
| `hazard` | `river_flooding`, `tropical_cyclone_wind` |
| `exposure` | `population`, `capital_stock`, `roads`, `rail`, `power`, `healthcare_facilities`, `educational_facilities` |
| `vulnerability` | `relative_wealth_index`, `wealth_distribution` |
| `risk` | `population`, `capital_stock`, `direct_damage` |
| `adaptation_potential` | `slope_vegetation`, `mangroves`, `river_catchment_restoration`, `existing_flood_protection`, `river_network_context` |
| `adaptation_outcomes` | `dry_proofing`, `relocation`, `flood_protection` |

Each selected card needs its required inputs and its full set of return
periods or scenarios. Concentration Curves uses its own registry.

The notebook lists the selected and skipped cards before calculating metrics.
It reports any CSVs from earlier runs for skipped cards. Those files remain
on disk, so use the paths printed by the export cell to identify this run's
results.

Raw datasets, boundary files, and generated CSVs are kept out of Git.

## Outputs

The six section notebooks write one tidy CSV per card under
`results/<ISO3>/<section>/` using
`<ISO3>_<admin-level>_<section>_<card>_metrics.csv`. The concentration-curve
notebook writes `results/<ISO3>/concentration_curves/<ISO3>_concentration_curves.csv`.
See the [card CSV contracts](docs/card_csv_contracts.md) for metric definitions,
units, and output schemas. See the [card documentation](docs/cards/README.md)
for plain-language summaries and calculation methods.
