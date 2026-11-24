# Follow-up plan: is day 14 a limit of the model or of the data?

Written after the main results (`out/delay.json`) were seen and before anything below was run. It does not change
the pre-specified decisions, which were not met.

Seen in the main run: the delayed-feedback network predicts 0.780, 0.950 and 1.036 times the actual conversions at
days 14, 21 and 28. Seen in a profile of the log after the run: 20.7%, 9.9% and 2.0% of the conversions within 30
days come more than 14, 21 and 28 days after the impression.

## Analyses

1. **What the data can show at each cutoff.** At cutoff T no impression has been observed for more than T days, so
   delays longer than T are never seen in training and any model must extrapolate them. For each cutoff: the share of
   30-day conversions in the log with a delay longer than T, next to the delay network's shortfall (1 minus its
   calibration ratio).
2. **A heavier-tailed delay.** The same network and training as the main run, with the exponential delay replaced
   by a Weibull delay whose shape and scale depend on the features: density (k/λ)(d/λ)^(k−1) exp(−(d/λ)^k), survival
   exp(−(e/λ)^k), shape initialized at 0.6 and scale at 5 days. A shape below 1 gives many short delays and a long
   tail. The exponential network is retrained in the same run with the same seed, so the two are compared on the
   same bootstrap draws.

## Decision rule

The Weibull delay improves calibration at day 14 if |ratio − 1| is smaller than the exponential network's, with
the 95% interval of the paired difference of |ratio − 1| below zero. Log loss and the other cutoffs are reported
whatever they show.
