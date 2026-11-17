"""Checks of the adjusted readouts on made-up users (no data needed)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
import covariate_adjustment as ca


def population(n, lift, rng):
    """Outcome = covariate signal + noise, with half of the variance explained by the prediction g."""
    g = rng.normal(0, 1, n)
    X = np.column_stack([g + rng.normal(0, 0.5, n), rng.normal(0, 1, n)])
    y = lift + g + rng.normal(0, 1, n)
    return y, X, g


def test_adjustment_halves_the_variance_and_keeps_the_estimate():
    rng = np.random.default_rng(1)
    ya, Xa, ga = population(200_000, 0.3, rng)
    yb, Xb, gb = population(200_000, 0.0, rng)
    est, se = ca.run_studies(ya, Xa, ga, yb, Xb, gb, 400, 600, rng)
    assert np.allclose(est.mean(axis=0), 0.3, atol=0.02)                 # all three readouts recover the lift
    ratio = est[:, 2].var() / est[:, 0].var()
    assert 0.4 < ratio < 0.6                                              # g explains half of the outcome variance
    assert est[:, 1].var() < est[:, 0].var()                              # the raw covariates help too


def test_aa_studies_reject_about_five_percent_and_intervals_cover():
    rng = np.random.default_rng(2)
    ya, Xa, ga = population(200_000, 0.3, rng)
    yb, Xb, gb = population(200_000, 0.0, rng)
    est, se = ca.run_studies(ya, Xa, ga, yb, Xb, gb, 400, 800, rng)
    est_aa, se_aa = ca.run_studies(None, None, None, yb, Xb, gb, 400, 800, rng, aa=True)
    s = ca.summarize(est, se, est_aa, se_aa, 400, rng, boot=300)
    for name in ("D", "L", "M"):
        assert 0.02 < s[name]["aa_rejection"] < 0.09
        assert 0.92 < s[name]["coverage95"] < 0.98
        assert 0.9 < s[name]["mean_se_over_sd"] < 1.1
    assert s["M"]["variance_ratio_ci"][1] < 1


def test_required_sample_follows_the_variance():
    by_n = {100: {"D": {"n_times_variance": 0.04}, "M": {"n_times_variance": 0.02}}}
    assert np.isclose(ca.required_n(by_n, "M") / ca.required_n(by_n, "D"), 0.5)
    assert np.isclose(ca.required_n(by_n, "D", lift=0.01), (ca.Z_POWER / 0.01) ** 2 * 0.04)
