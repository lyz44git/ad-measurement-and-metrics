"""Checks of the path construction and the attribution rules on simulated touches (no Criteo data needed)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
import mta

DAY = 86400


def touches(rows):
    return pd.DataFrame(rows, columns=["timestamp", "uid", "campaign", "conversion", "conversion_timestamp",
                                       "conversion_id", "click"])


def test_converter_paths_keep_unclicked_touches_and_stop_at_the_first_conversion():
    d = touches([
        (0 * DAY, 1, 7, 0, -1, -1, 0),          # unclicked touch before the conversion: kept
        (9 * DAY, 1, 7, 1, 10 * DAY, 11, 1),    # clicked touch labeled with the conversion
        (12 * DAY, 1, 7, 0, -1, -1, 1),         # after the conversion: dropped
        (1 * DAY, 2, 7, 0, -1, -1, 0),          # non-converter: all touches kept
        (2 * DAY, 2, 8, 0, -1, -1, 1),
    ])
    p = mta.build_paths(d)
    a, b = p[p.uid == 1], p[p.uid == 2]
    assert list(a.timestamp) == [0, 9 * DAY] and (a.y == 1).all() and (a.conversion_timestamp == 10 * DAY).all()
    assert list(b.timestamp) == [DAY, 2 * DAY] and (b.y == 0).all()
    assert list(a.bucket) == [3, 0]           # 9 days before the last touch (over 7 days), then the last touch
    assert list(b.bucket) == [2, 0]           # exactly 1 day before the last touch falls in the 1-7 day bucket
    assert list(a.feat) == [3, 4]             # unclicked touch in bucket 3; clicked last touch (4 + 0)


def simulated_converting_paths(n_users=400, seed=5):
    rng = np.random.default_rng(seed)
    rows = []
    for u in range(n_users):
        n = int(rng.integers(2, 8))
        t = np.sort(rng.uniform(0, 20 * DAY, n))
        tc = t[-1] + rng.uniform(0, DAY)
        for i, ti in enumerate(t):
            rows.append(dict(uid=u, timestamp=ti, conversion_timestamp=tc, n=n, pos=i, is_last=(i == n - 1)))
    return pd.DataFrame(rows)


def test_each_rule_gives_each_conversion_one_unit_of_credit():
    c = mta.rule_credits(simulated_converting_paths(), lam=0.0877)
    for r in ["cr_last", "cr_first", "cr_linear", "cr_decay"]:
        assert np.allclose(c.groupby("uid")[r].sum(), 1.0)
    assert (c.loc[c.is_last, "cr_last"] == 1).all() and (c.loc[~c.is_last, "cr_last"] == 0).all()
    assert np.allclose(c.cr_linear, 1 / c.n)


def test_time_decay_gives_more_credit_to_touches_closer_to_the_conversion():
    c = mta.rule_credits(simulated_converting_paths(), lam=0.0877).sort_values(["uid", "timestamp"])
    assert (c.groupby("uid").cr_decay.diff().dropna() >= -1e-12).all()
    flat = mta.rule_credits(simulated_converting_paths(), lam=1e-9)
    assert np.allclose(flat.cr_decay, flat.cr_linear, atol=1e-6)    # no decay -> equal shares


def test_decay_rate_recovers_a_known_half_life():
    rng = np.random.default_rng(1)
    lam = np.log(2) / 7.9
    est = mta.decay_rate(rng.exponential(1 / lam, 200_000))
    assert abs(np.log(2) / est - 7.9) < 0.1
