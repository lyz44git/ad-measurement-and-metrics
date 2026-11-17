"""Checks of the geo-experiment simulation on synthetic panels (no Zillow data needed)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
import geo_experiment_power as g

ANCOVA, YOY, LEVELS, WEIGHTED = ("CR: ANCOVA (CUPED)", "CR: year-over-year difference", "CR: difference in means",
                                 "CR: volume-weighted ANCOVA")


def synthetic_pool(units=60, months=60, rho=0.8, seed=0):
    """Metros of very different size with persistent (AR(1)) monthly shocks and a common seasonal pattern."""
    rng = np.random.default_rng(seed)
    size = np.exp(rng.normal(6.0, 1.0, units))
    e = rng.normal(0, 0.05, (units, months)); shock = np.zeros((units, months))
    shock[:, 0] = e[:, 0] / np.sqrt(1 - rho ** 2)
    for t in range(1, months):
        shock[:, t] = rho * shock[:, t - 1] + e[:, t]
    season = 0.2 * np.sin(2 * np.pi * np.arange(months) / 12)
    Y = size[:, None] * np.exp(shock + season[None, :])
    return pd.DataFrame(Y, index=[f"metro_{i}" for i in range(units)], columns=pd.period_range("2018-01", periods=months, freq="M"))


@pytest.fixture(scope="module")
def small_grid():
    old = g.NS, g.DS, g.R
    g.NS, g.DS, g.R = [20, 40], [2], 600
    yield
    g.NS, g.DS, g.R = old


@pytest.fixture(scope="module")
def sim(small_grid):
    return g.simulate(synthetic_pool(), "synthetic", seed=1).set_index(["metros", "estimator"])


def test_false_positive_rate_is_near_nominal(sim):
    for est in (ANCOVA, YOY, LEVELS):
        for n in (20, 40, 60):
            assert 0.02 <= sim.loc[(n, est), "false_positive_rate"] <= 0.09


def test_regression_adjustment_detects_smaller_effects_than_year_over_year(sim):
    mde = sim["mde_80_pct"].fillna(np.inf)      # NaN means not detectable within the grid of lifts (above 50%)
    for n in (20, 40, 60):
        assert mde[(n, ANCOVA)] < mde[(n, YOY)]


def test_raw_levels_are_dominated_by_metro_size(sim):
    assert sim.loc[(40, ANCOVA), "variance_vs_difference_in_means"] < 0.1


def test_more_metros_detect_smaller_effects(sim):
    mde = sim["mde_80_pct"].fillna(np.inf)
    assert mde[(60, ANCOVA)] < mde[(40, ANCOVA)] < mde[(20, ANCOVA)]


def test_hc2_matches_the_two_sample_standard_error():
    rng = np.random.default_rng(3)
    tr = np.r_[np.ones(15), np.zeros(25)]; y = rng.normal(size=40) + 0.5 * tr
    b, se, df = g.ols_hc2(np.c_[np.ones(40), tr], y)
    b2, se2, df2 = g.dim(y, tr)
    assert np.isclose(b, b2) and np.isclose(se, se2) and df == df2 == 38


def test_screen_drops_incomplete_small_and_broken_series():
    Y = synthetic_pool(units=12, months=36, seed=4)
    Y.iloc[0, 5] = np.nan                       # incomplete series
    Y.iloc[1] = Y.iloc[1] / Y.iloc[1].mean()    # too small
    Y.iloc[2, 20] = Y.iloc[2].median() * 0.1    # coverage break
    pool, breaks, summ = g.screen(Y, "synthetic", min_mean=10)
    assert set(Y.index[:3]).isdisjoint(pool.index)
    assert list(breaks.unit) == [Y.index[2]]
    assert summ["pool"] == len(pool) == 9


def test_randomization_inference_keeps_the_false_positive_rate(small_grid):
    ri = g.ri_check(synthetic_pool(), "synthetic", seed=5, D=2, draws=300, perms=99)
    assert set(ri.estimator) == {ANCOVA, WEIGHTED}
    assert ri.false_positive_rate.between(0.01, 0.10).all()
