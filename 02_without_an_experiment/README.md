# 2. Without an experiment: when can the usual metrics be trusted?

**[Explore these studies interactively →](https://lyz44git.github.io/ad-measurement-and-metrics/02.html)**

Studies 02a and 02c check a metric used in place of an experiment against a benchmark: the experiment of
[study 01a](../01_with_an_experiment/01a_ad_incrementality), or a simulation with known returns. Study 02b shows how
much the credit given to each touch depends on the rule chosen, and study 02d whether that changes what a bidder
buys; these two have no benchmark. Study 02e checks estimates of what a new targeting
rule would bring against a benchmark from the experiment, and study 02f checks conversion forecasts made before the
labels arrive against the labels that arrive later.

| Study | Question | Key result |
|---|---|---|
| [`02a_attribution_metric_validation`](02a_attribution_metric_validation) | Can an exposure-based attribution metric be trusted as a measure of ad impact? | It credited 23,031 conversions where the experiment puts those caused by the ads at an estimated 13,687 (unadjusted; about 11,902 after regression adjustment) (68% more than the unadjusted estimate; 44% more for visits). Without an experiment, covariate adjustment moved the per-exposed-user effect from a naive 38.0 points to 24.6-25.5, between the two experimental estimates (21.5 regression-adjusted, 28.7 unadjusted); these are associations within the ad arm and the experimental figures are complier effects, so the band is descriptive, not a bound. |
| [`02b_multi_touch_attribution`](02b_multi_touch_attribution) | When a user sees several ads before converting, how much does the credit rule change which touch gets credit? | On 6.1M display-ad user paths, 65% of converting paths had several touches and last touch gave no credit to 82% of the touches in them; a time-decay rule fitted to observed delays (half-life 7.9 days) left 39% of the credit on the last touch. |
| [`02c_marketing_mix_modeling`](02c_marketing_mix_modeling) | Can a marketing mix model recover each channel's return from a brand's own spend and revenue, and can one tell in advance when it will? | In simulations on the real spend of 31 to 34 e-commerce brands, recovery depended on a signal-to-noise index computed from the planted contribution before the marketing mix model is fitted (a simulation diagnostic): in a pre-specified held-out test, the median error of a channel's estimated return was 19% for brand-channels with an index of 2 or more (rank correlation 0.80 with the truth) and 50% for the rest. Only 19% of brand-channels reach that level in the weekly simulation, against 55% in the daily one, which also differs in planted returns, noise and carry-over. Pooling the brands in one model did not help, and media terms did not reliably improve holdout forecasts. |
| [`02d_attribution_and_bidding`](02d_attribution_and_bidding) | If a bidder values impressions by expected credit, does the attribution rule change what it buys? | Hardly: in a replay on 4.6M logged impressions with their prices, a last-touch bidder and a time-decay bidder share 90% of their spend at half the logged budget, where bidding with the other rule's model costs at most 2.2% of credit (3.1% at a quarter of the budget). The pre-specified 5% threshold was not met. |
| [`02e_off_policy_evaluation`](02e_off_policy_evaluation) | What is a targeting policy worth before it has run? | On logs of about 1.6 million users that favor likely visitors, where an unweighted comparison gives 3 to 4 times the lift, one log's doubly robust estimate with an estimated assignment probability is off by 2.5% to 2.7% of a feature-adjusted benchmark from the experiment, and inverse probability weighting with the logged probability by 3.0% to 3.9%; both pre-specified rules (below 10%, coverage at least 90%) were met. Under strong bias the doubly robust estimate stays within 6% while weighting by an estimated probability falls about a third short. Two earlier designs with smaller logs missed their rules. |
| [`02f_delayed_conversions`](02f_delayed_conversions) | Can a conversion model trained before its labels arrive be corrected for the delay? | The level, yes: retrained daily on the conversions seen so far, a network predicts 11.5% too few 14-day conversions; a delayed-feedback network in PyTorch with a non-parametric delay predicts 1.8% too many, against 0.0% with complete labels, and campaign by campaign lowers the forecast error from 16.0% to 13.3% (floor 11.7%); both pre-specified rules were met. Its log loss did not improve, nor did that of a ranker given its level (two rules not met). Leaving out the last two weeks instead ranks much worse (ROC AUC 0.760 against 0.791). Two earlier designs are documented. |

## Main figure of each study

**[02a · Validating an attribution metric against a randomized experiment](02a_attribution_metric_validation)**

[![Outcomes credited by attribution against outcomes caused by the ads, and estimates of the effect of exposure by method](02a_attribution_metric_validation/out/fig_attributed_vs_incremental.png)](https://lyz44git.github.io/ad-measurement-and-metrics/02.html#s02a)

**[02b · Multi-touch attribution on 6.1M display-ad user paths](02b_multi_touch_attribution)**

[![Share of conversion credit by rule and timing of the touch, and credit on clicked touches](02b_multi_touch_attribution/out/fig_credit_by_rule.png)](https://lyz44git.github.io/ad-measurement-and-metrics/02.html#s02b)

**[02c · Marketing mix models: which brands have enough signal to measure a channel's return?](02c_marketing_mix_modeling)**

[![Recovery error against the signal-to-noise index, and the smallest detectable ROAS on real spend](02c_marketing_mix_modeling/out/fig_detectability.png)](https://lyz44git.github.io/ad-measurement-and-metrics/02.html#s02c)

Study 02d has no figure; the results are the tables in the study's README.

**[02e · Off-policy evaluation against a randomized experiment](02e_off_policy_evaluation)**

[![Error and interval coverage of off-policy estimators, and the experiment's value with and without adjustment](02e_off_policy_evaluation/out/fig_ope.png)](https://lyz44git.github.io/ad-measurement-and-metrics/02.html#s02e)

**[02f · Conversion models before the labels arrive](02f_delayed_conversions)**

[![Calibration of conversion models by test day, three designs, and fit and ranking](02f_delayed_conversions/out/fig_delay.png)](https://lyz44git.github.io/ad-measurement-and-metrics/02.html#s02f)

Method, data, decision rules and limitations are in each study's README; the four questions are introduced in
the [main README](../README.md).
