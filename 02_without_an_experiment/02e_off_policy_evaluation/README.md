# 02e · What is a targeting policy worth before it has run?

**[Explore this study interactively →](https://lyz44git.github.io/ad-measurement-and-metrics/02.html#s02e)**

> **Takeaway.** On average, a biased log gives the right answer; a single log gives it only roughly. On 200 logs
> that favor likely visitors, inverse probability weighting (IPS) with the logged probability of assignment is within
> 3% of a feature-adjusted benchmark from the experiment for each of four targeting policies, and the doubly robust
> estimator (DR) with an estimated probability within 6%; the 95% intervals of both cover the benchmark in 94% to 97%
> of logs. One log of about 108,000 rows is off by 22% to 53% on average, so the accuracy rules of the plan, a mean
> absolute error below 10%, were not met. IPS with an estimated probability loses 67% to 83% of the lift, and an
> unweighted comparison gives 6 to 10 times the benchmark. A first design, which assumed that every user had the
> same chance of assignment, also missed its rule; why is part of the result.

## Question

A team wants to know how many extra visits a new rule for choosing which users may be shown ads would bring, but it
has only the log of the current rule, which favored users who were already likely to visit. In that log the outcome
under the new rule is never observed for the users the two rules treat differently. How close do off-policy
estimates computed from such a log come to the value the randomized experiment gives for the same rule?
[Study 02a](../02a_attribution_metric_validation) checks a count of past conversions against the experiment; this
study checks an estimate of what a rule that has not run would bring.

## Data

Criteo Uplift Prediction Dataset v2.1, the experiment of [study 01a](../../01_with_an_experiment/01a_ad_incrementality):
13,979,592 rows, outcome `visit`. A random 30% of rows (4,192,415) fits the policies' models and an assignment
model, 35% (4,894,241; the log part) is the source of the logs and of the benchmark, and 35% (4,892,936) replicates
the benchmark. Pass the path to `criteo-research-uplift-v2.1.csv.gz`.

## Method

The plan of this design, [`design/analysis_plan_v2.md`](design/analysis_plan_v2.md), was fixed after the first design
and its follow-ups, whose results were known, and before this design ran (SHA-256 in `logs/plan_v2_hash.txt`). The
plan calls the benchmark "the truth".

1. **Policies.** Assign to ads: every user; a fixed random 20%; the top 20% by a response model P(visit | X); the top
   20% by a T-learner's predicted uplift. LightGBM, fitted on the model part.
2. **Assignment model.** In this pooled release the probability of assignment varies slightly with the features
   (held-out ROC AUC 0.509; between 0.83 and 0.90 for 98% of users). A LightGBM model r̂(x) of it is fitted on the
   model part.
3. **Benchmark.** The lift of each policy over assigning nobody, in extra visits per 1,000 users, by AIPW on the whole
   log part with r̂(x) and cross-fitted outcome models. It is an estimate from the experiment, not a known value. The
   logs are subsamples of the same rows, so the sampling error of the log part does not enter the comparison.
4. **Logs.** Rejection sampling from the experiment (Gentzel, Pruthi and Jensen 2021): from 2,000,000 rows of the log
   part, keep a treated row with probability c · e(x) / r̂(x) and a control row with probability
   c · (1 − e(x)) / (1 − r̂(x)), with c = 0.054. If r̂(x) is the assignment probability, the probability of assignment
   among kept rows is e(x) = sigmoid(β · z(x)), clipped to [0.02, 0.98], where z is the standardized logit of the
   response model: likely visitors are more often assigned. About 108,000 rows per log. Two settings, β = 1
   (moderate) and β = 2 (strong), 200 logs each.
5. **Estimators.** An unweighted comparison of the rows whose logged assignment agrees with the policy with the rows
   assigned to no ads (the "naive" estimator of the result files); the direct method (DM, outcome models only); IPS
   and DR with the logged e(x); IPS, self-normalized IPS (SNIPS) and DR (Dudík, Langford and Li 2011) with a
   propensity model fitted on the log. Outcome and propensity models are LightGBM with 300 trees, cross-fitted in two
   folds. 95% normal intervals from per-row contributions.
6. **Decision rules (moderate setting).** (1) IPS with the logged propensity, a check of the construction, and
   (2) DR with an estimated propensity, the primary rule, each have a mean absolute error below 10% of the benchmark
   and coverage of at least 90% for each of the four policies. The run compared the absolute value of the *mean*
   error with 10%, which is a different quantity. The rules are read here as written, and both quantities are
   reported ([`design/erratum.md`](design/erratum.md)).

## Results

Sources: [`out/ope_v2.json`](out/ope_v2.json); [`out/ope_v2_accuracy.json`](out/ope_v2_accuracy.json) for the errors
of single logs; every estimate of every log is in [`out/ope_v2_logs.csv`](out/ope_v2_logs.csv).

**Benchmark** (extra visits per 1,000 users):

| Policy | AIPW with r̂, log part (benchmark, SE) | Same, other part | AIPW with the constant 0.85 | IPS with r̂ | Unadjusted |
|---|---|---|---|---|---|
| All users | 7.41 (0.22) | 7.41 | 7.41 | 7.45 | 10.48 |
| Response model 20% | 6.70 (0.21) | 6.62 | 6.70 | 6.75 | 9.83 |
| Uplift model 20% | 6.42 (0.18) | 6.29 | 6.42 | 6.47 | 9.59 |
| Random 20% | 1.41 (0.10) | 1.34 | 1.46 | 1.38 | 2.04 |

The three adjusted estimates agree within 0.05 visits per 1,000 for every policy but one, and the benchmark is close
on the other part. The unadjusted comparison is 42% to 49% higher: in this release a slightly uneven assignment share
among the most likely visitors moves it, as study 01a's gap between its unadjusted and adjusted effects (1.03 against
0.77 points) also shows.

**Moderate setting.** In each cell, the mean error over 200 logs and the mean absolute error of one log, as shares
of the benchmark; coverage of the 95% intervals over the four policies:

| Estimator | All users | Response 20% | Uplift 20% | Random 20% | Coverage |
|---|---|---|---|---|---|
| Unweighted comparison | +901% / 901% | +682% / 682% | +534% / 534% | +902% / 902% |  |
| Direct method | +50% / 50% | +48% / 49% | +37% / 37% | +56% / 57% |  |
| **IPS, logged propensity** | **0% / 22%** | **−1% / 24%** | **−2% / 22%** | **+3% / 53%** | **94.5% to 97.0%** |
| DR, logged propensity | 0% / 17% | −1% / 19% | −2% / 18% | +4% / 42% | 96.0% to 96.5% |
| **DR, estimated propensity** | **−4% / 23%** | **−5% / 25%** | **−6% / 22%** | **0% / 50%** | **94.0% to 96.5%** |
| SNIPS, estimated propensity | −65% / 65% | −69% / 69% | −55% / 56% | −63% / 76% |  |
| IPS, estimated propensity | −75% / 75% | −83% / 83% | −67% / 67% | −73% / 86% | 38.0% to 90.0% |

- **Neither pre-specified rule was met as written.** Coverage met its condition (94% to 97% for both estimators).
  The mean absolute error is 22% to 53% for IPS with the logged propensity and 22% to 50% for DR with an estimated
  one, above the 10% of the plan for every policy. What the run had checked, and what the first plan had named, is
  the mean error, which is within 3% and 6% ([`design/erratum.md`](design/erratum.md)).
- **On average the estimators are right, and their intervals say how far one log can be off.** The 95% interval of a
  single log is about ±55% of the benchmark for the three larger policies and wider than the benchmark for the
  random 20% policy, whose lift is 1.4 visits per 1,000. The lift per assigned user is small next to the visit rate,
  so about 108,000 rows do not pin it down. A team with one log would report the interval, not the point.
- **The logged probability is what keeps the average right.** With it, IPS needs no model. Without it, the mean of
  DR is still within 6%, while IPS and SNIPS with the same estimated propensity lose most of the lift and the direct
  method is 37% to 56% too high.
- **Why IPS with an estimated propensity fails.** Among untreated rows in the top decile of the logging propensity,
  the mean weight 1/(1 − ê) is 10.5 against 9.1 for 1/(1 − e), and 12.6 against 10.8 among those with a visit (first
  50 logs). The weight is convex in the propensity, so estimation error near 1 raises its mean even when ê is right
  on average. The untreated likely visitors are counted too often, the visit rate without ads is overstated, and the
  lift, a difference of two rates that are close, mostly disappears.
- **Ranking the three 20% policies** in the benchmark's order: the unweighted comparison in 100% and DM in 98.5% of
  logs, because they rank policies by how likely to visit the users they treat are, which happens to be the order
  here; IPS with the logged propensity in 64% and DR in 61%. The response and uplift policies are 0.28 visits per
  1,000 apart, about one standard error, so their order is close to a coin flip for an estimator that is right on
  average.

**Strong setting** (propensities from 0.09 to 0.98): the mean of IPS with the logged propensity stays within 16% of
the benchmark (coverage 95% to 98%) and that of DR with it within 16%; DR with an estimated propensity is 29% to 53%
below the benchmark (coverage 92% to 94%); IPS with an estimated propensity turns negative; DM is 88% to 123% above
and the unweighted comparison 6.9 to 12.8 times the benchmark. The stronger the bias of the log, the more the answer
depends on having recorded the probability.

[![Error and interval coverage of off-policy estimators, and the experiment's value with and without adjustment](out/fig_ope.png)](https://lyz44git.github.io/ad-measurement-and-metrics/02.html#s02e)

## How this design came about

The first design ([`design/analysis_plan.md`](design/analysis_plan.md); results in [`out/ope.json`](out/ope.json))
built the logs as if every user had been assigned with probability 0.85 and took the unadjusted lift as the
benchmark. Its rule, a mean bias of DR within 10% with 90% coverage, was not met: DR was 32% to 35% below that value.
Two follow-ups, each planned and hashed before it ran ([`design/followup_plan.md`](design/followup_plan.md),
[`design/followup_plan_2.md`](design/followup_plan_2.md); results in [`out/followup.json`](out/followup.json) and
[`out/followup2.json`](out/followup2.json)), found:

1. The propensity model was calibrated within 0.01 in every decile of the true propensity, and DR given the "known"
   propensity was as far off, so the propensity model was not the cause.
2. A model of assignment on the features has a held-out AUC of 0.509, and the feature-adjusted lift of every policy is
   28% to 32% below the unadjusted one. The constant 0.85 was therefore not the logging probability, and the
   unadjusted lift not the only candidate for the benchmark.
3. Against the adjusted value, the mean of the first design's DR was within 6%, with 95% to 97% coverage.

The second design was planned with these results in hand: the sampling scheme and the benchmark were changed after
it was known that DR was close to the adjusted value on average. It is a design chosen after a failure and a
diagnosis, not an independent confirmation.

In a sensitivity check on 20 logs, not committed, keeping identical rows in one cross-fitting fold gave the same
bias, so the file's duplicate rows (study 01c: 16% of rows have an exact twin) are an unlikely cause. One deviation
from the first plan, made on simulated data before the Criteo file was read, is in
[`design/deviations.md`](design/deviations.md): the nuisance models use 300 trees, not 100, because 100 left the
propensity model compressed toward 0.5.

## Reproduce

```bash
python code/run_ope_v2.py /path/to/criteo-research-uplift-v2.1.csv.gz out      # this design, about 25 minutes on 32 cores
python code/accuracy_from_logs.py out                                          # single-log errors and the rules as written, seconds
python code/run_ope.py /path/to/criteo-research-uplift-v2.1.csv.gz out         # first design, about 10 minutes
python code/run_followup.py /path/to/criteo-research-uplift-v2.1.csv.gz out    # first follow-up, about 20 minutes
python code/run_followup2.py /path/to/criteo-research-uplift-v2.1.csv.gz out   # second follow-up, about 6 minutes
```

`tests/` checks on simulated experiments that the policy value from the experiment recovers a known lift, that logs
have the intended propensity and the experiment's feature distribution, that IPS and DR recover the lift where the
unweighted comparison does not, that a propensity model with too few trees is compressed toward 0.5, that when the
assignment share varies with the features a constant-share benchmark is biased while AIPW with the true share and
logs built on it are not, and that a mean error near zero does not imply a small mean absolute error.

## Scope

- The logs are built from a randomized experiment, so every confounder is among the features; a real log need not
  have that property, and an estimated propensity is then likely to do worse, not better.
- The benchmark and the logs both rest on the estimated assignment probability r̂(x). The agreement of three adjusted
  estimates, their closeness on the other part and the small mean error of IPS with the logged propensity support
  it; none of them is a known population value.
- The accuracy figures are for logs of about 108,000 rows. A larger log narrows the error of a single log; it does
  not remove the bias of the estimators that have one.
- A policy here chooses who may be assigned to ads, not which ad or what bid; only 3.6% of the ad arm saw an ad, so the
  lift per assigned user is small next to the visit rate, which is what makes the propensity's errors costly.
- One display network; absolute visit rates are not population rates because of the data's subsampling.
