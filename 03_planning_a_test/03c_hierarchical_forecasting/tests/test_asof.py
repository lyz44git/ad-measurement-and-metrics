"""As-of (pseudo-real-time) leakage tests: nothing dated after the origin may change a forecast."""
import numpy as np
import pytest
from hier_toy import TOY_ORIGINS, cheap_base, make_toy_src
from hierfc import backtest, data
from hierfc.paths import ZILLOW_DIR, TARGET_FILES


def test_known_month_is_next_month(toy_src):
    assert (toy_src.known_month == toy_src.valid_month + 1).all()


@pytest.mark.skipif(not (ZILLOW_DIR / TARGET_FILES["inventory"]).exists(), reason="Zillow file not present")
def test_real_source_known_month_and_view():
    src = data.load_source("inventory")
    assert (src.known_month == src.valid_month + 1).all()
    assert src.valid_month.min() == data.START
    for a in backtest.origins()[::5]:
        v = data.asof_view(src, a)
        assert v.valid_month.max() == a - 1           # the month just before the as-of month, never later


def test_training_window_ends_before_origin(toy_src):
    _, hier = backtest.setup(toy_src, TOY_ORIGINS[0])
    for a in TOY_ORIGINS:
        months, L, Y, _, _ = backtest.origin_inputs(toy_src, hier, a)
        assert months[-1] == a - 1 and Y.shape[1] == len(months)


def _poison(src, a, value):
    p = src.copy()
    late = p.valid_month >= a
    p.loc[late, "value"] = value * (1 + p.loc[late].index.to_numpy() % 7)
    return p


@pytest.mark.parametrize("use_ets", [False, True])
def test_poisoned_future_leaves_forecasts_unchanged(toy_src, use_ets):
    """Replace every value dated at or after the origin by huge numbers: all forecasts must be identical."""
    if use_ets:
        pytest.importorskip("statsforecast")         # the ETS case needs the forecasting package from requirements.txt
    a = TOY_ORIGINS[1]
    base_fn = None if use_ets else cheap_base
    outs = []
    for src in (toy_src, _poison(toy_src, a, 1e9)):
        _, hier = backtest.setup(src, TOY_ORIGINS[0])
        months, L, Y, _, _ = backtest.origin_inputs(src, hier, a)
        out, d = backtest.forecast_origin(hier, months, L, Y, "ets", 1, base_fn)
        outs.append((out, d["lambda"]))
    for m in backtest.METHODS:
        np.testing.assert_array_equal(outs[0][0][m], outs[1][0][m])
    assert outs[0][1] == outs[1][1]


def test_membership_uses_only_first_origin_data(toy_src):
    """Deleting a member's values after the first origin must not change the member set."""
    a0 = TOY_ORIGINS[0]
    m0, _ = backtest.setup(toy_src, a0)
    cut = toy_src[~((toy_src.region == "4") & (toy_src.valid_month >= a0))]
    m1, _ = backtest.setup(cut, a0)
    assert m0.region.tolist() == m1.region.tolist()
    assert "9" not in set(m0.region)                 # the late starter is not a member


def test_actuals_and_scale_alignment(toy_src):
    res = backtest.run("toy", src=toy_src, origin_list=TOY_ORIGINS, base_fn=cheap_base, log=lambda *_: None)
    us = toy_src[toy_src.region == data.US].set_index("valid_month").value
    for k, a in enumerate(TOY_ORIGINS):
        for h in (1, 6, 12):
            assert res["actual"][k, 0, h - 1] == us[a - 1 + h]
        # no-change forecast is the last value known at the origin
        assert np.all(res["fc"][backtest.METHODS.index("naive"), k, 0] == us[a - 1])
    # the member with a gap after the first origin is carried forward in the actuals, never left missing
    assert res["n_filled_full"] == 1
    assert np.isfinite(res["actual"]).all() and (res["scale"] > 0).all()


def test_carry_forward_uses_only_past(toy_src):
    """The filled value equals the previous month's value, not an interpolation using the next month."""
    gap = data.ym(2021, 9)
    _, hier = backtest.setup(toy_src, TOY_ORIGINS[0])
    months, L, Y, n_filled, _ = backtest.origin_inputs(toy_src, hier, gap + 2)
    i = hier.leaves.region.tolist().index("2")
    j = int(np.where(months == gap)[0][0])
    assert n_filled == 1 and L[i, j] == L[i, j - 1]
