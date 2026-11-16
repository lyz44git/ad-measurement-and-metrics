"""Checks of the attribution estimators on simulated data with a known effect (no Criteo data needed)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
import attribution_vs_experiment as av


def simulate(n=30_000, effect=0.15, confounded=True, seed=0):
    """Exposure D and outcome Y both depend on x0 when confounded; the effect of D on P(Y = 1) is `effect`."""
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, 3))
    s = 1 / (1 + np.exp(-2 * X[:, 0]))
    p_d = 1 / (1 + np.exp(1 - 1.5 * X[:, 0])) if confounded else np.full(n, 0.3)
    D = (rng.random(n) < p_d).astype(float)
    Y = (rng.random(n) < 0.05 + effect * D + (0.25 * s if confounded else 0.1)).astype(float)
    return Y, D, X


def test_attribution_summary_accounting():
    r = av.attribution_summary(n0=1000, n1=1000, exposed1=200, y0=100, y1=150, attributed=120)
    assert np.isclose(r["itt"], 0.05)
    assert np.isclose(r["incremental"], 50)
    assert np.isclose(r["attributed_over_incremental"], 2.4)
    assert np.isclose(r["cace"], 0.25)
    assert np.isclose(r["share_of_treated_outcomes_attributed"], 0.8)


def test_naive_difference_is_biased_under_confounding():
    Y, D, X = simulate()
    naive, se = av.naive_difference(Y, D)
    assert naive - 0.15 > 5 * se          # overstates the true effect of 0.15


def test_adjustment_recovers_the_effect():
    Y, D, X = simulate()
    naive, _ = av.naive_difference(Y, D)
    ols, _ = av.ols_adjusted(Y, D, X)
    dml, se = av.dml_plr(Y, D, X, max_iter=40)
    assert abs(ols - 0.15) < abs(naive - 0.15)
    assert abs(dml - 0.15) < 0.02
    assert abs(dml - 0.15) < 4 * se


def test_all_estimators_agree_without_confounding():
    Y, D, X = simulate(confounded=False, seed=1)
    for est, se in (av.naive_difference(Y, D), av.ols_adjusted(Y, D, X), av.dml_plr(Y, D, X, max_iter=40)):
        assert abs(est - 0.15) < 4 * se


def test_no_effect_is_not_detected():
    Y, D, X = simulate(effect=0.0, seed=2)
    dml, se = av.dml_plr(Y, D, X, max_iter=40)
    assert abs(dml) < 4 * se
