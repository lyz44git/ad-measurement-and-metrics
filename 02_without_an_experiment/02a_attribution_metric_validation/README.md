# 02a · Validating an attribution metric against a randomized experiment

**[Explore this study interactively →](https://lyz44git.github.io/ad-measurement-and-metrics/02.html#s02a)**

> **Takeaway.** On the same experiment, exposure-based attribution credited 23,031 conversions in the ad arm, while
> the randomized comparison estimates 13,687 additional conversions (95% CI 12,887 to 14,488): the exposure count is
> 68% higher. Attribution counts should not drive budget decisions without an experimental calibration. The counts
> are reproduced from the raw file in SQL in [study 01c](../../01_with_an_experiment/01c_sql_metric_readout).

## Question

An exposure-based attribution metric credits the ad with every exposed record that has a visit or a conversion. How far is
that from what the ad actually caused, and can covariate adjustment close the gap when no experiment is available?

## Data

The Criteo experiment used in [study 01a](../../01_with_an_experiment/01a_ad_incrementality): 13,979,592 users,
2,096,937 in the control arm and 11,882,655 in the ad arm, of whom 428,212 were exposed. Pass the path to
`criteo-research-uplift-v2.1.csv.gz` as the first argument, or place the file as described in study 01a.

## Method

A descriptive comparison with no decision rule.

1. **Attributed outcomes.** Visits and conversions by exposed users in the ad arm.
2. **Estimated additional outcomes.** The intent-to-treat effect multiplied by the number of users in the ad arm.
3. **Per-exposed-user effect on visits, three ways:** the raw exposed-minus-unexposed difference; OLS with the 12
   features as covariates (HC1 standard errors); and two-fold cross-fitted double machine learning with
   gradient-boosted nuisance models on a random 2,000,000 users of the ad arm.
4. **Benchmark.** The effect on exposed users from study 01a: the assignment effect divided by the 3.6% exposure
   rate, unadjusted and regression-adjusted. These are two specifications, not an interval. The benchmark assumes
   assignment affects visits only through exposure.

## Results

Sources: [`out/attribution_vs_experiment.json`](out/attribution_vs_experiment.json); intervals and the sensitivity
check in [`out/benchmark_sensitivity.json`](out/benchmark_sensitivity.json).

| | Exposure-attributed | Estimated additional (95% CI) | Count above estimate |
|---|---|---|---|
| Visits | 177,510 | 122,895 (119,487 to 126,303) | 44% |
| Conversions | 23,031 | 13,687 (12,887 to 14,488) | 68% |

With the regression-adjusted assignment effect of study 01a instead, the estimates are 91,898 visits and 11,902 conversions, and both exposure counts are
93% above them. The intervals apply to the estimates, not to the percentages.

[![Additional conversions and visits estimated from the experiment, with 95% ranges, against the larger numbers credited by an exposure count; and estimates of the effect of seeing an ad from a raw comparison and two adjusted methods, set against the two estimates from the experiment](out/fig_attributed_vs_incremental.png)](https://lyz44git.github.io/ad-measurement-and-metrics/02.html#s02a)

| Per-exposed-user effect on visits | pp |
|---|---|
| Exposed minus unexposed, ad arm (raw) | 38.0 |
| OLS with covariates | 25.5 |
| Double machine learning | 24.6 |
| Experimental benchmark, two specifications (unadjusted / regression-adjusted) | 28.7 / 21.5 |

- The raw difference is 9 to 17 points above the two experimental estimates; both covariate-adjusted estimates fall
  between them. This comparison cannot say how much of the bias was removed.

## Reproduce

```bash
python code/attribution_vs_experiment.py /path/to/criteo-research-uplift-v2.1.csv.gz   # about 1 minute
python code/benchmark_sensitivity.py   # intervals and sensitivity, from committed outputs only
```

`code/attribution_vs_experiment.py` exposes the estimators as functions; `tests/test_attribution.py` checks them on
simulated data with a known effect and confounded exposure.

The adjusted benchmark is read from study 01a's committed `out/criteo/a_incrementality.json`; rerun 01a only to
regenerate it. The double machine learning estimate can differ in the third decimal between runs because the gradient-boosting fits are multi-threaded
(24.60 and 24.63 pp in two runs).

## Scope

- Single-channel, user-level attribution: the data have one exposure flag per user and no touch paths, so this is not
  multi-touch or cross-channel attribution.
