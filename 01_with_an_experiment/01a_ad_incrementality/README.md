# 01a · Ad incrementality on a 14.0M-user randomized experiment

**[Explore this study interactively →](https://lyz44git.github.io/ad-measurement-and-metrics/01.html#s01a)**

> **Takeaway.** Assignment to the ad arm raised the visit rate by about one percentage point (3.82% to 4.85%) and the
> conversion rate from 0.19% to 0.31%, in Criteo's released sample of the experiment. The pre-specified uplift model
> did not beat a plain response model at ranking users for targeting, so on this evidence uplift modeling does not earn
> its extra complexity.

## Question

How many site visits and conversions did the ads cause, compared with what would have happened without them?
Which users does the ad move most, and does targeting them beat targeting the users most likely to visit?

## Data

Criteo Uplift Prediction Dataset v2.1 ([Diemert et al. 2018](https://ailab.criteo.com/criteo-uplift-prediction-dataset/)): 13,979,592 users, 85% assigned to
the ad arm, 12 anonymized features, and exposure, visit and conversion flags. The experiment was designed, run and
released by Criteo.

Download `criteo-research-uplift-v2.1.csv.gz` from the Criteo AI Lab dataset page into
`data_raw/criteo_uplift_v2.1/` (git-ignored). `python code/00_check_criteo.py <path>` prints the file's md5 and the
visit and conversion rates by arm.

## Method

The analysis plan, [`docs/10_plan_criteo_incrementality_uplift.md`](docs/10_plan_criteo_incrementality_uplift.md), was
fixed before the run; its SHA-256 is in `logs/10_plan_hash.txt`.

1. **Incrementality.** Intent-to-treat effects with Neyman standard errors, and a regression-adjusted estimate (AIPW
   with linear outcome models).
2. **Randomization check.** Standardized mean differences of the features, and the held-out AUC of a model predicting
   assignment.
3. **Effect on exposed users.** Only 3.6% of the ad arm saw an ad; exposure is treated as one-sided non-compliance.
4. **Targeting.** A response model P(visit | X), T-, X- and DR-learners and a causal forest, trained on 50% of users,
   selected on 20% and scored once on the remaining 4.19M users with the Qini coefficient and a paired bootstrap.

## Results

Full tables: [`docs/11_results_criteo_incrementality_uplift.md`](docs/11_results_criteo_incrementality_uplift.md).

| | Unadjusted | Regression-adjusted |
|---|---|---|
| Visit rate, control → ad arm | 3.82% → 4.85% (+1.03 pp, SE 0.015) | +0.77 pp (SE 0.013) |
| Conversion rate, control → ad arm | 0.19% → 0.31% (+0.115 pp, SE 0.003) | +0.100 pp (SE 0.003) |
| Visit effect among exposed users | 28.7 pp (SE 0.41) | 21.5 pp (SE 0.35) |

[![Visit and conversion rates by group, the effect by decile of predicted uplift, and the Qini coefficient of each targeting model](out/fig_rates_by_arm.png)](https://lyz44git.github.io/ad-measurement-and-metrics/01.html#s01a)

- Assignment is slightly predictable from the features (held-out AUC 0.509; largest standardized difference 0.049),
  so both columns are reported.
- The effect is concentrated: the top tenth of test users by predicted uplift gained 6.0 pp against 1.05 pp overall,
  and the top fifth by T-learner score accounts for 75% of incremental visits. Ranking by the response model gives the
  same share (76%), so this concentration is not specific to the uplift model.
- **The pre-specified targeting comparison was not met.** The selected T-learner did not beat the response model on
  Qini (difference −1.2 × 10⁻⁴ per user, 95% CI −3.0 to +0.6). Ranking by likelihood to visit was as good a targeting rule
  here as ranking by predicted uplift.
- Predicted uplift is well calibrated in deciles 1–9, where decile 1 has the highest predicted uplift (6.6 pp
  predicted, 6.0 pp realized). Decile 10 is predicted negative (−0.8 pp) but realized +0.7 pp, so the model does
  not identify a group the ad harms.

## Reproduce

```bash
python code/10_run_criteo.py        # about 7 minutes on 16 cores; writes out/criteo/ and models/
python -m pytest code/tests -q      # runs on simulated data; service tests are skipped until models/ exists
```

The estimators and the evaluation code are in `code/upliftkit`, with a local scoring endpoint for the selected model
(`code/upliftkit/service.py`).

## Scope

- The released data pool several tests with non-uniform subsampling, so absolute lifts are not population effects;
  comparisons between methods are valid.
- This is an analysis of released experimental data, not the design or operation of an experiment.
