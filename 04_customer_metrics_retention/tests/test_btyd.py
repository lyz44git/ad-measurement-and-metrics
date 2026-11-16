"""Checks of the BG/NBD and Gamma-Gamma implementations on simulated customers (no retail data needed)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
import btyd_impl as b

TRUE = dict(r=0.243, alpha=4.414, a=0.793, b=2.426)   # published CDNOW estimates, used only as a plausible truth


def simulated_customers(n=6000, seed=7):
    return b.simulate_bgnbd(n, *TRUE.values(), T_max=78, rng=np.random.default_rng(seed))


def test_bgnbd_fit_reaches_at_least_the_true_likelihood_and_recovers_the_purchase_rate():
    x, tx, T = simulated_customers()
    est, ll = b.fit_bgnbd(x, tx, T)
    ll_true = b.bgnbd_ll(np.log(list(TRUE.values())), x, tx, T).sum()
    assert ll >= ll_true - 1e-6
    r, alpha = est[:2]
    assert abs(r / alpha - TRUE["r"] / TRUE["alpha"]) / (TRUE["r"] / TRUE["alpha"]) < 0.15   # mean purchase rate


def test_bgnbd_predictions_are_well_behaved():
    x, tx, T = simulated_customers(2000)
    params = np.array(list(TRUE.values()))
    alive = b.bgnbd_palive(params, x, tx, T)
    assert ((alive >= 0) & (alive <= 1)).all()
    assert (alive[x == 0] == 1).all()                       # no repeat purchase yet: cannot have dropped out
    short, long = b.bgnbd_expected(params, 13, x, tx, T), b.bgnbd_expected(params, 52, x, tx, T)
    assert (long >= short).all() and (short >= 0).all()


def test_gamma_gamma_recovers_mean_spend_on_both_scales():
    rng = np.random.default_rng(11)
    p, q, n = 6.25, 3.74, 6000
    x = rng.integers(1, 15, n).astype(float)
    for g in (15.44, 15.44 * 30):                           # the second scale is spend in hundreds
        nu = rng.gamma(q, 1 / g, n)
        m = np.array([rng.gamma(p * k, 1 / v) / k for k, v in zip(x, nu)])
        ph, qh, gh = b.fit_gg(x, m)
        assert abs(ph * gh / (qh - 1) - p * g / (q - 1)) / (p * g / (q - 1)) < 0.05


def test_gamma_gamma_uses_the_population_mean_for_customers_without_repeat_purchases():
    params = np.array([6.25, 3.74, 15.44])
    out = b.gg_expected(params, np.array([0.0, 3.0]), np.array([0.0, 40.0]))
    assert np.isclose(out[0], 6.25 * 15.44 / 2.74)
    assert out[1] > out[0]                                  # a customer who spends more than average
