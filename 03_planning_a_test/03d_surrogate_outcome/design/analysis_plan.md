# Analysis plan: can the effect on visits stand in for the effect on conversions?

Written before any model in this study was fitted and before any estimate below was computed.

Already known when this plan was written, from studies 01a and 01c on the same file: assignment to the ad arm raised
the visit rate from 3.82% to 4.85% and the conversion rate from 0.19% to 0.31% (full sample, unadjusted); no row has a
conversion without a visit; a conversion endpoint needs about 20 times the users of a visit endpoint for the same
relative lift. Not yet computed: any surrogate model, any estimate in this plan, any split used here.

## Question

Conversions are the outcome an advertiser pays for, but they are rare: a test powered for conversions must be about 20
times larger than one powered for visits. If the effect on conversions could be read from the effect on visits, a
test could be much smaller. How close does a visit-based estimate come to the conversion effect measured directly in
the same experiment, and at what test size is the biased but precise estimate preferable to the unbiased but noisy
one?

## Data

Criteo Uplift Prediction Dataset v2.1, all 13,979,592 rows, features f0 to f11, flags `treatment`, `visit`,
`conversion`. Rows are users as released (study 01c: 16% of rows duplicate another row; counts are counts of rows).
Seed 20261124. A uniform random draw splits rows 50/50 into a **historical** half, used only to fit the surrogate
models, and an **experiment** half, on which every effect below is estimated.

## Estimators of the effect of assignment on the conversion rate (experiment half)

1. **Direct.** Difference in conversion rates between arms.
2. **Visit effect times a fixed conversion rate.** Difference in visit rates between arms, multiplied by the
   conversion rate among visitors of the control arm of the historical half.
3. **Surrogate index (primary).** S = visit × q(X), where q(X) is a LightGBM model of P(conversion | visit = 1, X)
   fitted on the visitors of the control arm of the historical half, the data a team would have before running ads
   to the new arm. The estimate is the difference in mean S between arms.
4. **Surrogate index, both arms (sensitivity).** As 3, with q(X) fitted on visitors of both arms of the historical
   half. Reported as a sensitivity check; it uses treated conversions, which a team would not have in advance.

LightGBM settings are those of study 01a (200 trees, learning rate 0.05, 63 leaves, at least 200 rows per leaf,
row subsample 0.5, column subsample 0.8), with the binary objective.

Intervals: 95% percentile intervals from 200 Poisson bootstrap draws of experiment rows, with the fitted q(X) held
fixed. The uncertainty of q(X) itself is not propagated; this is stated with the results.

## Decomposition

Direct minus surrogate index is the part of the conversion effect that does not come from extra visits converting at
the rate predicted for visitors of that kind without ads. Also reported: the conversion rate among visitors in each
arm of the experiment half, and the mean q(X) among visitors in each arm.

## Test size

For n users per arm with equal arms, the error of each estimator against the direct estimate on the full experiment
half is computed two ways:

- **Formula.** Root mean squared error = sqrt(bias² + SE(n)²), with the bias of the surrogate index taken from the
  full experiment half (zero for the direct estimator) and SE(n) from the per-arm variances of conversion and of S.
- **Resampling check.** For n = 10,000, 30,000, 100,000 and 300,000 users per arm, 500 draws of n users from each arm
  without replacement; root mean squared error of each estimator against the full-half direct estimate.

The crossover n* is the size per arm at which the two formula curves meet.

## Segments (descriptive)

Ten segments by decile of a LightGBM model of P(visit | X) fitted on the control arm of the historical half. For each:
direct and surrogate-index effects with bootstrap intervals and their ratio. No decision rests on this table.

## Decision rule

Visits stand in for conversions if the 90% bootstrap interval of (surrogate index − direct) / direct lies inside
[−0.20, 0.20] (an equivalence margin of 20%). Whatever the result, n* and the resampling check are reported.

## What this cannot show

One experiment on one display network, pooled and non-uniformly subsampled by the data's authors, so the size of
the gap is specific to these data. A conversion here is any conversion in the logging window, not a long-run outcome;
what transfers is the check itself: comparing a proxy effect with the outcome effect in an experiment where both
are measured.
