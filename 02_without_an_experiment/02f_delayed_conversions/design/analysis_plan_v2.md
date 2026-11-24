# Analysis plan, second design: features that do not drift, a window the data can identify, daily retraining

Written after the first design and its two follow-ups were run and seen (`out/delay.json`, `out/followup.json`,
`out/followup2.json`), after the model-free checks below, and before any model of this design was fitted.

## Why a second design

The first design had four faults.

1. **Two features drifted with calendar time.** The numbers of a user's earlier impressions and clicks were counted
   from the first day of the log, so they grew as the log went on: 1.2 earlier impressions on average in the first
   week, 6.0 after day 28. Among impressions with five or more earlier ones, the 30-day conversion rate fell from
   12.0% to 8.1%. A model trained on earlier days therefore over-predicted later ones, and the reference model with
   complete labels was 7% to 10% too high. The rule's band of ±10% did not allow for this.
2. **It started cold.** Retraining at day 14 on a 30-day label, no impression had been watched for more than 14
   days, while 21% of conversions take longer. That part of the delay distribution is not in the data at any cutoff
   of a 31-day log; any model has to extrapolate it. A running system has older impressions whose labels are
   complete.
3. **The second rule asked a sequence model for a gain the data cannot give.** Users have 2.7 impressions on
   average and half have one.
4. The initial weights were drawn before the seed was set.

## Model-free checks made before this plan

With the features below (no model fitted): from the second week on, the mean number of impressions in the previous
7 days is 2.0 to 2.1 in every week, and the 7-day conversion rate among impressions with five or more is 6.4% to
7.0%. 62.6% of the log's conversions arrive within 7 days of the impression. The 7-day conversion rate is 3.07%
overall and 2.81% to 3.42% by day, so a single day's rate differs from the average by up to 11%.

## Data

As before: 16,468,027 impressions over 31 days (days 0 to 30), conversions recorded up to day 61. The first 7 days
only supply history for the features; no model is trained or scored on them.

## Label

A conversion **within 7 days** of the impression. At a cutoff, an impression older than 7 days has its complete
label; only the impressions of the last 7 days can still convert.

## Features, known when the impression is bought

Campaign; the user's impressions and clicks in the previous 7 days; time since the previous impression in that
window; time since the user's last click if within 7 days; hour of day; day of the week (the day number modulo 7).

## Cutoffs

Retraining at the start of each of days 17 to 30 (14 cutoffs) on the impressions from day 7 up to the cutoff, with
the labels as seen at the cutoff. Each model is scored on the impressions of the day that follows, against their
complete 7-day labels. Results are pooled over the 14 test days.

## Models (PyTorch; one architecture: campaign embedding of 16, two hidden layers of 64)

1. **Labels seen:** trained on the labels as seen at the cutoff.
2. **Complete labels only:** trained on the impressions older than 7 days, whose labels are complete. It is unbiased
   and ignores the most recent week.
3. **Delayed-feedback network:** predicts p(x), the chance of a conversion within 7 days, and the shares π_1(x) to
   π_7(x) of those conversions arriving on each day after the impression. Likelihood: a seen conversion on day k
   contributes p · π_k; an impression watched for t days without one contributes 1 − p · F(t), with F the cumulative
   share and the density constant within a day. No parametric delay distribution is assumed.
4. **Reference:** trained on the complete 7-day labels of every training impression, which no system has at the
   cutoff.

Adam, learning rate 0.001, batch size 8,192, three epochs, seed set before each network is built. No sequence model:
fault 3.

## Metrics

Pooled over the 14 test days, and by day: predicted over actual conversions, log loss, ROC AUC. 95% intervals from
200 bootstrap draws of users over the pooled test impressions.

## Decision rules (pooled over the 14 test days)

1. **The delay is corrected:** the delayed-feedback network's predicted over actual conversions is within 0.90 to
   1.10, and its log loss is below that of the labels-seen network, with the 95% interval of the difference below
   zero.
2. **Most of the cost of the delay is recovered:** the delayed-feedback network closes at least half of the log-loss
   gap between the labels-seen network and the reference.

Reported whatever they show, with no rule attached: the same quantities by day; the comparison with the
complete-labels-only network; the mean estimated delay shares against the observed ones.

## What can and cannot be said in advance

The pooled rate of the test days is close to that of the training days, so a model with correct labels should be
near 1.00 pooled; by day it cannot be, since daily rates differ from the average by up to 11%, which is why the rules
are pooled. With 10 to 23 training days of which the last 7 are incomplete, the labels-seen network is expected to
predict too few. Whether the delayed-feedback network beats the complete-labels-only network is not known: without
drift the latter loses only data, so no rule is attached to that comparison.

This design uses the same log as the first, so it is a new design on data already seen, not an independent
replication.

## What this cannot show

Conversions later than 7 days (37% of the log's) are outside the label. The 30-day results of the first design stay
in the study as the record of what a cold start on a long window gives.
