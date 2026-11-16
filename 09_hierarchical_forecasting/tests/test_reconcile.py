"""Reconciliation: coherence, projection properties, and a cross-check against Nixtla hierarchicalforecast."""
import numpy as np
import pytest
from hier_toy import TOY_ORIGINS
from hierfc import backtest, hierarchy, reconcile as rc


@pytest.fixture
def toy_hier(toy_src):
    _, hier = backtest.setup(toy_src, TOY_ORIGINS[0])
    return hier


def _all_G(S, rng):
    n, m = S.shape
    E = rng.normal(size=(40, n)) * rng.uniform(1, 50, n)
    W, lam = rc.shrink_cov(E)
    return {"bu": rc.g_bottom_up(S), "td": rc.g_top_down(S, rng.dirichlet(np.ones(m))),
            "ols": rc.g_mint(S, rc.w_ols(S)), "wls_struct": rc.g_mint(S, rc.w_wls_struct(S)),
            "mint_shrink": rc.g_mint(S, W)}


def test_hierarchy_structure(toy_hier):
    h = toy_hier
    assert h.S.shape == (h.n_agg + h.m, h.m)
    assert h.nodes[0] == "US" and h.S[0].sum() == h.m
    # every level partitions the leaves, so every level sums to the US row
    for L in range(4):
        assert np.allclose(h.S[h.level == L].sum(0), 1)
    # children of each aggregate node sum to it
    for i, ch in h.children.items():
        assert np.allclose(h.S[ch].sum(0), h.S[i])


def test_reconciled_forecasts_are_coherent(toy_hier):
    rng = np.random.default_rng(1)
    S = toy_hier.S
    y_hat = rng.uniform(10, 1000, size=(S.shape[0], 12))     # incoherent base forecasts
    assert rc.coherence_error(S, y_hat).max() > 1
    for name, G in _all_G(S, rng).items():
        y = rc.reconcile(S, G, y_hat)
        assert rc.coherence_error(S, y).max() < 1e-8 * np.abs(y).max(), name
        for i, ch in toy_hier.children.items():                # parent = sum of children, level by level
            assert np.allclose(y[i], y[ch].sum(0)), name


def test_projection_keeps_coherent_forecasts(toy_hier):
    """G S = I for unbiased methods: forecasts that are already coherent come back unchanged."""
    rng = np.random.default_rng(2)
    S = toy_hier.S
    b = rng.uniform(10, 100, size=(S.shape[1], 5))
    y = S @ b
    for name, G in _all_G(S, rng).items():
        if name == "td":
            continue
        np.testing.assert_allclose(G @ S, np.eye(S.shape[1]), atol=1e-9, err_msg=name)
        np.testing.assert_allclose(rc.reconcile(S, G, y), y, rtol=1e-9, err_msg=name)


def test_bottom_up_and_top_down_definitions(toy_hier):
    rng = np.random.default_rng(3)
    S, m = toy_hier.S, toy_hier.m
    y_hat = rng.uniform(10, 1000, size=(S.shape[0], 4))
    np.testing.assert_allclose(rc.reconcile(S, rc.g_bottom_up(S), y_hat)[-m:], y_hat[-m:])
    p = rc.td_proportions(rng.uniform(1, 9, size=(m, 30)))
    td = rc.reconcile(S, rc.g_top_down(S, p), y_hat)
    np.testing.assert_allclose(td[0], y_hat[0])                # top-down keeps the top base forecast
    np.testing.assert_allclose(td[-m:], np.outer(p, y_hat[0]))


def test_u_form_equals_gls_form(toy_hier):
    rng = np.random.default_rng(4)
    S = toy_hier.S
    A = rng.normal(size=(S.shape[0], S.shape[0]))
    W = A @ A.T + np.eye(S.shape[0])
    Wi = np.linalg.inv(W)
    G_gls = np.linalg.solve(S.T @ Wi @ S, S.T @ Wi)
    np.testing.assert_allclose(rc.g_mint(S, W), G_gls, atol=1e-9)


def test_shrinkage_properties():
    rng = np.random.default_rng(5)
    E = rng.normal(size=(30, 12)) @ rng.normal(size=(12, 12))
    W, lam = rc.shrink_cov(E)
    assert 0 <= lam <= 1
    np.testing.assert_allclose(W, W.T)
    np.testing.assert_allclose(np.diag(W), np.var(E, axis=0, ddof=1))   # variances are not shrunk
    assert np.linalg.eigvalsh(W).min() > 0


def test_matches_nixtla_hierarchicalforecast(toy_hier):
    mt = pytest.importorskip("hierarchicalforecast.methods")
    rng = np.random.default_rng(6)
    S = toy_hier.S
    n, T = S.shape[0], 48
    y_ins = rng.uniform(100, 1000, size=(n, T))
    y_fit = y_ins + rng.normal(size=(n, T)) * rng.uniform(1, 30, size=(n, 1)) + rng.normal(size=(1, T)) * 5
    y_hat = rng.uniform(100, 1000, size=(n, 3))
    mine = {"ols": rc.g_mint(S, rc.w_ols(S)), "wls_struct": rc.g_mint(S, rc.w_wls_struct(S)),
            "mint_shrink": rc.g_mint(S, rc.shrink_cov((y_ins - y_fit).T)[0])}
    for name, G in mine.items():
        P, W = mt.MinTrace(method=name)._get_PW_matrices(S=S, y_hat=y_hat, y_insample=y_ins, y_hat_insample=y_fit)
        np.testing.assert_allclose(S @ G @ y_hat, S @ P @ y_hat, rtol=1e-6, err_msg=name)
    P = mt.BottomUp()._get_PW_matrices(S=S)[0]
    np.testing.assert_allclose(P, rc.g_bottom_up(S))
