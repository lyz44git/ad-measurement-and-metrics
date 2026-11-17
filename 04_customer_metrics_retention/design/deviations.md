# Deviations from `analysis_plan.md` (step 14)

1. **E4, value terciles in SQL.** The first run used `NTILE(3)`, which gives groups of 906 / 905 / 905 accounts; the
   pandas result it is compared with (`qcut` on ranks) gives 905 / 905 / 906. The SQL was changed to rank-based
   terciles with boundary accounts in the upper group, and the script was rerun in full. E1-E3 are unchanged
   (same seeds, same numbers).
2. **E1-E3.** No deviations. E1's decision rule was not met and is reported as such in the README.
