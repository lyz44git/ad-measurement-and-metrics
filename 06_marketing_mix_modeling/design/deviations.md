# Deviations from `analysis_plan.md` (Part A)

The plan covers this study (Part A) and study 05 (Part B); it was written and hashed once, before either was run.

1. **Daily rerun (added after seeing the weekly results).** The planned weekly model failed its own parameter-recovery
   check: with real spend and simulated revenue, the rank correlation between true and estimated ROAS was 0.01
   (18 converged brands). The model was rerun on daily data: same priors, adstock over 28 days, annual Fourier terms
   plus day-of-week dummies, last 91 days held out, eligibility 728+ consecutive days with Google and Meta spend on
   80%+ of days. Recovery improved to 0.70 in the 15 Nov run (0.75 in the published rerun, item 2). Both runs are kept (`out/mmm_*` for weekly, `out/mmm_*_daily.*` for
   daily). The real-data results of the weekly run had been seen before this decision.
2. **Rerun for publication (16 Nov).** The published `code/run_mmm.py` is the original script reorganised into
   functions, with the media transforms moved to `code/mmm_core.py` so they can be tested; the model, priors, data
   rules and seeds are unchanged. NUTS draws are sensitive to small floating-point differences, and neither this script
   nor the original reproduced the 15 Nov draws exactly. The results in `out/` and the README are from the 16 Nov rerun
   of the published script. The 15 Nov run gave: converged brands 33 (weekly) and 25 (daily);
   recovery rank correlation 0.01 and 0.70; daily model ROAS 2.3 (Google) and 2.7 (Meta) against revenue per unit of
   spend of 5.7; the forecasting rule not met in either run. The conclusions are the same in both runs.
