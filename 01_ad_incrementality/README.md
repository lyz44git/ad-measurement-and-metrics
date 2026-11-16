# 01. Ad incrementality on a 14.0M-user randomized experiment

**Question.** How many site visits and conversions did the ads cause, as opposed to those that would have happened
anyway? And can a model find the users an ad moves most?

**Data.** Criteo Uplift Prediction Dataset v2.1: 13,979,592 users, 85% randomized to the ad arm, 12 anonymized
features, exposure, visit and conversion flags. Criteo ran the experiment; I analysed the released data.
Download `criteo-research-uplift-v2.1.csv.gz` from the Criteo AI Lab page and place it in
`data_raw/criteo_uplift_v2.1/` (git-ignored). `code/00_check_criteo.py` prints the md5 and arm-level rates.

**What I did.** The plan (`docs/10_plan_criteo_incrementality_uplift.md`) was written and hashed before the run
(`logs/10_plan_hash.txt`).
- Intent-to-treat effects with Neyman standard errors, and a regression-adjusted (AIPW, linear) version.
- Assignment diagnostics: standardized mean differences and the held-out AUC of a model predicting treatment.
- Effect on users actually exposed (3.6% of the ad arm), treating exposure as one-sided non-compliance.
- Response model, T-, X- and DR-learners and a causal forest, selected on validation and scored once on a 4.19M-user
  test set with Qini and a paired bootstrap.
- A small tested package (`code/upliftkit`), a config file and a local scoring endpoint.

**What I found** (full table in `docs/11_results_criteo_incrementality_uplift.md`).
- Ads raised the visit rate from 3.82% to 4.85% (+1.03 points, SE 0.015; +0.77 after regression adjustment) and the
  conversion rate from 0.19% to 0.31%.
- Assignment is slightly predictable (AUC 0.509), so both the unadjusted and the adjusted figures are reported.
- Among exposed users the visit effect is 21.5 to 28.7 points.
- Heterogeneity is large: the top tenth of test users by predicted uplift gained 6.0 points against 1.05 overall, and
  the top fifth accounts for 75% of incremental visits.
- **The pre-specified comparison was not won:** uplift targeting did not beat a plain response model on Qini
  (difference -1.2, 95% CI -3.0 to +0.6). In this experiment the users most likely to visit are also the users the ad
  moves most.

**Run.**
```bash
python code/10_run_criteo.py            # about 7 minutes on 16 cores; writes out/criteo/ and models/
python -m pytest code/tests -q          # 15 checks; the service tests need models/ from the run above
```

**Does not show.** Designing or running an experiment, a population-level lift (the data are subsampled), or a
deployed service.
