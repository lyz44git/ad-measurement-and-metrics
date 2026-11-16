# Deviations from `analysis_plan.md` (Part A)

The plan covers this study (Part A) and study 05 (Part B); it was written and hashed once, before either was run.

1. **Daily rerun (added after seeing the weekly results).** The planned weekly model failed its own parameter-recovery
   check: with real spend and simulated revenue, the rank correlation between true and estimated ROAS was 0.01
   (18 converged brands). The model was rerun on daily data: same priors, adstock over 28 days, annual Fourier terms
   plus day-of-week dummies, last 91 days held out, eligibility 728+ consecutive days with Google and Meta spend on
   80%+ of days. Recovery improved to 0.75. Both the weekly and the daily results are kept (`out/mmm_*` and
   `out/mmm_*_daily.*`). The real-data results of the weekly run had been seen before this decision.
