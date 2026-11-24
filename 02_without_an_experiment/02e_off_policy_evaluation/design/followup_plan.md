# Follow-up plan: why do the estimators with an estimated propensity lose the lift?

Written after the main results (`out/ope.json`) were seen and before anything below was run. It does not change the
pre-specified decision, which was not met.

Seen in the main run, moderate setting: IPS with the known propensity is within 0% to 8% of the true lift for every
policy, with 93% to 95% coverage. With the propensity estimated on the log, IPS is 81% to 95% below the true lift,
SNIPS 72% to 84% below and DR 32% to 35% below; the mean absolute error of the estimated propensity is 0.037.

## Questions and analyses

All on the moderate setting (β = 1), with the main run's code and settings unless stated.

1. **Where is the propensity model wrong?** On the same 200 logs as the main run (same seeds): by decile of the true
   logging propensity e(x), the mean of e, the mean estimated propensity ê, and the share of the log's visits in the
   decile.
2. **Is the outcome model the problem?** On the same logs, DR with the known propensity in place of ê, for all four
   policies: bias, root mean squared error and coverage.
3. **Levels against differences.** On the same logs, IPS with ê for V(all) and for V(none) separately, each as a
   share of its true level (the truth part's IPS value), to show how a small relative error in two levels becomes a
   large error in their difference.
4. **Does a larger log fix it?** 50 logs drawn with every row of the log part as a candidate (about 734,000 kept rows
   each, against about 150,000), seeds 20261125 + 9000 + r: bias and coverage of IPS with ê and of DR, for the four
   policies.

Results are reported as a follow-up, next to the main results, whatever they show.
