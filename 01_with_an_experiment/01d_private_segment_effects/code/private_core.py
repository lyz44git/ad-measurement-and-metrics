"""Laplace release of segment counts, estimators that see only the noisy counts, and allocation by segment."""
import numpy as np

S = 100                                  # segments
EPS = [0.1, 0.5, 1.0, 5.0, None]         # None: no noise
SEED = 20261115


def cell_arrays(df):
    """Counts n and y by segment (rows) and arm (columns) from a table with seg, treatment, n, y."""
    n = np.zeros((S, 2)); y = np.zeros((S, 2))
    for r in df.itertuples():
        n[r.seg, r.treatment] += r.n; y[r.seg, r.treatment] += r.y
    return n, y


def laplace_release(n, y, eps, rng):
    """Noisy counts under epsilon-differential privacy and the noise scale b.

    One user changes n by 1 and y by at most 1 in one cell (L1 sensitivity 2), so each count gets Laplace noise with
    scale 2 / eps. Noisy n is clipped below at 1. eps None returns the counts unchanged.
    """
    b = 2.0 / eps if eps else 0.0
    nn = np.maximum(n + (rng.laplace(0, b, n.shape) if eps else 0), 1.0)
    yy = y + (rng.laplace(0, b, y.shape) if eps else 0)
    return nn, yy, b


def no_pooling(nn, yy):
    """Difference of noisy rates, ad arm minus control, by segment."""
    p = yy / nn
    return p[:, 1] - p[:, 0]


def sampling_variance(nn, yy, b):
    """Variance of the no-pooling estimate by segment: binomial sampling plus the Laplace noise on y."""
    P = np.clip(yy.sum(0) / nn.sum(0), 1e-4, 1 - 1e-4)
    return (P * (1 - P) / nn + 2 * b ** 2 / nn ** 2).sum(1)


def rmse(x, bench):
    return float(np.sqrt(np.mean((x - bench) ** 2)))


def share_captured(score, bench, top):
    """Share of total benchmark effect in the `top` segments with the highest score."""
    return float(bench[np.argsort(-score)[:top]].sum() / bench.sum())
