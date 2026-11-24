"""Estimators of a conversion effect from visits (design/analysis_plan.md), kept free of file paths for testing."""
import numpy as np

FEATURES = [f"f{i}" for i in range(12)]
LGBM = dict(objective="binary", n_estimators=200, learning_rate=0.05, num_leaves=63, min_child_samples=200,
            subsample=0.5, subsample_freq=1, colsample_bytree=0.8, verbose=-1)


def fit_classifier(X, y, seed, n_jobs=16):
    import lightgbm as lgb
    return lgb.LGBMClassifier(**LGBM, random_state=seed, n_jobs=n_jobs).fit(X, y)


def diff(y, t, w=None):
    """Difference in (weighted) means between t == 1 and t == 0."""
    w = np.ones(len(y)) if w is None else w
    w1, w0 = w * (t == 1), w * (t == 0)
    return float((w1 @ y) / w1.sum() - (w0 @ y) / w0.sum())


def neyman_se(y, t):
    y1, y0 = y[t == 1], y[t == 0]
    return float(np.sqrt(y1.var(ddof=1) / len(y1) + y0.var(ddof=1) / len(y0)))


def estimates(conv, visit, t, q, r0, w=None):
    """Direct, fixed-rate and surrogate-index estimates of the effect on the conversion rate.

    q: dict name -> fitted P(conversion | visit = 1, X) for each row, one entry per surrogate model;
    r0: conversion rate among visitors of the historical control arm.
    """
    out = {"direct": diff(conv, t, w), "visit_x_fixed_rate": r0 * diff(visit, t, w)}
    for name, qq in q.items():
        out[name] = diff(visit * qq, t, w)
    return out


def bootstrap(conv, visit, t, q, r0, draws, seed):
    """Poisson bootstrap of rows; returns name -> array of draws. The fitted q is held fixed."""
    rng = np.random.default_rng(seed)
    res = {k: [] for k in ["direct", "visit_x_fixed_rate", *q]}
    for _ in range(draws):
        w = rng.poisson(1.0, len(t)).astype(np.float64)
        for k, v in estimates(conv, visit, t, q, r0, w).items():
            res[k].append(v)
    return {k: np.asarray(v) for k, v in res.items()}


def interval(x, level):
    a = (1 - level) / 2
    return [float(np.quantile(x, a)), float(np.quantile(x, 1 - a))]


def equivalent(rel_draws, margin=0.20, level=0.90):
    """True if the `level` percentile interval of the relative difference lies inside [-margin, margin]."""
    lo, hi = interval(rel_draws, level)
    return bool(lo > -margin and hi < margin)


def per_arm_var(y, t):
    return float(y[t == 1].var(ddof=1)), float(y[t == 0].var(ddof=1))


def rmse_curve(n, bias, var1, var0):
    """Root mean squared error of an estimator with this bias at n users per arm (equal arms)."""
    n = np.asarray(n, dtype=float)
    return np.sqrt(bias ** 2 + var1 / n + var0 / n)


def crossover(bias, var_direct, var_surr):
    """n per arm at which sqrt(var_direct_sum / n) equals sqrt(bias^2 + var_surr_sum / n).

    var_direct and var_surr are the sums of the two per-arm variances. None if the surrogate never wins
    (it is less precise) or never loses (no bias).
    """
    gap = var_direct - var_surr
    if gap <= 0 or bias == 0:
        return None
    return float(gap / bias ** 2)


def resample_rmse(conv, s, t, n, draws, target, seed):
    """RMSE against `target` of the direct and surrogate estimators on draws of n rows per arm without replacement."""
    rng = np.random.default_rng(seed)
    i1, i0 = np.flatnonzero(t == 1), np.flatnonzero(t == 0)
    d_err, s_err = [], []
    for _ in range(draws):
        a = rng.choice(i1, n, replace=False)
        b = rng.choice(i0, n, replace=False)
        d_err.append(conv[a].mean() - conv[b].mean() - target)
        s_err.append(s[a].mean() - s[b].mean() - target)
    d_err, s_err = np.asarray(d_err), np.asarray(s_err)
    return {"direct": float(np.sqrt((d_err ** 2).mean())), "surrogate_index": float(np.sqrt((s_err ** 2).mean())),
            "surrogate_index_mean_error": float(s_err.mean())}


def deciles(score):
    """Decile index 0..9 of a score (ties broken by order)."""
    r = np.argsort(np.argsort(score, kind="stable"), kind="stable")
    return (10 * r // len(score)).astype(np.int8)
