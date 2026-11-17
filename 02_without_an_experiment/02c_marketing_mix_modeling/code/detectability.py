"""Signal-to-noise index of each brand-channel, scored against recovery error (design/detectability_plan.md).

Usage: python code/detectability.py <conjura_mmm_data.csv> <out_dir>
Needs out/mmm_pooled_recovery.csv and out/mmm_pooled_recovery_daily.csv from run_pooled.py. NumPy and pandas only.
Writes <out_dir>/detectability.json and detectability.csv.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mmm_core import settings, load_brands, design, lag_matrix, media_contribution, simulate_revenue, simulate_revenue_shapes  # noqa: E402

CHANNELS = ("google", "meta")
Z_POWER = 1.959964 + 0.841621
THRESHOLD = 2.0


def residual(y, X):
    """Residual of an OLS regression of y on an intercept and the columns of X."""
    Z = np.column_stack([np.ones(len(y)), X])
    return y - Z @ np.linalg.lstsq(Z, y, rcond=None)[0]


def index(contrib, other, X, noise_sd):
    """sqrt(n) x SD of the part of `contrib` not explained by the baseline terms X and `other`, over the noise SD."""
    return float(np.sqrt(len(contrib)) * residual(contrib, np.column_stack([X, other])).std() / noise_sd)


def brand_indices(g, freq, contrib):
    """Index of both channels of one brand for the given contributions (2 x n array, revenue units)."""
    H = settings(freq)["H"]; n = len(g); ntr = n - H
    X = design(n, freq, g.week.dt.weekday.values)[:ntr]
    noise_sd = residual(g.rev.values.astype(float)[:ntr], X).std()
    return [index(contrib[c, :ntr], contrib[1 - c, :ntr], X, noise_sd) for c in range(2)], noise_sd, X


def min_detectable_roas(g, freq, a=0.5, h=0.5):
    """Smallest ROAS of each channel detectable with 80% power for an assumed shape (adstock a, Hill h, k = 1)."""
    s = settings(freq); H, L = s["H"], s["L"]; n = len(g); ntr = n - H
    S = np.column_stack([g.google.values, g.meta.values]).astype(float)
    smax = S[:ntr].max(axis=0); smax[smax == 0] = 1.0
    unit = np.zeros((2, n))                                    # contribution of each channel at ROAS = 1
    for c in range(2):
        sat = media_contribution(lag_matrix(S[:, c] / smax[c], L), a, h, 1.0, 1.0)
        unit[c] = sat * S[:ntr, c].sum() / sat[:ntr].sum()
    per_unit, noise_sd, _ = brand_indices(g, freq, unit)
    return [Z_POWER / t if t > 0 else np.inf for t in per_unit]


def score(t, model="single", boot=2000, seed=1):
    """Predictions P1 and P2 of the plan for one test table (columns org, index, true, <model>)."""
    from scipy.stats import spearmanr
    t = t.assign(err=(t[model] - t["true"]).abs() / t["true"])
    rho = float(spearmanr(t["index"], t.err)[0])
    rng = np.random.default_rng(seed); orgs = t.org.unique(); groups = {o: g for o, g in t.groupby("org")}
    bs = []
    for _ in range(boot):
        s = pd.concat([groups[o] for o in rng.choice(orgs, len(orgs))])
        bs.append(spearmanr(s["index"], s.err)[0])
    lo, hi = np.nanquantile(bs, [0.025, 0.975])
    hi_g, lo_g = t[t["index"] >= THRESHOLD], t[t["index"] < THRESHOLD]

    def group(k):
        return dict(n=int(len(k)), median_err=float(k.err.median()) if len(k) else None,
                    spearman_true_est=float(spearmanr(k["true"], k[model])[0]) if len(k) > 3 else None)

    p1 = bool(rho < 0 and hi < 0)
    p2 = bool(len(hi_g) > 0 and len(lo_g) > 0 and hi_g.err.median() < 0.25 and hi_g.err.median() < lo_g.err.median())
    return dict(n=int(len(t)), brands=int(len(orgs)), spearman_index_error=rho, spearman_ci=[float(lo), float(hi)],
                index_2_or_more=group(hi_g), index_below_2=group(lo_g), share_index_2_or_more=float(len(hi_g) / len(t)),
                p1=p1, p2=p2, both=bool(p1 and p2))


def main(raw_path, out):
    raw = pd.read_csv(raw_path, parse_dates=["DATE_DAY"])
    res, rows = {}, []
    for freq in ("W", "D"):
        suf = settings(freq)["SUF"]
        brands, _ = load_brands(raw, freq); orgs = sorted(brands)
        rec = pd.read_csv(os.path.join(out, f"mmm_pooled_recovery{suf}.csv"))
        rng1, rng2 = np.random.default_rng(21), np.random.default_rng(22)
        for o in orgs:
            g = brands[o]; n = len(g)
            ymean = g.rev.values[: n - settings(freq)["H"]].mean()
            _, tr1, c1 = simulate_revenue_shapes(g, np.ones(n), ymean, 1.0, rng1, freq)   # same draws as run_pooled.py
            _, tr2, c2 = simulate_revenue(g, np.ones(n), ymean, 1.0, rng2, freq)
            mde = min_detectable_roas(g, freq)
            for sim, tr, c in (("brand_shapes", tr1, c1), ("common_shapes", tr2, c2)):
                idx, _, _ = brand_indices(g, freq, c)
                for k, ch in enumerate(CHANNELS):
                    rows.append(dict(freq=freq, sim=sim, org=o, channel=ch, true=tr[k], index=idx[k], min_detectable_roas=mde[k]))
        d = pd.DataFrame([r for r in rows if r["freq"] == freq]).merge(rec, on=["sim", "org", "channel"], suffixes=("", "_rec"))
        assert np.allclose(d["true"], d["true_rec"]), "simulation draws do not match run_pooled.py"
        res[freq] = {}
        for sim in ("brand_shapes", "common_shapes"):
            t = d[(d.sim == sim) & d.single_converged]
            res[freq][sim] = dict(single=score(t, "single"), pooled=score(d[(d.sim == sim) & d.pooled_converged], "pooled"))
        m = d[d.sim == "brand_shapes"].min_detectable_roas
        res[freq]["real_spend"] = dict(brand_channels=int(len(m)), median_min_detectable_roas=float(m.median()),
                                       quartiles=m.quantile([0.25, 0.75]).tolist(),
                                       share_at_most={str(k): float((m <= k).mean()) for k in (1, 2, 4)})
    all_rows = pd.DataFrame(rows)
    all_rows.to_csv(os.path.join(out, "detectability.csv"), index=False)
    res["tests"] = {"T1": res["D"]["brand_shapes"]["single"], "T2": res["D"]["common_shapes"]["single"],
                    "T3": res["W"]["common_shapes"]["single"]}
    res["exploration_weekly_brand_shapes"] = res["W"]["brand_shapes"]["single"]
    res["rule_met"] = res["tests"]["T1"]["both"]
    json.dump(res, open(os.path.join(out, "detectability.json"), "w"), indent=1)
    print(json.dumps({k: res[k] for k in ("tests", "exploration_weekly_brand_shapes", "rule_met")}, indent=1))
    print(json.dumps({f: res[f]["real_spend"] for f in ("W", "D")}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
