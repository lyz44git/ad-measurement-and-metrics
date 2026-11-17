"""Descriptive data checks (reported, never used to change the data).

Logic copied, not imported, from an earlier unpublished project of the same author (metro_market_ssm): the Zillow-name -> CBSA crosswalk
(`match_regions`) and the coverage-break rule (`clean_coverage`), here used only to flag breaks."""
from __future__ import annotations
import re
import numpy as np
import pandas as pd
from .paths import CENSUS_XLSX


def cbsa_titles(path=CENSUS_XLSX) -> pd.DataFrame:
    x = pd.read_excel(path, header=2, dtype={"CBSA Code": str})
    x = x[x["CBSA Code"].str.fullmatch(r"\d{5}", na=False)]
    return (x[["CBSA Code", "CBSA Title", "Metropolitan/Micropolitan Statistical Area"]].drop_duplicates("CBSA Code")
            .rename(columns={"CBSA Code": "cbsa", "CBSA Title": "title",
                             "Metropolitan/Micropolitan Statistical Area": "kind"}))


def _key(city: str, state: str) -> str:
    city = re.sub(r"[^a-z]", "", city.lower().replace("saint", "st").replace("st.", "st"))
    return f"{city}|{state.strip().upper()}"


def match_regions(z: pd.DataFrame, t: pd.DataFrame) -> pd.DataFrame:
    """z: region, name ('Dallas, TX'); t: cbsa, title. First city + first state of the CBSA title ('exact'),
    then any city x any state of the title for names still unmatched ('alias'). Ambiguous keys are never matched."""
    t = t.copy()
    city = t.title.str.split(",").str[0].str.split("-").str[0]
    state = t.title.str.split(",").str[1].str.strip().str.split("-").str[0]
    t["key"] = [_key(c, s) for c, s in zip(city, state)]
    t1 = t.drop_duplicates("key", keep=False)
    z = z.copy()
    z["key"] = [_key(n.split(",")[0], n.split(",")[1] if "," in n else "") for n in z.name]
    m = z.merge(t1[["key", "cbsa"]], on="key", how="left")
    m["match"] = np.where(m.cbsa.notna(), "exact", "none")
    rows = []
    for cb, title in zip(t.cbsa, t.title):
        cities, _, states = title.partition(",")
        for c in re.split(r"[-/]", cities):
            for s in states.strip().split("-"):
                rows.append((_key(c, s), cb))
    alias = pd.DataFrame(rows, columns=["key", "cbsa"]).drop_duplicates()
    alias = alias[~alias.key.duplicated(keep=False)]
    alias = alias[~alias.cbsa.isin(set(m.cbsa.dropna()))].set_index("key").cbsa
    miss = m.match.eq("none")
    m.loc[miss, "cbsa"] = m.loc[miss, "key"].map(alias)
    m.loc[miss & m.cbsa.notna(), "match"] = "alias"
    dup = m.cbsa.notna() & m.cbsa.duplicated(keep=False) & m.match.eq("alias")
    m.loc[dup, ["cbsa", "match"]] = [np.nan, "none"]
    return m.drop(columns="key")


def crosswalk_summary(members: pd.DataFrame) -> dict:
    t = cbsa_titles()
    m = match_regions(members[["region", "name", "state"]], t).merge(t, on="cbsa", how="left")
    first_state = m.title.str.split(",").str[1].str.strip().str.split("-").str[0]
    matched = m.cbsa.notna()
    return {"members": int(len(m)), "matched": int(matched.sum()),
            "matched_metro": int(m.kind.eq("Metropolitan Statistical Area").sum()),
            "matched_micro": int(m.kind.eq("Micropolitan Statistical Area").sum()),
            "state_agrees_with_cbsa_first_state": int((first_state[matched] == m.state[matched]).sum())}


def flag_breaks(Y: np.ndarray, shift=np.log(4), persist=np.log(3), spike=np.log(4)) -> dict:
    """Coverage-break rule on log values of each row (members x months), one pass each: a largest one-month jump
    above `shift` whose 6-month medians before/after differ by more than `persist` (level shift), and points more
    than `spike` from the median of their 3 neighbors on each side (spike). Counts only."""
    n_shift = n_spike = 0
    rows_flagged = set()
    for r, v in enumerate(np.log(Y)):
        dv = np.abs(np.diff(v))
        j = int(np.argmax(dv)) + 1
        if dv[j - 1] > shift and abs(np.median(v[j:j + 6]) - np.median(v[max(0, j - 6):j])) > persist:
            n_shift += 1
            rows_flagged.add(r)
        for k in range(len(v)):
            nb = np.r_[v[max(0, k - 3):k], v[k + 1:k + 4]]
            if len(nb) >= 3 and abs(v[k] - np.median(nb)) > spike:
                n_spike += 1
                rows_flagged.add(r)
    return {"level_shifts": n_shift, "spikes": n_spike, "members_flagged": len(rows_flagged)}
