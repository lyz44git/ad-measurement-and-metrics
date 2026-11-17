# Analysis plan: does the attribution rule change what a bidder buys?

Written before any model in this study was fitted and before any bidder outcome was computed.

Already known when this plan was written: the results of study 02b on the same data (credit shares by rule, a
time-decay half-life of 7.9 days, 82% of the touches of multi-touch conversions get no credit under last touch), and
the distribution of the logged price `cost` (median 7.6e-05, 13% of impressions at the floor of 1e-05, 99th percentile
3.5e-03). Not yet computed: any value model, any set of impressions a bidder would buy, any metric below.

## Question

A bidder values an impression by the conversion credit it expects the impression to earn. If the credit rule changes
from last touch to time decay, how different are the impressions it buys, and how much of the other rule's credit does
it give up?

## Data

Criteo Attribution Modeling for Bidding dataset: 16,468,027 logged display impressions of 6,142,256 users over 30
days, with the price paid for each impression (`cost`). Criteo released `cost` and the cost-per-order `cpo` in a
transformed form, so money amounts and profit are not interpretable; `cpo` is not used. Only impressions that were
bought are in the log. Read from a local `derived/` folder (read only).

## Definitions

- **Paths, split and credits** are those of study 02b (`build_paths`, `rule_credits`, `decay_rate` in its
  `code/mta.py`): a converting user's path is their impressions up to the first conversion; users are split 70/30
  into train and test by a hash of the user id; the time-decay rate is the maximum-likelihood exponential rate of
  touch-to-conversion delays among training converters. Under each rule the credits of a converting path sum to 1.
  Impressions of users who do not convert have credit 0. Last-touch credit: 1 for the last impression of a converting
  path. Time-decay credit: proportional to exp(-rate x days to conversion).
- **Features known before the impression is bought:** campaign (categorical), seconds since the user's last click
  (missing if none), number of earlier impressions of the user in the log, number of those that were clicked, seconds
  since the user's previous impression (missing for the first), and hour of day. Whether the impression itself was
  clicked is not used.
- **Value models:** two LightGBM models with the same settings (cross-entropy objective, 300 trees, learning rate
  0.05, 63 leaves, at least 200 rows per leaf, seed 20261117), one trained on last-touch credit and one on time-decay
  credit, on the impressions of training users.
- **Bidders:** on the impressions of test users, a bidder buys in decreasing order of predicted credit per unit of
  `cost` until its spend reaches a share B of the total logged cost of those impressions, for B = 25%, 50% and 75%.
  This is what a bidder whose bids are proportional to predicted value would win at the logged prices. The last-touch
  bidder uses the first model, the time-decay bidder the second.

## Metrics, at each budget

1. Captured credit: the share of all test credit under rule r that sits on the impressions a bidder buys, for both
   rules and both bidders. A random purchase captures B.
2. Cross-rule loss under rule r: 1 - (credit under r captured by the other rule's bidder) / (credit under r captured by
   rule r's own bidder).
3. Spend overlap: logged cost of impressions bought by both bidders, over the budget.
4. Composition of each bidder's spend: share on impressions within 24 hours of the user's last click, on impressions
   of users with no earlier click, and on a user's first logged impression.

Intervals: 95% percentile intervals from 500 bootstrap draws of test users (Poisson weights), with each bidder's
purchase set held fixed.

## Decision rule

The attribution rule matters for what a bidder buys if, at the 50% budget, the cross-rule loss is at least 5% under
both rules and the lower end of its 95% interval is above 0 under both. Results at 25% and 75% are reported whatever
they show.

## What this cannot show

No experiment is available in these data, so nothing here says which bidder would cause more conversions. Purchases
are replayed on impressions that the logging policy won; a bidder cannot buy impressions that were not logged, and
buying fewer impressions is assumed not to change later user behavior.
