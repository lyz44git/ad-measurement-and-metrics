# Second follow-up plan: predicting the 30-day label

Written after the first follow-up (`out/followup.json`) was seen and before anything below was run. It does not
change any earlier decision.

Seen in the first follow-up: the Weibull network predicts 2.0, 3.2 and 3.5 times the actual 30-day conversions at
days 14, 21 and 28, with a fitted shape of about 0.4 and scales of hundreds of days, while fitting the delays seen in
training better than the exponential network (final training loss 0.112 against 0.146 at day 14).

The cause is in the plans, not the data: both networks' p(x) is the probability of a conversion at any time, and the
label is a conversion within 30 days. The prediction for that label is p(x) · F_x(30), where F is the fitted delay
distribution. For the exponential network F(30) is close to 1, so the main results change little; for a Weibull with
shape 0.4 and a scale of 100 days or more, most of the probability lies beyond 30 days.

## Analysis

Same data, features, training and seeds as the first follow-up. For both networks at each cutoff:

1. Calibration ratio, log loss and ROC AUC of p(x) · F_x(30) on the test impressions, with 95% intervals from 200
   bootstrap draws of test users, and paired differences between the networks.
2. The mean of p(x) and of F_x(30) on the test impressions.
3. The mean training loss of each network on its training impressions, as a measure of how well it fits the delays it
   has seen.

Reported as a correction next to the earlier results, whatever it shows.
