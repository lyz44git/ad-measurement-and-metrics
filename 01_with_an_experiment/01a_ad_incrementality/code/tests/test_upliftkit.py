"""Checks on simulated experiments with known truth. Run: python -m pytest code/tests -q"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import upliftkit as uk

P = {"n_estimators": 60, "learning_rate": 0.1, "num_leaves": 15, "min_child_samples": 50, "n_jobs": 2, "random_state": 0}


def sim(n=60000, hetero=True, seed=0):
    r = np.random.default_rng(seed)
    X = r.normal(size=(n, 12)).astype(np.float32)
    t = (r.random(n) < 0.85).astype(np.int8)
    tau = 0.10 * (X[:, 0] > 0) if hetero else np.zeros(n)
    base = 0.20 + 0.10 * (X[:, 1] > 0)          # baseline risk driven by a different feature
    y = (r.random(n) < base + tau * t).astype(np.int8)
    return X, t, y, tau


def test_itt_recovers_known_effect():
    X, t, y, tau = sim()
    r = uk.itt(y.astype(float), t)
    assert abs(r["est"] - tau.mean()) < 3 * r["se"]


def test_aipw_agrees_with_itt_under_randomization():
    X, t, y, _ = sim()
    a, b = uk.aipw_linear(y.astype(float), t, X.astype(float)), uk.itt(y.astype(float), t)
    assert abs(a["est"] - b["est"]) < 3 * b["se"] and a["se"] <= b["se"] * 1.01


def test_cace_scales_by_compliance():
    t = np.array([1, 1, 1, 1, 0, 0]); ex = np.array([1, 0, 0, 0, 0, 0])
    assert abs(uk.cace(0.01, 0.001, ex, t)["est"] - 0.04) < 1e-12


def test_learner_detects_heterogeneity_and_response_model_does_not():
    X, t, y, _ = sim(n=200000, seed=1); Z, tz, yz, _ = sim(n=200000, seed=2)
    s = {"t_learner": uk.fit_t_learner(X, t, y, P)(Z), "response": uk.fit_response(X, y, P)(Z)}
    e = uk.evaluate(s, tz, yz, B=100, seed=0, baseline="response")
    assert e["t_learner"]["qini_ci"][0] > 0                      # detects real heterogeneity
    assert e["t_learner"]["qini_minus_baseline_ci"][0] > 0       # and beats ranking by baseline risk
    assert e["t_learner"]["top10_uplift"] > 0.07


def test_no_false_detection_under_null():
    X, t, y, _ = sim(hetero=False, seed=3); Z, tz, yz, _ = sim(hetero=False, seed=4)
    e = uk.evaluate({"t_learner": uk.fit_t_learner(X, t, y, P)(Z)}, tz, yz, B=100, seed=0)
    lo, hi = e["t_learner"]["qini_ci"]
    assert lo <= 0 <= hi


def test_x_and_dr_learners_rank_like_truth():
    X, t, y, _ = sim(seed=5); Z, _, _, tau = sim(seed=6)
    for f in (uk.fit_x_learner(X, t, y, P), uk.fit_dr_learner(X, t, y, P)):
        assert np.corrcoef(f(Z), tau)[0, 1] > 0.5


def test_bootstrap_is_seeded_and_bins_are_balanced():
    X, t, y, _ = sim(n=20000); s = {"a": X[:, 0].astype(float)}
    assert uk.evaluate(s, t, y, B=20, seed=7) == uk.evaluate(s, t, y, B=20, seed=7)
    assert np.bincount(uk.rank_bins(s["a"], 100)).tolist() == [200] * 100
