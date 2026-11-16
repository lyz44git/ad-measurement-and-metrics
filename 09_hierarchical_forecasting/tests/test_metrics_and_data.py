import numpy as np
import pytest
from scipy import stats
from hierfc import backtest, data, metrics
from hierfc.paths import ZILLOW_DIR, TARGET_FILES


def test_rmsse_by_hand():
    fc = np.zeros((1, 1, 3)); actual = np.array([[[1.0, 2.0, 2.0]]]); scale = np.array([[4.0]])
    assert np.isclose(metrics.rmsse(fc, actual, scale)[0, 0], np.sqrt((1 + 4 + 4) / 3 / 4))
    assert np.isclose(metrics.rmsse(fc, actual, scale, hs=[1])[0, 0], 0.5)


def test_dm_hln_h1_is_corrected_t_test():
    rng = np.random.default_rng(0)
    d = rng.normal(0.3, 1, 24)
    r = metrics.dm_hln(d, 1)
    T = len(d)
    dm = d.mean() / np.sqrt(d.var() / T)
    hln = dm * np.sqrt((T - 1) / T)
    assert np.isclose(r["stat"], hln) and np.isclose(r["p"], 2 * stats.t.sf(abs(hln), T - 1))
    assert np.isclose(metrics.dm_hln(-d, 12)["stat"], -metrics.dm_hln(d, 12)["stat"])


def test_coherence_metric_zero_for_sums():
    children = {0: [1, 2]}
    fc = np.ones((2, 3, 4)); fc[:, 0] = 2
    actual = np.full((2, 3, 4), 2.0)
    assert metrics.coherence(fc, actual, children, [0]) == (0.0, 0.0)


@pytest.mark.skipif(not (ZILLOW_DIR / TARGET_FILES["inventory"]).exists(), reason="Zillow file not present")
@pytest.mark.parametrize("target", ["inventory", "new_listings"])
def test_real_hierarchy_sums_exactly(target):
    """Every level of the real hierarchy adds up to the Zillow US row in every month, and the Remainder is > 0."""
    src = data.load_source(target)
    _, hier = backtest.setup(src)
    months, L, Y, n_filled, us = backtest.origin_inputs(src, hier, data.ym(2026, 10))
    assert months[0] == data.START and months[-1] == data.ym(2026, 9)
    for lv in range(4):
        np.testing.assert_allclose(Y[hier.level == lv].sum(0), us, rtol=1e-12)
    assert (L[-1] > 0).all()
    assert len({s for s in hier.leaves.state if s != "Remainder"}) == 51
