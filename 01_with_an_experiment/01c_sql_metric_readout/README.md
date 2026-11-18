# 01c · The experiment readout in SQL: metric definitions, data checks and reconciliation

**[Explore this study interactively →](https://lyz44git.github.io/ad-measurement-and-metrics/01.html#s01c)**

> **Takeaway.** 29 published readout quantities of studies 01a and 02a were recomputed with short SQL queries, each
> with a stated numerator and denominator, and all 29 agree with the Python results. The data checks pass. Two facts
> that the readout depends on are recorded: the file has no user identifier, so a "user" is a row, and 16% of rows
> are identical to another row in every column. A conversion endpoint needs about 20 times as many users as a visit
> endpoint for the same relative lift (849,000 against 41,000 per arm for a 10% lift).

## Question

Can the readout of studies [01a](../01a_ad_incrementality) and
[02a](../../02_without_an_experiment/02a_attribution_metric_validation) be produced from the raw file by SQL that a
reviewer can audit line by line, with every metric defined before it is computed, and does it agree with the Python
results?

## Data

The Criteo experiment used in [study 01a](../01a_ad_incrementality): 13,979,592 rows with 12 anonymized features and
four 0/1 flags: `treatment` (assigned to the ad arm), `exposure` (saw an ad), `visit` and `conversion`. The file has
no user identifier; each row is treated as one user record. Pass the path to `criteo-research-uplift-v2.1.csv.gz` as
the first argument.

## Method

The analysis plan, [`design/analysis_plan.md`](design/analysis_plan.md), was hashed before any query was run on the data
(SHA-256 in `logs/plan_hash.txt`). The Python results of studies 01a and 02a were already known; the SQL
results, the checks and the sample-size table were not.

1. **Metric definitions.** The denominator of every rate is all users assigned to the arm, whether or not they saw an
   ad.

   | Metric | Numerator | Denominator |
   |---|---|---|
   | Visit rate, by arm | users with a visit | all users assigned to the arm |
   | Conversion rate, by arm | users with a conversion | all users assigned to the arm |
   | Exposure rate, ad arm | users who saw an ad | all users assigned to the ad arm |
   | Effect of assignment (primary readout) | ad-arm rate minus control rate | (difference in arm rates) |
   | Estimated additional outcomes in the ad arm | effect of assignment × users in the ad arm | (estimated count) |
   | Outcomes credited by attribution (diagnostic) | outcomes of exposed users in the ad arm | (count) |
   | Over-crediting (diagnostic) | outcomes credited | estimated additional outcomes |
   | Effect per exposed user (diagnostic) | effect of assignment | exposure rate of the ad arm |

   The effect per exposed user assumes that assignment changes the outcome only through exposure.
2. **Data checks** ([`sql/checks.sql`](sql/checks.sql), [`sql/duplicates.sql`](sql/duplicates.sql)). Four checks have
   an expected value and stop the run if it is not met; three are reported because the dataset's documentation does
   not say what they should be.
3. **Readout** ([`sql/readout_by_arm.sql`](sql/readout_by_arm.sql),
   [`sql/readout_effects.sql`](sql/readout_effects.sql)), run with DuckDB on the full file.
4. **Reconciliation.** 29 quantities are compared with the result files of studies 01a and 02a. Rule: counts must be
   equal, rates and effects within 1e-9, standard errors within one part in a million.
5. **Sample size by endpoint.** Users per arm for a two-sided 5% test with 80% power and equal arms, from the control
   rates of the readout. This is a calculation, not a test.

## Results

Source: [`out/readout.json`](out/readout.json); tables in `out/*.csv`. The run takes about 4 seconds.

**Data checks.**

| Check | Expected | Found |
|---|---|---|
| C1. Rows | 13,979,592 | 13,979,592 |
| C2. Rows with a missing value | 0 | 0 |
| C3. Rows with a flag other than 0 or 1 | 0 | 0 |
| C4. Exposed users in the control arm | 0 | 0 |
| C5. Users with a conversion and no visit | not stated | 0 |
| C6. Exposed users with no visit | not stated | 250,702 (59% of exposed users) |
| C7. Rows with at least one identical counterpart in all 16 columns | not stated | 2,221,150 (16% of rows) |

**Readout by arm.**

| | Control | Ad arm |
|---|---|---|
| Users | 2,096,937 | 11,882,655 |
| Exposed users (exposure rate) | 0 | 428,212 (3.60%) |
| Visits (visit rate) | 80,105 (3.820%) | 576,824 (4.854%) |
| Conversions (conversion rate) | 4,063 (0.194%) | 36,711 (0.309%) |

**Effect of assignment and attribution diagnostics.**

| | Visits | Conversions |
|---|---|---|
| Effect of assignment (standard error) | +1.034 pp (0.015) | +0.115 pp (0.003) |
| Estimated additional outcomes in the ad arm | 122,895 | 13,687 |
| Outcomes credited by attribution | 177,510 | 23,031 |
| Credited over estimated (ratio) | 1.44 | 1.68 |
| Effect per exposed user | 28.7 pp | 3.20 pp |

**Users per arm for 80% power, by relative lift.**

| Relative lift | Visit rate (control 3.82%) | Conversion rate (control 0.19%) | Ratio |
|---|---|---|---|
| 5% | 161,879 | 3,315,096 | 20.5 |
| 10% | 41,413 | 848,944 | 20.5 |
| 25% | 7,075 | 145,509 | 20.6 |
| 50% | 1,953 | 40,406 | 20.7 |

- **The pre-specified reconciliation rule was met:** all 29 comparisons agree
  ([`out/reconciliation.csv`](out/reconciliation.csv)). Counts are identical; the largest difference in a rate or
  effect is below 1e-12, and standard errors differ by two parts in ten million (the Python code uses the sample
  variance).
- **A conversion implies a visit in this file** (C5), so conversion is a subset of visit and the two endpoints are not
  independent readouts.
- **16% of rows have an exact twin** (C7). Without a user identifier they cannot be told apart from distinct users
  with the same recorded values, so no row is dropped and every count above is a count of rows. If they were
  duplicates of the same user, the standard errors above would be too small.
- **A conversion test is about 20 times larger than a visit test** for the same relative lift, because the base rate
  is about 20 times lower. For a 1-percentage-point absolute lift in the visit rate, the formula gives 6,485 users per arm,
  against about 6,500 by simulation in [study 03a](../../03_planning_a_test/03a_lift_study_sizing).

## Reproduce

```bash
python code/run_readout.py /path/to/criteo-research-uplift-v2.1.csv.gz out   # about 4 seconds; needs 01a and 02a outputs
```

[`tests/`](tests) builds a small simulated experiment and checks that the SQL readout equals an independent pandas
computation, that the data checks pass on clean data and catch planted errors, that the reconciliation flags a
changed number, and the sample-size formula.

## Scope

- Unadjusted estimates only. Regression-adjusted estimates are in studies 01a and 03a.
- The reconciliation shows that two implementations agree, not that either definition is the right one for a given
  product decision.
- The released file pools several tests with non-uniform subsampling, so rates are not population rates.
- The sample-size table assumes equal arms and no covariate adjustment; study 03a shows what adjustment saves for the
  visit endpoint.
