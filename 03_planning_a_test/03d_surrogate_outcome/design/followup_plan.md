# Follow-up plan: does the result hold with feature-adjusted estimates?

Written after the main results (`out/surrogate.json`) were seen and before anything below was run. It does not
change the pre-specified decision, which was not met.

Reason: study 05c found that in this pooled release the probability of assignment to the ad arm varies slightly
with the features (held-out AUC 0.509), and that unadjusted and feature-adjusted effects differ by about 30%. The
main results of this study are unadjusted differences between arms. Both the direct and the surrogate estimates
could carry the imbalance, so the share of the conversion effect that visits recover could change.

## Analysis

On the experiment half, with the surrogate model q(X) of the main run unchanged:

1. An assignment model r̂(x) = P(A = 1 | x), LightGBM (300 trees, otherwise the main run's settings), fitted on the
   historical half.
2. Outcome models for conversion and for the surrogate S = visit × q(X), one per arm, cross-fitted in two folds on
   the experiment half (LightGBM, 300 trees).
3. AIPW estimates of the effect on conversion and on S, with r̂(x), and with the constant assignment share; the
   ratio of the two effects with a delta-method 95% interval from the joint influence functions. The visit effect
   is reported the same way.

## Reading

The main conclusion stands if the adjusted ratio of surrogate to direct effect is below 0.80 (outside the
equivalence margin) with its 95% interval below 0.80. Whatever the result, both adjusted versions are reported next
to the unadjusted one.
