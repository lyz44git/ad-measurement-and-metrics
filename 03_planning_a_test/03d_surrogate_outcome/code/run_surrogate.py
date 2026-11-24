"""Surrogate-outcome check on the Criteo experiment (design/analysis_plan.md, hashed in logs/plan_hash.txt).

Usage: python code/run_surrogate.py <criteo-research-uplift-v2.1.csv.gz> [out_dir]
About 10 minutes on 32 cores.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pyarrow.csv as pacsv

sys.path.insert(0, str(Path(__file__).resolve().parent))
import surrogate_core as sc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SEED, DRAWS, RESAMPLE_DRAWS = 20261124, 200, 500
SIZES = [10_000, 30_000, 100_000, 300_000]
GRID = np.unique(np.logspace(3, 7, 81).astype(int))


def log(msg, t0=[time.time()]):
    print(f"[{time.time() - t0[0]:6.0f}s] {msg}", flush=True)


def load(path):
    tab = pacsv.read_csv(path).to_pandas()
    X = tab[sc.FEATURES].to_numpy(np.float32)
    return X, tab.treatment.to_numpy(np.int8), tab.visit.to_numpy(np.float64), tab.conversion.to_numpy(np.float64)


def main(src, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    X, t, visit, conv = load(src)
    n = len(t)
    log(f"loaded {n:,} rows")
    hist = np.random.default_rng(SEED).random(n) < 0.5
    exp_ = ~hist
    R = {"rows": n, "historical_rows": int(hist.sum()), "experiment_rows": int(exp_.sum())}

    # surrogate models, historical half only
    hc = hist & (t == 0)
    hv_c, hv_all = hc & (visit == 1), hist & (visit == 1)
    r0 = float(conv[hv_c].mean())
    q_ctrl = sc.fit_classifier(X[hv_c], conv[hv_c], SEED)
    q_pool = sc.fit_classifier(X[hv_all], conv[hv_all], SEED)
    resp = sc.fit_classifier(X[hc], visit[hc], SEED)
    R["historical"] = {"control_rows": int(hc.sum()), "control_visitors": int(hv_c.sum()),
                       "visitors_both_arms": int(hv_all.sum()),
                       "conversion_rate_among_control_visitors": r0}
    log("surrogate models fitted")

    Xe, te, ve, ce = X[exp_], t[exp_], visit[exp_], conv[exp_]
    del X
    q = {"surrogate_index": q_ctrl.predict_proba(Xe)[:, 1], "surrogate_index_both_arms": q_pool.predict_proba(Xe)[:, 1]}
    seg = sc.deciles(resp.predict_proba(Xe)[:, 1])
    del Xe

    point = sc.estimates(ce, ve, te, q, r0)
    boot = sc.bootstrap(ce, ve, te, q, r0, DRAWS, SEED + 1)
    log("bootstrap done")
    est = {}
    for k, v in point.items():
        e = {"estimate": v, "ci95": sc.interval(boot[k], 0.95)}
        if k != "direct":
            rel = (boot[k] - boot["direct"]) / boot["direct"]
            e |= {"relative_difference": (v - point["direct"]) / point["direct"],
                  "relative_difference_ci90": sc.interval(rel, 0.90),
                  "relative_difference_ci95": sc.interval(rel, 0.95),
                  "share_of_direct": v / point["direct"]}
        est[k] = e
    R["experiment"] = {
        "rows_by_arm": {"ad": int((te == 1).sum()), "control": int((te == 0).sum())},
        "visit_rate": {"ad": float(ve[te == 1].mean()), "control": float(ve[te == 0].mean())},
        "conversion_rate": {"ad": float(ce[te == 1].mean()), "control": float(ce[te == 0].mean())},
        "conversion_rate_among_visitors": {a: float(ce[(te == i) & (ve == 1)].mean()) for a, i in (("ad", 1), ("control", 0))},
        "mean_q_among_visitors": {a: float(q["surrogate_index"][(te == i) & (ve == 1)].mean()) for a, i in (("ad", 1), ("control", 0))},
        "visit_effect": sc.diff(ve, te), "visit_effect_se": sc.neyman_se(ve, te),
        "direct_se_neyman": sc.neyman_se(ce, te),
        "estimates": est,
    }
    rel = (boot["surrogate_index"] - boot["direct"]) / boot["direct"]
    R["decision"] = {"rule": "90% interval of (surrogate index - direct) / direct inside [-0.20, 0.20]",
                     "met": sc.equivalent(rel)}

    # test size
    s = ve * q["surrogate_index"]
    bias = point["surrogate_index"] - point["direct"]
    vd, vs = sc.per_arm_var(ce, te), sc.per_arm_var(s, te)
    R["test_size"] = {
        "bias": bias, "var_per_arm_direct": vd, "var_per_arm_surrogate": vs,
        "crossover_n_per_arm": sc.crossover(bias, sum(vd), sum(vs)),
        "grid_n": GRID.tolist(), "rmse_direct": sc.rmse_curve(GRID, 0.0, *vd).tolist(),
        "rmse_surrogate": sc.rmse_curve(GRID, bias, *vs).tolist(),
        "resampling": {str(m): sc.resample_rmse(ce, s, te, m, RESAMPLE_DRAWS, point["direct"], SEED + 2 + i)
                       for i, m in enumerate(SIZES)},
        "formula_at_sizes": {str(m): {"direct": float(sc.rmse_curve(m, 0.0, *vd)),
                                      "surrogate_index": float(sc.rmse_curve(m, bias, *vs))} for m in SIZES},
    }
    log("test-size check done")

    # segments (descriptive)
    rng = np.random.default_rng(SEED + 9)
    rows = []
    for g in range(10):
        m = seg == g
        cg, vg, tg, qg = ce[m], ve[m], te[m], {"surrogate_index": q["surrogate_index"][m]}
        pt = sc.estimates(cg, vg, tg, qg, r0)
        bd, bs = [], []
        for _ in range(DRAWS):
            w = rng.poisson(1.0, m.sum()).astype(np.float64)
            e2 = sc.estimates(cg, vg, tg, qg, r0, w)
            bd.append(e2["direct"]); bs.append(e2["surrogate_index"])
        rows.append({"decile": g, "rows": int(m.sum()), "control_visit_rate": float(vg[tg == 0].mean()),
                     "direct": pt["direct"], "direct_ci95": sc.interval(np.asarray(bd), 0.95),
                     "surrogate_index": pt["surrogate_index"], "surrogate_ci95": sc.interval(np.asarray(bs), 0.95),
                     "share_of_direct": pt["surrogate_index"] / pt["direct"] if pt["direct"] != 0 else None})
    R["segments_by_control_visit_decile"] = rows
    R["seconds"] = round(time.time() - log.__defaults__[0][0])
    (out / "surrogate.json").write_text(json.dumps(R, indent=1))
    log(json.dumps({k: R[k] for k in ("decision",)}) + f" crossover {R['test_size']['crossover_n_per_arm']}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ROOT / "out")
