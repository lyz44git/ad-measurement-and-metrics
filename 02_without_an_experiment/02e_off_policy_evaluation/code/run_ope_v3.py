"""Third design of study 02e: logs of 1.4 to 1.6 million rows and a rule on one log's error (design/analysis_plan_v3.md).

Usage: python code/run_ope_v3.py <criteo-research-uplift-v2.1.csv.gz> [out_dir]
About two hours on 32 cores.
"""
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
from joblib import Parallel, delayed

sys.path.insert(0, str(Path(__file__).resolve().parent))
import design_calc_v3 as dc  # noqa: E402
import ope_core as oc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261125
SETTINGS = {"mild": (0.1, 100), "moderate": (0.25, 200), "strong": (1.0, 100)}   # beta, logs
RULE_POLICIES = ["all", "response_20", "uplift_20"]
TWENTY = ["random_20", "response_20", "uplift_20"]
ESTIMATORS = oc.ESTIMATORS + ["dr_known"]


def log(msg, t0=[time.time()]):
    print(f"[{time.time() - t0[0]:6.0f}s] {msg}", flush=True)


def one_log(seed, X, a, y, e, r, acts, c):
    rng = np.random.default_rng(seed)
    idx = oc.draw_log_pool(rng, a, e, r, c)
    Xl, al, yl, el = X[idx], a[idx], y[idx], e[idx]
    mu1, mu0, eh = oc.crossfit(Xl, al, yl, seed)
    res = {}
    for p in oc.POLICIES:
        act = acts[p][idx]
        d = oc.estimate(yl, al, act, el, mu1, mu0, eh)
        d["dr_known"] = oc.estimate(yl, al, act, el, mu1, mu0, el)["dr"]
        res[p] = d
    return res, {"rows": int(len(idx)), "treated_share": float(al.mean()),
                 "ehat_abs_error_mean": float(np.abs(eh - el).mean())}


def main(src, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    X, a, y, z, r, acts, thr, pool, trim = dc.setup(src)
    X, a, y, z, r = X[pool], a[pool], y[pool], z[pool], r[pool]
    acts = {p: v[pool] for p, v in acts.items()}
    R = {"pool_rows": int(len(a)), "trim_r": trim, "thresholds": thr}
    log(f"pool of {len(a):,} rows")

    mu1, mu0, _ = oc.crossfit(X, a, y, SEED + 800, n_jobs=32)
    R["benchmark"] = {}
    for p in oc.POLICIES:
        act = acts[p]
        est, se = oc.aipw_lift(y, a, act, mu1, mu0, r)
        p_pi = np.where(act == 1, r, 1 - r)
        ips = float(((a == act) * y / p_pi - (a == 0) * y / (1 - r)).mean())
        R["benchmark"][p] = {"aipw_r": 1000 * est, "aipw_r_se": 1000 * se, "ips_r": 1000 * ips,
                             "unadjusted": 1000 * oc.truth(y, a, act)[0]}
    del mu1, mu0
    tv = {p: R["benchmark"][p]["aipw_r"] / 1000 for p in oc.POLICIES}
    log("benchmark: " + json.dumps({p: round(1000 * v, 3) for p, v in tv.items()}))

    rows, R["settings"] = [], {}
    for si, (name, (beta, n_logs)) in enumerate(SETTINGS.items()):
        e = oc.logging_propensity(z, beta); c = dc.keep_constant(e, r)
        seeds = [SEED + 30000 + 1000 * si + k for k in range(n_logs)]
        res = Parallel(n_jobs=30)(delayed(one_log)(s, X, a, y, e, r, acts, c) for s in seeds)
        log(f"{name}: {n_logs} logs done")
        S = {"beta": beta, "keep_constant": c, "logs": n_logs,
             "log_rows_mean": float(np.mean([x[1]["rows"] for x in res])),
             "log_treated_share_mean": float(np.mean([x[1]["treated_share"] for x in res])),
             "ehat_abs_error_mean": float(np.mean([x[1]["ehat_abs_error_mean"] for x in res])), "summary": {}}
        for p in oc.POLICIES:
            S["summary"][p] = {}
            for k in ESTIMATORS:
                ests = [x[0][p][k] for x in res]
                d = oc.summarize(ests, tv[p]) | oc.accuracy([q["estimate"] for q in ests], tv[p])
                S["summary"][p][k] = d
        S["same_order_as_benchmark_for_20pct_policies"] = {
            k: float(np.mean([oc.same_order({p: x[0][p][k]["estimate"] for p in TWENTY}, tv, TWENTY) for x in res]))
            for k in ESTIMATORS}
        R["settings"][name] = S
        for i, x in enumerate(res):
            for p in oc.POLICIES:
                for k in ESTIMATORS:
                    d = x[0][p][k]; lo, hi = d.get("ci95", [None, None])
                    rows.append([name, i, p, k, d["estimate"], lo, hi])
        (out / "ope_v3_partial.json").write_text(json.dumps(R, indent=1))

    def rule(key):
        s = R["settings"]["moderate"]["summary"]
        ok = {p: oc.rule_as_written(s[p][key], s[p][key]["coverage95"]) for p in RULE_POLICIES}
        return {"met": all(ok.values()), "by_policy": ok,
                "mean_absolute_error": {p: s[p][key]["mean_absolute_error"] for p in RULE_POLICIES},
                "coverage95": {p: s[p][key]["coverage95"] for p in RULE_POLICIES}}
    R["decision"] = {"rule": "moderate setting; all, response_20 and uplift_20: mean absolute error of one log below 10% "
                             "of the benchmark and 95% interval coverage of at least 90%",
                     "1_ips_logged_propensity": rule("ips_known"), "2_dr_estimated_propensity": rule("dr")}
    R["seconds"] = round(time.time() - log.__defaults__[0][0])
    (out / "ope_v3.json").write_text(json.dumps(R, indent=1))
    (out / "ope_v3_partial.json").unlink()
    with open(out / "ope_v3_logs.csv", "w", newline="") as f:
        wr = csv.writer(f); wr.writerow(["setting", "log", "policy", "estimator", "estimate", "ci_low", "ci_high"]); wr.writerows(rows)
    log("decision " + json.dumps({k: v["met"] for k, v in R["decision"].items() if k != "rule"}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ROOT / "out")
