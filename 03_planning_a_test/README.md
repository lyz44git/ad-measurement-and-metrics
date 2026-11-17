# 3. Planning a test: how large must it be?

The two studies size an experiment by user (03a) and by market (03b). In both, adjusting for what is known before
the test is the main way to make it smaller.

| Study | Question | Key result |
|---|---|---|
| [`03a_lift_study_sizing`](03a_lift_study_sizing) | How many users per arm does a lift study need, and how much does covariate adjustment save? | An unadjusted readout needs about 6,500 users per arm to detect a one-point lift on a 3.8% base rate with 80% power (19% power at 1,000 per arm, 94% at 10,000). Adjusting for a model prediction built from pre-treatment features cut the sampling variance by 31% and the required sample to about 4,400, with false-positive rates near 5%. |
| [`03b_geo_experiment_design`](03b_geo_experiment_design) | If a change can only be randomized by market, how large a test is needed, and does the usual t-test keep its 5% false-positive rate? | Across 5,000 placebo tests per design on 151 U.S. metros, adjusting for pre-period volume lowered the smallest detectable change in a two-month, 100-metro test from 9.5% to 6.7%. For the volume-weighted estimate the t-test rejected a true null 5.7-9.1% of the time; randomization inference brought it back to about 5%. |

## Main figure of each study

**[03a · Sizing user-level lift studies, with and without covariate adjustment](03a_lift_study_sizing)**

![Minimum detectable lift and sampling variance of adjusted and unadjusted readouts](03a_lift_study_sizing/out/fig_mde_by_adjustment.png)

**[03b · Sizing market-level (geo) experiments](03b_geo_experiment_design)**

![Minimum detectable effect by number of metros](03b_geo_experiment_design/out/fig1_mde_by_metros.png)

Method, data, decision rules and limitations are in each study's README; the four questions are introduced in
the [main README](../README.md).
