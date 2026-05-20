# National Tool Metrics

This repository provides a simple workflow for converting OPSIS risk model outputs and context datasets into standardized sub-national metrics for an interactive national tool.

The aim is to keep the process lightweight and repeatable:

1. Store country boundary layers in a consistent structure.
2. Store raw input data by country, analysis module, and hazard where relevant.
3. Use one notebook per analysis module to summarize inputs to administrative regions.
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
        context/
        socioeconomic/
          flooding/
        infrastructure/
          flooding/
        service_disruption/
          flooding/

  notebooks/

  src/

  results/
    KEN/
      context/
      socioeconomic/
        flooding/
      infrastructure/
        flooding/
      service_disruption/
        flooding/

  docs/
```

## Analysis Modules

The current planned modules are:

- `context`: non-risk data such as population, demographics, wealth, infrastructure, and nature-based solutions.
- `socioeconomic`: socioeconomic risk metrics derived from model outputs.
- `infrastructure`: infrastructure exposure, damage, or loss metrics derived from model outputs.
- `service_disruption`: service disruption metrics derived from model outputs.

Risk modules are organized by hazard. For example:

```text
data/raw/KEN/socioeconomic/flooding/
```

Future hazards can be added using the same pattern:

```text
data/raw/KEN/socioeconomic/tropical_cyclone/
data/raw/KEN/infrastructure/tropical_cyclone/
data/raw/KEN/service_disruption/tropical_cyclone/
```

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

Each analysis module should have one notebook in `notebooks/`.

The notebooks should follow the same broad pattern:

1. Set the country, administrative level, module, and hazard if relevant.
2. Load the relevant boundary layer.
3. Load the raw input data.
4. Clean and standardize input columns.
5. Summarize or aggregate the data to the chosen administrative level.
6. Create metric columns.
7. Export a standardized CSV to `results/`.

Example notebook names:

```text
notebooks/01_context_metrics.ipynb
notebooks/02_socioeconomic_risk_metrics.ipynb
notebooks/03_infrastructure_risk_metrics.ipynb
notebooks/04_service_disruption_risk_metrics.ipynb
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
module
hazard
```

These should be followed by the metric columns created by the notebook.

Example output path:

```text
results/KEN/socioeconomic/flooding/KEN_adm2_socioeconomic_flooding_metrics.csv
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
