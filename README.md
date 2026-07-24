# National Tool Metrics

This repository provides a simple workflow for converting OPSIS risk model outputs and context datasets into standardized sub-national metrics for an interactive national tool.

The repository is being migrated to the tool's six-section structure:
Hazard, Exposure, Vulnerability, Risk, Adaptation Options, and Adaptation
Analysis. See [`docs/data_layout.md`](docs/data_layout.md) for the target
folder structure, compatibility behaviour, and staged move sequence. Legacy
input folders remain temporarily so existing notebooks continue to work.

The aim is to keep the process lightweight and repeatable:

1. Store country boundary layers in a consistent structure.
2. Store raw input data by country and tool section.
3. Use one notebook per tool section to summarize inputs to administrative regions.
4. Export clean CSV files with one row per sub-national region and one column per metric.

Country folders should use ISO3 codes. The first test country is `KEN`. The first hazard for the risk modules is flooding, but the folder structure is designed to allow additional hazards later.

## Repository Structure

```text
national_tool_metrics/
  data/
    boundaries/
      KEN/
        adm0/
        adm1/
        adm2/

    raw/
      KEN/
        exposure/
        vulnerability/
        risk/
      global/
        adaptation_options/

  notebooks/

  src/

  results/
    KEN/
      hazard/
      exposure/
      vulnerability/
      risk/
      adaptation_options/
      adaptation_analysis/

  docs/
```

## Tool Sections

The tool sections are:

- `hazard`: physical hazard characteristics; scope to be agreed.
- `exposure`: population, demographics, capital stock, networks, and facilities.
- `vulnerability`: relative wealth, wealth distribution, and baseline accessibility.
- `risk`: socioeconomic, infrastructure-network, and social-infrastructure risk.
- `adaptation_options`: available interventions and opportunity locations.
- `adaptation_analysis`: outcomes and comparisons; scope to be agreed.

## Boundary Data

Country boundary layers should be stored under:

```text
data/boundaries/<ISO3>/
```

For `KEN`, the current folders are:

```text
data/boundaries/KEN/adm0/
data/boundaries/KEN/adm1/
data/boundaries/KEN/adm2/
```

Each boundary layer should include a stable administrative identifier that can be carried into the final metric CSVs.

## Notebook Workflow

Each implemented tool section should have one notebook in `notebooks/`.

The notebooks should follow the same broad pattern:

1. Load the country configuration and administrative level.
2. Load the relevant boundary layer.
3. Load the raw input data.
4. Clean and standardize input columns.
5. Summarize or aggregate the data to the chosen administrative level.
6. Create metric columns.
7. Export a standardized CSV to `results/`.

Target notebook names:

```text
notebooks/01_hazard_metrics.ipynb
notebooks/02_exposure_metrics.ipynb
notebooks/03_vulnerability_metrics.ipynb
notebooks/04_risk_metrics.ipynb
notebooks/05_adaptation_options_metrics.ipynb
notebooks/06_adaptation_analysis_metrics.ipynb
```

## Output Format

Each notebook should produce one CSV with one row per sub-national region.

Suggested standard identifier columns:

```text
country_iso3
country_name
admin_level
adm_id
adm_name
section
hazard
scenario
model_run
```

These should be followed by the metric columns created by the notebook.

Example output path:

```text
results/KEN/risk/KEN_adm2_risk_metrics.csv
```

For the `context` module, use `hazard = none` or omit the hazard column if the downstream tool does not need it.

## Metric Dictionary

Metric definitions should be documented in:

```text
docs/metric_dictionary.csv
```

Suggested columns:

```text
module,hazard,metric_name,description,unit,aggregation_method,source_notes
```

This file should make it clear what each output column means and how it was calculated.
