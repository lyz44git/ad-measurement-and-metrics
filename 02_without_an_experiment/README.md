# 2. Without an experiment: when can the usual metrics be trusted?

Studies 02a and 02c check a metric used in place of an experiment against a benchmark: the experiment of
[study 01a](../01_with_an_experiment/01a_ad_incrementality), or a simulation with known returns. Study 02b shows how
much the credit given to each touch depends on the rule chosen; it has no benchmark.

| Study | Question | Key result |
|---|---|---|
| [`02a_attribution_metric_validation`](02a_attribution_metric_validation) | Can an exposure-based attribution metric be trusted as a measure of ad impact? | It credited 23,031 conversions where the experiment puts those caused by the ads at 13,687 (68% more; 44% more for visits). Without an experiment, covariate adjustment moved the per-exposed-user effect from a naive 38.0 points to 24.6-25.5, between the two experimental estimates (21.5 regression-adjusted, 28.7 unadjusted). |
| [`02b_multi_touch_attribution`](02b_multi_touch_attribution) | When a user sees several ads before converting, how much does the credit rule change which touch gets credit? | On 6.1M display-ad user paths, 65% of converting paths had several touches and last touch gave no credit to 82% of the touches in them; a time-decay rule fitted to observed delays (half-life 7.9 days) left 39% of the credit on the last touch. |
| [`02c_marketing_mix_modeling`](02c_marketing_mix_modeling) | Can a marketing mix model recover each channel's return from a brand's own spend and revenue, and can one tell in advance when it will? | In simulations on the real spend of 31 to 34 e-commerce brands, recovery depended on a signal-to-noise index computed before fitting: in a pre-specified held-out test, the median error of a channel's estimated return was 19% for brand-channels with an index of 2 or more (rank correlation 0.80 with the truth) and 50% for the rest. Only 19% of brand-channels reach that level on weekly data, against 55% on daily data. Pooling the brands in one model did not help, and media terms did not reliably improve holdout forecasts. |

## Main figure of each study

**[02a · Validating an attribution metric against a randomized experiment](02a_attribution_metric_validation)**

![Outcomes credited by attribution against incremental outcomes from the experiment](02a_attribution_metric_validation/out/fig_attributed_vs_incremental.png)

**[02b · Multi-touch attribution on 6.1M display-ad user paths](02b_multi_touch_attribution)**

![Share of conversion credit by recency of the touch and on clicked touches, by rule](02b_multi_touch_attribution/out/fig_credit_by_rule.png)

**[02c · Marketing mix models: which brands have enough signal to measure a channel's return?](02c_marketing_mix_modeling)**

![Recovery error against the signal-to-noise index, and the smallest detectable ROAS on real spend](02c_marketing_mix_modeling/out/fig_detectability.png)

Method, data, decision rules and limitations are in each study's README; the four questions are introduced in
the [main README](../README.md).
