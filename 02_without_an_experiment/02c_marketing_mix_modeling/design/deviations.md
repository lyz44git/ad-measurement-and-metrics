# Deviations from the plans of this study

## `analysis_plan.md` (Part A)

The plan covers this study (Part A) and study 02b (Part B); it was written and hashed once, before either was run.

1. **Daily rerun (added after seeing the weekly results).** The planned weekly model failed its own parameter-recovery
   check: with real spend and simulated revenue, the rank correlation between true and estimated ROAS was 0.01
   (18 converged brands). The model was rerun on daily data: same priors, adstock over 28 days, annual Fourier terms
   plus day-of-week dummies, last 91 days held out, eligibility 728+ consecutive days with Google and Meta spend on
   80%+ of days. Recovery improved to 0.75. Both the weekly and the daily results are kept (`out/mmm_*` and
   `out/mmm_*_daily.*`). The real-data results of the weekly run had been seen before this decision.

## `followup_plan.md` (pooled model)

2. **Brand-channels used for the recovery rule.** The plan did not say on which brand-channels the rule is evaluated.
   It is evaluated on those converged under both models; over all brand-channels the outcome is the same (not met).
3. **Pooled fit to real daily revenue.** With the planned sampler settings this fit did not converge (largest R-hat
   48, 322 divergent transitions). It was not rerun with other settings; its forecasts are reported and not
   interpreted.

## `detectability_plan.md` (signal-to-noise index)

4. **A figure quoted in the plan.** The plan quotes a median error of 0.18 for an index of 2 or more in the
   exploration set. That figure is for an index between 2 and 4; for 2 or more it is 0.17. No test is affected.
