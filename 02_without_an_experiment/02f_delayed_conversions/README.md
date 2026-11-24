# 02f · Can a conversion model trained before its labels arrive be corrected for the delay?

**[Explore this study interactively →](https://lyz44git.github.io/ad-measurement-and-metrics/02.html#s02f)**

> **Takeaway.** The level, yes; the overall fit, not measurably. A network retrained each day on the conversions seen
> so far predicts 11.5% too few 14-day conversions on the following day, because recent impressions whose conversions
> are still to come count as failures. A delayed-feedback network (Chapelle 2014) in PyTorch, which learns the
> conversion probability and the share of conversions arriving on each of the 14 days, predicts 1.8% too many, against
> 0.0% for a reference trained on complete labels; this pre-specified rule was met. Its log loss is the same as the
> uncorrected network's (the second rule was not met): it fixes the level and ranks slightly less well. Waiting for
> complete labels instead, by dropping the last 14 days, is far worse on both log loss and ranking. Two earlier designs,
> on a cold start and a 7-day window, are below.

## Question

The bidders of [study 02d](../02d_attribution_and_bidding) price impressions with a model of expected credit, trained
there on complete labels. A conversion model retrained every day must learn from recent impressions whose conversions
have not happened yet, so its training labels count late converters as non-converters. How much does this bias its
predictions, and can a model of the delay correct it? The log records every conversion up to 30 days after each
impression, so the labels a model could not see at the time can be used to score it.

## Data

Criteo Attribution Modeling for Bidding dataset, the log of studies
[02b](../02b_multi_touch_attribution) and [02d](../02d_attribution_and_bidding):
16,468,027 impressions of 675 campaigns over 31 days (days 0 to 30), with conversions recorded up to day 61. 3.9% of
impressions are followed by a conversion within 14 days, 79% of all conversions in the log. Pass the path to the
`criteo_attr.parquet` file written by study 02b's `code/load_attribution.py`.

## Method

The plan of this design, [`design/analysis_plan_v3.md`](design/analysis_plan_v3.md), was fixed after the two earlier
designs had run and before any model of this design was fitted (SHA-256 in `logs/plan_v3_hash.txt`).

1. **Label.** A conversion within 14 days of the impression. At a cutoff, an impression older than 14 days has its
   complete label; only the last 14 days can still convert.
2. **Features known when the impression is bought**, over a rolling 7-day window so that they do not grow with
   calendar time: campaign; the user's impressions and clicks in the previous 7 days; time since the previous
   impression in that window; time since the user's last click if within 7 days; hour of day; day of the week. The
   first 7 days of the log only supply history.
3. **Daily retraining.** At the start of each of days 22 to 30, every model is retrained on the impressions from day
   7 up to the cutoff, with the labels as seen at the cutoff, and scored on the next day's impressions against their
   complete 14-day labels. Results are pooled over the 9 test days (4,500,151 impressions, 173,195 conversions).
4. **Four networks, one architecture** (campaign embedding and two hidden layers of 64, in PyTorch):
   - **labels seen**, trained on the labels as seen at the cutoff;
   - **complete labels only**, trained on the impressions older than 14 days;
   - **delayed-feedback network**, which predicts p(x), the chance of a conversion within 14 days, and the shares of
     those conversions arriving on each day after the impression. A seen conversion on day k contributes p · π_k to
     the likelihood and an impression watched for t days without one contributes 1 − p · F(t), with F the cumulative
     share. No parametric delay distribution is assumed;
   - **reference**, trained on the complete 14-day labels of every training impression, which no system has at the
     cutoff.
5. **Decision rules (pooled).** (1) The level is corrected: the delayed-feedback network's predicted over actual
   conversions lies within 0.95 to 1.05 and its calibration error is at most half the labels-seen network's in at
   least 95% of bootstrap draws. (2) The fit improves: its log loss is below the labels-seen network's, with the 95%
   interval of the difference below zero.

Adam, learning rate 0.001, batch size 8,192, three epochs, seed set before each network is built; Apple MPS backend.
95% intervals from 200 bootstrap draws of users.

## Results

Source: [`out/delay_v3.json`](out/delay_v3.json).

At the cutoffs, the conversions seen in the training data are 77% to 85% of their complete 14-day count.

| Network | Predicted / actual (95% CI) | Log loss | ROC AUC |
|---|---|---|---|
| Labels seen | 0.885 (0.878 to 0.892) | 0.1392 | 0.793 |
| Complete labels only | 0.967 (0.959 to 0.974) | 0.1447 | 0.760 |
| **Delayed-feedback network** | **1.018 (1.010 to 1.026)** | **0.1392** | **0.791** |
| Reference, complete labels | 1.000 (0.992 to 1.008) | 0.1386 | 0.795 |

- **Rule 1 was met.** The delayed-feedback network moves the forecast from 11.5% too few conversions to 1.8% too
  many, and its calibration error is less than half the labels-seen network's in all 200 bootstrap draws. This is
  the quantity a bid or a conversion forecast is priced on.
- **Rule 2 was not met.** The log loss of the two networks differs by −0.00002 (95% interval −0.00009 to +0.00004).
  Log loss changes little with a uniform shift in the level of small probabilities, and the delayed-feedback network
  ranks impressions slightly less well (ROC AUC 0.791 against 0.793), which offsets what the level gains. The
  reference leads both by 0.0006.
- **Waiting for complete labels is the costly alternative.** The network trained only on impressions older than 14
  days is close in level but has a log loss 0.0055 higher than the delayed-feedback network (interval below zero) and
  a ROC AUC of 0.760, because it never sees the most recent two weeks.
- **The delay itself is learned.** The estimated shares of conversions on each day after the impression average
  36.6% on day 1, against 41.8% observed in the test days, and 3.3% on day 14 against 2.5%: the network puts a little
  too much of the delay late, which is consistent with its forecast being slightly high.
- **Single days vary more than the pool.** On individual test days the delayed-feedback network ranges from 0.91 to
  1.13 and the reference from 0.91 to 1.11, moving together, because the 14-day conversion rate itself ranges from
  3.6% to 4.1% between days. The rules were pooled for this reason.

[![Calibration of conversion models by test day, design history and delay tails](out/fig_delay.png)](https://lyz44git.github.io/ad-measurement-and-metrics/02.html#s02f)

## How this design came about

**First design: 30-day label, cold start** ([`design/analysis_plan.md`](design/analysis_plan.md);
[`out/delay.json`](out/delay.json)). Retrained at days 14, 21 and 28 from the first day of the log and scored on the
next three days against 30-day labels. Networks trained on the labels seen predicted 27% to 44% too few; the
delayed-feedback network with an exponential delay reached 0.950 at day 21 and 1.036 at day 28, but 0.780 at day 14,
so its rule, which required all three cutoffs, was not met. A GRU over each user's last 20 impressions did not improve
log loss (users have 2.7 impressions on average). Two follow-ups, each hashed before it ran
([`design/followup_plan.md`](design/followup_plan.md), [`design/followup_plan_2.md`](design/followup_plan_2.md);
[`out/followup.json`](out/followup.json), [`out/followup2.json`](out/followup2.json)), tried a Weibull delay: scored
as planned on the probability of converting at any time it predicted 2.0 to 3.5 times the conversions, which missed
its rule; scored on the 30-day probability it was within 4% at day 14 and 10% to 14% too high at days 21 and 28. With
two weeks of a 31-day log no impression has been watched for longer than 14 days while 21% of conversions take longer,
so any model extrapolates that tail.

Two faults of that design were found afterwards. The counts of a user's earlier impressions and clicks ran from the
first day of the log and grew with calendar time (1.2 earlier impressions on average in the first week, 6.0 after day
28), so a model trained on earlier days over-predicted later ones: the reference with complete labels was 7% to 10%
too high. And the initial weights of the networks were drawn before the seed was set.

**Second design: 7-day label, warm start** ([`design/analysis_plan_v2.md`](design/analysis_plan_v2.md);
[`out/delay_v2.json`](out/delay_v2.json)). Rolling 7-day features, a 7-day label and 14 daily cutoffs. The labels-seen
network predicted only 3.8% too few and the delayed-feedback network 0.3% too few (reference 1.4% too few), but its
rules required a lower log loss and half of the log-loss gap to the reference closed; the two networks' log losses
were equal and neither rule was met. With so short a window the delay barely mattered.

**This design** keeps the second design's features and daily retraining and uses the longest window the log allows
with a warm start and nine test days. Its first rule states the level more tightly (0.95 to 1.05) because the level
is what a bid is priced on; its second rule is the earlier log-loss condition unchanged. It is a third design on the
same log, chosen with the first two results known, so it is not an independent replication.

## Reproduce

```bash
python code/run_delay_v3.py /path/to/derived/criteo_attr.parquet out   # this design, about 13 minutes on an Apple M3 Ultra (MPS)
python code/run_delay_v2.py /path/to/derived/criteo_attr.parquet out   # second design, about 25 minutes
python code/run_delay.py /path/to/derived/criteo_attr.parquet out      # first design, about 25 minutes
python code/run_followup.py /path/to/derived/criteo_attr.parquet out   # first follow-up, about 9 minutes
python code/run_followup2.py /path/to/derived/criteo_attr.parquet out  # second follow-up, about 7 minutes
```

`tests/` checks on small simulated logs that features and histories use only earlier impressions, that the rolling
window drops impressions older than 7 days, that labels after the cutoff are hidden, that both delayed-feedback losses
match their formulas, that the delay models remove the under-prediction of a naive model on censored labels, and that
the grouped ROC and PR AUC match scikit-learn with ties and weights.

## Scope

- One display network. The label is any conversion by the user within 14 days of the impression; conversions later
  than 14 days (21% of the log's) are outside it, and nothing here concerns what the ads caused.
- Retraining is simulated on nine days of one month, not run as a production system; a system with a longer history
  would also have more impressions with complete labels.
- The study checks the calibration and fit of a forecast. It does not test whether a bidder using the corrected model
  would buy better.
