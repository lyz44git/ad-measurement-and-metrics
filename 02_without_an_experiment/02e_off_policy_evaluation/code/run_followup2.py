"""Second follow-up of study 02e (design/followup_plan_2.md, hashed in logs/followup_plan_2_hash.txt).

Usage: python code/run_followup2.py <criteo-research-uplift-v2.1.csv.gz> [out_dir]
"""
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
import pyarrow.csv as pacsv
from joblib import Parallel, delayed
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ope_core as oc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SEED, M, WEIGHT_LOGS = 20261125, 1_000_000, 50


def log(msg, t0=[time.time()]):
    print(f"[{time.time() - t0[0]:6.0f}s] {msg}", flush=True)


def aipw_lift(y, a, act, mu1, mu0, p):
    """Lift V(pi) - V(none) by AIPW with assignment probability p (array or scalar)."""
    p = np.broadcast_to(p, y.shape)
    mu_pi = np.where(act == 1, mu1, mu0); p_pi = np.where(act == 1, p, 1 - p)
    phi = (mu_pi + (a == act) * (y - mu_pi) / p_pi) - (mu0 + (a == 0) * (y - mu0) / (1 - p))
    return float(phi.mean()), float(phi.std(ddof=1) / np.sqrt(len(y)))


def weights(seed, X, a, y, e):
    idx = oc.draw_log(np.random.default_rng(seed), a, e, M)
    Xl, al, yl, el = X[idx], a[idx], y[idx], e[idx]
    _, _, eh = oc.crossfit(Xl, al, yl, seed)
    top = el > np.quantile(el, 0.9); c = top & (al == 0); cy = c & (yl == 1)
    return {"control_rows": int(c.sum()), "w_true": float((1 / (1 - el[c])).mean()), "w_hat": float((1 / (1 - eh[c])).mean()),
            "w_true_visit": float((1 / (1 - el[cy])).mean()), "w_hat_visit": float((1 / (1 - eh[cy])).mean())}


def main(src, out):
    out = Path(out)
    main_res = json.loads((out / "ope.json").read_text())
    tab = pacsv.read_csv(src).to_pandas()
    X = tab[oc.FEATURES].to_numpy(np.float32); a = tab.treatment.to_numpy(np.int8)
    y = tab.visit.to_numpy(np.float64); del tab
    n = len(a); rowid = np.arange(n)
    u = np.random.default_rng(SEED).random(n)
    mp, tp, lp = u < 0.30, (u >= 0.30) & (u < 0.65), u >= 0.65
    resp = oc.classifier(200, SEED, 16).fit(X[mp], y[mp])
    m1 = oc.classifier(200, SEED + 1, 16).fit(X[mp & (a == 1)], y[mp & (a == 1)])
    m0 = oc.classifier(200, SEED + 2, 16).fit(X[mp & (a == 0)], y[mp & (a == 0)])
    s_resp = resp.predict_proba(X)[:, 1]
    s_upl = m1.predict_proba(X)[:, 1] - m0.predict_proba(X)[:, 1]
    thr = {"response_20": float(np.quantile(s_resp[mp], 0.8)), "uplift_20": float(np.quantile(s_upl[mp], 0.8))}
    acts = {"all": np.ones(n, np.int8), "random_20": oc.random_fifth(rowid),
            "response_20": (s_resp > thr["response_20"]).astype(np.int8),
            "uplift_20": (s_upl > thr["uplift_20"]).astype(np.int8)}
    lz = oc.logit(s_resp); z = (lz - lz[mp].mean()) / lz[mp].std()
    log(f"setup rebuilt; thresholds identical to the main run: {thr == main_res['thresholds']}")

    # 1 and 2 on the truth part
    Xt, at, yt = X[tp], a[tp], y[tp]
    mu1, mu0, _ = oc.crossfit(Xt, at, yt, SEED + 500, n_jobs=32)
    rhat_raw = np.empty(len(at)); fold = np.random.default_rng(SEED + 500).integers(0, 2, len(at))
    auc = []
    for k in range(2):
        tr, te = fold != k, fold == k
        rhat_raw[te] = oc.classifier(300, SEED + 510 + k, 32).fit(Xt[tr], at[tr]).predict_proba(Xt[te])[:, 1]
        auc.append(roc_auc_score(at[te], rhat_raw[te]))
    log("truth-part models fitted")
    truth = {}
    for p in oc.POLICIES:
        act = acts[p][tp]
        unadj = oc.truth(yt, at, act)
        adj = aipw_lift(yt, at, act, mu1, mu0, oc.P_TREAT)
        p_pi = np.where(act == 1, rhat_raw, 1 - rhat_raw)
        phi = (at == act) * yt / p_pi - (at == 0) * yt / (1 - rhat_raw)
        truth[p] = {"unadjusted_ips": 1000 * unadj[0], "unadjusted_se": 1000 * unadj[1],
                    "aipw_constant_p": 1000 * adj[0], "aipw_se": 1000 * adj[1],
                    "ips_estimated_assignment": 1000 * float(phi.mean()),
                    "aipw_over_unadjusted": adj[0] / unadj[0]}
    R = {"1_truth_part": truth,
         "2_assignment_model": {"heldout_auc_by_fold": auc, "assigned_share": float(at.mean()),
                                "estimated_assignment_quantiles": [float(q) for q in np.quantile(rhat_raw, [0.01, 0.1, 0.5, 0.9, 0.99])]}}

    # 3: main-run estimates against both truths
    rows = list(csv.DictReader(open(out / "ope_logs.csv")))
    err = {}
    for p in oc.POLICIES:
        err[p] = {}
        for k in oc.ESTIMATORS:
            x = np.array([float(r["estimate"]) for r in rows if r["setting"] == "moderate" and r["policy"] == p and r["estimator"] == k])
            err[p][k] = {"vs_unadjusted": float(1000 * x.mean() / truth[p]["unadjusted_ips"] - 1),
                         "vs_adjusted": float(1000 * x.mean() / truth[p]["aipw_constant_p"] - 1)}
    R["3_moderate_errors_against_both_truths"] = err

    # 4: inverse weights of control rows in the top decile of e
    e = oc.logging_propensity(z[lp], 1.0)
    w = Parallel(n_jobs=25)(delayed(weights)(SEED + 1000 + r, X[lp], a[lp], y[lp], e) for r in range(WEIGHT_LOGS))
    R["4_top_decile_control_weights"] = {k: float(np.mean([d[k] for d in w])) for k in w[0]}
    R["seconds"] = round(time.time() - log.__defaults__[0][0])
    (out / "followup2.json").write_text(json.dumps(R, indent=1))
    log(json.dumps({p: round(v["aipw_over_unadjusted"], 3) for p, v in truth.items()}) + f" auc {[round(x, 4) for x in auc]}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ROOT / "out")
