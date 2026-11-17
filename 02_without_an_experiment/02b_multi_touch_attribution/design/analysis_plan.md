# Analysis plan: marketing mix models (MMM) and multi-touch attribution (MTA) on real public data

Written 2026-11-15 before running `code/10_mmm.py` and `code/20_mta.py`; SHA-256 saved to `logs/plan_hash.txt` first.
Only data profiling had been run (`out/00_mta_profile.json`, column coverage of the MMM file). No model had been fit.
Everything here is an independent project on public data. Nothing was run for a company; no budget was changed.

## Part A. MMM on 93 real e-commerce brands
Data: "Multi-Region Marketing Mix Modelling (MMM) Dataset for Several eCommerce Brands" (Conjura; Figshare article
25314841, CC BY 4.0; `conjura_mmm_data.csv`, md5 84fc8f32...f985). Daily, anonymised, real brands; spend by channel
(Google, Meta, TikTok) and purchases. No price, promotion calendar, offline media or competitor data.

- Unit: one series per brand, `TERRITORY_NAME == "All Territories"`. Weekly sums (weeks starting Monday); incomplete
  first and last weeks dropped.
- Outcome: weekly revenue = `ALL_PURCHASES_ORIGINAL_PRICE - ALL_PURCHASES_GROSS_DISCOUNT`, divided by its training mean.
- Channels: Google = sum of the five Google spend columns; Meta = sum of the three Meta spend columns. TikTok (3% of
  rows) is left out. Missing spend = 0.
- Eligible brands: at least 104 complete weeks, and Google spend > 0 and Meta spend > 0 in at least 80% of weeks each.
- Split: the last 13 weeks are the holdout; the model is fit on the weeks before.
- Model (per brand, Bayesian, NUTS in NumPyro, 2 chains x 500 warm-up + 500 draws):
  y_t = b0 + b1*t + Fourier(2 harmonics, 52.18 weeks) + sum_c beta_c * Hill(adstock_c(x_ct)) + e_t, e ~ Normal(0, sigma).
  Geometric adstock over 8 weeks with decay a_c ~ Beta(2,2), weights normalised to sum to 1; spend scaled by its
  training maximum; Hill(s) = s^k / (s^k + h^k), h ~ Beta(2,2), k ~ LogNormal(0, 0.3); beta_c ~ HalfNormal(1);
  b0 ~ Normal(1,1); b1, Fourier ~ Normal(0, 0.5); sigma ~ HalfNormal(0.5).
- Comparators: (B0) the same model without media terms; (B1) seasonal naive (the same week one year earlier).
- Primary metric: holdout weighted absolute percentage error, wMAPE = sum|y - yhat| / sum y, posterior-mean forecast.
- Decision rule: the MMM is preferred to B0 if its holdout wMAPE is lower in more than half of the brands AND the
  95% bootstrap interval (brands resampled, 2,000 draws) of the mean difference MMM - B0 lies below 0.
- Reported whatever the outcome: number of eligible brands, convergence (share with max R-hat < 1.05), wMAPE of the
  three forecasts, share of training revenue attributed to each channel, ROAS by channel (model revenue contribution /
  spend, posterior median and 90% interval), platform-blended ROAS (revenue / total spend) for contrast, and a
  10% reallocation toward the channel with the higher marginal return (model-implied revenue change; not validated).
- Parameter recovery (simulation, labelled as such): for 20 eligible brands (seed 7), keep the real spend series,
  simulate revenue from the B0 fit plus known media effects (true ROAS drawn Uniform(0.5, 4) per channel, adstock 0.5,
  Hill h 0.5, k 1) plus Normal noise at the B0 residual SD, refit, and report the rank correlation between true and
  estimated ROAS and the coverage of 90% intervals.
- Limits stated in advance: observational; spend responds to demand, so ROAS is not a causal estimate and no
  experiment calibrates it; two channels; weekly data.

## Part B. Touch-level MTA on Criteo display paths
Data: Criteo Attribution Modeling for Bidding dataset (Diemert et al. 2017; CC BY-NC-SA 4.0; from Criteo's Hugging Face
account, sha256 94ac7a46...1a98). 16,468,027 impressions, 6,142,256 users, 675 campaigns, 30 days, 435,810 conversions.
Profile: 32.3% of conversions have more than one touch; only 0.7% touch more than one campaign. So this is attribution
across the touches of a path (which impression gets credit), NOT cross-channel or cross-campaign attribution.

- Path: for converters, the impressions sharing the user's first `conversion_id`; for other users, all their
  impressions. One path per user. Users split 70/30 by hash of uid (train/test).
- Rule-based credit per conversion: last touch, first touch, linear, and time decay exp(-lambda * (t_conv - t_touch))
  with lambda estimated by maximum likelihood (exponential) on touch-to-conversion delays in the training users.
- Data-driven credit: logistic model of path conversion with additive touch terms (clicked or not x recency bucket
  relative to the last touch: last touch, <1 day, 1-7 days, >7 days before it) and log(1 + number of touches). Credit of
  a touch = fall in predicted conversion probability when that touch is removed, normalised to sum to 1 per conversion.
- Reported: test AUC of the path model against a model with log(1 + touches) only (paired user bootstrap, 500 draws);
  among multi-touch conversions in the test users, the share of credit on the last touch under each rule and the
  share of converting-path touches that receive no credit under last touch; credit share of clicked vs unclicked touches.
- Decision rule: the data-driven model is used for credit only if its test AUC exceeds the touches-only model with a
  paired 95% interval above 0. Otherwise report rule-based results only.
- Limits: one advertiser-side display network; costs are transformed; removal effects are model-based, not experimental.
