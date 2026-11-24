# Analysis plan, third design: logs large enough for the question, and a rule stated in one quantity

Written after the first two designs, their follow-ups and the erratum were run and seen (`out/ope.json`,
`out/followup.json`, `out/followup2.json`, `out/ope_v2.json`, `out/ope_v2_accuracy.json`), after the design
calculation below, and before any log of this design was drawn.

## Why a third design

The second design had three faults, none of them in the estimators.

1. **Its logs were too small for its rule.** A log kept 5.4% of 2,000,000 candidate rows, about 108,000. At that size
   the standard error of inverse probability weighting is about a quarter of the policy lift, so one log could not
   be within 10% of the benchmark whatever the estimator did. No calculation of the attainable precision was made
   before the rule was written. The keep rate was that low because the experiment assigns only 15% of users to
   control and a few rows have an extreme estimated assignment probability, which caps the keep constant.
2. **Its "moderate" logging policy was not moderate.** The naive comparison on those logs overstated the lift about
   tenfold, so a small error in an estimated propensity left a large share of the bias in place.
3. **Its rule was worded as one quantity and coded as another** (`design/erratum.md`).

## Design calculation (run before this plan; `code/design_calc_v3.py`, `out/design_calc_v3.json`)

On the pool the logs are drawn from, and without drawing any log, the calculation gives the keep constant, the
expected rows of a log, the error built into the naive comparison, and the standard error that inverse probability
weighting with the logged propensity would have on one log (from the variance of its per-row term under the log's
distribution). The mean absolute error is sqrt(2/π) times that standard error. Shares are of the policy's lift by
inverse probability weighting on the pool.

| Setting | β | Rows in a log | Naive comparison overstates by | Predicted mean absolute error of IPS, one log: all / response 20% / uplift 20% / random 20% |
|---|---|---|---|---|
| Mild | 0.1 | 1,552,000 | 87% to 148% | 4.1% / 4.4% / 3.9% / 10.2% |
| Moderate | 0.25 | 1,649,000 | 211% to 358% | 4.1% / 4.4% / 3.9% / 10.2% |
| Strong (the β of the second design's "moderate") | 1.0 | 1,358,000 | 580% to 1,037% | 7.1% / 7.9% / 7.0% / 18.0% |

## Data, parts and policies

Seed 20261125. Model part 30% (the same rows as before); the other 70% is the **pool**. The four policies and the
assignment model r̂(x) are those of the second design, fitted on the model part. Rows of the pool whose r̂ lies
outside its 0.5th to 99.5th percentile (0.828 to 0.915) are dropped, which leaves 9,689,305 rows. The policy values
are defined on this trimmed pool.

## Benchmark

The policy lift, in extra visits per 1,000 users, by AIPW on the whole trimmed pool: outcome models cross-fitted in
two folds (LightGBM, 300 trees), assignment probability r̂(x). It is a feature-adjusted experimental estimate, not a
known population value. Also reported: IPS with r̂ and the unadjusted comparison on the pool.

## Logs

Logging propensity e(x) = clip(sigmoid(β · z(x)), 0.02, 0.98), z the standardized logit of the response score, as
before. Every row of the pool is kept independently, a treated row with probability c · e(x) / r̂(x) and a control
row with probability c · (1 − e(x)) / (1 − r̂(x)), c being the largest value, rounded down to two significant
digits, for which no keep probability exceeds 1 in that setting. If r̂ is the assignment probability, P(A = 1 | x)
= e(x) among kept rows. 200 logs in the moderate setting, 100 in each of the other two. Seeds: 20261125 + 30000 +
1000 × (setting index) + k.

## Estimators

As in the second design: naive comparison, direct method, IPS with the logged e, IPS with an estimated propensity,
SNIPS, DR with an estimated propensity, DR with the logged e. Nuisance models: LightGBM, 300 trees, two-fold
cross-fitting on the log. Intervals: estimate ± 1.96 standard errors of the per-row term.

## Metrics

Per setting, policy and estimator: mean error (the error of the average estimate), **mean absolute error** (the
average size of one log's error) and median absolute error, each as a share of the benchmark; coverage of the 95%
intervals; and the share of logs that rank the three 20% policies in the benchmark's order.

## Decision rules (moderate setting)

For each of the three policies **all users, response 20% and uplift 20%**:

1. **With the logged propensity:** IPS has a mean absolute error below 10% of the benchmark and interval coverage of
   at least 90%.
2. **Without it (primary):** DR with an estimated propensity meets the same two conditions.

`code/run_ope_v3.py` computes both with `ope_core.accuracy` and `ope_core.rule_as_written`, the functions written
for the erratum, so the code compares the quantity this text names.

The random 20% policy is reported and is not part of the rules: its lift is a fifth of the others by construction
and the design calculation puts its attainable error at 10.2%, at the threshold itself. The mild and strong settings
and every other estimator are reported whatever they show.

## What is known and what is not

Known before this plan: all results of the first two designs, and the design calculation above. The calculation
predicts the error of IPS with the logged propensity; it says nothing about DR with an estimated propensity, whose
bias in the second design was 4% to 6% under a logging policy as strong as this design's strong setting.

The logs of this design are drawn from the same experiment as before, so this is a new design on data already
seen, not an independent replication.

## What this cannot show

r̂(x) is itself estimated; if it is wrong, the logs' propensity differs from e(x) and the benchmark carries the
error. Each log holds 14% to 17% of the pool, so logs overlap and the pool's own sampling error is not part of the
comparison. Every confounder is among the features by construction, which a real log need not satisfy.
