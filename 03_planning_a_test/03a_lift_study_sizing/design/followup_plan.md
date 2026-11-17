# Follow-up plan: does covariate adjustment lower the sample a lift study needs?

Written 2026-11-16, after the first part of this study (power of the unadjusted readout by sample size) had been run
and read, and before any adjusted estimate was computed. SHA-256 saved to `logs/followup_plan_hash.txt` first.

## Question

The first part found that an unadjusted readout needs about 10,000 users per arm to detect a one-point lift. Study 03
found that regression adjustment on pre-period volume was the main gain for market-level tests. Does adjustment for
user features recorded before the ad give a comparable gain for user-level studies, and does the adjusted readout keep
its 5% false-positive rate?

## Data

Criteo Uplift Prediction Dataset v2.1: 13,979,592 users, treatment flag, visit flag and 12 anonymized features
(`f0` to `f11`), which Criteo describes as user features. Outcome: visit.

## Design

1. **Split.** Users are split at random into a model half and a study half (NumPy `default_rng(20261116)`, one uniform
   draw per row in file order, model half if below 0.5).
2. **Prediction model.** A LightGBM classifier of visit on the 12 features, trained on the control-arm users of the
   model half only (300 trees, learning rate 0.05, 63 leaves, at least 200 users per leaf, seed 0). Its predicted
   probability `g` is computed for every user of the study half. No user of the study half is used to fit it.
3. **Studies.** For each size n in 1,000, 2,500, 5,000, 10,000 and 20,000 users per arm, 2,000 studies. A study draws n
   users without replacement from the ad arm and n from the control arm of the study half. A/A studies draw two
   disjoint samples of n users from the control arm.
4. **Readouts of each study.**
   - D: difference in visit rates, unequal-variance standard error.
   - L: coefficient on treatment in OLS of visit on treatment and the 12 features, HC1 standard error.
   - M: coefficient on treatment in OLS of visit on treatment and `g`, HC1 standard error.
   All three use a two-sided test at 5%.
5. **Quantities reported for each readout and size.** Standard deviation of the estimate across the 2,000 studies;
   its variance relative to D, with a 95% bootstrap interval (studies resampled, 2,000 draws); the ratio of the mean
   reported standard error to that standard deviation; coverage of the 95% interval for the readout's own expectation
   (the mean of the estimate across the studies of that size); the A/A rejection rate; and the minimum detectable
   effect at 80% power, (1.960 + 0.842) x standard deviation.
6. **Required sample.** For each readout, the users per arm needed to detect a one-point lift with 80% power:
   (2.802 x s / 0.01)^2, where s^2 is the mean over the five sizes of n x variance.

Assignment in this dataset is slightly predictable from the features (study 01), so the adjusted readouts estimate a
smaller lift than D does on these data. Readouts are therefore compared by their sampling variance and minimum
detectable effect, which do not depend on the size of this experiment's lift, and not by how often each detects it.

## Decision rule

Adjustment by M (and, separately, by L) is said to help if, at every size, the 95% bootstrap interval of its variance
relative to D lies below 1, its A/A rejection rate is between 3.5% and 6.5%, and its interval coverage is at least 93%.

## Limits stated in advance

Site visit stands in for a survey response; survey studies usually have weaker covariates than these. One experiment,
one outcome. The size of the gain depends on how well the features predict the outcome and does not carry over to
other outcomes.
