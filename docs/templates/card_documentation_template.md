# [Card title]

## Summary

[Briefly explain what the card shows, the principal measures and units, and
how users should interpret the values. Include any essential warning needed to
avoid misinterpreting the metric. Aim for one short paragraph.]

## How it is calculated

[Begin with one or two sentences describing the overall approach—for example,
the level at which the calculation is performed, the main types of input data,
and how the results are aggregated.]

1. [Describe the main input data and any important grouping or classification.]
2. [Describe how the principal metric is calculated.]
3. [Describe any secondary or annualised metric, if applicable.]
4. [State the main exclusions or treatment of missing data, if important.]
5. [Explain how results are aggregated and note any derived groups or values.]

## Understanding the CSV download

| Item | Description |
|---|---|
| Filename | `<ISO3>_<admin-level>_<section>_<card>_metrics.csv` |
| One row represents | [Exact meaning of one row] |
| Rows per area | [Number of rows or rule] |
| Value column | `value` |
| Boundary join | `country_iso3` + `admin_level` + `adm_id` |
| Geometry | Not included |

| Field | Meaning | Values |
|---|---|---|
| `country_iso3` | Three-letter ISO country code | [For example, `KEN`, `MOZ`] |
| `country_name` | Country name | [Country names] |
| `admin_level` | Administrative level used for the calculation | `ADM0`, `ADM1`, `ADM2` |
| `adm_id` | geoBoundaries `shapeID`; used to link the CSV row to the matching boundary geometry | Identifier from the selected geoBoundaries layer |
| `adm_name` | geoBoundaries `shapeName` for the administrative area | Area name from the selected boundary layer |
| `section` | Section of the tool | `[section]` |
| `card` | Card represented by the file | `[card]` |
| `[dimension]` | [Meaning of the card-specific field] | [Allowed values] |
| `unit` | Unit for the selected metric | [Allowed units] |
| `value` | Numeric result described by the other fields | [Rounding and treatment of zero or missing values] |

For example, to reproduce [a representative view from the card], filter to:

```text
[field] = [value]
[field] = [value]
```

[Explain the result of the filter and the most likely interpretation mistake,
such as overlapping groups or rows that must not be summed.]

## Sources

| Dataset | Provider | Citation | Licence | Link |
|---|---|---|---|---|
| [Dataset name] | [Provider] | [Full citation] | [Licence] | [Dataset page] |

