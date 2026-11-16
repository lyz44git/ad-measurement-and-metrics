# Deviations from `analysis_plan.md` (step 14)

1. **E4, value terciles in SQL.** The first run used `NTILE(3)`, which gives groups of 906 / 905 / 905 accounts; the
   pandas result it is compared with (`qcut` on ranks) gives 905 / 905 / 906. Three accounts at the two tercile
   boundaries changed group and the largest difference in a cell count was 1. The SQL was changed to rank-based
   terciles with boundary accounts in the upper group, and the script was rerun in full. E1-E3 are unchanged
   (same seeds, same numbers). The first-run numbers are recorded only in this note.
2. **E1-E3.** No deviations. E1's decision rule was not met and is reported as such in the README.
