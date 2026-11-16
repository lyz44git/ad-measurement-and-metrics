"""Data preparation, media transforms and the recovery simulation for the marketing mix models.

Pure NumPy and pandas, so it can be tested without NumPyro. `run_mmm.py` calls the same transforms with JAX arrays.
"""
import numpy as np
import pandas as pd

GOOGLE = ["GOOGLE_PAID_SEARCH_SPEND", "GOOGLE_SHOPPING_SPEND", "GOOGLE_PMAX_SPEND", "GOOGLE_DISPLAY_SPEND",
          "GOOGLE_VIDEO_SPEND"]
META = ["META_FACEBOOK_SPEND", "META_INSTAGRAM_SPEND", "META_OTHER_SPEND"]


def settings(freq):
    """Holdout length H, adstock window L, seasonal period, minimum series length, one-year lag and file suffix.

    "W" is the planned weekly model; "D" is the daily rerun (design/deviations.md, item 1).
    """
    if freq == "W":
        return dict(H=13, L=8, PERIOD=52.18, MINLEN=104, YEAR=52, SUF="")
    if freq == "D":
        return dict(H=91, L=28, PERIOD=365.25, MINLEN=728, YEAR=364, SUF="_daily")
    raise ValueError("freq must be 'W' or 'D'")


def load_brands(path_or_frame, freq):
    """One revenue and spend series per brand ("All Territories"), restricted to eligible brands.

    Revenue = purchases at original price minus discounts. Google and Meta spend are the sums of their columns.
    Weekly data keep complete weeks only. Each brand keeps its longest run of consecutive periods, and is eligible if
    that run has at least MINLEN periods with Google and Meta spend above 0 in at least 80% of them.
    Returns (dict brand -> DataFrame with columns week, rev, google, meta, nd; number of brands in the file).
    """
    s = settings(freq)
    d = path_or_frame if isinstance(path_or_frame, pd.DataFrame) else pd.read_csv(path_or_frame, parse_dates=["DATE_DAY"])
    d = d[d.TERRITORY_NAME == "All Territories"].copy()
    d["rev"] = d.ALL_PURCHASES_ORIGINAL_PRICE.fillna(0) - d.ALL_PURCHASES_GROSS_DISCOUNT.fillna(0)
    d["google"] = d[GOOGLE].fillna(0).sum(axis=1)
    d["meta"] = d[META].fillna(0).sum(axis=1)
    d["week"] = d.DATE_DAY - pd.to_timedelta(d.DATE_DAY.dt.weekday, unit="D") if freq == "W" else d.DATE_DAY
    w = d.groupby(["ORGANISATION_ID", "week"]).agg(rev=("rev", "sum"), google=("google", "sum"), meta=("meta", "sum"),
                                                   nd=("DATE_DAY", "nunique")).reset_index()
    step = 7 if freq == "W" else 1
    w = w[w.nd == step]
    out, n_all = {}, d.ORGANISATION_ID.nunique()
    for org, g in w.groupby("ORGANISATION_ID"):
        g = g.sort_values("week").reset_index(drop=True)
        brk = (g.week.diff().dt.days != step).cumsum()
        g = g[brk == brk.value_counts().idxmax()].reset_index(drop=True)
        if len(g) >= s["MINLEN"] and (g.google > 0).mean() >= 0.8 and (g.meta > 0).mean() >= 0.8:
            out[org] = g
    return out, n_all


def design(n, freq, dow=None):
    """Trend, two annual Fourier harmonics and, for daily data, day-of-week dummies."""
    period = settings(freq)["PERIOD"]
    t = np.arange(n)
    X = [t / period]
    for k in (1, 2):
        X += [np.sin(2 * np.pi * k * t / period), np.cos(2 * np.pi * k * t / period)]
    if freq == "D":
        X += [(dow == j).astype(float) for j in range(1, 7)]
    return np.column_stack(X)


def geometric_adstock(x, a, L, xp=np):
    """Carry-over of spend: weighted sum of the last L periods with weights a**lag, normalised to sum to 1.

    xp is the array module (NumPy, or jax.numpy inside the model).
    """
    lag = np.arange(L)
    w = a ** lag
    w = w / w.sum()
    padded = xp.concatenate([xp.zeros(L - 1), x])
    idx = xp.arange(x.shape[0])[:, None] + (L - 1) - lag[None, :]
    return (padded[idx] * w[None, :]).sum(axis=1)


def hill(s, h, k):
    """Diminishing returns: s**k / (s**k + h**k); equals 0.5 at s = h."""
    return s ** k / (s ** k + h ** k + 1e-12)


def simulate_revenue(g, base_fit, ymean, resid_sd, rng, freq):
    """Real spend, simulated revenue with known media effects (plan: adstock 0.5, Hill h 0.5, k 1).

    Each channel's contribution is scaled so that its ROAS over the training periods equals a true value drawn from
    Uniform(0.5, 4). Returns (revenue series, true ROAS for Google and Meta).
    """
    s = settings(freq); H, L = s["H"], s["L"]
    n = len(g); ntr = n - H
    S = np.column_stack([g.google.values, g.meta.values]).astype(float)
    smax = S[:ntr].max(axis=0); Sx = S / smax
    w = 0.5 ** np.arange(L); w /= w.sum()
    true_roas = rng.uniform(0.5, 4.0, 2); contrib = np.zeros((2, n))
    for c in range(2):
        padded = np.concatenate([np.zeros(L - 1), Sx[:, c]])
        st = np.array([(padded[t + L - 1 - np.arange(L)] * w).sum() for t in range(n)])
        sat = st / (st + 0.5)
        contrib[c] = sat * true_roas[c] * S[:ntr, c].sum() / sat[:ntr].sum()
    y = np.array(base_fit) * ymean + contrib.sum(axis=0) + rng.normal(0, resid_sd * ymean, n)
    return np.clip(y, 1.0, None), true_roas, contrib
