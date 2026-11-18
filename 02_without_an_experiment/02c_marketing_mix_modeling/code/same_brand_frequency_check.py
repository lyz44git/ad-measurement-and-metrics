"""Weekly against daily recovery of the per-brand model on the same brand-channels.

Added after all runs. Reads the per-brand model columns (`single*`) of the committed part 2 outputs
out/mmm_pooled_recovery.csv (weekly) and out/mmm_pooled_recovery_daily.csv (daily), keeps the brand-channels present
and converged in both, and compares their recovery. The simulation design is the same at both frequencies, but the
true returns and shapes are drawn separately for each run (`true_identical` reports this). No model is refitted;
existing outputs are not changed.

Usage: python code/same_brand_frequency_check.py [out_dir]
Writes <out_dir>/same_brand_frequency_check.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

KEY = ["sim", "org", "channel"]


def recovery(t, est, lo, hi):
    err = np.abs(est - t) / t
    return {"median_abs_rel_err": float(np.median(err)), "spearman": float(spearmanr(t, est)[0]),
            "coverage90": float(((lo <= t) & (t <= hi)).mean())}


def compare(w, d, seed=1, draws=2000):
    m = w.merge(d, on=KEY, suffixes=("_w", "_d"))
    out = {"in_both": int(len(m)), "only_weekly": int(len(w) - len(m)), "only_daily": int(len(d) - len(m)),
           "true_identical": bool(np.allclose(m.true_w, m.true_d))}
    res = {}
    for sim, g in m.groupby("sim"):
        k = g[g.single_converged_w & g.single_converged_d]
        ew = np.abs(k.single_w - k.true_w) / k.true_w
        ed = np.abs(k.single_d - k.true_d) / k.true_d
        diff = (ed - ew).values
        rng = np.random.default_rng(seed)
        bs = [rng.choice(diff, len(diff)).mean() for _ in range(draws)]
        res[sim] = {"brand_channels": int(len(g)), "converged_both": int(len(k)),
                    "weekly": recovery(k.true_w.values, k.single_w.values, k.single_lo_w.values, k.single_hi_w.values),
                    "daily": recovery(k.true_d.values, k.single_d.values, k.single_lo_d.values, k.single_hi_d.values),
                    "share_daily_error_lower": float((diff < 0).mean()),
                    "mean_error_diff_daily_minus_weekly": float(diff.mean()),
                    "mean_error_diff_ci95": np.quantile(bs, [0.025, 0.975]).tolist()}
    out["by_simulation"] = res
    return out


def main(out="out"):
    w = pd.read_csv(Path(out) / "mmm_pooled_recovery.csv")
    d = pd.read_csv(Path(out) / "mmm_pooled_recovery_daily.csv")
    res = compare(w, d)
    json.dump(res, open(Path(out) / "same_brand_frequency_check.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:2])
