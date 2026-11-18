# 3. Planning a test: how large must it be, and what is the baseline?

**[Explore these studies interactively →](https://lyz44git.github.io/ad-measurement-and-metrics/03.html)**

Where a budget decision needs incremental evidence that the metrics of section 2 cannot give, the next step is an
experiment. Studies 03a and 03b size it, by user and by market; in both, adjusting for what is known before the
test is the main way to make it smaller. Study 03c forecasts the baseline of a metric so that national, state and
metro levels agree.

| Study | Data and method | Question | Key result |
|---|---|---|---|
| [`03a_lift_study_sizing`](03a_lift_study_sizing) | Criteo experiment, resampled | How many users per arm does a lift study need, and how much does covariate adjustment save? | For a one-point lift in site visits on a 3.8% base rate, an unadjusted readout needs about 6,500 users per arm for 80% power. Adjusting for 12 pre-treatment user features cuts this to about 4,700, and adjusting for a model prediction built from them to about 4,400, with false-positive rates near 5%. |
| [`03b_geo_experiment_design`](03b_geo_experiment_design) | Zillow pending listings, placebo tests | If a change can only be randomized by market, how large a test is needed, and does the usual t-test keep its 5% false-positive rate? | In placebo tests drawn from 151 U.S. metros, adjusting for pre-period volume lowered the smallest change a two-month, 100-metro test detects with 80% power from 9.5% (year-over-year difference) to 6.7%. For the volume-weighted estimate the t-test rejected a true null 5.7-9.1% of the time; randomization inference kept it between 4.2% and 5.8%, with a detectable change of 8.8% against 8.2% at 100 metros. |
| [`03c_hierarchical_forecasting`](03c_hierarchical_forecasting) | Zillow inventory and new listings, backtest | Can the baseline of a metric be forecast at national, state and metro levels so that the levels add up, without losing accuracy? | Separate forecasts of for-sale housing inventory disagreed across levels by 3.5-5.2%. Bottom-up reconciliation removed the gap; its error matched or improved on the separate forecasts in 11 of 12 comparisons, the exception being national new listings (0.7% higher). MinT-shrink cut state and metro error by 7-10% with one base model but not with another. |

## Main figure of each study

Titles link to each study; figures link to its interactive version.

**[03a · Sizing user-level lift studies, with and without covariate adjustment](03a_lift_study_sizing)**

[![Smallest detectable lift by users per group with no adjustment and with two adjustments, against a one-point target; and the variance of the adjusted readouts relative to no adjustment, about 0.7 at every size](03a_lift_study_sizing/out/fig_mde_by_adjustment.png)](https://lyz44git.github.io/ad-measurement-and-metrics/03.html#s03a)

**[03b · Sizing market-level (geo) experiments](03b_geo_experiment_design)**

[![Smallest detectable effect of a market-level test by number of markets and by test length, for three designs; and the false-alarm rate of a volume-weighted estimate under a standard t-test and under a randomization test](03b_geo_experiment_design/out/fig1_mde_by_metros.png)](https://lyz44git.github.io/ad-measurement-and-metrics/03.html#s03b)

**[03c · Hierarchical forecasts of a marketplace metric that add up across levels](03c_hierarchical_forecasting)**

[![Gap between a forecast and the sum of the forecasts one level below it, 3.5% to 5.2% when forecast separately and zero after reconciliation; and forecast error relative to assuming no change, by months ahead, at four geographic levels, for separate forecasts and two ways of reconciling them](03c_hierarchical_forecasting/reports/figures/relative_rmsse_by_horizon_inventory_ets.png)](https://lyz44git.github.io/ad-measurement-and-metrics/03.html#s03c)

Method, data, decision rules and limitations are in each study's README; the four questions are introduced in
the [main README](../README.md).
