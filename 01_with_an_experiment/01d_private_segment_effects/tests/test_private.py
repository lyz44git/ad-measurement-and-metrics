"""Checks of the Laplace release, the no-pooling estimator and its variance, and allocation (no data or NumPyro)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
import private_core as pc


def counts(rng, n=2000, p=(0.04, 0.05)):
    nn = np.full((pc.S, 2), float(n))
    return nn, np.column_stack([rng.binomial(n, p[0], pc.S), rng.binomial(n, p[1], pc.S)]).astype(float)


def test_release_adds_laplace_noise_of_scale_two_over_epsilon():
    rng = np.random.default_rng(0)
    n, y = counts(rng)
    nn, yy, b = pc.laplace_release(n, y, 0.5, rng)
    assert b == 4.0
    draws = np.concatenate([(pc.laplace_release(n, y, 0.5, rng)[1] - y).ravel() for _ in range(200)])
    assert abs(draws.var() / (2 * b ** 2) - 1) < 0.05 and abs(draws.mean()) < 0.1    # Laplace variance is 2 b^2
    same_n, same_y, b0 = pc.laplace_release(n, y, None, rng)
    assert b0 == 0.0 and (same_n == n).all() and (same_y == y).all()
    tiny = pc.laplace_release(np.full((pc.S, 2), 1.0), np.zeros((pc.S, 2)), 0.1, rng)[0]
    assert tiny.min() >= 1.0                                                         # noisy n is clipped at 1


def test_variance_formula_matches_the_spread_of_the_estimate():
    rng = np.random.default_rng(1); est = []; var = []
    for _ in range(300):
        n, y = counts(rng)
        nn, yy, b = pc.laplace_release(n, y, 0.5, rng)
        est.append(pc.no_pooling(nn, yy)); var.append(pc.sampling_variance(nn, yy, b))
    ratio = np.var(np.array(est), axis=0).mean() / np.mean(var)
    assert 0.9 < ratio < 1.1


def test_less_privacy_budget_means_more_error():
    rng = np.random.default_rng(2)
    n, y = counts(rng)
    truth = np.full(pc.S, 0.01)
    err = {e: np.mean([pc.rmse(pc.no_pooling(*pc.laplace_release(n, y, e, rng)[:2]), truth) for _ in range(50)])
           for e in (0.1, 0.5, 5.0)}
    assert err[0.1] > err[0.5] > err[5.0]


def test_share_captured():
    bench = np.arange(1.0, 101.0)
    assert pc.share_captured(bench, bench, 10) == bench[-10:].sum() / bench.sum()     # the oracle takes the top ten
    assert pc.share_captured(-bench, bench, 10) == bench[:10].sum() / bench.sum()     # the reverse ranking the bottom
    rng = np.random.default_rng(3)
    rand = np.mean([pc.share_captured(rng.random(100), np.ones(100), 20) for _ in range(20)])
    assert abs(rand - 0.20) < 1e-12
