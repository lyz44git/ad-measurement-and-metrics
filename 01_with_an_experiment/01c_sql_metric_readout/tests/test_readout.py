"""Checks of the SQL readout on a small simulated experiment (no dataset needed)."""
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
import readout_core as rc


def table(n=20000, seed=0):
    rng = np.random.default_rng(seed)
    t = (rng.random(n) < 0.8).astype(int)
    e = ((rng.random(n) < 0.1) & (t == 1)).astype(int)
    v = (rng.random(n) < 0.05 + 0.02 * t + 0.4 * e).astype(int)
    c = ((rng.random(n) < 0.2) & (v == 1)).astype(int)
    d = pd.DataFrame({f"f{i}": rng.normal(size=n) for i in range(12)})
    return d.assign(treatment=t, exposure=e, visit=v, conversion=c)


def connect(d):
    con = duckdb.connect()
    con.register("d", d)
    con.execute("CREATE TABLE users AS SELECT * FROM d")
    return con


def test_sql_readout_matches_pandas():
    d = table()
    by_arm, eff = rc.readout(connect(d))
    g = d.groupby("treatment")
    for r in by_arm:
        k = g.get_group(r["arm"])
        assert r["users"] == len(k) and r["visits"] == k.visit.sum() and r["conversions"] == k.conversion.sum()
        assert r["exposed_users"] == k.exposure.sum() and abs(r["visit_rate"] - k.visit.mean()) < 1e-12
        assert r["conversions_of_exposed_users"] == (k.conversion * k.exposure).sum()
    c, a = g.get_group(0), g.get_group(1)
    for o in ("visit", "conversion"):
        e = eff[o]
        itt = a[o].mean() - c[o].mean()
        se = np.sqrt(a[o].mean() * (1 - a[o].mean()) / len(a) + c[o].mean() * (1 - c[o].mean()) / len(c))
        credited = (a[o] * a.exposure).sum()
        assert abs(e["effect_of_assignment"] - itt) < 1e-12 and abs(e["standard_error"] - se) < 1e-12
        assert abs(e["outcomes_caused"] - itt * len(a)) < 1e-8 and e["outcomes_credited"] == credited
        assert abs(e["credited_over_caused"] - credited / (itt * len(a))) < 1e-9
        assert abs(e["effect_per_exposed_user"] - itt / a.exposure.mean()) < 1e-12


def test_checks_pass_on_clean_data_and_catch_planted_errors():
    d = table()
    counts, failed = rc.checks(connect(d), len(d))
    assert failed == [] and counts["c5_conversion_without_visit"] == 0 and counts["c7_rows_identical_to_another"] == 0
    bad = d.copy()
    i = bad.index[bad.treatment == 0][:3]
    bad.loc[i, "exposure"] = 1                                   # exposed users in the control arm
    bad.loc[bad.index[5], "visit"] = 2                           # a flag that is not 0 or 1
    bad = pd.concat([bad, bad.iloc[[7, 7]]], ignore_index=True)  # row 7 now appears three times
    bad.loc[bad.index[9], "f3"] = None
    counts, failed = rc.checks(connect(bad), len(d))
    assert set(failed) == {"c1_rows", "c2_rows_with_null", "c3_rows_with_non_binary_flag", "c4_exposed_in_control"}
    assert counts["c4_exposed_in_control"] == 3 and counts["c7_rows_identical_to_another"] == 3


def other_implementation(d):
    """The same quantities computed with pandas, in the layout of the result files of studies 01a and 02a."""
    c, a = d[d.treatment == 0], d[d.treatment == 1]
    s1 = {"n": len(d), "treated_share": len(a) / len(d)}
    s2 = {"n_control": len(c), "n_treated": len(a), "exposed_treated": int(a.exposure.sum()),
          "exposed_control": int(c.exposure.sum()), "exposure_share": a.exposure.mean()}
    for o in ("visit", "conversion"):
        itt = a[o].mean() - c[o].mean()
        se = np.sqrt(a[o].mean() * (1 - a[o].mean()) / len(a) + c[o].mean() * (1 - c[o].mean()) / len(c))
        credited = int((a[o] * a.exposure).sum())
        s1[o] = {"itt": {"est": itt, "se": se, "control_mean": c[o].mean(), "n1": len(a), "n0": len(c)}}
        s2[o] = {"itt": itt, "incremental": itt * len(a), "attributed": credited,
                 "attributed_over_incremental": credited / (itt * len(a)), "cace": itt / a.exposure.mean(),
                 "treated_total": int(a[o].sum())}
    return s1, s2


def test_reconciliation_agrees_and_flags_a_changed_number():
    d = table(seed=3)
    by_arm, eff = rc.readout(connect(d))
    s1, s2 = other_implementation(d)
    rec = rc.reconcile(by_arm, eff, s1, s2)
    assert len(rec) == 29 and all(r["agree"] for r in rec)
    s2["conversion"]["attributed"] += 1
    s1["visit"]["itt"]["est"] += 1e-6
    wrong = [r["metric"] for r in rc.reconcile(by_arm, eff, s1, s2) if not r["agree"]]
    assert wrong == ["01a visit: effect of assignment", "02a conversion: outcomes credited"]


def test_sample_size_formula():
    assert abs(rc.n_per_arm(0.5, 0.6) - rc.Z_POWER ** 2 * 0.49 / 0.01) < 1e-9
    rows = rc.sizing(0.04, 0.002)
    v = {r["size"]: r["users_per_arm"] for r in rows if r["endpoint"] == "visit" and r["lift"] == "relative"}
    c = {r["size"]: r["users_per_arm"] for r in rows if r["endpoint"] == "conversion"}
    assert all(c[k] > 15 * v[k] for k in v)          # a rarer endpoint needs far more users for the same relative lift
    assert v[0.05] > v[0.10] > v[0.25] > v[0.50]
