"""Second design of study 02e: logs and truth built on the estimated assignment probability (design/analysis_plan_v2.md).

Usage: python code/run_ope_v2.py <criteo-research-uplift-v2.1.csv.gz> [out_dir]
About 25 minutes on 32 cores.
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
SEED, LOGS, M, WEIGHT_LOGS = 20261125, 200, 2_000_000, 50
SETTINGS = {"moderate": 1.0, "strong": 2.0}
TWENTY = ["random_20", "response_20", "uplift_20"]
ESTIMATORS = oc.ESTIMATORS + ["dr_known"]


def log(msg, t0=[time.time()]):
    print(f"[{time.time() - t0[0]:6.0f}s] {msg}", flush=True)


def one_log(seed, X, a, y, e, r, acts, c, weights):
    rng = np.random.default_rng(seed)
    idx = oc.draw_log_assigned(rng, a, e, r, M, c)
    Xl, al, yl, el = X[idx], a[idx], y[idx], e[idx]
    mu1, mu0, eh = oc.crossfit(Xl, al, yl, seed)
    res = {}
    for p in oc.POLICIES:
        act = acts[p][idx]
        d = oc.estimate(yl, al, act, el, mu1, mu0, eh)
        d["dr_known"] = oc.estimate(yl, al, act, el, mu1, mu0, el)["dr"]
        res[p] = d
    st = {"rows": int(len(idx)), "treated_share": float(al.mean())}
    if weights:
        top = el > np.quantile(el, 0.9); cm = top & (al == 0); cy = cm & (yl == 1)
        st |= {"w_true": float((1 / (1 - el[cm])).mean()), "w_hat": float((1 / (1 - eh[cm])).mean()),
               "w_true_visit": float((1 / (1 - el[cy])).mean()), "w_hat_visit": float((1 / (1 - eh[cy])).mean())}
    return res, st


def main(src, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
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
    assign = oc.classifier(300, SEED + 3, 32).fit(X[mp], a[mp])
    r = assign.predict_proba(X)[:, 1]
    R = {"same_policies_as_first_design": thr == main_res["thresholds"],
         "assignment_model": {"auc_truth_part": float(roc_auc_score(a[tp], r[tp])), "auc_log_part": float(roc_auc_score(a[lp], r[lp])),
                              "quantiles_log_part": [float(q) for q in np.quantile(r[lp], [0, .01, .1, .5, .9, .99, 1])]}}
    log(f"setup rebuilt (policies identical: {R['same_policies_as_first_design']}); assignment AUC {R['assignment_model']['auc_log_part']:.4f}")

    # truth: AIPW with r on the whole log part, and replications
    def aipw_part(part, seed):
        Xp, ap, yp, rp = X[part], a[part], y[part], r[part]
        mu1, mu0, _ = oc.crossfit(Xp, ap, yp, seed, n_jobs=32)
        res = {}
        for p in oc.POLICIES:
            act = acts[p][part]
            est, se = oc.aipw_lift(yp, ap, act, mu1, mu0, rp)
            est_c, se_c = oc.aipw_lift(yp, ap, act, mu1, mu0, oc.P_TREAT)
            p_pi = np.where(act == 1, rp, 1 - rp)
            ipw_r = float(((ap == act) * yp / p_pi - (ap == 0) * yp / (1 - rp)).mean())
            unadj = oc.truth(yp, ap, act)
            res[p] = {"aipw_r": 1000 * est, "aipw_r_se": 1000 * se, "aipw_constant": 1000 * est_c,
                      "ips_r": 1000 * ipw_r, "unadjusted": 1000 * unadj[0]}
        return res
    R["truth_log_part"] = aipw_part(lp, SEED + 600)
    R["truth_truth_part"] = aipw_part(tp, SEED + 700)
    tv = {p: R["truth_log_part"][p]["aipw_r"] / 1000 for p in oc.POLICIES}
    log("truth: " + json.dumps({p: round(1000 * v, 3) for p, v in tv.items()}))

    Xl, al, yl, zl, rl = X[lp], a[lp], y[lp], z[lp], r[lp]
    acts_l = {p: v[lp] for p, v in acts.items()}
    del X
    es = {k: oc.logging_propensity(zl, b) for k, b in SETTINGS.items()}
    c = oc.keep_constant(list(es.values()), rl)
    R["keep_constant"] = c
    rows, R["settings"] = [], {}
    for si, (name, beta) in enumerate(SETTINGS.items()):
        e = es[name]
        seeds = [SEED + 20000 + 1000 * si + k for k in range(LOGS)]
        res = Parallel(n_jobs=30)(delayed(one_log)(s, Xl, al, yl, e, rl, acts_l, c, name == "moderate" and k < WEIGHT_LOGS)
                                  for k, s in enumerate(seeds))
        log(f"{name}: {LOGS} logs done")
        est = {p: {k: [x[0][p][k] for x in res] for k in ESTIMATORS} for p in oc.POLICIES}
        summ = {p: {k: oc.summarize(est[p][k], tv[p]) for k in ESTIMATORS} for p in oc.POLICIES}
        order = {k: float(np.mean([oc.same_order({p: x[0][p][k]["estimate"] for p in TWENTY}, tv, TWENTY) for x in res]))
                 for k in ESTIMATORS}
        st = [x[1] for x in res]
        S = {"beta": beta, "log_rows_mean": float(np.mean([s["rows"] for s in st])),
             "log_treated_share_mean": float(np.mean([s["treated_share"] for s in st])),
             "summary": summ, "same_order_as_truth_for_20pct_policies": order}
        if name == "moderate":
            w = [s for s in st if "w_true" in s]
            S["top_decile_control_weights"] = {k: float(np.mean([s[k] for s in w])) for k in ("w_true", "w_hat", "w_true_visit", "w_hat_visit")}
        R["settings"][name] = S
        for i, x in enumerate(res):
            for p in oc.POLICIES:
                for k in ESTIMATORS:
                    d = x[0][p][k]; lo, hi = d.get("ci95", [None, None])
                    rows.append([name, i, p, k, d["estimate"], lo, hi])

    def rule(key):
        s = R["settings"]["moderate"]["summary"]
        ok = {p: abs(s[p][key]["relative_bias"]) < 0.10 and s[p][key]["coverage95"] >= 0.90 for p in oc.POLICIES}
        return {"met": all(ok.values()), "by_policy": ok}
    R["decision"] = {"1_known_propensity_ips": rule("ips_known"), "2_dr_estimated_propensity": rule("dr")}
    R["seconds"] = round(time.time() - log.__defaults__[0][0])
    (out / "ope_v2.json").write_text(json.dumps(R, indent=1))
    with open(out / "ope_v2_logs.csv", "w", newline="") as f:
        wr = csv.writer(f); wr.writerow(["setting", "log", "policy", "estimator", "estimate", "ci_low", "ci_high"]); wr.writerows(rows)
    log("decision " + json.dumps({k: v["met"] for k, v in R["decision"].items()}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ROOT / "out")
