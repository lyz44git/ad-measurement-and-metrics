"""Checks of the signal-to-noise index and its scoring (no data or NumPyro needed)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import detectability as dt
import mmm_core as m
from test_mmm_core import conjura_like


def test_index_is_the_t_statistic_of_a_known_shape():
    rng = np.random.default_rng(0); n = 400
    X = np.column_stack([np.arange(n) / n, np.sin(np.arange(n) / 9.0)])
    other = rng.normal(0, 1, n)
    x = 0.6 * other + rng.normal(0, 1, n)                     # the channel's shape, partly collinear with the other
    y = 1 + X @ np.array([0.5, -0.3]) + 0.8 * other + 0.25 * x + rng.normal(0, 1.5, n)
    Z = np.column_stack([np.ones(n), X, other, x])
    beta = np.linalg.lstsq(Z, y, rcond=None)[0]; u = y - Z @ beta
    t_ols = beta[-1] / np.sqrt(u.var(ddof=Z.shape[1]) * np.linalg.inv(Z.T @ Z)[-1, -1])
    expected = dt.index(0.25 * x, 0.8 * other, X, 1.5)        # index of the true contribution at the true noise SD
    assert abs(expected - 0.25 * np.sqrt(n) * dt.residual(x, np.column_stack([X, other])).std() / 1.5) < 1e-9
    assert abs(t_ols - expected) < 2.5                        # the fitted t-statistic scatters around the index
    assert dt.index(0.5 * x, 0.8 * other, X, 1.5) > expected > dt.index(0.25 * x, 0.8 * other, X, 3.0)
    assert dt.index(0.25 * other, other, X, 1.5) < 1e-6       # a channel that moves only with the other one: no signal


def test_min_detectable_roas_falls_with_more_data():
    short = m.load_brands(conjura_like(7 * 110), "W")[0]["b1"]
    long = m.load_brands(conjura_like(7 * 330), "W")[0]["b1"]
    a, b = dt.min_detectable_roas(short, "W"), dt.min_detectable_roas(long, "W")
    assert all(v > 0 and np.isfinite(v) for v in a + b) and b[0] < a[0] and b[1] < a[1]


def table(n=14, informative=True):
    rng = np.random.default_rng(1); rows = []
    for i in range(n):
        for ch in ("google", "meta"):
            idx = 0.3 + 0.4 * i
            err = (0.8 / (1 + idx) if informative else 0.3) * (1 + 0.05 * rng.normal())
            rows.append(dict(org=f"b{i}", channel=ch, index=idx, true=2.0 + 0.1 * i, single=(2.0 + 0.1 * i) * (1 + err)))
    return pd.DataFrame(rows)


def test_score_applies_both_predictions():
    good = dt.score(table(), boot=200)
    assert good["p1"] and good["p2"] and good["both"] and good["spearman_index_error"] < -0.8
    assert good["index_2_or_more"]["median_err"] < good["index_below_2"]["median_err"]
    flat = dt.score(table(informative=False), boot=200)
    assert not flat["both"]
