# Follow-up plan 3: campaign-level calibration, and a ranker with a corrected level

Written after the third design was run and seen (`out/delay_v3.json`), after the model-free check below, and before
anything below was fitted. The third design's results and its rule that was not met stay as they are.

## Questions

1. **By campaign.** The third design pooled all campaigns. An advertiser reads the conversions and the cost per
   conversion of its own campaign, and campaigns differ in how long their conversions take. How far off is each
   campaign's forecast, with and without the delay model?
2. **A ranker with a corrected level.** The delayed-feedback network fixed the level of the forecast but ranked
   slightly less well than the network trained on the labels seen (ROC AUC 0.791 against 0.793), and the two had the
   same log loss. Does keeping the labels-seen network's ranking and taking the level from the delay model lower the
   log loss?

## Model-free check made before this plan

Among campaigns with at least 100 complete 14-day conversions in training, the conversions seen at the cutoff are
64% (10th percentile) to 89% (90th percentile) of the complete count at cutoff 22, and 76% to 93% at cutoff 30 (pooled
77% and 85%). Over the nine test days, 148 campaigns have at least 200 conversions within 14 days; they hold 84% of
the test conversions.

## Models

The third design's labels-seen, delayed-feedback and reference networks, refitted with its data, features, cutoffs,
settings and seeds (20261128 + cutoff), with their predictions kept. One new forecast, built from the two fitted
networks without new training:

**Corrected ranker.** For campaign c at a cutoff, k_c = (mean of the delay network's p over c's training impressions)
/ (mean of the labels-seen network's prediction over the same impressions), computed on training data only; the
forecast for a test impression of campaign c is min(k_c · p_seen(x), 0.99). Within a campaign it ranks as the
labels-seen network; its level per campaign is the delay model's.

## Metrics

1. **Campaign calibration error:** over the campaigns with at least 200 test conversions pooled over the nine days,
   the mean of |predicted / actual − 1| weighted by the campaign's test conversions. Reported for every forecast,
   with the reference giving the floor that sampling noise and day-to-day variation set.
2. Pooled log loss, ROC AUC and predicted over actual, as in the third design.

95% intervals from 200 bootstrap draws of users (seed 20261129), the campaign set fixed.

## Decision rules

1. **Campaign forecasts are corrected:** the delayed-feedback network's campaign calibration error is lower than the
   labels-seen network's, with the 95% interval of the difference below zero.
2. **The corrected ranker improves the fit:** its pooled log loss is lower than the labels-seen network's, with the 95%
   interval of the difference below zero (the third design's second rule, applied to the new forecast).

Reported whatever they show: the corrected ranker's campaign calibration error and ROC AUC; the share of campaigns
whose error is smaller under each forecast.

## What this cannot show

This is a follow-up on data already seen; the third design's rule 2 for the delayed-feedback network itself remains
not met. The networks are refitted, so their pooled numbers can differ slightly from the third design's run (MPS).
k_c is a ratio of two models' means; a campaign new at the cutoff has no k_c and keeps k = the pooled ratio.
