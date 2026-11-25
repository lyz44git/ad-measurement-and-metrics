# Follow-up plan 4: the corrected ranker with its ratio taken where it is applied

Written after follow-up 3 was run and seen (`out/followup3.json`), and before anything below was fitted. Follow-up 3's
results, and its rule 2 that was not met, stay as they are; this plan is a second attempt written after that failure,
and is reported as one.

## Why follow-up 3's corrected ranker failed

Its ratio k_c was the delay network's mean prediction over the labels-seen network's, both taken over campaign c's
training impressions (days 7 to the cutoff). Over those impressions the ratio had a median of 1.19 to 1.40 by cutoff,
while on the test days the two networks' pooled predictions differ by a factor of 1.018 / 0.885 = 1.15. The ratio was
measured on a population of impressions that is not the one it was applied to, and the corrected ranker predicted
13.7% too many conversions.

## Question

If the ratio is taken on the impressions it is applied to, using only the two networks' predictions there and no
outcome, does keeping the labels-seen network's ranking and the delay model's level lower the log loss?

## Models

Follow-up 3's labels-seen, delayed-feedback and reference networks, refitted with the third design's data, features,
cutoffs (22 to 30), settings and seeds (20261128 + cutoff). New forecasts, built from the two fitted networks without
new training, p_seen and p_delay being their predictions:

1. **Corrected ranker, test-day ratio (primary).** For campaign c on test day T, k_c = (sum of p_delay over c's
   impressions of day T) / (sum of p_seen over the same impressions); the forecast is min(k_c · p_seen, 0.99). It uses
   the day's predicted values, never its outcomes; a live system would use a running mean over the day.
2. **Corrected ranker, previous-day ratio (reported).** The same, with k_c taken over c's impressions of day T − 1,
   the last training day, scored by the networks fitted at cutoff T; a campaign with no impression on day T − 1 takes
   the pooled ratio of that day. Nothing from day T is used.
3. **Pooled test-day ratio (reported).** One ratio for all campaigns on day T, from the same sums.

## Metrics

As in follow-up 3: pooled log loss, ROC AUC, predicted over actual, and campaign calibration error over the campaigns
with at least 200 test conversions. 95% intervals from 200 bootstrap draws of users (seed 20261129), the campaign set
fixed.

## Decision rule

**The corrected ranker improves the fit:** the pooled log loss of forecast 1 is lower than the labels-seen network's,
with the 95% interval of the difference below zero (follow-up 3's rule 2, applied to forecast 1).

Reported whatever they show: forecast 1 against the delayed-feedback network and against the reference network
(log loss differences with intervals); forecasts 2 and 3 on every metric; forecast 1's campaign calibration error,
which equals the delay network's by construction except for the cap at 0.99.

## What this cannot show

This is a second attempt on data already seen, so its result is weaker evidence than a rule set before any run;
follow-up 3's rule 2 stays listed as not met. The networks are refitted, so their pooled numbers can differ slightly
from follow-up 3's run (MPS). Forecast 1 needs both networks at serving time.
