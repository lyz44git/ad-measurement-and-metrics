"""Sampling variance of adjusted and unadjusted lift-study readouts (design/followup_plan.md).

Usage: python code/covariate_adjustment.py <criteo-research-uplift-v2.1.csv.gz> [out_dir]
Writes <out_dir>/covariate_adjustment.json. About 5 minutes and 8 GB of memory.

Readouts: D, difference in means; L, OLS on treatment and the raw features; M, OLS on treatment and a model
prediction of the outcome fitted on other users.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SIZES = (1000, 2500, 5000, 10000, 20000)
SEED = 20261116
Z = 1.959964
Z_POWER = 1.959964 + 0.841621


def diff_in_means(y, t):
    """Difference in means of y between t == 1 and t == 0, with an unequal-variance standard error."""
    y1, y0 = y[t == 1], y[t == 0]
    return y1.mean() - y0.mean(), np.sqrt(y1.var(ddof=1) / len(y1) + y0.var(ddof=1) / len(y0))


def ols_treatment(y, t, x):
    """Coefficient on t from OLS of y on an intercept, t and x (one or more columns), with an HC1 standard error."""
    x = x.reshape(len(y), -1)
    Zm = np.column_stack([np.ones(len(y)), t, x - x.mean(axis=0)])
    XtX = Zm.T @ Zm
    inv = np.linalg.pinv(XtX)
    beta = inv @ (Zm.T @ y)
    u = y - Zm @ beta
    meat = (Zm * (u ** 2)[:, None]).T @ Zm
    V = inv @ meat @ inv * len(y) / (len(y) - Zm.shape[1])
    return beta[1], np.sqrt(V[1, 1])


def read_study(y, t, X, g):
    """The three readouts of one study: estimates and standard errors in the order D, L, M."""
    d = diff_in_means(y, t)
    l = ols_treatment(y, t, X)
    m = ols_treatment(y, t, g)
    return np.array([d[0], l[0], m[0]]), np.array([d[1], l[1], m[1]])


def run_studies(y_a, X_a, g_a, y_b, X_b, g_b, n, studies, rng, aa=False):
    """Estimates and standard errors of `studies` studies with n users per arm.

    Arm 1 is drawn from population a and arm 0 from population b. With aa=True both arms are disjoint samples of
    population b, so the true effect is zero. Returns two arrays of shape (studies, 3).
    """
    est = np.zeros((studies, 3)); se = np.zeros((studies, 3))
    t = np.r_[np.ones(n), np.zeros(n)]
    for s in range(studies):
        if aa:
            idx = rng.choice(len(y_b), 2 * n, replace=False)
            i1, i0 = idx[:n], idx[n:]
            y = np.r_[y_b[i1], y_b[i0]]; X = np.vstack([X_b[i1], X_b[i0]]); g = np.r_[g_b[i1], g_b[i0]]
        else:
            i1 = rng.choice(len(y_a), n, replace=False); i0 = rng.choice(len(y_b), n, replace=False)
            y = np.r_[y_a[i1], y_b[i0]]; X = np.vstack([X_a[i1], X_b[i0]]); g = np.r_[g_a[i1], g_b[i0]]
        est[s], se[s] = read_study(y.astype(float), t, X.astype(float), g.astype(float))
    return est, se


def summarize(est, se, est_aa, se_aa, n, rng, boot=2000):
    """Per-readout summary of one sample size (see design/followup_plan.md, step 5)."""
    names = ("D", "L", "M")
    sd = est.std(axis=0, ddof=1)
    k = len(est)
    idx = rng.integers(0, k, (boot, k))
    out = {}
    for j, name in enumerate(names):
        ratio = (est[:, j].var(ddof=1) / est[:, 0].var(ddof=1))
        bs = est[idx, j].var(axis=1, ddof=1) / est[idx, 0].var(axis=1, ddof=1)
        out[name] = {
            "sd": float(sd[j]), "mean_estimate": float(est[:, j].mean()),
            "variance_ratio_to_D": float(ratio), "variance_ratio_ci": np.quantile(bs, [0.025, 0.975]).tolist(),
            "mean_se_over_sd": float(se[:, j].mean() / sd[j]),
            "coverage95": float((np.abs(est[:, j] - est[:, j].mean()) <= Z * se[:, j]).mean()),
            "aa_rejection": float((np.abs(est_aa[:, j]) > Z * se_aa[:, j]).mean()),
            "mde80": float(Z_POWER * sd[j]), "n_times_variance": float(n * sd[j] ** 2),
        }
    return out


def required_n(by_n, name, lift=0.01):
    """Users per arm needed to detect `lift` with 80% power, from the mean of n x variance over the sizes."""
    s2 = np.mean([v[name]["n_times_variance"] for v in by_n.values()])
    return float((Z_POWER / lift) ** 2 * s2)


def decision(by_n, name):
    """The rule of design/followup_plan.md for readout `name`."""
    return bool(all(v[name]["variance_ratio_ci"][1] < 1 and 0.035 <= v[name]["aa_rejection"] <= 0.065
                    and v[name]["coverage95"] >= 0.93 for v in by_n.values()))


def main(src, out_dir, studies=2000):
    import duckdb
    import lightgbm as lgb
    from sklearn.metrics import roc_auc_score

    cols = ", ".join(f"f{i}" for i in range(12))
    d = duckdb.connect().execute(f"select treatment, visit, {cols} from read_csv_auto('{src}')").fetchnumpy()
    T = d["treatment"].astype(np.int8); Y = d["visit"].astype(np.int8)
    X = np.column_stack([d[f"f{i}"] for i in range(12)]).astype(np.float32)
    del d
    rng = np.random.default_rng(SEED)
    model_half = rng.random(len(Y)) < 0.5
    fit = model_half & (T == 0)
    clf = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=63, min_child_samples=200,
                             random_state=0, n_jobs=16, verbose=-1).fit(X[fit], Y[fit])
    st = ~model_half
    Ys, Ts, Xs = Y[st], T[st], X[st]
    g = clf.predict_proba(Xs)[:, 1].astype(np.float32)
    a, b = Ts == 1, Ts == 0
    res = {
        "users": int(len(Y)), "model_half_control_users": int(fit.sum()), "study_half": int(st.sum()),
        "study_half_ad_arm": int(a.sum()), "study_half_control_arm": int(b.sum()), "studies_per_n": studies,
        "auc_of_g_in_study_half_control": float(roc_auc_score(Ys[b], g[b])),
        "r2_of_g_in_study_half_control": float(np.corrcoef(Ys[b], g[b])[0, 1] ** 2),
        "by_n": {},
    }
    yf, tf = Ys.astype(float), Ts.astype(float)
    full = [diff_in_means(yf, Ts)[0], ols_treatment(yf, tf, Xs.astype(float))[0], ols_treatment(yf, tf, g.astype(float))[0]]
    res["study_half_estimates"] = dict(zip(("D", "L", "M"), map(float, full)))
    for n in SIZES:
        est, se = run_studies(Ys[a], Xs[a], g[a], Ys[b], Xs[b], g[b], n, studies, rng)
        est_aa, se_aa = run_studies(None, None, None, Ys[b], Xs[b], g[b], n, studies, rng, aa=True)
        res["by_n"][n] = summarize(est, se, est_aa, se_aa, n, rng)
        print(n, {k: round(v["variance_ratio_to_D"], 3) for k, v in res["by_n"][n].items()}, flush=True)
    res["required_n_one_point_lift"] = {k: required_n(res["by_n"], k) for k in ("D", "L", "M")}
    res["rule_met"] = {k: decision(res["by_n"], k) for k in ("L", "M")}
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    json.dump(res, open(Path(out_dir) / "covariate_adjustment.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "by_n"}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ROOT / "out")
