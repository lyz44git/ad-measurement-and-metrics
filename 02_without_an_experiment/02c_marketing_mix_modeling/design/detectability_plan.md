# Plan: can the reliability of a marketing mix model be predicted before it is fitted?

Written 2026-11-16. SHA-256 saved to `logs/detectability_plan_hash.txt` first.

## What had been seen when this was written

The weekly results of `design/followup_plan.md` (pooled and per-brand recovery, both simulations). An exploratory
look at the weekly simulation with brand-specific shapes showed that the error of a per-brand estimate fell with a
signal-to-noise index computed from the spend series alone (rank correlation -0.69 over 68 brand-channels; median
absolute relative error 0.59 where the index was below 2 and 0.18 where it was 2 or more). That look suggested the
index and the threshold of 2 used below.

Not seen: any result of the daily simulations (the daily run of `code/run_pooled.py` had not finished), and the
weekly simulation with common shapes split by the index. These are the test sets.

## Question

A marketing mix model learns a channel's return from the part of its spend that moves independently of trend,
season and the other channel. Can a number computed before fitting tell which brand-channels have enough of that
movement for their return to be recovered?

## Index

For brand b, channel c, with n training periods:

    index = sqrt(n) x SD(part of the channel's revenue contribution not explained by the baseline terms and the
            other channel's contribution) / SD(noise)

- Baseline terms: the model's trend, seasonal and day-of-week terms.
- Noise SD: residual SD of an OLS regression of revenue on the baseline terms.
- "Not explained by": residual of an OLS regression on an intercept, the baseline terms and the other channel's
  contribution.

It is the t-statistic the channel's effect would have if its carry-over and saturation shape were known, so an index
below 2 means the effect cannot be told from zero even in that best case. In a simulation the contribution is the
planted one. On real data, where it is unknown, the same formula gives the smallest ROAS detectable with 80% power in
a two-sided 5% test for an assumed shape (adstock decay 0.5, Hill h 0.5, k 1): 2.80 x noise SD / (sqrt(n) x SD of the
independent part of the contribution per unit of ROAS).

## Tests

Per-brand estimates from `out/mmm_pooled_recovery*.csv`, brand-channels with a converged per-brand fit. Error =
absolute relative error of the estimated ROAS.

- T1 (primary): daily data, simulation with brand-specific shapes.
- T2: daily data, simulation with common shapes.
- T3: weekly data, simulation with common shapes.

## Predictions and decision rule

For each test:

- P1. The rank correlation between the index and the error is negative, with a 95% bootstrap interval (brands
  resampled, 2,000 draws) below 0.
- P2. Brand-channels with an index of 2 or more have a median error below 25% and below the median error of those
  with an index under 2.

The index is said to predict reliability if P1 and P2 hold in T1. T2 and T3 are reported in the same way. The pooled
model's estimates are scored against the same index and reported, without a rule.

## Also reported

On real spend and revenue, at each frequency: the distribution across brand-channels of the smallest detectable
ROAS, and the share for which it is at most 1, 2 and 4.

## Limits stated in advance

The index uses the true contribution in a simulation, which an analyst never has; on real data it rests on an assumed
shape. It ignores the uncertainty in carry-over and saturation, so it is an upper bound on what the model can learn.
The tests are simulations on real spend and do not show that real returns have the assumed form.
