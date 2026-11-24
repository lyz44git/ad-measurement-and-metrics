# Analysis plan, third design: a 14-day window

Written after the second design was run and seen (`out/delay_v2.json`), after the model-free check below, and before
any model of this design was fitted.

## Why a third design

The second design removed the drifting features and the cold start, and with them most of the problem: on a 7-day
window the network trained on the labels seen at the cutoff predicted only 3.8% too few conversions, the gap in log
loss between it and the reference was 0.0003, and the delayed-feedback network, which brought the level to 0.997,
could not show a gain in log loss. The question of whether correcting the delay pays off needs a window in which the
delay matters. A 14-day window is the longest that the 31-day log supports with the 7-day warm-up and at least nine
test days. Everything else is as in the second design.

## Model-free check made before this plan

On a 14-day window, 79.3% of the log's conversions arrive within the window (62.6% on 7 days). Among training
impressions, the conversions seen at the cutoff are 76.8%, 81.7% and 85.1% of the complete 14-day ones at cutoffs
22, 26 and 30 (83.4%, 89.4% and 92.9% at cutoffs 17, 23 and 30 on the 7-day window).

## Changes from the second design

- **Label:** a conversion within 14 days of the impression; the delay network has 14 daily shares.
- **Cutoffs:** days 22 to 30 (9 cutoffs), training on impressions from day 7, each scored on the next day against
  complete 14-day labels; results pooled over the 9 test days. The complete-labels-only network uses impressions
  older than 14 days (1 to 9 days of them).
- Features, architecture, training settings, bootstrap and seed rule as in the second design (seed 20261128).

## Decision rules (pooled over the 9 test days)

1. **The level is corrected:** the delay network's predicted over actual conversions lies within 0.95 to 1.05, and
   its absolute calibration error |ratio − 1| is at most half that of the labels-seen network, in at least 95% of the
   bootstrap draws.
2. **The fit improves:** the delay network's log loss is below the labels-seen network's, with the 95% interval of the
   difference below zero.

Reported with no rule: the share of the log-loss gap to the reference that is closed (undefined when the gap is near
zero, as on the 7-day window, so it is not a rule here); the comparison with the complete-labels-only network; the
same quantities by day; estimated against observed delay shares.

Rule 1 states the level more tightly than before (0.95 to 1.05 against 0.90 to 1.10) because the level is what a bid
is priced on and the second design showed that it can be reached; rule 2 is the second design's log-loss condition
unchanged.

## What is known and what is not

This is the third design on the same log; the results of the first two are known, so it is not an independent
replication. Whether the labels-seen network falls short by as much as its training labels do is not known: on the
7-day window it fell short by 3.8% while its training labels were 7% to 17% short.

## What this cannot show

Conversions later than 14 days (21% of the log's) are outside the label.
