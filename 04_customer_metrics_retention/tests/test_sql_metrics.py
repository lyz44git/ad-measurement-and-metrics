"""The published SQL (out/14_sql_queries.sql) against an independent pandas implementation, on synthetic purchases."""
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

SQL = (Path(__file__).resolve().parents[1] / "out" / "14_sql_queries.sql").read_text()
SEGMENT_SQL, COHORT_SQL = SQL.split("-- New-account cohorts")


@pytest.fixture(scope="module")
def days():
    """One row per customer and purchase day, 2009-12-01 to 2011-12-09, with customers of very different activity."""
    rng = np.random.default_rng(0)
    span = (pd.Timestamp("2011-12-09") - pd.Timestamp("2009-12-01")).days
    rows = []
    for cid in range(600):
        start = rng.integers(0, span - 30)
        n = 1 + rng.poisson(rng.gamma(1.0, 4.0))
        offs = np.unique(np.r_[start, rng.integers(start, span, n - 1)])
        rows += [(cid, pd.Timestamp("2009-12-01") + pd.Timedelta(days=int(o)), float(rng.lognormal(5, 1))) for o in offs]
    return pd.DataFrame(rows, columns=["cid", "day", "rev"])


@pytest.fixture(scope="module")
def con(days):
    c = duckdb.connect()
    c.register("days_df", days)
    c.execute("CREATE TABLE days AS SELECT cid, CAST(day AS DATE) AS day, rev FROM days_df")
    return c


def test_new_account_cohorts_match_pandas(days, con):
    sql = con.execute(COHORT_SQL).df()
    d = days.assign(mon=days.day.dt.to_period("M"))
    cohort = {}
    for cm in pd.period_range("2010-12", "2011-06", freq="M"):
        start = cm.to_timestamp()
        prior = set(d[(d.day < start) & (d.day >= start - pd.DateOffset(months=12))].cid)
        for cid in set(d[d.mon == cm].cid) - prior:
            cohort.setdefault(cid, cm)                      # first month in which the account counts as new
    c = pd.Series(cohort, name="cm")
    size = c.value_counts()
    act = d.merge(c, left_on="cid", right_index=True)
    act = act[(act.mon > act.cm) & (act.mon <= pd.Period("2011-11", "M"))]
    act["k"] = (act.mon - act.cm).apply(lambda o: o.n)
    ref = (act.groupby(["cm", "k"]).cid.nunique() / act.groupby(["cm", "k"]).cm.first().map(size)).rename("rate")
    ref.index = pd.MultiIndex.from_tuples([(str(cm), k) for cm, k in ref.index], names=["cm", "k"])
    got = sql.set_index(["cm", "k"]).repeat_rate
    assert len(got) == len(ref) > 20
    assert np.allclose(got.sort_index().values, ref.sort_index().values)
    assert (sql.groupby("cm").n.first().sort_index().values == size.sort_index().values).all()


def test_rule_segments_match_pandas(days, con):
    sql = con.execute(SEGMENT_SQL).df()
    cut = pd.Timestamp("2011-06-01")
    w = days[(days.day >= cut - pd.DateOffset(months=6)) & (days.day < cut)]
    rfm = w.groupby("cid").agg(gross6=("rev", "sum"), last=("day", "max"))
    rfm["y"] = days[(days.day >= cut) & (days.day < cut + pd.DateOffset(months=6))].groupby("cid").rev.sum().reindex(rfm.index).fillna(0)
    rec = (cut - rfm["last"]).dt.days
    rfm["rband"] = np.where(rec <= 60, "recent<=60d", np.where(rec <= 120, "61-120d", ">120d"))
    rank, n = rfm.gross6.rank(method="first"), len(rfm)
    rfm["vtile"] = np.where(rank < 1 + (n - 1) / 3, 1, np.where(rank < 1 + 2 * (n - 1) / 3, 2, 3))
    ref = rfm.groupby(["rband", "vtile"]).agg(n=("y", "size"), y_sum=("y", "sum"), repeat_rate=("y", lambda s: (s > 0).mean()))
    got = sql.set_index(["rband", "vtile"]).sort_index()
    ref = ref.sort_index()
    assert list(got.index) == list(ref.index)
    assert (got.n.values == ref.n.values).all()
    assert np.allclose(got.y_sum.values, ref.y_sum.values) and np.allclose(got.repeat_rate.values, ref.repeat_rate.values)
    assert np.isclose(got.share_accounts.sum(), 1) and np.isclose(got.share_sales.sum(), 1)
