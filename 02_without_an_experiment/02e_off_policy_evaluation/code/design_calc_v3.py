"""Design calculation for the third design of study 02e: how large a log is, and how exact one log can be.

Run before design/analysis_plan_v3.md was written. It rebuilds the policies and the assignment model of the earlier
designs, then, for a grid of logging policies, computes from the pool the logs will be drawn from:
  - the keep constant c and the expected number of rows in a log;
  - the error of the naive comparison that the logging policy builds in;
  - the standard error that inverse probability weighting with the logged propensity would have on one log, from the
    variance of its per-row term under the log's distribution, and the mean absolute error this implies
    (sqrt(2/pi) x SE for a normal error).
No off-policy estimate is computed on any log here: nothing is drawn.

Usage: python code/design_calc_v3.py <criteo-research-uplift-v2.1.csv.gz> [out_dir]
"""
import json
import sys
from pathlib import Path

import numpy as np
import pyarrow.csv as pacsv

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ope_core as oc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261125
TRIM = (0.005, 0.995)
GRID = [(b, lo) for lo in (0.02, 0.10) for b in (0.1, 0.25, 0.5, 1.0)]


def setup(src):
    """Model part (30%), pool (70%), the four policies, z and the assignment probability r, as in the earlier designs."""
    tab = pacsv.read_csv(src).to_pandas()
    X = tab[oc.FEATURES].to_numpy(np.float32); a = tab.treatment.to_numpy(np.int8)
    y = tab.visit.to_numpy(np.float64); del tab
    n = len(a); u = np.random.default_rng(SEED).random(n); mp = u < 0.30
    resp = oc.classifier(200, SEED, 16).fit(X[mp], y[mp])
    m1 = oc.classifier(200, SEED + 1, 16).fit(X[mp & (a == 1)], y[mp & (a == 1)])
    m0 = oc.classifier(200, SEED + 2, 16).fit(X[mp & (a == 0)], y[mp & (a == 0)])
    s_resp = resp.predict_proba(X)[:, 1]
    s_upl = m1.predict_proba(X)[:, 1] - m0.predict_proba(X)[:, 1]
    thr = {"response_20": float(np.quantile(s_resp[mp], 0.8)), "uplift_20": float(np.quantile(s_upl[mp], 0.8))}
    acts = {"all": np.ones(n, np.int8), "random_20": oc.random_fifth(np.arange(n)),
            "response_20": (s_resp > thr["response_20"]).astype(np.int8),
            "uplift_20": (s_upl > thr["uplift_20"]).astype(np.int8)}
    lz = oc.logit(s_resp); z = (lz - lz[mp].mean()) / lz[mp].std()
    r = oc.classifier(300, SEED + 3, 32).fit(X[mp], a[mp]).predict_proba(X)[:, 1]
    lo, hi = np.quantile(r[~mp], TRIM)
    pool = (~mp) & (r >= lo) & (r <= hi)
    return X, a, y, z, r, acts, thr, pool, (float(lo), float(hi))


def propensity(z, beta, lo):
    return np.clip(1 / (1 + np.exp(-beta * z)), lo, 1 - lo)


def keep_constant(e, r):
    c = min(float(np.min(r / e)), float(np.min((1 - r) / (1 - e))))
    mag = 10 ** (np.floor(np.log10(c)) - 1)
    return float(np.floor(c / mag) * mag)


def main(src, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    X, a, y, z, r, acts, thr, pool, trim = setup(src)
    a, y, z, r = a[pool], y[pool], z[pool], r[pool]
    acts = {p: v[pool] for p, v in acts.items()}
    R = {"pool_rows": int(pool.sum()), "trim_r": trim, "grid": []}
    # reference value of each policy on the pool: IPS with r (the plan's benchmark is AIPW with r, close to it)
    ref = {}
    for p in oc.POLICIES:
        p_pi = np.where(acts[p] == 1, r, 1 - r)
        ref[p] = float(((a == acts[p]) * y / p_pi - (a == 0) * y / (1 - r)).mean())
    R["reference_ips_r_per_1000"] = {p: 1000 * v for p, v in ref.items()}
    for beta, lo in GRID:
        e = propensity(z, beta, lo); c = keep_constant(e, r)
        k = np.where(a == 1, c * e / r, c * (1 - e) / (1 - r)); n_log = float(k.sum())
        row = {"beta": beta, "clip": [lo, 1 - lo], "c": c, "log_rows": n_log,
               "treated_share": float((k * (a == 1)).sum() / n_log), "policies": {}}
        for p in oc.POLICIES:
            act = acts[p]; agree, ctrl = (a == act), (a == 0)
            naive = float((k * agree * y).sum() / (k * agree).sum() - (k * ctrl * y).sum() / (k * ctrl).sum())
            e_pi = np.where(act == 1, e, 1 - e)
            phi = agree * y / e_pi - ctrl * y / (1 - e)
            m = float((k * phi).sum() / n_log); v = float((k * (phi - m) ** 2).sum() / n_log)
            se = np.sqrt(v / n_log)
            row["policies"][p] = {"naive_error": naive / ref[p] - 1, "ips_expected_error": m / ref[p] - 1,
                                  "ips_se_share": se / ref[p], "ips_mae_share": float(np.sqrt(2 / np.pi) * se / ref[p])}
        R["grid"].append(row)
        print(beta, lo, c, round(n_log), {p: (round(d["naive_error"], 2), round(d["ips_mae_share"], 3))
                                         for p, d in row["policies"].items()}, flush=True)
    (out / "design_calc_v3.json").write_text(json.dumps(R, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ROOT / "out")
