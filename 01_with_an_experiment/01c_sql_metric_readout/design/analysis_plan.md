# Analysis plan: the experiment readout in SQL

Written before any query in this study was run on the data. The Python results of studies 01a and 02a were already
known when this plan was written; the SQL results, the data checks and the sample-size table were not.

## Purpose

Studies 01a and 02a read the Criteo experiment with Python. This study states each metric by its numerator and
denominator, produces the same readout from the raw file with short SQL (DuckDB), checks the data before reading it,
and tests whether the SQL and Python results agree.

## Data

Criteo Uplift Prediction Dataset v2.1, one row per user: 12 features (`f0` to `f11`) and four 0/1 flags,
`treatment` (assigned to the ad arm), `exposure` (saw an ad), `visit` and `conversion`. Read from a local
`data_raw/` folder (read only).

## Metric definitions

| Metric | Numerator | Denominator |
|---|---|---|
| Visit rate, by arm | users with `visit = 1` | all users assigned to the arm |
| Conversion rate, by arm | users with `conversion = 1` | all users assigned to the arm |
| Exposure rate, ad arm | users with `exposure = 1` | all users assigned to the ad arm |
| Effect of assignment (primary readout) | ad-arm rate minus control rate | (difference of the two rates above) |
| Outcomes caused by the ads | effect of assignment times users in the ad arm | (a count) |
| Outcomes credited by attribution (diagnostic) | outcomes of exposed users in the ad arm | (a count) |
| Over-crediting (diagnostic) | credited outcomes | outcomes caused by the ads |
| Effect per exposed user (diagnostic) | effect of assignment | exposure rate of the ad arm |

The standard error of the effect of assignment is sqrt(p1 (1 - p1) / n1 + p0 (1 - p0) / n0). The effect per exposed
user assumes that assignment changes the outcome only through exposure.

## Data checks (`sql/checks.sql`)

Each check returns a count. Checks C1 to C4 have an expected value and fail the run if it is not met; C5 to C7 are
reported, because the dataset's documentation does not state what they should be.

- C1. Rows: 13,979,592.
- C2. NULL values in any column: 0.
- C3. Values other than 0 and 1 in `treatment`, `exposure`, `visit`, `conversion`: 0.
- C4. Exposed users in the control arm: 0.
- C5. Users with a conversion and no visit.
- C6. Exposed users with no visit.
- C7. Rows that are identical to another row in all 16 columns. The file has no user identifier, so identical rows
  cannot be told apart from distinct users with the same recorded values; the count is reported and no row is dropped.

## Readout (`sql/readout.sql`)

One query returns a row per arm (users, exposed users, visits, conversions, outcomes of exposed users, rates). A
second query returns, for visits and for conversions, every metric in the table above.

## Reconciliation rule

The SQL readout is compared with `out/criteo/a_incrementality.json` of study 01a and
`out/attribution_vs_experiment.json` of study 02a. The two agree if every count is equal, every rate, effect and
ratio differs by at most 1e-9 in absolute value (1e-6 for counts expressed as non-integers), and every standard error
differs by at most 1e-6 in relative terms. Any disagreement is reported as found; neither side is changed to match.

## Sample size by endpoint

Users per arm for a two-sided 5% test with 80% power and equal arms,
n = (1.959964 + 0.841621)^2 (p0 (1 - p0) + p1 (1 - p1)) / (p1 - p0)^2, with p0 the control rate from the SQL readout,
for relative lifts of 5%, 10%, 25% and 50% in the visit rate and in the conversion rate, and for a one-point
absolute lift in the visit rate (to compare with study 03a). This is a calculation, not a test; no decision rule
applies. Regression-adjusted estimates are outside this study (they are in studies 01a and 03a).
