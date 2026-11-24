# Second follow-up plan: which experimental value does DR recover?

Written after the first follow-up (`out/followup.json`) was seen and before anything below was run. It does not
change the pre-specified decision.

Seen in the first follow-up: the propensity model is calibrated within 0.01 in every decile of the true logging
propensity, yet DR is 27% to 30% below the truth even when it is given the known propensity, which DR's
construction should not allow if the known propensity is the true one. A diagnostic on 20 logs (not committed) ruled
out leakage through duplicate rows: cross-fitting with identical rows kept in one fold gave the same bias. Study 01a
reported that on the full experiment the unadjusted visit effect (1.03 points) and the regression-adjusted one
(0.77) differ by a quarter, which suggests that the assignment share is not exactly constant across the features in
this pooled release. The truth used so far assumes it is constant.

## Analyses

1. **Adjusted truth.** On the truth part: the lift of each policy by cross-fitted AIPW, with LightGBM outcome models
   (two folds, 300 trees, otherwise the settings of the plan) and the constant assignment probability 0.85. Compared
   with the unadjusted truth, for each policy.
2. **Does assignment depend on the features?** On the truth part: the held-out ROC AUC of a LightGBM model of
   assignment (two folds), and the lift by IPS with this estimated assignment probability.
3. **Errors against both truths.** On the 200 moderate-setting logs of the main run (`out/ope_logs.csv`), the mean
   error of every estimator as a share of the adjusted truth, next to the share of the unadjusted truth already
   reported.
4. **Why IPS with an estimated propensity overstates V(none).** On 50 of the moderate-setting logs (main-run seeds
   0 to 49): among control rows in the top decile of the true propensity, the mean of 1/(1 − e) and of 1/(1 − ê), and
   the same among control rows with a visit.

Results are reported as a second follow-up, whatever they show.
