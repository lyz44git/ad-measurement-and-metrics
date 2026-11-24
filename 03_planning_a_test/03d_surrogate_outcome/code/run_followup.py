"""Follow-up of study 03d: feature-adjusted estimates (design/followup_plan.md, hashed in logs/followup_plan_hash.txt).

Usage: python code/run_followup.py <criteo-research-uplift-v2.1.csv.gz> [out_dir]
Rebuilds the main run's split and surrogate model with the same seeds. About 15 minutes on 32 cores.
"""
import json
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import surrogate_core as sc  # noqa: E402
from run_surrogate import load, SEED  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REG = {k: v for k, v in sc.LGBM.items() if k != "objective"} | {"objective": "regression", "n_estimators": 300}
CLF = sc.LGBM | {"n_estimators": 300}


def log(msg, t0=[time.time()]):
    print(f"[{time.time() - t0[0]:6.0f}s] {msg}", flush=True)


def crossfit_outcome(X, t, y, binary, seed):
    fold = np.random.default_rng(seed).integers(0, 2, len(y))
    mu1, mu0 = np.empty(len(y)), np.empty(len(y))
    for k in range(2):
        tr, te = fold != k, fold == k
        for arm, out in ((1, mu1), (0, mu0)):
            m = tr & (t == arm)
            if binary:
                out[te] = lgb.LGBMClassifier(**CLF, random_state=seed + k, n_jobs=32).fit(X[m], y[m]).predict_proba(X[te])[:, 1]
            else:
                out[te] = lgb.LGBMRegressor(**REG, random_state=seed + k, n_jobs=32).fit(X[m], y[m]).predict(X[te])
    return mu1, mu0


def phi(y, t, mu1, mu0, r):
    return mu1 + t * (y - mu1) / r - mu0 - (1 - t) * (y - mu0) / (1 - r)


def summarize(p_s, p_c):
    n = len(p_c); ms, mc = p_s.mean(), p_c.mean(); theta = ms / mc
    se_ratio = float(np.sqrt(np.var(p_s - theta * p_c, ddof=1) / n) / abs(mc))
    return {"direct": float(mc), "direct_se": float(p_c.std(ddof=1) / np.sqrt(n)),
            "surrogate_index": float(ms), "surrogate_se": float(p_s.std(ddof=1) / np.sqrt(n)),
            "share_of_direct": float(theta), "share_ci95": [float(theta - 1.96 * se_ratio), float(theta + 1.96 * se_ratio)]}


def main(src, out):
    out = Path(out)
    main_res = json.loads((out / "surrogate.json").read_text())
    X, t, visit, conv = load(src)
    n = len(t)
    hist = np.random.default_rng(SEED).random(n) < 0.5
    exp_ = ~hist
    hv_c = hist & (t == 0) & (visit == 1)
    q_ctrl = sc.fit_classifier(X[hv_c], conv[hv_c], SEED)
    assign = lgb.LGBMClassifier(**CLF, random_state=SEED + 5, n_jobs=32).fit(X[hist], t[hist])
    Xe, te, ve, ce = X[exp_], t[exp_].astype(float), visit[exp_], conv[exp_]
    s = ve * q_ctrl.predict_proba(Xe)[:, 1]
    r = assign.predict_proba(Xe)[:, 1]
    R = {"main_run_surrogate_index": main_res["experiment"]["estimates"]["surrogate_index"]["estimate"],
         "rebuilt_surrogate_index_unadjusted": float(sc.diff(s, te.astype(np.int8))),
         "assignment_model": {"quantiles": [float(q) for q in np.quantile(r, [0.01, 0.1, 0.5, 0.9, 0.99])]}}
    from sklearn.metrics import roc_auc_score
    R["assignment_model"]["auc_experiment_half"] = float(roc_auc_score(te, r))
    log(f"rebuilt: surrogate unadjusted {R['rebuilt_surrogate_index_unadjusted']:.6f} vs main {R['main_run_surrogate_index']:.6f}")
    mc1, mc0 = crossfit_outcome(Xe, te, ce, True, SEED + 10)
    ms1, ms0 = crossfit_outcome(Xe, te, s, False, SEED + 20)
    mv1, mv0 = crossfit_outcome(Xe, te, ve, True, SEED + 30)
    log("outcome models fitted")
    share = float(te.mean())
    for name, rr in (("aipw_estimated_assignment", r), ("aipw_constant_share", np.full(len(te), share))):
        p_c, p_s, p_v = phi(ce, te, mc1, mc0, rr), phi(s, te, ms1, ms0, rr), phi(ve, te, mv1, mv0, rr)
        R[name] = summarize(p_s, p_c) | {"visit_effect": float(p_v.mean()), "visit_effect_se": float(p_v.std(ddof=1) / np.sqrt(len(p_v)))}
    R["unadjusted"] = {"direct": main_res["experiment"]["estimates"]["direct"]["estimate"],
                       "surrogate_index": main_res["experiment"]["estimates"]["surrogate_index"]["estimate"],
                       "share_of_direct": main_res["experiment"]["estimates"]["surrogate_index"]["share_of_direct"],
                       "visit_effect": main_res["experiment"]["visit_effect"]}
    a = R["aipw_estimated_assignment"]
    R["reading"] = {"conclusion_holds": bool(a["share_ci95"][1] < 0.80),
                    "rule": "adjusted ratio of surrogate to direct effect below 0.80 with its 95% interval below 0.80"}
    R["seconds"] = round(time.time() - log.__defaults__[0][0])
    (out / "followup.json").write_text(json.dumps(R, indent=1))
    log(json.dumps({k: (round(R[k]["share_of_direct"], 3), [round(x, 3) for x in R[k]["share_ci95"]]) for k in ("aipw_estimated_assignment", "aipw_constant_share")}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ROOT / "out")
