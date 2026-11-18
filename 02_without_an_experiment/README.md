# 2. Without an experiment: when can the usual metrics be trusted?

**[Explore these studies interactively →](https://lyz44git.github.io/ad-measurement-and-metrics/02.html)**

Studies 02a and 02c check a metric used in place of an experiment against a benchmark: the experiment of
[study 01a](../01_with_an_experiment/01a_ad_incrementality), or a simulation with known returns. Study 02b shows how
much the credit given to each touch depends on the rule chosen, and study 02d whether that changes what a bidder
buys; these two have no benchmark.

| Study | Question | Evidence | Key result |
|---|---|---|---|
| [`02a_attribution_metric_validation`](02a_attribution_metric_validation) | Can an exposure-based attribution metric be trusted as a measure of ad impact? | Randomized experiment (study 01a) | It credited 23,031 conversions where the experiment estimates 13,687 additional conversions (the count is 68% higher; 44% higher for visits). Within the ad arm, the raw exposed-minus-unexposed visit difference was 38.0 points; covariate adjustment gave 24.6-25.5, between the two experimental specifications (28.7 unadjusted, 21.5 regression-adjusted). |
| [`02b_multi_touch_attribution`](02b_multi_touch_attribution) | When a user sees several ads before converting, how much does the credit rule change which touch gets credit? | None: four credit rules compared | On 64,159 multi-touch converting test paths, moving from last touch to a time-decay rule fitted to observed delays (half-life 7.9 days) cut the credit on the last touch from 100% to 39%. |
| [`02c_marketing_mix_modeling`](02c_marketing_mix_modeling) | Can a marketing mix model recover each channel's return from a brand's own spend and revenue, and can one tell in advance when it will? | Simulation with known returns | In simulations on the real spend of 31 to 34 e-commerce brands, error was lower where a signal-to-noise index computed before fitting was higher: in the pre-specified test, the median error of a channel's estimated return was 19% for brand-channels with an index of 2 or more (33 of 54) and 50% for the rest. In these simulations 19% of brand-channels reach that level on weekly data and 55% on daily data. Pooling the brands failed its pre-specified rule, and media terms did not reliably improve holdout forecasts. |
| [`02d_attribution_and_bidding`](02d_attribution_and_bidding) | If a bidder values impressions by expected credit, does the attribution rule change what it buys? | None: replay of logged impressions | In a replay on 4.6M logged test impressions at their logged prices, a last-touch bidder and a time-decay bidder share 90.4% of their spend at half the logged budget, where bidding with the other rule's model loses at most 2.2% of that rule's credit (3.1% at a quarter of the budget). The pre-specified rule, a loss of at least 5% under both rules at that budget, was not met. |

## Main figure of each study

**[02a · Validating an attribution metric against a randomized experiment](02a_attribution_metric_validation)**

[![Additional conversions and visits estimated from the experiment, with 95% ranges, against the larger numbers credited by an exposure count; and estimates of the effect of seeing an ad from a raw comparison and two adjusted methods, set against the two estimates from the experiment](02a_attribution_metric_validation/out/fig_attributed_vs_incremental.png)](https://lyz44git.github.io/ad-measurement-and-metrics/02.html#s02a)

**[02b · Multi-touch attribution on 6.1M display-ad user paths](02b_multi_touch_attribution)**

[![How four attribution rules divide conversion credit between the last ad and earlier ads, by time before the last ad; and the share of credit each rule gives to ads that were clicked, against the 52% of ads on these paths that were clicked](02b_multi_touch_attribution/out/fig_credit_by_rule.png)](https://lyz44git.github.io/ad-measurement-and-metrics/02.html#s02b)

**[02c · Marketing mix models: which brands have enough signal to measure a channel's return?](02c_marketing_mix_modeling)**

[![In a simulation, error of the estimated return against the signal-to-noise index, with median error 50% below an index of 2 and 19% at or above it; and the smallest return each brand-channel pair's real spend could detect with 80% power, where 6% of weekly and 42% of daily pairs could detect a return of 2](02c_marketing_mix_modeling/out/fig_detectability.png)](https://lyz44git.github.io/ad-measurement-and-metrics/02.html#s02c)

Study 02d has no figure; its results are the tables in [its README](02d_attribution_and_bidding) and the
[interactive replay](https://lyz44git.github.io/ad-measurement-and-metrics/02.html#s02d).

Method, data, decision rules and limitations are in each study's README; the four questions are introduced in
the [main README](../README.md).
