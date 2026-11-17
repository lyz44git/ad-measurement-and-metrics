# Deviations from design/analysis_plan.md

1. Part A: 10 of 130 fits had max R-hat between 1.01 and 1.019 (500 / 500 draws). As the plan says, they are listed
   here and were not rerun.
2. Part B: the adjusted CACE (21.5 pp) is quoted from study 01a (`out/criteo/a_incrementality.json`),
   not recomputed here.
No change to any estimator, metric or decision rule.

3. The published code was reorganized into functions (`code/private_core.py`) so that they can be tested, and takes
   file locations as arguments. Part A was rerun with the reorganized code on 2026-11-17; the rerun is compared with
   the original run in `logs/rerun_check.txt`.
