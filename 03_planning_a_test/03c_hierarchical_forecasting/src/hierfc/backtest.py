"""Rolling-origin, pseudo-real-time backtest (pre-analysis plan §4-§5).

At as-of month a the forecaster sees only rows with known_month <= a (valid months up to a - 1), rebuilds the
hierarchy from those rows, fits one base model per node, reconciles, and forecasts valid months a-1+1 .. a-1+12."""
from __future__ import annotations
import time
import numpy as np
import pandas as pd
from . import data, hierarchy, models, reconcile as rc

H = 12
FIRST_ORIGIN = data.ym(2023, 11)
LAST_ORIGIN = data.ym(2025, 10)
RECON = ["bu", "td", "ols", "wls_struct", "mint_shrink"]
METHODS = ["base"] + RECON + ["naive", "snaive"]


def origins() -> list:
    return list(range(FIRST_ORIGIN, LAST_ORIGIN + 1))


def setup(src: pd.DataFrame, first_origin: int = FIRST_ORIGIN):
    """Members (fixed from what is known at the first origin) and the hierarchy."""
    view0 = data.asof_view(src, first_origin)
    members = data.select_members(view0, data.START, first_origin - 1)
    hier = hierarchy.build(members)
    return members, hier


def origin_inputs(src, hier, a: int):
    """Training matrix (n x T) for as-of month a, built only from rows known by a."""
    view = data.asof_view(src, a)
    mem = hier.leaves.iloc[:-1]
    months, Ym, us, n_filled = data.member_panel(view, mem, end=a - 1)
    assert months[-1] == a - 1 and view.valid_month.max() <= a - 1
    L = hier.leaf_values(Ym, us)
    if (L[-1] <= 0).any():
        raise ValueError(f"Remainder <= 0 at origin {data.ym_str(a)}")
    return months, L, hier.aggregate(L), n_filled, us


def forecast_origin(hier, months, L, Y, base: str, n_jobs: int, base_fn=None):
    """All methods at one origin. Returns dict method -> n x H forecasts, plus diagnostics."""
    S = hier.S
    if base_fn is None:
        y_hat, fitted = models.base_forecasts(Y, months, H, base, n_jobs=n_jobs)
    else:                                              # tests plug in a cheap base model
        y_hat, fitted = base_fn(Y, H)
    W_shr, lam = rc.shrink_cov((Y - fitted).T)
    G = {"bu": rc.g_bottom_up(S),
         "td": rc.g_top_down(S, rc.td_proportions(L)),
         "ols": rc.g_mint(S, rc.w_ols(S)),
         "wls_struct": rc.g_mint(S, rc.w_wls_struct(S)),
         "mint_shrink": rc.g_mint(S, W_shr)}
    out = {"base": y_hat}
    for k, g in G.items():
        out[k] = rc.reconcile(S, g, y_hat)
    out["naive"] = models.naive(Y, H)
    out["snaive"] = models.seasonal_naive(Y, H)
    return out, {"lambda": lam}


def run(target: str, base: str = "ets", n_jobs: int = 8, src: pd.DataFrame | None = None,
        origin_list=None, base_fn=None, log=print) -> dict:
    src = data.load_source(target) if src is None else src
    origin_list = origins() if origin_list is None else origin_list
    members, hier = setup(src, origin_list[0])
    last_target = origin_list[-1] - 1 + H
    # actuals: the full data (single vintage), same members and same carry-forward rule
    months_all, Lall, Yall, n_filled_all, us_all = origin_inputs(src, hier, last_target + 1)
    O, n = len(origin_list), hier.n
    fc = np.full((len(METHODS), O, n, H), np.nan)
    actual = np.full((O, n, H), np.nan)
    scale = np.full((O, n), np.nan)
    diag = []
    for k, a in enumerate(origin_list):
        t0 = time.time()
        months, L, Y, n_filled, us = origin_inputs(src, hier, a)
        out, d = forecast_origin(hier, months, L, Y, base, n_jobs, base_fn)
        for mi, mth in enumerate(METHODS):
            fc[mi, k] = out[mth]
        cols = np.searchsorted(months_all, np.arange(a, a + H))
        actual[k] = Yall[:, cols]
        scale[k] = (np.diff(Y, axis=1) ** 2).mean(1)
        diag.append({"origin": data.ym_str(a), "train_end": data.ym_str(int(months[-1])), "T": len(months),
                     "lambda": d["lambda"], "n_filled": n_filled, "rem_share_min": float((L[-1] / us).min()),
                     "secs": round(time.time() - t0, 1)})
        log(f"{target}/{base} origin {data.ym_str(a)} T={len(months)} lambda={d['lambda']:.3f} "
            f"({time.time() - t0:.1f}s)")
    diag = pd.DataFrame(diag)
    if (scale <= 0).any():
        raise ValueError("a node has zero one-step variation in a training window")
    return {"target": target, "base": base, "methods": METHODS, "origins": [data.ym_str(a) for a in origin_list],
            "fc": fc, "actual": actual, "scale": scale, "hier": hier, "members": members, "diag": diag,
            "n_filled_full": n_filled_all, "rem_share_full": (Lall[-1] / us_all)}
