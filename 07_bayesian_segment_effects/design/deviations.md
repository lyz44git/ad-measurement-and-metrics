# Deviations from design/analysis_plan.md

1. Replicates 4, 7 and 9 (0-based ids) missed the convergence target with 1,000 / 1,000 draws (max R-hat 1.011,
   1.0107 and 1.011; replicate 9 min bulk ESS 399). As the plan specifies, they were rerun with 3,000 / 3,000 draws
   (`logs/03_rerun.log`, `out/part2_segments_rerun.json`): max R-hat 1.0017, 1.0032 and 1.0005, min ESS 1,215+.
   The reruns replace the original fits in the summary. Estimates barely moved (replicate 9 RMSE 0.764 -> 0.760 pp).
