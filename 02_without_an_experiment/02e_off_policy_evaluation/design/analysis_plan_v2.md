# Analysis plan, second design: logs whose propensity is known

Written after the first design and its two follow-ups were run and seen (`out/ope.json`, `out/followup.json`,
`out/followup2.json`), and before anything below was run.

## Why a second design

The first design built each log from the experiment as if every user had been assigned to ads with probability
0.85. The second follow-up found that the assignment probability varies slightly with the features in this pooled
release (held-out AUC 0.509; estimated probability 0.83 to 0.90 between the 1st and 99th percentiles), and that the
unadjusted and feature-adjusted lifts of each policy differ by 28% to 32%. Two consequences: the "known" logging
propensity of the first design was not exactly the true one, and the truth was not uniquely defined. This design
removes both by building the logs and the truth on the same estimated assignment probability.

Known before this plan: every result of the first design and its follow-ups, including that DR came within 6% of the
feature-adjusted lift and that IPS with an estimated propensity lost most of the lift.

## Data, parts and policies

As in the first design (seed 20261125): model part 30%, truth part 35%, log part 35%; the same four policies (all
users, random 20%, response 20%, uplift 20%) fitted on the model part.

**Assignment model.** r̂(x) = P(A = 1 | x), LightGBM (300 trees, otherwise the settings of the first design) fitted on
the model part and applied to the other two parts.

## Truth

The policy lift Δ(π), in extra visits per 1,000 users, by AIPW on the **whole log part**, the population the logs are
drawn from: outcome models μ_a(x) cross-fitted in two folds (LightGBM, 300 trees), assignment probability r̂(x).
Because the logs are subsamples of the same rows, the sampling error of the log part is shared and does not enter
the comparison. Also reported: the same AIPW on the truth part (an out-of-sample replication), and on the log part
IPS with r̂(x) and AIPW with the constant 0.85.

## Logs

From the log part, draw m = 2,000,000 rows without replacement. Logging propensity e(x) = clip(sigmoid(β · z(x)),
0.02, 0.98) as before, with β = 1 (moderate) and β = 2 (strong). Keep a treated row with probability c · e(x) / r̂(x)
and a control row with probability c · (1 − e(x)) / (1 − r̂(x)). Then, if r̂ is the true assignment probability,
P(A = 1 | x) = e(x) among kept rows and the features keep their distribution. c is the largest value, rounded down
to two significant digits, for which no keep probability on the log part exceeds 1 in either setting. 200 logs per
setting.

## Estimators

As in the first design, with the nuisance models of its deviation 1 (300 trees, two-fold cross-fitting): naive
comparison, direct method, IPS with the known e, IPS with an estimated propensity, SNIPS, and DR with an estimated
propensity. Added: **DR with the known e**. Intervals as before.

## Metrics

Per setting, policy and estimator: mean error and root mean squared error as shares of the truth, coverage of the
95% intervals, and for the three 20% policies the share of logs that rank them in the true order. Among untreated
rows in the top decile of e, the mean of 1/(1 − e) and of 1/(1 − ê), over the first 50 moderate logs.

## Decision rules (moderate setting)

1. **The log's propensity is known** (a check of the construction): IPS with the known e has mean absolute error
   below 10% of the truth and coverage of at least 90% for each of the four policies.
2. **Off-policy evaluation recovers policy value without the logged propensity** (primary): DR with an estimated
   propensity meets the same two conditions for each of the four policies.

The strong setting and every other estimator are reported whatever they show.

## What this cannot show

r̂(x) is itself estimated. If it is wrong, the logs' propensity differs from e(x) and the truth carries the error;
the two-part replication of the truth and rule 1 are the checks. Every confounder is among the features by
construction, which a real log need not satisfy.
