"""Off-policy evaluation of targeting policies on logs built from the Criteo experiment (design/analysis_plan.md).

Usage: python code/run_ope.py <criteo-research-uplift-v2.1.csv.gz> [out_dir]
About 10 minutes on 32 cores.
"""
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
import pyarrow.csv as pacsv
from joblib import Parallel, delayed

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ope_core as oc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SEED, LOGS, M = 20261125, 200, 1_000_000
SETTINGS = {"moderate": 1.0, "strong": 2.0}
TWENTY = ["random_20", "response_20", "uplift_20"]


def log(msg, t0=[time.time()]):
    print(f"[{time.time() - t0[0]:6.0f}s] {msg}", flush=True)


def one_log(seed, X, a, y, e, acts):
    rng = np.random.default_rng(seed)
    idx = oc.draw_log(rng, a, e, M)
    Xl, al, yl, el = X[idx], a[idx], y[idx], e[idx]
    mu1, mu0, eh = oc.crossfit(Xl, al, yl, seed)
    res = {p: oc.estimate(yl, al, acts[p][idx], el, mu1, mu0, eh) for p in oc.POLICIES}
    stats = {"rows": int(len(idx)), "treated_share": float(al.mean()), "visit_rate": float(yl.mean()),
             "max_weight_known": float(np.max(1 / np.minimum(el, 1 - el))),
             "ehat_abs_error_mean": float(np.abs(eh - el).mean())}
    return res, stats


def main(src, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    tab = pacsv.read_csv(src).to_pandas()
    X = tab[oc.FEATURES].to_numpy(np.float32); a = tab.treatment.to_numpy(np.int8)
    y = tab.visit.to_numpy(np.float64); del tab
    n = len(a); rowid = np.arange(n)
    u = np.random.default_rng(SEED).random(n)
    part = {"model": u < 0.30, "truth": (u >= 0.30) & (u < 0.65), "log": u >= 0.65}
    log(f"loaded {n:,} rows; parts {[int(v.sum()) for v in part.values()]}")

    mp = part["model"]
    resp = oc.classifier(200, SEED, 16).fit(X[mp], y[mp])
    m1 = oc.classifier(200, SEED + 1, 16).fit(X[mp & (a == 1)], y[mp & (a == 1)])
    m0 = oc.classifier(200, SEED + 2, 16).fit(X[mp & (a == 0)], y[mp & (a == 0)])
    s_resp = resp.predict_proba(X)[:, 1]
    s_upl = m1.predict_proba(X)[:, 1] - m0.predict_proba(X)[:, 1]
    thr = {"response_20": float(np.quantile(s_resp[mp], 0.8)), "uplift_20": float(np.quantile(s_upl[mp], 0.8))}
    acts = {"all": np.ones(n, np.int8), "random_20": oc.random_fifth(rowid),
            "response_20": (s_resp > thr["response_20"]).astype(np.int8),
            "uplift_20": (s_upl > thr["uplift_20"]).astype(np.int8)}
    lz = oc.logit(s_resp)
    z = (lz - lz[mp].mean()) / lz[mp].std()
    log("policies fitted")

    tp = part["truth"]
    true = {p: oc.truth(y[tp], a[tp], acts[p][tp]) for p in oc.POLICIES}
    R = {"rows": n, "parts": {k: int(v.sum()) for k, v in part.items()}, "thresholds": thr,
         "share_treated_by_policy_truth_part": {p: float(acts[p][tp].mean()) for p in oc.POLICIES},
         "truth_per_1000_users": {p: {"lift": 1000 * v[0], "se": 1000 * v[1]} for p, v in true.items()},
         "truth_visit_rate_control": float(y[tp & (a == 0)].mean()), "settings": {}}
    tv = {p: v[0] for p, v in true.items()}
    log("truth: " + json.dumps({p: round(1000 * v, 3) for p, v in tv.items()}))

    lp = part["log"]
    Xl, al, yl, zl = X[lp], a[lp], y[lp], z[lp]
    acts_l = {p: v[lp] for p, v in acts.items()}
    del X
    rows = []
    for si, (name, beta) in enumerate(SETTINGS.items()):
        e = oc.logging_propensity(zl, beta)
        seeds = [SEED + 1000 * (si + 1) + r for r in range(LOGS)]
        res = Parallel(n_jobs=30)(delayed(one_log)(s, Xl, al, yl, e, acts_l) for s in seeds)
        log(f"{name}: {LOGS} logs done")
        est = {p: {k: [r[0][p][k] for r in res] for k in oc.ESTIMATORS} for p in oc.POLICIES}
        summ = {p: {k: oc.summarize(est[p][k], tv[p]) for k in oc.ESTIMATORS} for p in oc.POLICIES}
        order = {k: float(np.mean([oc.same_order({p: r[0][p][k]["estimate"] for p in TWENTY}, tv, TWENTY) for r in res]))
                 for k in oc.ESTIMATORS}
        st = [r[1] for r in res]
        R["settings"][name] = {
            "beta": beta, "logging_propensity_quantiles": [float(q) for q in np.quantile(e, [0, .05, .25, .5, .75, .95, 1])],
            "log_rows_mean": float(np.mean([s["rows"] for s in st])),
            "log_treated_share_mean": float(np.mean([s["treated_share"] for s in st])),
            "propensity_model_abs_error_mean": float(np.mean([s["ehat_abs_error_mean"] for s in st])),
            "summary": summ, "same_order_as_truth_for_20pct_policies": order}
        for i, r in enumerate(res):
            for p in oc.POLICIES:
                for k in oc.ESTIMATORS:
                    d = r[0][p][k]; lo, hi = d.get("ci95", [None, None])
                    rows.append([name, i, p, k, d["estimate"], lo, hi])
    R["decision"] = oc.decision(R["settings"]["moderate"]["summary"], tv)
    R["decision"]["rule"] = ("moderate setting: DR mean absolute bias below 10% of the true lift and 95% coverage of at "
                             "least 90% for each of the four policies")
    R["seconds"] = round(time.time() - log.__defaults__[0][0])
    (out / "ope.json").write_text(json.dumps(R, indent=1))
    with open(out / "ope_logs.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["setting", "log", "policy", "estimator", "estimate", "ci_low", "ci_high"])
        w.writerows(rows)
    log("decision " + json.dumps(R["decision"]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ROOT / "out")
