# Analysis plan: what is a targeting policy worth before it has run?

Written before any policy, log or estimator in this study was built.

Already known when this plan was written, from study 01a on the same file: assignment raised the visit rate from
3.82% to 4.85%; the assigned share is 85% and does not depend on the features (held-out AUC 0.51); ranking users by a
response model P(visit | X) captured as many incremental visits as ranking by a T-learner (top fifth: 76% and 75%).
Not yet computed: any log, policy value or estimator in this plan.

## Question

A team wants to know how many extra visits a new rule for choosing which users may be shown ads would bring, but it
has only the log of the current rule, which favored users who were already likely to visit. In that log the
outcome under the new rule is never observed for the users the two rules treat differently. How close do
off-policy estimates computed from such a log come to the value the randomized experiment gives for the same rule?

## Data and splits

Criteo Uplift Prediction Dataset v2.1, all 13,979,592 rows, features f0 to f11, outcome `visit` (conversions are too
rare in logs of this size; see the scope). Seed 20261125. A uniform random draw splits rows into three parts:

- **Model part (30%).** Fits the policies' scoring models. Nothing else.
- **Truth part (35%).** The randomized experiment, used only to compute the true value of each policy.
- **Log part (35%).** Source of the logs on which the off-policy estimators run.

## Policies (fixed before any log is drawn)

A policy decides, for each user, whether the user is assigned to ads (A = 1) or not (A = 0).

1. **All:** every user.
2. **Random 20%:** a fixed random fifth of users (a hash of the row number).
3. **Response 20%:** users in the top fifth of a LightGBM model of P(visit | X) fitted on the model part.
4. **Uplift 20%:** users in the top fifth of a T-learner (two LightGBM models, one per arm) fitted on the model part.

Thresholds are the 80th percentiles of the scores on the model part. LightGBM settings are those of study 01a.

**Estimand.** The policy lift Δ(π) = V(π) − V(none): extra visits per 1,000 users compared with assigning nobody.

**Truth.** Δ(π) on the truth part by inverse probability weighting with the known assignment probability 0.85,
which is unbiased because assignment was random. Its standard error is reported alongside.

## Logs

Each log imitates a logging rule that favors likely visitors. Draw m = 1,000,000 rows from the log part without
replacement. For each row compute z(x), the standardized logit of the response model's score, and the logging
propensity e(x) = clip(sigmoid(β · z(x)), 0.02, 0.98). Keep a treated row with probability 0.15 · e(x) / 0.85 and a
control row with probability 0.15 · (1 − e(x)) / 0.15. In the kept rows, P(A = 1 | x) = e(x) and the distribution of
x is that of the log part (rejection sampling from a randomized experiment). Each log has about 150,000 rows.

Two settings: **moderate** (β = 1) and **strong** (β = 2). 200 logs per setting.

## Estimators (on each log)

Nuisance models are fitted on the log with 2-fold cross-fitting: an outcome model μ_a(x) = P(visit | A = a, x) per arm
and a propensity model ê(x), all LightGBM with 100 trees and otherwise the settings above; ê is clipped to
[0.01, 0.99]. For each policy, the value of π and of "none" are estimated and differenced.

1. **Naive.** Visit rate among logged users whose logged action agrees with the policy, minus the same for "none".
2. **Direct method (DM).** Mean of μ_π(x)(x).
3. **IPS, known propensity.** Mean of 1{A = π(x)} · visit / e_π(x).
4. **IPS, estimated propensity.** As 3 with ê.
5. **Self-normalized IPS, estimated propensity (SNIPS).**
6. **Doubly robust, estimated propensity (DR, primary).** Mean of μ_π(x)(x) + 1{A = π(x)} · (visit − μ_π(x)(x)) / ê_π(x).

Intervals for 3, 4 and 6: 95% normal intervals from the per-row contributions to the difference (influence-function
standard errors, nuisance models treated as fixed). DM, naive and SNIPS are scored on bias and error only.

## Metrics, per setting, policy and estimator

Mean bias and root mean squared error over the 200 logs, relative to the truth and as a share of the true lift;
coverage of the 95% intervals; and, for the three 20% policies, the share of logs in which each estimator ranks
them in the same order as the truth.

## Decision rule

Off-policy evaluation recovers policy value from a biased log here if, in the **moderate** setting, DR has mean
absolute bias below 10% of the true lift and interval coverage of at least 90% for each of the four policies. The
naive comparison is reported against the same standard. The strong setting is reported whatever it shows.

## What this cannot show

The logs are built from a randomized experiment, so the propensity model is correctly specifiable from the same
features and there is no unmeasured confounding; real logs need not have either property. A policy here chooses who
may be assigned to ads, not which ad or what bid; the experiment's exposure share (3.6% of the ad arm) is taken as
given. One display network; absolute visit rates are not population rates because of the data's subsampling.
