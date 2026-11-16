"""Linear forecast reconciliation: y_tilde = S @ G @ y_hat.

S is n x m (all nodes x leaves) with S = [C; I]: the first n_agg rows aggregate, the last m rows are the identity.
G is m x n and maps the n base forecasts to m leaf forecasts; S @ G @ y_hat then adds them back up, so the result
is coherent (every parent equals the sum of its children) for any y_hat.

For the MinT family we use the form that never inverts W (Wickramasuriya, Athanasopoulos & Hyndman 2019):
    G = J - J W U (U' W U)^{-1} U',   J = [0 | I_m],   U' = [I_{n_agg} | -C].
It equals (S' W^-1 S)^-1 S' W^-1 whenever W is invertible, and only needs an n_agg x n_agg solve."""
from __future__ import annotations
import numpy as np


def _split(S: np.ndarray):
    n, m = S.shape
    n_agg = n - m
    if not np.allclose(S[n_agg:], np.eye(m)):
        raise ValueError("S must be [C; I] with the leaves last")
    return n, m, n_agg, S[:n_agg]


def g_bottom_up(S: np.ndarray) -> np.ndarray:
    n, m, n_agg, _ = _split(S)
    return np.hstack([np.zeros((m, n_agg)), np.eye(m)])


def g_top_down(S: np.ndarray, p: np.ndarray, top: int = 0) -> np.ndarray:
    """Leaf forecast = p_j * base forecast of node `top`. p are leaf proportions summing to 1."""
    n, m, _, _ = _split(S)
    if not np.isclose(p.sum(), 1.0):
        raise ValueError("top-down proportions must sum to 1")
    G = np.zeros((m, n))
    G[:, top] = p
    return G


def td_proportions(Y_leaves_train: np.ndarray, window: int = 12) -> np.ndarray:
    """Proportions of historical averages (Gross & Sohl method F) over the last `window` training months."""
    tot = Y_leaves_train[:, -window:].sum(1)
    return tot / tot.sum()


def g_mint(S: np.ndarray, W: np.ndarray) -> np.ndarray:
    """General MinT/GLS projection for a given (symmetric, PSD) W, using the U-form above."""
    n, m, n_agg, C = _split(S)
    J = np.hstack([np.zeros((m, n_agg)), np.eye(m)])
    Ut = np.hstack([np.eye(n_agg), -C])                         # n_agg x n
    WU = W @ Ut.T                                               # n x n_agg
    return J - (J @ WU) @ np.linalg.solve(Ut @ WU, Ut)


def w_ols(S: np.ndarray) -> np.ndarray:
    return np.eye(S.shape[0])


def w_wls_struct(S: np.ndarray) -> np.ndarray:
    return np.diag(S.sum(1))


def shrink_cov(E: np.ndarray):
    """Schäfer-Strimmer shrinkage of the covariance of residuals E (T x n) toward its diagonal.
    Residuals are centred; T-1 denominators; lambda = sum_{i!=j} Var(r_ij) / sum_{i!=j} r_ij^2, clipped to [0, 1].
    Matches hierarchicalforecast 1.5.3 (MinTrace 'mint_shrink') apart from its 2e-8 diagonal ridge.
    Series with zero residual variance get correlation 0 with everything else. Returns (W, lambda)."""
    E = np.asarray(E, float)
    T, n = E.shape
    X = E - E.mean(0)
    C = X.T @ X / (T - 1)
    sd = np.sqrt(np.diag(C))
    ok = sd > 0
    Z = np.zeros_like(X)
    Z[:, ok] = X[:, ok] / sd[ok]
    R = Z.T @ Z / (T - 1)
    # Var(r_ij) = T / (T-1)^3 * sum_t (w_ijt - w_bar_ij)^2, with w_ijt = z_it z_jt; expanded to avoid a T x n x n array
    Z2 = Z ** 2
    s2 = Z2.T @ Z2                                              # sum_t w_ijt^2
    wbar = Z.T @ Z / T                                          # mean_t w_ijt
    var_r = (s2 - T * wbar ** 2) * T / (T - 1) ** 3
    off = ~np.eye(n, dtype=bool)
    denom = (R[off] ** 2).sum()
    lam = 1.0 if denom == 0 else float(np.clip(var_r[off].sum() / denom, 0.0, 1.0))
    Rs = (1 - lam) * R
    np.fill_diagonal(Rs, 1.0)
    return Rs * np.outer(sd, sd), lam


def reconcile(S: np.ndarray, G: np.ndarray, y_hat: np.ndarray) -> np.ndarray:
    """y_hat: n x h base forecasts -> n x h coherent forecasts."""
    return S @ (G @ y_hat)


def coherence_error(S: np.ndarray, y: np.ndarray) -> np.ndarray:
    """|aggregate - sum of its leaves| for each aggregate row of S (n_agg x h). Zero for coherent forecasts."""
    n, m, n_agg, C = _split(S)
    return np.abs(y[:n_agg] - C @ y[n_agg:])
