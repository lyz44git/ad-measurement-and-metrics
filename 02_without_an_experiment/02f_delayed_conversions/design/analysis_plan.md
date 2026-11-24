# Analysis plan: can a conversion model trained before its labels arrive be corrected for the delay?

Written before any model in this study was fitted and before any metric below was computed.

Already known when this plan was written: the results of studies 02b and 02d on the same log (a time-decay half-life
of 7.9 days for touch-to-conversion delays; LightGBM value models from bid-time features are well calibrated on
complete labels), and a profile of the log: 16,468,027 impressions over 31 days, conversions recorded up to day 61,
every delay at most 30 days, 4.9% of impressions followed by a conversion within 30 days, and delay quantiles of
3 minutes (10th percentile), 3.7 days (median) and 21 days (90th percentile). Not yet computed: any model in this
plan, any label as seen at a cutoff, any metric below.

## Question

A conversion model retrained every day must learn from recent impressions whose conversions have not happened yet,
so its training labels count late converters as non-converters. How much does this bias its predictions, and can a
model of the delay (Chapelle 2014) correct it? Because the log records every conversion up to 30 days after each
impression, the labels the model could not see at the time can be used to score it.

## Data

Criteo Attribution Modeling for Bidding dataset, the file `criteo_attr.parquet` written by study 02b's
`code/load_attribution.py`, all impressions. For an impression at time t: the **30-day label** y = `conversion`
(a conversion within 30 days after the impression) and, if y = 1, the delay d = `conversion_timestamp` − t.

**Features known when the impression is bought** (as in study 02d): campaign, seconds since the user's last click
(missing if none), number of the user's earlier impressions in the log and how many were clicked, seconds since the
user's previous impression (missing for the first) and hour of day. The impression's own click is not used.
**History** for the sequence model: the user's previous impressions, up to the last 20, each with campaign, log of
the seconds before the current impression, and whether it was clicked.

## Cutoffs

The model is retrained at cutoff day T, for T = 14, 21 and 28.

- **Training impressions:** t < T. **Label seen at the cutoff:** y_T = 1 if y = 1 and t + d < T, else 0.
  **Elapsed time** e = T − t.
- **Test impressions:** T ≤ t < T + 3 days. They are scored against their 30-day label y.

## Models (same features in all)

1. **Naive LightGBM** on y_T (300 trees, learning rate 0.05, 63 leaves, at least 200 rows per leaf).
2. **Naive network** on y_T: a PyTorch MLP with a 16-dimensional campaign embedding and two hidden layers of 64
   units, cross-entropy loss.
3. **Delayed-feedback network (primary).** The same MLP with two outputs, the logit of the conversion probability
   p(x) and the log of an exponential delay rate λ(x), fitted by maximum likelihood with censoring at e:
   p · λ · exp(−λ d) for a conversion seen by the cutoff, and 1 − p + p · exp(−λ e) otherwise. The prediction
   is p(x).
4. **Delayed-feedback sequence network.** As 3, with a one-layer GRU (32 units) over the history, whose last state
   is concatenated with the features.
5. **Oracle LightGBM** on the 30-day labels of the training impressions, which no real system has at the cutoff;
   reported as the reference for what complete labels would give.

Networks: Adam, learning rate 0.001, batch size 8,192, 3 epochs, no early stopping, seed 20261126, Apple MPS
backend. Inputs are scaled with statistics of the training impressions; missing times get their own indicator.

## Metrics, on the test impressions of each cutoff

Calibration ratio (sum of predicted probabilities over the number of 30-day conversions), log loss, ROC AUC and
PR AUC. Intervals: 95% percentile intervals from 200 Poisson bootstrap draws of test users, predictions fixed.
Differences between models use the same draws.

## Decision rules

1. **The delay model corrects the bias** if, at all three cutoffs, its calibration ratio is in [0.90, 1.10] and its
   log loss is lower than the naive network's with the 95% interval of the difference below zero.
2. **The user's history adds to the delay model** if, at all three cutoffs, the sequence network's log loss is lower
   than the delayed-feedback network's with the 95% interval of the difference below zero.

All five models are reported at every cutoff whatever the rules show.

## What this cannot show

The labels are those of this log: conversions attributed to a user within 30 days on one display network, with no
experiment, so nothing here concerns what the ads caused. The exponential delay is a modeling choice; the delay
distribution has many very short delays and a long tail, which this form may not fit. Retraining is simulated at
three cutoffs on 31 days of data, not run as a production system.
