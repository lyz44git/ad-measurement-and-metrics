"""Checks of the log construction and the off-policy estimators on a simulated experiment with a known answer."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
import ope_core as oc


def experiment(n=600_000, seed=0):
    """Randomized at P_TREAT; visits rise with x and with assignment, more so for high x."""
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, 3)).astype(np.float32)
    a = (rng.random(n) < oc.P_TREAT).astype(np.int8)
    p0 = 1 / (1 + np.exp(-(-2.5 + 1.0 * X[:, 0])))
    p1 = 1 / (1 + np.exp(-(-2.5 + 1.0 * X[:, 0] + 0.3 + 0.3 * X[:, 1])))
    y = (rng.random(n) < np.where(a == 1, p1, p0)).astype(float)
    return X, a, y, p0, p1


def test_random_fifth_is_fixed_and_about_twenty_percent():
    r = oc.random_fifth(np.arange(200_000))
    assert abs(r.mean() - 0.2) < 0.005 and (r == oc.random_fifth(np.arange(200_000))).all()


def test_truth_recovers_the_policy_lift():
    X, a, y, p0, p1 = experiment()
    act = (X[:, 1] > 0).astype(np.int8)
    true_lift = float(np.where(act == 1, p1 - p0, 0).mean())
    est, se = oc.truth(y, a, act)
    assert abs(est - true_lift) < 3 * se


def test_log_has_the_target_propensity_and_the_same_features():
    X, a, y, p0, p1 = experiment(seed=1)
    e = oc.logging_propensity(X[:, 0], beta=1.0)
    idx = oc.draw_log(np.random.default_rng(2), a, e, m=500_000)
    assert abs(len(idx) / 500_000 - oc.KEEP) < 0.005
    hi = X[idx, 0] > 1
    assert abs(a[idx][hi].mean() - e[idx][hi].mean()) < 0.01
    assert abs(X[idx, 0].mean() - X[:, 0].mean()) < 0.02


def test_ipw_and_dr_are_close_to_the_truth_and_the_naive_comparison_is_not():
    X, a, y, p0, p1 = experiment(seed=3)
    act = np.ones(len(y), dtype=np.int8)
    true_lift = float((p1 - p0).mean())
    e = oc.logging_propensity(X[:, 0], beta=1.5)
    idx = oc.draw_log(np.random.default_rng(4), a, e, m=600_000)
    Xl, al, yl, el = X[idx], a[idx], y[idx], e[idx]
    mu1, mu0, eh = oc.crossfit(Xl, al, yl, seed=5, n_jobs=8)
    r = oc.estimate(yl, al, act[idx], el, mu1, mu0, eh)
    for k in ("ips_known", "ips_estimated", "dr"):
        lo, hi = r[k]["ci95"]
        assert lo - 0.002 <= true_lift <= hi + 0.002, k
    assert abs(r["naive"]["estimate"] - true_lift) > 0.02


def test_too_few_trees_compress_the_propensity_model():
    """The reason for design/deviations.md, item 1."""
    X, a, y, p0, p1 = experiment(seed=3)
    e = oc.logging_propensity(X[:, 0], beta=1.5)
    idx = oc.draw_log(np.random.default_rng(4), a, e, m=600_000)
    low = e[idx] < 0.05
    eh100 = oc.crossfit(X[idx], a[idx], y[idx], seed=5, n_estimators=100, n_jobs=8)[2]
    eh300 = oc.crossfit(X[idx], a[idx], y[idx], seed=5, n_jobs=8)[2]
    assert eh100[low].mean() - e[idx][low].mean() > 0.05
    assert abs(eh300[low].mean() - e[idx][low].mean()) < 0.01


def test_summary_and_ordering():
    ests = [{"estimate": v, "ci95": [v - 1, v + 1]} for v in (0.9, 1.1, 1.0)]
    s = oc.summarize(ests, 1.0)
    assert np.isclose(s["bias"], 0.0) and s["coverage95"] == 1.0
    assert oc.same_order({"a": 1, "b": 2}, {"a": 0.5, "b": 3}, ["a", "b"])
    assert not oc.same_order({"a": 2, "b": 1}, {"a": 0.5, "b": 3}, ["a", "b"])


def uneven_experiment(n=800_000, seed=7):
    """Assignment probability rises with x0, which also raises visits: a pooled release with uneven test shares."""
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, 3)).astype(np.float32)
    r = np.clip(0.85 + 0.03 * X[:, 0], 0.78, 0.92)
    a = (rng.random(n) < r).astype(np.int8)
    p0 = 1 / (1 + np.exp(-(-2.5 + 1.0 * X[:, 0])))
    p1 = 1 / (1 + np.exp(-(-2.5 + 1.0 * X[:, 0] + 0.3 + 0.3 * X[:, 1])))
    y = (rng.random(n) < np.where(a == 1, p1, p0)).astype(float)
    return X, a, y, r, p0, p1


def test_constant_assignment_truth_is_biased_when_shares_are_uneven_and_aipw_with_r_is_not():
    X, a, y, r, p0, p1 = uneven_experiment()
    act = np.ones(len(y), dtype=np.int8)
    true_lift = float((p1 - p0).mean())
    naive_truth, se = oc.truth(y, a, act)
    assert naive_truth - true_lift > 5 * se
    est, se2 = oc.aipw_lift(y, a, act, p1, p0, r)
    assert abs(est - true_lift) < 3 * se2


def test_log_built_on_the_assignment_probability_has_the_target_propensity():
    X, a, y, r, p0, p1 = uneven_experiment(seed=8)
    e = oc.logging_propensity(X[:, 0], beta=1.0)
    c = oc.keep_constant([e], r)
    assert c * np.max(np.maximum(e / r, (1 - e) / (1 - r))) <= 1
    idx = oc.draw_log_assigned(np.random.default_rng(9), a, e, r, 600_000, c)
    hi = X[idx, 0] > 1
    assert abs(a[idx][hi].mean() - e[idx][hi].mean()) < 0.015
    act = np.ones(len(idx), dtype=np.int8)
    true_lift = float((p1 - p0).mean())
    r_ = oc.estimate(y[idx], a[idx], act, e[idx], p1[idx], p0[idx], e[idx])
    lo, hi_ = r_["ips_known"]["ci95"]
    assert lo - 0.003 <= true_lift <= hi_ + 0.003


def test_mean_absolute_error_is_not_the_absolute_mean_error():
    # estimates centered on the truth but spread widely: no bias, large error of a single log
    rng = np.random.default_rng(3); truth = 0.01
    x = truth + rng.normal(0, 0.003, 5000)
    acc = oc.accuracy(x, truth)
    assert abs(acc["mean_error"]) < 0.02
    assert 0.20 < acc["mean_absolute_error"] < 0.28            # E|N(0, 0.3)| = 0.3 * sqrt(2 / pi) = 0.239
    assert acc["mean_absolute_error"] >= abs(acc["mean_error"])
    assert not oc.rule_as_written(acc, coverage=0.95)           # coverage alone does not meet the rule
    assert oc.rule_as_written(oc.accuracy(truth + rng.normal(0, 0.0005, 5000), truth), coverage=0.95)
    assert not oc.rule_as_written(oc.accuracy(truth + rng.normal(0, 0.0005, 5000), truth), coverage=0.85)
