"""upliftkit: incrementality, CATE learners and held-out targeting tests for randomized experiments.

Extends the workflow of the randomized-price reanalysis (hashed plan, seeded routines, pytest checks)
to large two-arm experiments. Everything is plain numpy / LightGBM so it runs offline.
"""
from __future__ import annotations

import numpy as np
import lightgbm as lgb

FEATURES = [f"f{i}" for i in range(12)]


# ---------------------------------------------------------------- incrementality
def itt(y, t):
    """Difference in means with Neyman standard error."""
    y1, y0 = y[t == 1], y[t == 0]
    est = y1.mean() - y0.mean()
    se = np.sqrt(y1.var(ddof=1) / len(y1) + y0.var(ddof=1) / len(y0))
    return {"est": float(est), "se": float(se), "control_mean": float(y0.mean()),
            "relative_lift": float(est / y0.mean()), "n1": int(len(y1)), "n0": int(len(y0))}


def aipw_linear(y, t, X):
    """AIPW with arm-specific linear outcome models and the treated share as propensity."""
    e = t.mean()
    Xc = np.column_stack([np.ones(len(y)), X - X.mean(0)])
    mu = {}
    for a in (0, 1):
        m = t == a
        beta, *_ = np.linalg.lstsq(Xc[m].T @ Xc[m], Xc[m].T @ y[m], rcond=None)
        mu[a] = Xc @ beta
    psi = mu[1] - mu[0] + t * (y - mu[1]) / e - (1 - t) * (y - mu[0]) / (1 - e)
    return {"est": float(psi.mean()), "se": float(psi.std(ddof=1) / np.sqrt(len(y)))}


def smd(X, t):
    """Standardized mean differences, treated minus control."""
    a, b = X[t == 1], X[t == 0]
    return (a.mean(0) - b.mean(0)) / np.sqrt((a.var(0) + b.var(0)) / 2)


def cace(itt_est, itt_se, exposure, t):
    """Wald estimator under one-sided non-compliance."""
    pi = exposure[t == 1].mean()
    return {"est": float(itt_est / pi), "se": float(itt_se / pi), "compliance": float(pi)}


# ---------------------------------------------------------------- learners
def _clf(params):
    return lgb.LGBMClassifier(**params, verbose=-1)


def _reg(params):
    return lgb.LGBMRegressor(**params, verbose=-1)


def fit_response(X, y, params):
    m = _clf(params).fit(X, y)
    return lambda Z: m.predict_proba(Z)[:, 1]


def fit_t_learner(X, t, y, params, return_models=False):
    m1 = _clf(params).fit(X[t == 1], y[t == 1])
    m0 = _clf(params).fit(X[t == 0], y[t == 0])
    f = lambda Z: m1.predict_proba(Z)[:, 1] - m0.predict_proba(Z)[:, 1]
    return (f, m1, m0) if return_models else f


def fit_x_learner(X, t, y, params, g=None):
    g = t.mean() if g is None else g
    m1 = _clf(params).fit(X[t == 1], y[t == 1])
    m0 = _clf(params).fit(X[t == 0], y[t == 0])
    d1 = y[t == 1] - m0.predict_proba(X[t == 1])[:, 1]
    d0 = m1.predict_proba(X[t == 0])[:, 1] - y[t == 0]
    tau1 = _reg(params).fit(X[t == 1], d1)
    tau0 = _reg(params).fit(X[t == 0], d0)
    return lambda Z: g * tau0.predict(Z) + (1 - g) * tau1.predict(Z)


def fit_dr_learner(X, t, y, params, seed=0, clip=(0.05, 0.95)):
    """Two-fold cross-fitted AIPW pseudo-outcome regressed on X."""
    n = len(y)
    fold = np.random.default_rng(seed).integers(0, 2, n)
    pseudo = np.empty(n)
    for k in (0, 1):
        tr, te = fold != k, fold == k
        m1 = _clf(params).fit(X[tr & (t == 1)], y[tr & (t == 1)])
        m0 = _clf(params).fit(X[tr & (t == 0)], y[tr & (t == 0)])
        e = np.clip(_clf(params).fit(X[tr], t[tr]).predict_proba(X[te])[:, 1], *clip)
        mu1, mu0 = m1.predict_proba(X[te])[:, 1], m0.predict_proba(X[te])[:, 1]
        pseudo[te] = mu1 - mu0 + t[te] * (y[te] - mu1) / e - (1 - t[te]) * (y[te] - mu0) / (1 - e)
    m = _reg(params).fit(X, pseudo)
    return lambda Z: m.predict(Z)


def fit_causal_forest(X, t, y, cfg, seed=0):
    from econml.dml import CausalForestDML
    idx = np.random.default_rng(seed).choice(len(y), min(cfg["subsample"], len(y)), replace=False)
    small = {"n_estimators": 100, "learning_rate": 0.1, "num_leaves": 31, "n_jobs": cfg["n_jobs"]}
    cf = CausalForestDML(model_y=_reg(small), model_t=_clf(small), discrete_treatment=True,
                         n_estimators=cfg["n_estimators"], min_samples_leaf=cfg["min_samples_leaf"],
                         cv=2, random_state=seed, n_jobs=cfg["n_jobs"])
    cf.fit(y[idx].astype(float), t[idx], X=X[idx])
    return lambda Z: cf.effect(Z).ravel()


# ---------------------------------------------------------------- evaluation
def rank_bins(score, n_bins=100):
    """Bin 0 = highest scores. Ties broken by position, deterministically."""
    order = np.argsort(-score, kind="stable")
    b = np.empty(len(score), dtype=np.int32)
    b[order] = (np.arange(len(score)) * n_bins // len(score)).astype(np.int32)
    return b


def _curve(b, t, y, w, n_bins):
    nt = np.bincount(b, weights=w * t, minlength=n_bins)
    nc = np.bincount(b, weights=w * (1 - t), minlength=n_bins)
    yt = np.bincount(b, weights=w * t * y, minlength=n_bins)
    yc = np.bincount(b, weights=w * (1 - t) * y, minlength=n_bins)
    return nt, nc, yt, yc


def qini_from_counts(nt, nc, yt, yc):
    """Qini coefficient per user: area between the gain curve and the random line."""
    Nt, Nc, Yt, Yc = (np.cumsum(v) for v in (nt, nc, yt, yc))
    gain = (Yt - Yc * Nt / np.maximum(Nc, 1e-12)) / (nt.sum() + nc.sum())
    frac = (Nt + Nc) / (nt.sum() + nc.sum())
    qini = float(np.mean(gain - gain[-1] * frac))
    return qini, gain, frac


def top_uplift(nt, nc, yt, yc, k):
    """Realized difference in means among the top k bins."""
    return float(yt[:k].sum() / nt[:k].sum() - yc[:k].sum() / nc[:k].sum())


def evaluate(scores: dict, t, y, n_bins=100, B=200, seed=0, baseline=None):
    """Qini, top-decile/quintile uplift and Poisson-bootstrap CIs; paired difference vs `baseline`."""
    t = t.astype(float); y = y.astype(float)
    bins = {k: rank_bins(s, n_bins) for k, s in scores.items()}
    one = np.ones(len(y))
    out, draws = {}, {k: [] for k in scores}
    for k, b in bins.items():
        c = _curve(b, t, y, one, n_bins)
        q, gain, frac = qini_from_counts(*c)
        out[k] = {"qini": q, "top10_uplift": top_uplift(*c, n_bins // 10),
                  "top20_uplift": top_uplift(*c, n_bins // 5),
                  "share_incremental_top20": float(gain[n_bins // 5 - 1] / gain[-1])}
    rng = np.random.default_rng(seed)
    for _ in range(B):
        w = rng.poisson(1.0, len(y)).astype(float)
        for k, b in bins.items():
            draws[k].append(qini_from_counts(*_curve(b, t, y, w, n_bins))[0])
    for k in scores:
        d = np.array(draws[k])
        out[k]["qini_ci"] = [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]
        if baseline and k != baseline:
            diff = d - np.array(draws[baseline])
            out[k]["qini_minus_baseline"] = float(out[k]["qini"] - out[baseline]["qini"])
            out[k]["qini_minus_baseline_ci"] = [float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5))]
    return out


def calibration(score, t, y, n_bins=10):
    """Predicted vs realized uplift by score decile (bin 0 = highest)."""
    b = rank_bins(score, n_bins)
    rows = []
    for k in range(n_bins):
        m = b == k
        r = itt(y[m], t[m])
        rows.append({"decile": k + 1, "predicted": float(score[m].mean()), "realized": r["est"], "se": r["se"]})
    return rows
