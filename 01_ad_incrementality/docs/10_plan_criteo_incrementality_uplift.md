# Plan: Criteo Uplift v2.1 — incrementality, CATE learners, held-out targeting test (written before any run)

Date: 2026-11-12. Continues steps 1–2 of this folder's README plan (2026-10-31) and reuses the workflow of the
randomized-price reanalysis (hashed plan, seeded routines, pytest checks). Public randomized advertising experiment
(Diemert et al. 2018). The experiment was designed and run by the dataset's authors. Dataset documentation: several tests pooled with
non-uniform subsampling, so absolute lift is not interpretable as a population effect; method comparisons are.

## Data and split
All 13,979,592 rows. Seed 20261112. Random 50% train / 20% validation / 30% test. Features f0–f11 only.

## Stage A — incrementality (full sample)
- Outcomes: visit (primary), conversion (secondary).
- ITT: difference in means, Neyman SE. Regression-adjusted ITT: AIPW with linear outcome models and the sample
  treated share as propensity. Report both; if they differ, say so and do not pick one after the fact.
- Assignment diagnostics: standardized mean differences for f0–f11; held-out AUC of a LightGBM model predicting
  treatment (0.5 = no predictable assignment).
- CACE for visit: ITT / exposure share among treated (one-sided non-compliance; exposure is 0 in control).

## Stage B — CATE learners (train only, outcome = visit)
Response model P(visit | X) (the non-causal baseline), T-learner, X-learner, DR-learner (2-fold cross-fitted
nuisances, estimated propensity clipped to [0.05, 0.95]), and an EconML causal forest on a 300,000-row subsample.
LightGBM settings fixed in config.json before the run. No tuning on test.

## Stage C — evaluation
- Metric: Qini coefficient on 100 rank bins (area between the uplift gain curve and the random line, per user).
- Selection: best Qini on validation. Test is scored once, all learners reported.
- Primary test: selected causal learner vs response model, paired Poisson bootstrap (200 draws), 95% CI of the
  Qini difference. Decision rule: "uplift targeting beats response targeting" only if the CI excludes 0.
- Secondary: realized uplift in the top 10% and 20%; share of total incremental visits captured by the top 20%;
  decile calibration (predicted vs realized) for the selected learner.

## Stage D — packaging
`upliftkit` module, config file, CLI entry point, saved model, FastAPI scoring endpoint (local only), pytest:
recovery of a known simulated ATE and heterogeneity, no detection under a null, seeded bootstrap, API schema and
batch/API parity. Deviations from this plan are listed in the results file.
