"""SQL readout of a two-arm experiment: checks, metrics, reconciliation with another implementation, sample size."""
from pathlib import Path

SQL = Path(__file__).resolve().parents[1] / "sql"
Z_POWER = 1.959964 + 0.841621
EXPECTED = {"c2_rows_with_null": 0, "c3_rows_with_non_binary_flag": 0, "c4_exposed_in_control": 0}


def query(con, name):
    """Run sql/<name>.sql on the table `users`; return a list of dicts."""
    cur = con.execute((SQL / f"{name}.sql").read_text())
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def checks(con, expected_rows=None):
    """Counts C1 to C7 and the checks that failed (C1 to C4 have expected values)."""
    c = {k: int(v) for k, v in query(con, "checks")[0].items()}
    c.update({k: int(v) for k, v in query(con, "duplicates")[0].items()})
    want = dict(EXPECTED)
    if expected_rows is not None:
        want["c1_rows"] = expected_rows
    failed = [k for k, v in want.items() if c[k] != v]
    return c, failed


def readout(con):
    """Rows by arm and the effect table (one dict per outcome, keyed by outcome)."""
    return query(con, "readout_by_arm"), {r["outcome"]: r for r in query(con, "readout_effects")}


def compare(name, sql, other, kind):
    """One comparison. kind: 'count' (equal), 'value' (abs diff <= 1e-9), 'float_count' (<= 1e-6), 'se' (rel <= 1e-6)."""
    diff = abs(sql - other)
    ok = {"count": diff == 0, "value": diff <= 1e-9, "float_count": diff <= 1e-6,
          "se": diff <= 1e-6 * abs(other)}[kind]
    return dict(metric=name, kind=kind, sql=sql, python=other, abs_diff=diff, agree=bool(ok))


def reconcile(by_arm, eff, s01a, s02a):
    """Compare the SQL readout with the outputs of studies 01a and 02a (plan: reconciliation rule)."""
    a = {r["arm"]: r for r in by_arm}
    n0, n1 = a[0]["users"], a[1]["users"]
    out = [compare("01a users", n0 + n1, s01a["n"], "count"),
           compare("01a share assigned to the ad arm", n1 / (n0 + n1), s01a["treated_share"], "value"),
           compare("02a users, control", n0, s02a["n_control"], "count"),
           compare("02a users, ad arm", n1, s02a["n_treated"], "count"),
           compare("02a exposed users, ad arm", a[1]["exposed_users"], s02a["exposed_treated"], "count"),
           compare("02a exposed users, control", a[0]["exposed_users"], s02a["exposed_control"], "count"),
           compare("02a exposure rate, ad arm", a[1]["exposure_rate"], s02a["exposure_share"], "value")]
    for o in ("visit", "conversion"):
        e, p1, p2 = eff[o], s01a[o]["itt"], s02a[o]
        out += [compare(f"01a {o}: users, control", e["users_control"], p1["n0"], "count"),
                compare(f"01a {o}: users, ad arm", e["users_ad_arm"], p1["n1"], "count"),
                compare(f"01a {o}: control rate", e["control_rate"], p1["control_mean"], "value"),
                compare(f"01a {o}: effect of assignment", e["effect_of_assignment"], p1["est"], "value"),
                compare(f"01a {o}: standard error", e["standard_error"], p1["se"], "se"),
                compare(f"02a {o}: effect of assignment", e["effect_of_assignment"], p2["itt"], "value"),
                compare(f"02a {o}: outcomes in the ad arm", e["outcomes_ad_arm"], p2["treated_total"], "count"),
                compare(f"02a {o}: outcomes caused", e["outcomes_caused"], p2["incremental"], "float_count"),
                compare(f"02a {o}: outcomes credited", e["outcomes_credited"], p2["attributed"], "count"),
                compare(f"02a {o}: credited over caused", e["credited_over_caused"], p2["attributed_over_incremental"], "value"),
                compare(f"02a {o}: effect per exposed user", e["effect_per_exposed_user"], p2["cace"], "value")]
    return out


def n_per_arm(p0, p1):
    """Users per arm for a two-sided 5% test of two proportions with 80% power and equal arms."""
    return Z_POWER ** 2 * (p0 * (1 - p0) + p1 * (1 - p1)) / (p1 - p0) ** 2


def sizing(p0_visit, p0_conversion, lifts=(0.05, 0.10, 0.25, 0.50)):
    """Users per arm by endpoint and relative lift, plus a one-point absolute lift in the visit rate."""
    rows = [dict(endpoint=name, control_rate=p0, lift="relative", size=l, ad_arm_rate=p0 * (1 + l),
                 users_per_arm=n_per_arm(p0, p0 * (1 + l)))
            for name, p0 in (("visit", p0_visit), ("conversion", p0_conversion)) for l in lifts]
    rows.append(dict(endpoint="visit", control_rate=p0_visit, lift="absolute", size=0.01, ad_arm_rate=p0_visit + 0.01,
                     users_per_arm=n_per_arm(p0_visit, p0_visit + 0.01)))
    return rows
