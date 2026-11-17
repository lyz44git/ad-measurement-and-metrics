"""Summarize Part 2 across replicates; reruns (deviation 1) replace the original fits for those replicates.

Usage: python code/03b_summarize.py <out_dir>
"""
import sys
from pathlib import Path
import json, numpy as np
from scipy import stats
OUT = Path(sys.argv[1])
p2 = json.load(open(OUT / "part2_segments.json")); p2.update(json.load(open(OUT / "part2_segments_rerun.json")))
R = sorted(p2, key=int); g = lambda m, k: np.array([p2[r][m][k] for r in R])
d = g("rmse", "bayes") - g("rmse", "nopool"); se = d.std(ddof=1) / np.sqrt(len(d)); t = stats.t.ppf(.975, len(d) - 1)
ci = [float(d.mean() - t * se), float(d.mean() + t * se)]
s = {"n_reps": len(R), "mean_rmse": {m: float(g("rmse", m).mean()) for m in ("nopool", "cpool", "bayes")},
     "mean_mae": {m: float(g("mae", m).mean()) for m in ("nopool", "cpool", "bayes")},
     "bayes_better_count": int((d < 0).sum()), "bayes_better_than_cpool": int((g("rmse", "bayes") < g("rmse", "cpool")).sum()),
     "diff_mean": float(d.mean()), "diff_ci95": ci, "rmse_reduction_pct": float(-d.mean() / g("rmse", "nopool").mean() * 100),
     "rule_met": bool((d < 0).sum() >= 8 and ci[1] < 0),
     "top20": {m: float(g("top20_bench_mean", m).mean()) for m in ("nopool", "bayes", "oracle", "all")},
     "top20_bayes_ge_nopool": int((g("top20_bench_mean", "bayes") >= g("top20_bench_mean", "nopool")).sum()),
     "coverage90": {m: float(g("coverage90", m).mean()) for m in ("nopool", "bayes")},
     "rhat_max": float(max(p2[r]["rhat_max"] for r in R)), "ess_min": float(min(p2[r]["ess_min"] for r in R)),
     "users_per_rep_mean": float(np.mean([p2[r]["n_users"] for r in R])), "control_per_rep_mean": float(np.mean([p2[r]["n_control"] for r in R])),
     "sigma_b_mean": float(np.mean([p2[r]["sigma_b_mean"] for r in R]))}
json.dump(s, open(OUT / "part2_summary.json", "w"), indent=1); print(json.dumps(s, indent=1))
