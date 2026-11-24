"""Follow-up of study 02e (design/followup_plan.md, hashed in logs/followup_plan_hash.txt).

Usage: python code/run_followup.py <criteo-research-uplift-v2.1.csv.gz> [out_dir]
Rebuilds the main run's parts, policies and moderate-setting logs with the same seeds, then runs analyses 1 to 4.
"""
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
SEED, LOGS, M, BIG_LOGS, BETA = 20261125, 200, 1_000_000, 50, 1.0


def log(msg, t0=[time.time()]):
    print(f"[{time.time() - t0[0]:6.0f}s] {msg}", flush=True)


def analyses(seed, X, a, y, e, acts, m):
    rng = np.random.default_rng(seed)
    idx = oc.draw_log(rng, a, e, m)
    Xl, al, yl, el = X[idx], a[idx], y[idx], e[idx]
    mu1, mu0, eh = oc.crossfit(Xl, al, yl, seed)
    dec = np.minimum((10 * np.argsort(np.argsort(el, kind="stable"), kind="stable")) // len(el), 9)
    cal = [{"e": float(el[dec == k].mean()), "ehat": float(eh[dec == k].mean()),
            "visit_share": float(yl[dec == k].sum() / yl.sum())} for k in range(10)]
    out = {"calibration": cal, "dr_known": {}, "dr": {}, "ips_estimated": {}, "levels": {}}
    for p in oc.POLICIES:
        act = acts[p][idx]
        r_known = oc.estimate(yl, al, act, el, mu1, mu0, el)   # outcome models with the known propensity
        r_est = oc.estimate(yl, al, act, el, mu1, mu0, eh)
        out["dr_known"][p], out["dr"][p], out["ips_estimated"][p] = r_known["dr"], r_est["dr"], r_est["ips_estimated"]
    out["levels"] = {"all_known": float((al * yl / el).mean()), "none_known": float(((1 - al) * yl / (1 - el)).mean()),
                     "all_estimated": float((al * yl / eh).mean()), "none_estimated": float(((1 - al) * yl / (1 - eh)).mean())}
    out["rows"] = int(len(idx))
    return out


def summarize(res, key, tv):
    return {p: oc.summarize([r[key][p] for r in res], tv[p]) for p in oc.POLICIES}


def main(src, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    main_res = json.loads((out / "ope.json").read_text())
    tab = pacsv.read_csv(src).to_pandas()
    X = tab[oc.FEATURES].to_numpy(np.float32); a = tab.treatment.to_numpy(np.int8)
    y = tab.visit.to_numpy(np.float64); del tab
    n = len(a); rowid = np.arange(n)
    u = np.random.default_rng(SEED).random(n)
    part = {"model": u < 0.30, "truth": (u >= 0.30) & (u < 0.65), "log": u >= 0.65}
    mp = part["model"]
    resp = oc.classifier(200, SEED, 16).fit(X[mp], y[mp])
    m1 = oc.classifier(200, SEED + 1, 16).fit(X[mp & (a == 1)], y[mp & (a == 1)])
    m0 = oc.classifier(200, SEED + 2, 16).fit(X[mp & (a == 0)], y[mp & (a == 0)])
    s_resp = resp.predict_proba(X)[:, 1]
    s_upl = m1.predict_proba(X)[:, 1] - m0.predict_proba(X)[:, 1]
    thr = {"response_20": float(np.quantile(s_resp[mp], 0.8)), "uplift_20": float(np.quantile(s_upl[mp], 0.8))}
    same_setup = thr == main_res["thresholds"]
    acts = {"all": np.ones(n, np.int8), "random_20": oc.random_fifth(rowid),
            "response_20": (s_resp > thr["response_20"]).astype(np.int8),
            "uplift_20": (s_upl > thr["uplift_20"]).astype(np.int8)}
    lz = oc.logit(s_resp); z = (lz - lz[mp].mean()) / lz[mp].std()
    tp = part["truth"]
    tv = {p: oc.truth(y[tp], a[tp], acts[p][tp])[0] for p in oc.POLICIES}
    yt, at = y[tp], a[tp]
    true_levels = {"all": float((at * yt / oc.P_TREAT).mean()), "none": float(((1 - at) * yt / (1 - oc.P_TREAT)).mean())}
    log(f"setup rebuilt; thresholds identical to the main run: {same_setup}")

    lp = part["log"]
    Xl, al, yl, zl = X[lp], a[lp], y[lp], z[lp]
    acts_l = {p: v[lp] for p, v in acts.items()}
    del X
    e = oc.logging_propensity(zl, BETA)
    res = Parallel(n_jobs=30)(delayed(analyses)(SEED + 1000 + r, Xl, al, yl, e, acts_l, M) for r in range(LOGS))
    log("analyses 1-3 done")
    big = Parallel(n_jobs=10)(delayed(analyses)(SEED + 9000 + r, Xl, al, yl, e, acts_l, len(al)) for r in range(BIG_LOGS))
    log("analysis 4 done")

    cal = [{k: float(np.mean([r["calibration"][d][k] for r in res])) for k in ("e", "ehat", "visit_share")} for d in range(10)]
    lv = {k: float(np.mean([r["levels"][k] for r in res])) for k in res[0]["levels"]}
    R = {"same_setup_as_main_run": same_setup, "true_lift": tv, "true_levels": true_levels,
         "1_propensity_calibration_by_decile_of_e": cal,
         "2_dr_with_known_propensity": summarize(res, "dr_known", tv),
         "2_dr_with_estimated_propensity": summarize(res, "dr", tv),
         "3_levels": {"mean_estimates": lv,
                      "relative_error": {"all_known": lv["all_known"] / true_levels["all"] - 1,
                                         "none_known": lv["none_known"] / true_levels["none"] - 1,
                                         "all_estimated": lv["all_estimated"] / true_levels["all"] - 1,
                                         "none_estimated": lv["none_estimated"] / true_levels["none"] - 1}},
         "4_large_logs": {"rows_mean": float(np.mean([r["rows"] for r in big])),
                          "ips_estimated": summarize(big, "ips_estimated", tv), "dr": summarize(big, "dr", tv),
                          "dr_known": summarize(big, "dr_known", tv)},
         "4_small_logs_for_comparison": {"rows_mean": float(np.mean([r["rows"] for r in res])),
                                         "ips_estimated": summarize(res, "ips_estimated", tv)}}
    R["seconds"] = round(time.time() - log.__defaults__[0][0])
    (out / "followup.json").write_text(json.dumps(R, indent=1))
    log("written")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ROOT / "out")
