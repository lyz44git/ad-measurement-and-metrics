"""Scores by level: RMSSE, MAE, coherence error, and Diebold-Mariano with the HLN correction.

Array shapes: forecasts and actuals are (origins O, nodes n, horizons H); scale is (O, n), the mean squared
one-step change in each origin's training window (M5 RMSSE convention)."""
from __future__ import annotations
import numpy as np
from scipy import stats


def level_nodes(level: np.ndarray, is_rem: np.ndarray, L: int) -> np.ndarray:
    """Indices of the nodes scored at level L (the Remainder is scored separately, never inside a level)."""
    return np.where((level == L) & ~is_rem)[0]


def rmsse(fc: np.ndarray, actual: np.ndarray, scale: np.ndarray, hs=None) -> np.ndarray:
    """Per (origin, node) RMSSE over horizons `hs` (1-based list; default all). Returns O x n."""
    H = fc.shape[2]
    idx = np.arange(H) if hs is None else np.asarray(hs) - 1
    e2 = (actual[:, :, idx] - fc[:, :, idx]) ** 2
    return np.sqrt(e2.mean(2) / scale)


def level_rmsse(fc, actual, scale, nodes, hs=None) -> float:
    return float(rmsse(fc[:, nodes], actual[:, nodes], scale[:, nodes], hs).mean())


def level_mae(fc, actual, nodes, hs=None) -> float:
    H = fc.shape[2]
    idx = np.arange(H) if hs is None else np.asarray(hs) - 1
    return float(np.abs(actual[:, nodes][:, :, idx] - fc[:, nodes][:, :, idx]).mean())


def coherence(fc: np.ndarray, actual: np.ndarray, children: dict, parents) -> tuple:
    """Relative incoherence |parent - sum(children)| / actual parent over the given parent nodes.
    Returns (mean, max) over parents, origins and horizons."""
    errs = []
    for i in parents:
        ch = children[i]
        errs.append(np.abs(fc[:, i] - fc[:, ch].sum(1)) / actual[:, i])
    e = np.stack(errs)
    return float(e.mean()), float(e.max())


def origin_loss(fc, actual, scale, nodes, h: int) -> np.ndarray:
    """Per-origin loss at a single horizon: mean over nodes of e^2 / s^2. Returns length O."""
    e2 = (actual[:, nodes, h - 1] - fc[:, nodes, h - 1]) ** 2
    return (e2 / scale[:, nodes]).mean(1)


def dm_hln(d: np.ndarray, h: int) -> dict:
    """Diebold-Mariano test on loss differentials d (length T), Newey-West (Bartlett) long-run variance with lag
    h - 1, Harvey-Leybourne-Newbold small-sample correction, t(T-1) reference, two-sided."""
    d = np.asarray(d, float)
    T = len(d)
    dc = d - d.mean()
    lrv = dc @ dc / T
    for k in range(1, h):
        lrv += 2 * (1 - k / h) * (dc[k:] @ dc[:-k]) / T
    if lrv <= 0:
        return {"mean_d": float(d.mean()), "stat": float("nan"), "p": float("nan")}
    dm = d.mean() / np.sqrt(lrv / T)
    hln = dm * np.sqrt((T + 1 - 2 * h + h * (h - 1) / T) / T)
    p = 2 * stats.t.sf(abs(hln), df=T - 1)
    return {"mean_d": float(d.mean()), "stat": float(hln), "p": float(p)}
