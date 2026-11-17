# Follow-up plan: one marketing mix model for all brands, with partial pooling

Written 2026-11-16, after the per-brand weekly and daily results of this study had been run and read, and before any
pooled model was fitted to real or simulated revenue. SHA-256 saved to `logs/followup_plan_hash.txt` first.

## Question

Fitted one brand at a time, the planned weekly model could not recover known channel returns (rank correlation 0.01),
and media terms did not reliably improve holdout forecasts at either frequency. A single brand's series carries little
information about carry-over and saturation. Does fitting all eligible brands in one model, with the media parameters
of each brand drawn from a distribution shared across brands, recover channel returns better and forecast better?

## Data and preparation

As in `design/analysis_plan.md` (Part A) and deviation 1: the same eligible brands, outcome, channels, scaling, holdout
(last 13 weeks or 91 days), adstock window (8 weeks or 28 days) and trend, seasonal and day-of-week terms.

## Model

For brand b, period t and channel c (Google, Meta), with y scaled by its training mean and spend by its training
maximum:

    y_bt = b0_b + X_bt b_b + sum_c beta_bc Hill(adstock(spend_bct; a_bc); h_bc, k_bc) + e_bt,   e_bt ~ Normal(0, sigma_b)

Per brand, as in the plan: b0_b ~ Normal(1, 1), b_b ~ Normal(0, 0.5), sigma_b ~ HalfNormal(0.5).

Pooled across brands, separately for each channel (non-centered):

    logit(a_bc)  ~ Normal(mu_a_c, tau_a_c),      mu_a_c ~ Normal(0, 1),      tau_a_c ~ HalfNormal(1)
    logit(h_bc)  ~ Normal(mu_h_c, tau_h_c),      mu_h_c ~ Normal(0, 1),      tau_h_c ~ HalfNormal(1)
    log(k_bc)    ~ Normal(mu_k_c, tau_k_c),      mu_k_c ~ Normal(0, 0.3),    tau_k_c ~ HalfNormal(0.3)
    log(beta_bc) ~ Normal(mu_beta_c, tau_beta_c), mu_beta_c ~ Normal(-1, 1), tau_beta_c ~ HalfNormal(1)

NumPyro NUTS, 4 chains of 1,000 warm-up and 1,000 draws, target acceptance 0.9, 64-bit floats, seed 21. A brand's
pooled fit counts as converged if the split R-hat of both of its channel ROAS is below 1.05; the largest R-hat over
all parameters is reported as well.

Channel ROAS, its 90% interval and the holdout forecast are computed as in the per-brand run.

## Tests

Run at both frequencies (weekly, as planned; daily, as in deviation 1). All eligible brands are used in every test.

1. **Recovery, brand-specific shapes (primary).** Real spend; revenue simulated as the no-media fit plus known media
   effects plus Normal noise at the no-media residual SD. For each brand and channel, true ROAS ~ Uniform(0.5, 4),
   adstock decay ~ Uniform(0.2, 0.8), Hill h ~ Uniform(0.3, 0.8), k = 1 (NumPy `default_rng(21)`). The pooled model
   and the per-brand model are both fitted to the same simulated revenue.
2. **Recovery, common shapes (as in the original plan).** The original simulation (adstock 0.5, h 0.5, k 1 for every
   brand), for all eligible brands (`default_rng(22)`). Common shapes favor pooling by construction, so this test is
   reported for continuity with the per-brand result and is not used for the decision.
3. **Holdout forecast on real revenue.** wMAPE of the pooled model against the per-brand model without media.

## Reported

For tests 1 and 2, for each model: rank correlation between true and estimated ROAS, median absolute relative error
and coverage of the 90% intervals, over the brand-channels converged under both models (and over all of them).
For test 3: number of brands where the pooled model has the lower wMAPE and the mean difference with a 95% bootstrap
interval (brands resampled, 2,000 draws). Also: convergence, the pooled estimates of the shared parameters, and the
median model ROAS on real data.

## Decision rules

- **Recovery.** Pooling is said to improve recovery at a frequency if, in test 1, the pooled model's median absolute
  relative error is lower than the per-brand model's and the 95% bootstrap interval (brands resampled, 2,000 draws) of
  the difference in mean absolute relative error, pooled minus per-brand, lies below 0.
- **Forecast.** The original rule: the pooled media model is preferred to the no-media model if its holdout wMAPE is
  lower in more than half of the brands and the 95% bootstrap interval of the mean difference lies below 0.

Both outcomes are reported whatever they are, next to the per-brand results, which stay in the README.

## Limits stated in advance

The recovery tests are simulations: they show whether the model can recover returns of the assumed form, not whether
real returns have that form. Model ROAS on real data remains observational. Pooling assumes the brands' media
parameters are exchangeable; the brands differ in size, market and product.
