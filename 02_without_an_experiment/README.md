# 2. Without an experiment: when can the usual metrics be trusted?

**[Explore these studies interactively →](https://lyz44git.github.io/ad-measurement-and-metrics/02.html)**

Studies 02a and 02c check a metric used in place of an experiment against a benchmark: the experiment of
[study 01a](../01_with_an_experiment/01a_ad_incrementality), or a simulation with known returns. Study 02b shows how
much the credit given to each touch depends on the rule chosen, and study 02d whether that changes what a bidder
buys; these two have no benchmark.

| Study | Question | Key result |
|---|---|---|
| [`02a_attribution_metric_validation`](02a_attribution_metric_validation) | Can an exposure-based attribution metric be trusted as a measure of ad impact? | It credited 23,031 conversions where the experiment puts those caused by the ads at 13,687 (68% more; 44% more for visits). Without an experiment, covariate adjustment moved the per-exposed-user effect from a naive 38.0 points to 24.6-25.5, between the two experimental estimates (21.5 regression-adjusted, 28.7 unadjusted). |
| [`02b_multi_touch_attribution`](02b_multi_touch_attribution) | When a user sees several ads before converting, how much does the credit rule change which touch gets credit? | On 6.1M display-ad user paths, 65% of converting paths had several touches and last touch gave no credit to 82% of the touches in them; a time-decay rule fitted to observed delays (half-life 7.9 days) left 39% of the credit on the last touch. |
| [`02c_marketing_mix_modeling`](02c_marketing_mix_modeling) | Can a marketing mix model recover each channel's return from a brand's own spend and revenue, and can one tell in advance when it will? | In simulations on the real spend of 31 to 34 e-commerce brands, recovery depended on a signal-to-noise index computed before fitting: in a pre-specified held-out test, the median error of a channel's estimated return was 19% for brand-channels with an index of 2 or more (rank correlation 0.80 with the truth) and 50% for the rest. Only 19% of brand-channels reach that level on weekly data, against 55% on daily data. Pooling the brands in one model did not help, and media terms did not reliably improve holdout forecasts. |
| [`02d_attribution_and_bidding`](02d_attribution_and_bidding) | If a bidder values impressions by expected credit, does the attribution rule change what it buys? | Hardly: in a replay on 4.6M logged impressions with their prices, a last-touch bidder and a time-decay bidder share 90% of their spend at half the logged budget, where bidding with the other rule's model costs at most 2.2% of credit (3.1% at a quarter of the budget). The pre-specified 5% threshold was not met. |

## Main figure of each study

**[02a · Validating an attribution metric against a randomized experiment](02a_attribution_metric_validation)**

[![Outcomes credited by attribution against outcomes caused by the ads, and estimates of the effect of exposure by method](02a_attribution_metric_validation/out/fig_attributed_vs_incremental.png)](https://lyz44git.github.io/ad-measurement-and-metrics/02.html#s02a)

**[02b · Multi-touch attribution on 6.1M display-ad user paths](02b_multi_touch_attribution)**

[![Share of conversion credit by rule and timing of the touch, and credit on clicked touches](02b_multi_touch_attribution/out/fig_credit_by_rule.png)](https://lyz44git.github.io/ad-measurement-and-metrics/02.html#s02b)

**[02c · Marketing mix models: which brands have enough signal to measure a channel's return?](02c_marketing_mix_modeling)**

[![Recovery error against the signal-to-noise index, and the smallest detectable ROAS on real spend](02c_marketing_mix_modeling/out/fig_detectability.png)](https://lyz44git.github.io/ad-measurement-and-metrics/02.html#s02c)

Study 02d has no figure; the results are the tables in the study's README.

Method, data, decision rules and limitations are in each study's README; the four questions are introduced in
the [main README](../README.md).
