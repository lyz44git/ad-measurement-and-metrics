"""Policies, biased logs and off-policy estimators (design/analysis_plan.md), kept free of file paths for testing."""
import numpy as np

FEATURES = [f"f{i}" for i in range(12)]
P_TREAT = 0.85          # assignment probability of the randomized experiment
KEEP = 0.15             # share of rows kept by the rejection sampler
E_CLIP, EHAT_CLIP = (0.02, 0.98), (0.01, 0.99)
POLICIES = ["all", "random_20", "response_20", "uplift_20"]
ESTIMATORS = ["naive", "dm", "ips_known", "ips_estimated", "snips", "dr"]
LGBM = dict(objective="binary", learning_rate=0.05, num_leaves=63, min_child_samples=200, subsample=0.5,
            subsample_freq=1, colsample_bytree=0.8, verbose=-1)


def classifier(n_estimators, seed, n_jobs):
    import lightgbm as lgb
    return lgb.LGBMClassifier(**LGBM, n_estimators=n_estimators, random_state=seed, n_jobs=n_jobs)


def random_fifth(rowid):
    """A fixed pseudo-random 20% of rows, from a multiplicative hash of the row number."""
    h = (np.asarray(rowid, dtype=np.uint64) * np.uint64(2654435761)) % np.uint64(2 ** 32)
    return (h.astype(np.float64) / 2 ** 32 < 0.2).astype(np.int8)


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def logging_propensity(z, beta):
    return np.clip(1 / (1 + np.exp(-beta * z)), *E_CLIP)


def draw_log(rng, a, e, m):
    """Rows of a randomized experiment (assignment prob P_TREAT) kept so that P(A = 1 | x) = e(x) among kept rows.

    Draws m candidate rows without replacement, then keeps a treated row with prob KEEP * e / P_TREAT and a control
    row with prob KEEP * (1 - e) / (1 - P_TREAT). Returns the indices of the kept rows.
    """
    cand = rng.choice(len(a), m, replace=False)
    ac, ec = a[cand], e[cand]
    keep_p = np.where(ac == 1, KEEP * ec / P_TREAT, KEEP * (1 - ec) / (1 - P_TREAT))
    return np.sort(cand[rng.random(m) < keep_p])


def truth(y, a, act):
    """Policy lift V(pi) - V(none) by inverse probability weighting with the known assignment probability."""
    p_pi = np.where(act == 1, P_TREAT, 1 - P_TREAT)
    phi = (a == act) * y / p_pi - (a == 0) * y / (1 - P_TREAT)
    return float(phi.mean()), float(phi.std(ddof=1) / np.sqrt(len(y)))


def crossfit(X, a, y, seed, n_estimators=300, n_jobs=1, folds=2):
    """Out-of-fold predictions of mu_1(x), mu_0(x) and e_hat(x). 300 trees: design/deviations.md, item 1."""
    rng = np.random.default_rng(seed)
    fold = rng.integers(0, folds, len(y))
    mu1, mu0, eh = np.empty(len(y)), np.empty(len(y)), np.empty(len(y))
    for k in range(folds):
        tr, te = fold != k, fold == k
        for arm, out in ((1, mu1), (0, mu0)):
            m = tr & (a == arm)
            out[te] = classifier(n_estimators, seed + k, n_jobs).fit(X[m], y[m]).predict_proba(X[te])[:, 1]
        eh[te] = classifier(n_estimators, seed + 10 + k, n_jobs).fit(X[tr], a[tr]).predict_proba(X[te])[:, 1]
    return mu1, mu0, np.clip(eh, *EHAT_CLIP)


def _ci(phi):
    est, se = float(phi.mean()), float(phi.std(ddof=1) / np.sqrt(len(phi)))
    return est, [est - 1.96 * se, est + 1.96 * se]


def estimate(y, a, act, e_known, mu1, mu0, eh):
    """All estimators of V(pi) - V(none) on one log. act: the policy's action for each logged row."""
    agree, ctrl = (a == act), (a == 0)
    mu_pi = np.where(act == 1, mu1, mu0)
    ek_pi = np.where(act == 1, e_known, 1 - e_known)
    eh_pi = np.where(act == 1, eh, 1 - eh)
    out = {"naive": {"estimate": float(y[agree].mean() - y[ctrl].mean())},
           "dm": {"estimate": float(mu_pi.mean() - mu0.mean())}}
    phi_k = agree * y / ek_pi - ctrl * y / (1 - e_known)
    phi_e = agree * y / eh_pi - ctrl * y / (1 - eh)
    phi_dr = (mu_pi + agree * (y - mu_pi) / eh_pi) - (mu0 + ctrl * (y - mu0) / (1 - eh))
    for name, phi in (("ips_known", phi_k), ("ips_estimated", phi_e), ("dr", phi_dr)):
        est, ci = _ci(phi)
        out[name] = {"estimate": est, "ci95": ci}
    w_pi, w_0 = agree / eh_pi, ctrl / (1 - eh)
    out["snips"] = {"estimate": float((w_pi @ y) / w_pi.sum() - (w_0 @ y) / w_0.sum())}
    return out


def summarize(estimates, true_value):
    """Bias, RMSE and coverage over logs for one policy and estimator. estimates: list of dicts from `estimate`."""
    x = np.array([e["estimate"] for e in estimates])
    res = {"mean": float(x.mean()), "bias": float(x.mean() - true_value),
           "relative_bias": float((x.mean() - true_value) / true_value),
           "rmse": float(np.sqrt(((x - true_value) ** 2).mean())),
           "relative_rmse": float(np.sqrt(((x - true_value) ** 2).mean()) / abs(true_value))}
    if "ci95" in estimates[0]:
        lo = np.array([e["ci95"][0] for e in estimates]); hi = np.array([e["ci95"][1] for e in estimates])
        res["coverage95"] = float(((lo <= true_value) & (true_value <= hi)).mean())
        res["mean_ci_width"] = float((hi - lo).mean())
    return res


def same_order(est_by_policy, true_by_policy, policies):
    """True if the estimates rank `policies` in the same order as the truth."""
    order = lambda d: tuple(sorted(policies, key=lambda p: d[p]))
    return order(est_by_policy) == order(true_by_policy)


def decision(summary_moderate, true_values, max_rel_bias=0.10, min_coverage=0.90):
    rows = {p: summary_moderate[p]["dr"] for p in POLICIES}
    ok = {p: abs(r["relative_bias"]) < max_rel_bias and r["coverage95"] >= min_coverage for p, r in rows.items()}
    return {"met": all(ok.values()), "by_policy": ok}


# ----------------------------------------------------------------------------- second design (analysis_plan_v2.md)

def keep_constant(e_settings, r):
    """Largest c, rounded down to two significant digits, with every keep probability <= 1 in every setting."""
    c = min(min(float(np.min(r / e)), float(np.min((1 - r) / (1 - e)))) for e in e_settings)
    mag = 10 ** (np.floor(np.log10(c)) - 1)
    return float(np.floor(c / mag) * mag)


def draw_log_assigned(rng, a, e, r, m, c):
    """Rows of an experiment whose assignment probability is r(x), kept so that P(A = 1 | x) = e(x) among kept rows.

    Keeps a treated row with prob c * e / r and a control row with prob c * (1 - e) / (1 - r).
    """
    cand = rng.choice(len(a), m, replace=False)
    ac, ec, rc = a[cand], e[cand], r[cand]
    keep_p = np.where(ac == 1, c * ec / rc, c * (1 - ec) / (1 - rc))
    return np.sort(cand[rng.random(m) < keep_p])


def aipw_lift(y, a, act, mu1, mu0, p):
    """Policy lift V(pi) - V(none) by AIPW with assignment probability p (array or scalar): estimate and SE."""
    p = np.broadcast_to(np.asarray(p, dtype=float), y.shape)
    mu_pi = np.where(act == 1, mu1, mu0); p_pi = np.where(act == 1, p, 1 - p)
    phi = (mu_pi + (a == act) * (y - mu_pi) / p_pi) - (mu0 + (a == 0) * (y - mu0) / (1 - p))
    return float(phi.mean()), float(phi.std(ddof=1) / np.sqrt(len(y)))


# ----------------------------------------------------------------------------- accuracy of one log (design/erratum.md)

def accuracy(x, true_value):
    """Errors of the estimates x from many logs against one benchmark value, as shares of that value.

    mean_error is the error of the average estimate (its absolute value is what `decision` and run_ope_v2.py compared
    with 10%). mean_absolute_error is the average size of one log's error, which is what the text of
    analysis_plan_v2.md names. The first can be near zero while the second is large."""
    x = np.asarray(x, dtype=float); t = float(true_value)
    return {"mean_error": float((x.mean() - t) / t), "mean_absolute_error": float(np.abs(x - t).mean() / abs(t)),
            "median_absolute_error": float(np.median(np.abs(x - t)) / abs(t))}


def rule_as_written(acc, coverage, max_mae=0.10, min_coverage=0.90):
    """The decision rule of analysis_plan_v2.md read literally: mean absolute error below 10% and coverage of 90%."""
    return bool(acc["mean_absolute_error"] < max_mae and coverage >= min_coverage)


# ----------------------------------------------------------------------------- third design (analysis_plan_v3.md)

def draw_log_pool(rng, a, e, r, c):
    """As draw_log_assigned, with every row of the pool a candidate. Returns the indices of the kept rows."""
    keep_p = np.where(a == 1, c * e / r, c * (1 - e) / (1 - r))
    return np.flatnonzero(rng.random(len(a)) < keep_p)
