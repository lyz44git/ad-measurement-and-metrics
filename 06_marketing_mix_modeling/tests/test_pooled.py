"""Checks of the data preparation and the decision rule of the pooled model (no data or NumPyro needed)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
sys.path.insert(0, str(Path(__file__).resolve().parent))                # for the synthetic-data helper below
import mmm_core as m
import run_pooled as rp
from test_mmm_core import conjura_like


def test_prepare_pads_brands_and_scales_each_by_its_own_training_data():
    d = pd.concat([conjura_like(7 * 110, org="a"), conjura_like(7 * 130, org="b", seed=1)])
    brands, _ = m.load_brands(d, "W")
    p = rp.prepare(brands, ["a", "b"], "W")
    H, L = m.settings("W")["H"], m.settings("W")["L"]
    assert p["y"].shape == (2, 130) and p["SL"].shape == (2, 130, L, 2)
    assert list(p["n"]) == [110, 130] and list(p["ntr"]) == [110 - H, 130 - H]
    for i in range(2):
        ntr, n = p["ntr"][i], p["n"][i]
        assert np.isclose(p["y"][i, :ntr].mean(), 1.0)                       # revenue scaled by its training mean
        assert p["train"][i].sum() == ntr and not p["train"][i, ntr:].any()   # holdout and padding are not fitted
        assert np.isclose(p["SL"][i, :ntr, 0, :].max(), 1.0)                 # spend scaled by its training maximum
        assert (p["SL"][i, n:] == 0).all() and (p["y"][i, n:] == 0).all()    # padding beyond the brand's last period
    g = brands["a"]
    assert np.allclose(p["SL"][0, 5:110, 5, 0] * g.google.values[:97].max(), g.google.values[:105])   # lag 5 of Google
    assert np.allclose(p["spend_tr"][0], [g.google.values[:97].sum(), g.meta.values[:97].sum()])


def table(pooled_err, single_err, n=12):
    rows = []
    for i in range(n):
        for ch in ("google", "meta"):
            true = 1.0 + 0.2 * i
            rows.append(dict(org=f"b{i}", channel=ch, true=true, pooled=true * (1 + pooled_err), pooled_lo=0.5 * true,
                             pooled_hi=1.5 * true, single=true * (1 + single_err * (1 + 0.1 * i)),
                             single_lo=1.05 * true, single_hi=2.0 * true))       # the per-brand interval misses the truth
    return pd.DataFrame(rows)


def test_recovery_rule_needs_a_clear_improvement():
    better = rp.recovery_decision(table(0.1, 0.4))
    assert better["rule_met"] and better["diff_ci"][1] < 0 and better["brands"] == 12
    same = rp.recovery_decision(table(0.3, 0.3 / 1.55))                       # per-brand errors straddle the pooled error
    assert not same["rule_met"]
    worse = rp.recovery_decision(table(0.5, 0.2))
    assert not worse["rule_met"] and worse["diff_mean"] > 0


def test_recovery_metrics_report_error_and_coverage():
    t = table(0.1, 0.4)
    mp, ms = rp.recovery_metrics(t, "pooled"), rp.recovery_metrics(t, "single")
    assert np.isclose(mp["median_abs_rel_err"], 0.1) and mp["coverage90"] == 1.0 and ms["coverage90"] == 0.0
    assert mp["n"] == 24 and np.isclose(mp["spearman"], 1.0)
