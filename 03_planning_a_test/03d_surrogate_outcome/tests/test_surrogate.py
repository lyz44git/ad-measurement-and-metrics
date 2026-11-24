"""Checks of the surrogate estimators on simulated experiments with a known answer."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
import surrogate_core as sc


def experiment(n=400_000, extra_conversion_per_visit=0.0, seed=0):
    """Visits depend on x and assignment; conversion requires a visit and converts at q(x), raised in the ad arm
    by `extra_conversion_per_visit` (zero when visits carry the whole effect)."""
    rng = np.random.default_rng(seed)
    x = rng.normal(size=n)
    t = (rng.random(n) < 0.5).astype(np.int8)
    p_visit = 1 / (1 + np.exp(-(-3 + 0.8 * x + 0.4 * t)))
    visit = (rng.random(n) < p_visit).astype(float)
    q = 1 / (1 + np.exp(-(-2 + 0.5 * x)))
    q_arm = np.clip(q * (1 + extra_conversion_per_visit * t), 0, 1)
    conv = visit * (rng.random(n) < q_arm)
    return x, t, visit, conv, q


def test_difference_and_standard_error():
    y = np.array([1.0, 0, 1, 1, 0, 0]); t = np.array([1, 1, 1, 0, 0, 0])
    assert np.isclose(sc.diff(y, t), 2 / 3 - 1 / 3)
    assert sc.neyman_se(y, t) > 0


def test_surrogate_index_recovers_the_effect_when_visits_carry_it():
    x, t, visit, conv, q = experiment()
    e = sc.estimates(conv, visit, t, {"surrogate_index": q}, r0=0.1)
    se = sc.neyman_se(conv, t)
    assert abs(e["surrogate_index"] - e["direct"]) < 3 * se


def test_surrogate_index_understates_when_ads_also_raise_conversion_per_visit():
    x, t, visit, conv, q = experiment(extra_conversion_per_visit=0.5, seed=1)
    e = sc.estimates(conv, visit, t, {"surrogate_index": q}, r0=0.1)
    assert e["surrogate_index"] / e["direct"] < 0.85


def test_bootstrap_and_equivalence_rule():
    x, t, visit, conv, q = experiment(n=100_000, seed=2)
    b = sc.bootstrap(conv, visit, t, {"surrogate_index": q}, 0.1, draws=50, seed=3)
    assert set(b) == {"direct", "visit_x_fixed_rate", "surrogate_index"} and len(b["direct"]) == 50
    assert sc.equivalent(np.full(100, 0.05)) and not sc.equivalent(np.linspace(-0.3, 0.1, 100))


def test_crossover_is_where_the_two_error_curves_meet():
    bias, vd, vs = 2e-4, (3e-3, 2e-3), (1e-3, 5e-4)
    n = sc.crossover(bias, sum(vd), sum(vs))
    assert np.isclose(sc.rmse_curve(n, 0.0, *vd), sc.rmse_curve(n, bias, *vs))
    assert sc.rmse_curve(n / 4, 0.0, *vd) > sc.rmse_curve(n / 4, bias, *vs)
    assert sc.rmse_curve(4 * n, 0.0, *vd) < sc.rmse_curve(4 * n, bias, *vs)
    assert sc.crossover(0.0, 1.0, 0.5) is None and sc.crossover(1e-3, 0.5, 1.0) is None


def test_resampled_error_of_the_direct_estimate_matches_the_formula():
    x, t, visit, conv, q = experiment(n=300_000, seed=4)
    target = sc.diff(conv, t)
    r = sc.resample_rmse(conv, visit * q, t, 5_000, draws=300, target=target, seed=5)
    formula = sc.rmse_curve(5_000, 0.0, *sc.per_arm_var(conv, t))
    assert abs(r["direct"] / formula - 1) < 0.15


def test_deciles():
    d = sc.deciles(np.arange(1000)[::-1].astype(float))
    assert np.bincount(d).tolist() == [100] * 10 and d[0] == 9
