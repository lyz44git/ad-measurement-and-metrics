# 02d · Does the attribution rule change what a bidder buys?

> **Takeaway.** Hardly, in this log. Two bidders that value impressions by last-touch and by time-decay credit buy
> nearly the same impressions: at half the logged budget they share 90% of their spend, and a bidder trained on one
> rule gives up at most 2.2% of the other rule's credit. The pre-specified threshold of 5% was not met. The rule
> changes who gets the credit ([study 02b](../02b_multi_touch_attribution)) far more than it changes what gets bought.
> What does move is the marginal spend: the time-decay bidder buys fewer impressions shortly after a click and more
> from users who have not clicked before.

## Question

A bidder values an impression by the conversion credit it expects the impression to earn. If the credit rule changes
from last touch to time decay, how different are the impressions it buys, and how much of the other rule's credit does
it give up?

## Data

Criteo Attribution Modeling for Bidding dataset, the data of [study 02b](../02b_multi_touch_attribution):
16,468,027 logged display impressions with the price paid for each (`cost`). After removing impressions that follow a
user's first conversion, as in study 02b, 15,498,865 impressions remain: 10,854,116 of training users
and 4,644,749 of 1,842,430 test users, who have 98,387 conversions. Criteo released `cost`
in a transformed form, so money amounts are not interpretable and profit is not computed. Pass the path to the
`criteo_attr.parquet` file written by study 02b's `code/load_attribution.py`.

## Method

The analysis plan, [`design/analysis_plan.md`](design/analysis_plan.md), was fixed before any model was fitted
(SHA-256 in `logs/plan_hash.txt`). The results of study 02b and the distribution of `cost` were known; no bidder
outcome had been computed.

1. **Credit.** Paths, the 70/30 user split and the two rules are those of study 02b. Last touch gives the last
   impression of a converting path a credit of 1; time decay spreads it in proportion to exp(−rate × days to
   conversion), with a half-life of 7.9 days estimated on training converters.
2. **Value models.** Two LightGBM models with the same settings, one per rule, predict the credit of an impression
   from what is known before it is bought: campaign, time since the user's last click, earlier impressions and clicks
   of the user, time since the previous impression, and hour of day.
3. **Bidders.** On the impressions of test users, each bidder buys in decreasing order of predicted credit per unit of
   cost until it has spent 25%, 50% or 75% of the logged cost. This is what a bidder whose bids are proportional to
   predicted value would win at the logged prices.
4. **Comparison.** Credit captured under each rule, the loss from bidding with the other rule's model, the overlap of
   the two bidders' spend, and where the spend goes. Intervals come from 500 bootstrap draws of test users.
5. **Decision rule.** The rule matters for what a bidder buys if, at the 50% budget, the cross-rule loss is at least
   5% under both rules with the lower end of both 95% intervals above 0.

## Results

Source: [`out/bidding.json`](out/bidding.json). Both value models are calibrated on the test users (predicted over
realized credit 0.999 and 0.999).

| Budget | Spend overlap | Last-touch credit captured: last-touch bidder / time-decay bidder | Time-decay credit captured: time-decay bidder / last-touch bidder | Loss under last touch (95% CI) | Loss under time decay (95% CI) |
|---|---|---|---|---|---|
| 25% | 85.5% | 72.2% / 71.4% | 74.5% / 72.2% | 1.2% (0.9 to 1.4) | 3.1% (3.0 to 3.3) |
| 50% | 90.4% | 88.4% / 88.6% | 90.7% / 88.8% | −0.2% (−0.4 to −0.1) | 2.2% (2.1 to 2.3) |
| 75% | 94.9% | 96.6% / 96.9% | 97.8% / 96.8% | −0.2% (−0.3 to −0.2) | 1.0% (0.9 to 1.0) |

Where the spend goes at the 50% budget:

| Share of spend on | Last-touch bidder | Time-decay bidder | All logged spend |
|---|---|---|---|
| Impressions within 24 hours of the user's last click | 24.9% | 19.9% | 36.4% |
| Impressions of users with no earlier click | 36.4% | 41.9% | 29.7% |
| A user's first logged impression | 27.2% | 34.0% | 23.8% |

- **The pre-specified rule was not met.** At the 50% budget the loss is 2.2% under time decay and
  −0.2% under last touch: the time-decay bidder captures slightly more last-touch credit than the last-touch
  bidder itself. The largest loss at any budget is 3.1%.
- **The two bidders buy mostly the same impressions:** 85% of spend in common at a quarter of the budget, 90% at
  half, 95% at three quarters.
- **The difference is at the margin.** The time-decay bidder puts 20% of its spend on impressions within a day of
  a click, against 25% for the last-touch bidder, and 42% against 36% on users with no earlier click.
- **Under either rule, half of the logged spend buys about nine tenths of the credit** (88% and 91%), against
  50% for a random purchase. The logged spend is concentrated on impressions shortly after a click (36%), which
  both bidders buy less of.

## Reproduce

```bash
python code/run_bidding.py /path/to/derived/criteo_attr.parquet out    # about 2 minutes on 24 cores, 20 GB of memory
```

`tests/` checks on simulated logs that credits sum to one per converting path, that no feature of an impression uses
anything that happens at or after it, that the purchase takes the best value per cost within the budget, and the
comparison metrics on a case with a known answer.

## Scope

- No experiment is available in these data, so nothing here says which bidder would cause more conversions; both
  rules split credit and neither is validated.
- A replay on logged impressions: a bidder can only buy impressions that the logging policy won, at the logged
  price, and buying fewer impressions is assumed not to change what users do later.
- `cost` is a transformed price. Shares of spend are meaningful only if the transformation preserves ratios, which
  the dataset's documentation does not state.
- One display network and 30 days; 0.7% of conversions touch more than one campaign, so this is bidding within a
  campaign's own impressions, not across channels.
