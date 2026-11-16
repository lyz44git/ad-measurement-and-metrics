"""Part 1: Beta-Binomial posterior vs frequentist difference in means (plan Part 1).

Usage: python code/02_overall_bayes.py <derived_dir> <out_dir>
"""
import sys
from pathlib import Path
import json, duckdb, numpy as np
F, OUT = Path(sys.argv[1]) / "criteo_compact.parquet", Path(sys.argv[2])
agg = duckdb.sql(f"select treatment, count(*) n, sum(visit) v, sum(conversion) c from '{F}' group by 1 order by 1").fetchall()
rng = np.random.default_rng(20261115); D = 200_000
res = {"n_users": int(sum(a[1] for a in agg))}
for k, name in ((2, "visit"), (3, "conversion")):
    n0, y0 = agg[0][1], agg[0][k]; n1, y1 = agg[1][1], agg[1][k]
    p0 = rng.beta(1 + y0, 1 + n0 - y0, D); p1 = rng.beta(1 + y1, 1 + n1 - y1, D)
    d, rel = p1 - p0, p1 / p0 - 1
    m0, m1 = y0 / n0, y1 / n1; se = np.sqrt(m0 * (1 - m0) / n0 + m1 * (1 - m1) / n1)
    res[name] = {"n0": n0, "n1": n1, "rate0": m0, "rate1": m1,
                 "bayes_lift_mean": float(d.mean()), "bayes_lift_ci95": [float(x) for x in np.quantile(d, [.025, .975])],
                 "bayes_rel_mean": float(rel.mean()), "bayes_rel_ci95": [float(x) for x in np.quantile(rel, [.025, .975])],
                 "p_lift_gt_0": float((d > 0).mean()),
                 "freq_lift": m1 - m0, "freq_ci95": [m1 - m0 - 1.96 * se, m1 - m0 + 1.96 * se]}
json.dump(res, open(OUT / "part1_overall.json", "w"), indent=1)
print(json.dumps(res, indent=1))
