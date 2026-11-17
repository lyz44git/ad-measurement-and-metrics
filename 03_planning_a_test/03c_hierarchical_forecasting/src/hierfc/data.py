"""Zillow metro count files -> as-of long table -> member panel.

Months are integers: ym(2018, 3) = 2018 * 12 + 2. Each value carries the month it describes (valid_month) and the
month it is treated as known (known_month = valid_month + 1: Zillow publishes a month's metro data in the middle of
the next month). Only one vintage exists, so this is as-of masking on a late vintage (pseudo-real-time)."""
from __future__ import annotations
import re
from pathlib import Path
import numpy as np
import pandas as pd
from .paths import ZILLOW_DIR, TARGET_FILES


def ym(y: int, m: int) -> int:
    return y * 12 + (m - 1)


def ym_str(i: int) -> str:
    return f"{i // 12:04d}-{i % 12 + 1:02d}"


START = ym(2018, 3)          # 2018-01 and 2018-02 are partial months (pre-analysis plan §2)
US = "US"


def read_wide(path: Path) -> pd.DataFrame:
    """Wide Zillow CSV (RegionID, SizeRank, RegionName, RegionType, StateName, one column per month-end) -> long."""
    df = pd.read_csv(path)
    date_cols = [c for c in df.columns if re.match(r"^\d{4}-\d{2}-\d{2}$", str(c))]
    long = df.melt(id_vars=["RegionID", "RegionName", "RegionType", "StateName"], value_vars=date_cols,
                   var_name="date", value_name="value")
    d = pd.to_datetime(long["date"])
    long["valid_month"] = (d.dt.year * 12 + d.dt.month - 1).astype(int)
    return long.drop(columns="date")


def load_source(target: str, zdir: Path = ZILLOW_DIR) -> pd.DataFrame:
    """As-of long table for one target: region ('US' or the Zillow RegionID as text), name, state, valid_month,
    known_month, value. Only msa rows and the country row; months from START; missing values dropped."""
    w = read_wide(zdir / TARGET_FILES[target])
    w = w[w.RegionType.isin(["msa", "country"])].copy()
    w["region"] = np.where(w.RegionType.eq("country"), US, w.RegionID.astype(str))
    w["state"] = np.where(w.RegionType.eq("country"), "", w.RegionName.str.split(", ").str[-1])
    w = w[(w.valid_month >= START) & w.value.notna()]
    w["known_month"] = w.valid_month + 1
    return w[["region", "RegionName", "state", "valid_month", "known_month", "value"]].rename(
        columns={"RegionName": "name"}).reset_index(drop=True)


def asof_view(src: pd.DataFrame, a: int) -> pd.DataFrame:
    """Everything a forecaster standing in month `a` could know: rows with known_month <= a."""
    return src[src.known_month <= a]


def select_members(view: pd.DataFrame, start: int, end: int) -> pd.DataFrame:
    """Metros with a value in every month start..end. Returns region, name, state (one row per metro)."""
    m = view[(view.region != US) & view.valid_month.between(start, end)]
    n = m.groupby("region").valid_month.nunique()
    keep = n[n == end - start + 1].index
    return (m[m.region.isin(keep)].drop_duplicates("region")[["region", "name", "state"]]
            .sort_values(["state", "name"]).reset_index(drop=True))


def member_panel(view: pd.DataFrame, members: pd.DataFrame, end: int, start: int = START):
    """Member values (m x T, last value carried forward over gaps) and the US row (T) for months start..end.
    Returns months, Y (members in `members` order), us, number of filled cells."""
    months = np.arange(start, end + 1)
    v = view[view.valid_month.between(start, end)]
    wide = (v[v.region.isin(members.region)].pivot(index="region", columns="valid_month", values="value")
            .reindex(index=members.region, columns=months))
    n_filled = int(wide.isna().sum().sum())
    wide = wide.ffill(axis=1)                                     # uses only earlier months
    if wide.isna().any().any():
        raise ValueError("a member has no value before a gap; membership rule violated")
    us = v[v.region == US].set_index("valid_month").value.reindex(months)
    if us.isna().any():
        raise ValueError("US row missing a month inside the window")
    return months, wide.to_numpy(float), us.to_numpy(float), n_filled
