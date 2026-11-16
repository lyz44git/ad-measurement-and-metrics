"""Checks of the media transforms, the brand eligibility rule and the recovery simulation (no data or NumPyro needed)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
import mmm_core as m


def test_adstock_keeps_total_spend_and_carries_it_over_geometrically():
    x = np.zeros(40); x[5] = 1.0
    s = m.geometric_adstock(x, 0.6, 8)
    w = 0.6 ** np.arange(8); w /= w.sum()
    assert np.allclose(s[5:13], w) and np.isclose(s.sum(), 1.0)     # an impulse spreads over 8 periods, total kept
    assert np.allclose(m.geometric_adstock(np.full(30, 2.0), 0.6, 8)[7:], 2.0)   # steady spend passes through
    assert np.allclose(m.geometric_adstock(x, 1e-9, 8), x)          # no carry-over


def test_hill_saturates_and_is_half_way_at_h():
    s = np.linspace(0, 5, 501)
    for h, k in [(0.3, 0.7), (0.5, 1.0), (0.8, 2.0)]:
        v = m.hill(s, h, k)
        assert np.isclose(m.hill(h, h, k), 0.5) and (np.diff(v) >= 0).all() and v.max() < 1


def conjura_like(n_days, meta_share=1.0, seed=0, org="b1"):
    """Synthetic rows in the layout of the Conjura file; Meta spend is positive on `meta_share` of the days."""
    rng = np.random.default_rng(seed)
    d = pd.DataFrame({"DATE_DAY": pd.date_range("2021-01-04", periods=n_days, freq="D")})
    d["ORGANISATION_ID"] = org; d["TERRITORY_NAME"] = "All Territories"
    d["ALL_PURCHASES_ORIGINAL_PRICE"] = rng.uniform(900, 1100, n_days); d["ALL_PURCHASES_GROSS_DISCOUNT"] = 50.0
    for c in m.GOOGLE:
        d[c] = rng.uniform(0, 20, n_days)
    for c in m.META:
        d[c] = np.where(rng.random(n_days) < meta_share, rng.uniform(1, 20, n_days), 0.0)
    return d


def test_eligibility_needs_two_years_of_both_channels():
    d = pd.concat([conjura_like(7 * 110, org="ok"), conjura_like(7 * 90, org="short", seed=1),
                   conjura_like(7 * 110, meta_share=0.02, org="no_meta", seed=2)])
    weekly, n_all = m.load_brands(d, "W")
    assert n_all == 3 and sorted(weekly) == ["ok"] and len(weekly["ok"]) == 110
    g = weekly["ok"]
    assert (g.nd == 7).all() and np.isclose(g.rev.iloc[0], (d[d.ORGANISATION_ID == "ok"].ALL_PURCHASES_ORIGINAL_PRICE.iloc[:7] - 50).sum())
    daily, _ = m.load_brands(d, "D")
    assert sorted(daily) == ["ok"] and len(daily["ok"]) == 770        # daily rule: at least 728 consecutive days


def test_recovery_simulation_sets_training_roas_to_the_drawn_truth():
    g = m.load_brands(conjura_like(7 * 120), "W")[0]["b1"]
    n, H = len(g), m.settings("W")["H"]
    y, true_roas, contrib = m.simulate_revenue(g, np.ones(n), 1000.0, 0.05, np.random.default_rng(3), "W")
    spend = np.column_stack([g.google, g.meta])[: n - H].sum(axis=0)
    assert np.allclose(contrib[:, : n - H].sum(axis=1) / spend, true_roas)
    assert ((0.5 <= true_roas) & (true_roas <= 4)).all() and (y >= 1).all()
