# Concentration-Curve File Contract

The concentration-curve workflow combines precomputed curves used across the
national tool. Unlike the section metric outputs, these curves are country-level
and do not contain one row per administrative region.

Run `notebooks/concentration_curves.ipynb` to validate, review, plot, and export
all curves registered for a country.

## Input location

Store local input CSVs under:

```text
data/raw/<ISO3>/concentration_curves/
```

Raw files are ignored by Git. Their filenames do not determine their output
meaning; every curve must be explicitly registered in the country's TOML file.
This allows upstream workflows and contributors to retain useful source
filenames without creating a fragile filename parser.

Each input must contain at least two configured numeric columns:

- an X column containing cumulative population share; and
- a Y column containing the cumulative share of the outcome represented by the
  curve.

The Kenya source currently uses `frac_pop` and `frac_flood`. These names are
normalized in the combined output.

## How a source curve is constructed

The upstream calculation should:

1. order observations by the registered ranking variable and direction;
2. calculate cumulative population and divide it by total population;
3. calculate the cumulative outcome and divide it by the total outcome;
4. include explicit `(0, 0)` and `(1, 1)` endpoints; and
5. produce the shared population-share grid used by the other registered
   curves.

For a lowest-to-highest relative-wealth ranking, the X axis therefore moves
from the least wealthy population towards the wealthiest population. A curve's
Y axis is the cumulative share of its registered outcome, not a raw count or
currency value. Any grouping, tie handling, or interpolation needed to create
the shared grid belongs to the documented upstream calculation. This notebook
does not silently reconstruct or resample an already supplied curve.

## Registry

Register each curve in `config/countries/<ISO3>.toml`:

```toml
[concentration_curves.flood_risk__jrc__baseline_protected]
path = "data/raw/KEN/concentration_curves/KEN_jrc_protected_V-JRC_concentration_curve.csv"
x_column = "frac_pop"
y_column = "frac_flood"
ranked_by = "relative_wealth"
rank_direction = "lowest_to_highest"
description = "Cumulative share of baseline protection-adjusted JRC river-flood risk by cumulative population share."
```

The registry key becomes the output column name. It has three components:

```text
<indicator>__<model-or-source>__<scenario>
```

Components use lowercase letters, numbers, and single underscores. Double
underscores separate components. Do not include the tool section: the same
curve may be used in more than one part of the tool.

Examples include:

```text
flood_risk__jrc__baseline_protected
flood_risk__jrc__nature_based_solution
hospital_travel_time__accessibility_model__baseline_walking
```

`ranked_by` and `rank_direction` are required because the ordering determines
the interpretation of a concentration curve. `description` should define the
outcome, hazard where applicable, population basis, and scenario in plain
language.

## Validation

The workflow requires every registered curve to:

1. contain its registered X and Y columns;
2. contain only finite numeric values;
3. keep both axes within the inclusive range 0 to 1;
4. use unique, strictly increasing X values;
5. use non-decreasing Y values;
6. start at `(0, 0)` and end at `(1, 1)`; and
7. use exactly the same X grid as every other registered curve.

The current Kenya input has 101 rows from 0.00 to 1.00 in increments of 0.01.
Future inputs should use this grid unless the whole registered set is changed
deliberately. The workflow does not silently interpolate or resample curves.

## Combined output

The notebook writes:

```text
results/<ISO3>/concentration_curves/<ISO3>_concentration_curves.csv
```

The first column is the shared X axis. Each remaining column is one registered
curve:

```csv
cumulative_population_share,flood_risk__jrc__baseline_protected
0.00,0.0000
0.01,0.0120
...
1.00,1.0000
```

Column order follows registry order. Generated results are ignored by Git.

## Adding a curve

1. Place its input CSV in the country concentration-curve directory.
2. Add a uniquely named registry table to the country TOML file.
3. Record the X/Y source columns and ranking metadata explicitly.
4. Add or update provenance in `docs/data_sources.md`.
5. Run the notebook and review both the registry table and plot.
6. Export only after all validation checks pass.
