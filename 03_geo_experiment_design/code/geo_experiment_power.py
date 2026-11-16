"""Market-level (geo) test design for a pricing or operations change: how many metros and months a test needs, and
which randomization and estimator detect the smallest effect while keeping the false-positive rate at 5%.
Write-up: ../README.md.

Method: placebo experiments on historical data. Each draw picks a test start month, N metros at random, and assigns
half to treatment, either completely at random or within matched pairs (metros ranked by volume in the 3 months before
the test, adjacent metros paired). There is no true effect, so the share of draws that reject at 5% is the
false-positive rate. Adding a known lift log(1 + delta) to treated metros gives power; the minimum detectable effect
(MDE) is the smallest delta with 80% power (two-sided 5% test). Outcome: log of total volume in the test window
(1, 2 or 3 months). Because the lift is added on the log scale and every standard error below is unchanged by it,
power for every delta comes from the same null draws.

Estimators
- Complete randomization (CR): difference in means; year-over-year difference (outcome minus the same months one year
  earlier); ANCOVA (regression on same-months-last-year and last-3-months volume, CUPED-style; HC2 errors);
  volume-weighted ANCOVA (weights = prior 12-month volume; estimand = lift in total volume, not the average metro).
- Matched pairs (MP): mean within-pair difference; within-pair year-over-year difference; pair ANCOVA (pair differences
  regressed on covariate differences, intercept = effect; HC2).
t critical values use the residual degrees of freedom.

Data
Zillow Research public data: newly pending listings (raw, all homes, metro, monthly 2018-01..2026-09). Data Provided
by Zillow Group. Download Metro_new_pending_uc_sfrcondo_month.csv from zillow.com/research/data and pass its path as
the first argument (default: data_raw/Metro_new_pending_uc_sfrcondo_month.csv). The file is not stored in this repo.
Pools: complete monthly series; mean volume over the first 12 months at or above a threshold; metros with a
coverage break (any month below 1/4 or above 4x the metro's own median) are written to coverage_breaks.csv and dropped.
"""
import sys, json, functools, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
import figstyle
import numpy as np, pandas as pd
from scipy.stats import t as tdist
import matplotlib.pyplot as plt
print = functools.partial(print, flush=True)

DEFAULT_ZFILE = ROOT / "data_raw" / "Metro_new_pending_uc_sfrcondo_month.csv"
OUT = ROOT / "out"
NS, DS, R = [20, 50, 100, 200], [1, 2, 3], 5000
DELTA = np.round(np.arange(0, 0.5005, 0.001), 3)
BREAK_LO, BREAK_HI = 0.25, 4.0
SHOCKS = {"COVID (test window overlaps 2020-03..2020-06)": ("2020-03", "2020-06"),
          "Rate shock (overlaps 2022-05..2022-12)": ("2022-05", "2022-12")}
t0 = time.time()


# ------------------------------------------------------------------ data
def screen(Y, source, min_mean):
    """Y: units x months counts (NaN = missing). Returns the pool and writes the screening counts."""
    n_all = len(Y); tot_all = np.nansum(Y.to_numpy())
    comp = Y[Y.notna().all(axis=1)]                    # zeros stay in, so drops to zero show up as coverage breaks
    big = comp[comp.iloc[:, :12].mean(axis=1) >= min_mean]
    ratio = big.div(big.median(axis=1), axis=0)
    brk = (ratio < BREAK_LO) | (ratio > BREAK_HI)
    B = pd.DataFrame({"source": source, "unit": big.index[brk.any(axis=1)],
                      "min_ratio_to_median": ratio[brk.any(axis=1)].min(axis=1).round(3).values,
                      "month_of_min": ratio[brk.any(axis=1)].idxmin(axis=1).astype(str).values,
                      "max_ratio_to_median": ratio[brk.any(axis=1)].max(axis=1).round(3).values,
                      "months_flagged": brk.sum(axis=1)[brk.any(axis=1)].values})
    pool = big[~brk.any(axis=1)]
    summ = {"source": source, "units_with_any_data": n_all, "complete_series": len(comp),
            "min_mean_first12": min_mean, "above_size_threshold": len(big), "coverage_breaks_dropped": int(brk.any(axis=1).sum()),
            "pool": len(pool), "pool_share_of_all_volume": round(float(pool.to_numpy().sum() / tot_all), 4),
            "first_month": str(Y.columns[0])[:7], "last_month": str(Y.columns[-1])[:7], "months": Y.shape[1],
            "median_pool_monthly_volume": float(pool.median(axis=1).median())}
    print(summ)
    return pool, B, summ


def load_zillow(zfile=DEFAULT_ZFILE):
    z = pd.read_csv(zfile)
    z = z[z.RegionType.eq("msa")]
    dc = [c for c in z.columns if c[:2] in ("19", "20")]
    Y = z.set_index("RegionName")[dc].astype(float)
    Y.columns = pd.PeriodIndex(pd.to_datetime(dc), freq="M")
    return screen(Y, "Zillow newly pending listings", 100)


# ------------------------------------------------------------------ estimators
def ols_hc2(X, y, j=1):
    XtXi = np.linalg.inv(X.T @ X)
    b = XtXi @ (X.T @ y); e = y - X @ b
    h = np.einsum("ij,jk,ik->i", X, XtXi, X)
    meat = (X * (e ** 2 / (1 - h))[:, None]).T @ X
    V = XtXi @ meat @ XtXi
    return b[j], np.sqrt(V[j, j]), len(y) - X.shape[1]


def dim(y, tr):
    a, c = y[tr == 1], y[tr == 0]
    return a.mean() - c.mean(), np.sqrt(a.var(ddof=1) / len(a) + c.var(ddof=1) / len(c)), len(y) - 2


def mean_se(d):
    return d.mean(), d.std(ddof=1) / np.sqrt(len(d)), len(d) - 1


EST = ["CR: difference in means", "CR: year-over-year difference", "CR: ANCOVA (CUPED)", "CR: volume-weighted ANCOVA",
       "MP: pair difference", "MP: pair year-over-year difference", "MP: pair ANCOVA"]


def simulate(pool, source, seed):
    L = pool.to_numpy(float); U, Tm = L.shape
    months = pool.columns
    Cs = np.c_[np.zeros(U), np.cumsum(L, 1)]
    S = lambda a, b: Cs[:, b] - Cs[:, a]                   # volume over months [a, b)
    rng = np.random.default_rng(seed)
    n_all = U - (U % 2)
    out = []
    for D in DS:
        starts = np.arange(12, Tm - D + 1)
        for N in NS + [n_all]:
            if N > U:
                continue
            res = {k: np.empty((R, 3)) for k in EST}; svec = np.empty(R, int)
            for r in range(R):
                s = int(rng.choice(starts)); u = rng.choice(U, N, replace=False); svec[r] = s
                y = np.log(S(s, s + D)[u]); xy = np.log(S(s - 12, s - 12 + D)[u]); xr = np.log(S(s - 3, s)[u])
                w = S(s - 12, s)[u]
                tr = np.zeros(N); tr[rng.permutation(N)[: N // 2]] = 1
                X = np.c_[np.ones(N), tr, xy, xr]
                res[EST[0]][r] = dim(y, tr)
                res[EST[1]][r] = dim(y - xy, tr)
                res[EST[2]][r] = ols_hc2(X, y)
                sw = np.sqrt(w / w.mean()); res[EST[3]][r] = ols_hc2(X * sw[:, None], y * sw)
                pr = np.argsort(xr, kind="mergesort").reshape(-1, 2); P = len(pr)
                f = rng.integers(0, 2, P); a, c = pr[np.arange(P), f], pr[np.arange(P), 1 - f]
                dy, dxy, dxr = y[a] - y[c], xy[a] - xy[c], xr[a] - xr[c]
                res[EST[4]][r] = mean_se(dy)
                res[EST[5]][r] = mean_se(dy - dxy)
                res[EST[6]][r] = ols_hc2(np.c_[np.ones(P), dxy, dxr], dy, j=0)
            sd_dim = res[EST[0]][:, 0].std()
            for k in EST:
                est, se, df = res[k].T
                crit = tdist.ppf(0.975, df)
                pw = (np.abs(est[:, None] + np.log1p(DELTA)[None, :]) / se[:, None] > crit[:, None]).mean(0)
                hit = np.nonzero(pw >= 0.8)[0]
                row = {"source": source, "metros": N, "all_pool": N == n_all, "test_months": D, "estimator": k,
                       "draws": R, "sd_pct": est.std() * 100, "mean_est_pct": est.mean() * 100,
                       "false_positive_rate": pw[0], "mde_80_pct": DELTA[hit[0]] * 100 if len(hit) else np.nan,
                       "power_at_2pct": pw[DELTA == 0.02][0], "power_at_5pct": pw[DELTA == 0.05][0],
                       "variance_vs_difference_in_means": (est.std() / sd_dim) ** 2, "windows": len(starts)}
                for lab, (lo, hi) in SHOCKS.items():
                    a0, b0 = pd.Period(lo, "M"), pd.Period(hi, "M")
                    m = np.array([(months[s_] <= b0) and (months[s_ + D - 1] >= a0) for s_ in svec])
                    row[f"fpr_{lab.split(' (')[0]}"] = ((np.abs(est[m]) / se[m]) > crit[m]).mean() if m.any() else np.nan
                    row[f"draws_{lab.split(' (')[0]}"] = int(m.sum())
                out.append(row)
            print(f"{source}: D={D} N={N} done ({time.time() - t0:.0f}s)")
    return pd.DataFrame(out)


def ri_check(pool, source, seed, D=2, draws=2000, perms=199):
    """Randomization inference for the two ANCOVA estimators (2-month tests). The statistic is the treatment coefficient;
    its permutation distribution comes from re-drawing the half-and-half assignment. Because the coefficient is linear in
    the outcome, the p-value for any injected lift delta is exact from two vectors per draw:
    tau(T', y0 + delta*T) = tau(T', y0) + delta * b(T')."""
    L = pool.to_numpy(float); U, Tm = L.shape
    Cs = np.c_[np.zeros(U), np.cumsum(L, 1)]
    S = lambda a, b: Cs[:, b] - Cs[:, a]
    rng = np.random.default_rng(seed); starts = np.arange(12, Tm - D + 1)
    shift = np.log1p(DELTA)
    rows = []
    for N in NS + [U - (U % 2)]:
        if N > U:
            continue
        rej = {"CR: ANCOVA (CUPED)": np.zeros((draws, len(DELTA))), "CR: volume-weighted ANCOVA": np.zeros((draws, len(DELTA)))}
        for r in range(draws):
            s = int(rng.choice(starts)); u = rng.choice(U, N, replace=False)
            y = np.log(S(s, s + D)[u]); xy = np.log(S(s - 12, s - 12 + D)[u]); xr = np.log(S(s - 3, s)[u]); w = S(s - 12, s)[u]
            Tall = np.zeros((N, perms + 1))
            for p in range(perms + 1):
                Tall[rng.permutation(N)[: N // 2], p] = 1      # column 0 is the "real" assignment
            for k, sw in [("CR: ANCOVA (CUPED)", np.ones(N)), ("CR: volume-weighted ANCOVA", np.sqrt(w / w.mean()))]:
                Q, _ = np.linalg.qr(np.c_[np.ones(N), xy, xr] * sw[:, None])
                Ts = Tall * sw[:, None]; Rm = Ts - Q @ (Q.T @ Ts)                  # residualized assignments
                den = (Rm * Rm).sum(0)
                a = (Rm.T @ (y * sw)) / den                                         # tau under each assignment, no effect
                b = (Rm.T @ Ts[:, 0]) / den                                         # how the real lift loads on each
                stat = np.abs(a[1:, None] + b[1:, None] * shift[None, :])
                obs = np.abs(a[0] + shift)[None, :]
                pval = (1 + (stat >= obs - 1e-12).sum(0)) / (perms + 1)
                rej[k][r] = pval <= 0.05
        for k, m in rej.items():
            pw = m.mean(0); hit = np.nonzero(pw >= 0.8)[0]
            rows.append({"source": source, "metros": N, "test_months": D, "estimator": k, "inference": "randomization",
                         "draws": draws, "permutations": perms, "false_positive_rate": pw[0],
                         "mde_80_pct": DELTA[hit[0]] * 100 if len(hit) else np.nan})
        print(f"{source}: RI N={N} done ({time.time() - t0:.0f}s)")
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ run
def main(zfile=DEFAULT_ZFILE):
    OUT.mkdir(parents=True, exist_ok=True)
    pools, breaks, summs, results, ris = {}, [], [], [], []
    for seed in [11]:
        pool, B, summ = load_zillow(zfile)
        pools[summ["source"]] = pool; breaks.append(B); summs.append(summ)
        results.append(simulate(pool, summ["source"], seed))
        ris.append(ri_check(pool, summ["source"], seed + 100))
    RES = pd.concat(results, ignore_index=True)
    RES.to_csv(OUT / "design_summary.csv", index=False)
    RI = pd.concat(ris, ignore_index=True)
    tt = RES[(RES.test_months == 2) & RES.estimator.isin(RI.estimator.unique())][["source", "metros", "estimator",
                                                                                "false_positive_rate", "mde_80_pct"]]
    RI = RI.merge(tt, on=["source", "metros", "estimator"], suffixes=("", "_t_test"))
    RI.to_csv(OUT / "randomization_inference_check.csv", index=False)
    print(RI.round(3).to_string(index=False))
    pd.concat(breaks).to_csv(OUT / "coverage_breaks.csv", index=False)
    pd.DataFrame(summs).to_csv(OUT / "pool_summary.csv", index=False)
    mde2 = RES[RES.test_months == 2].pivot_table(index=["source", "estimator"], columns="metros", values="mde_80_pct")
    mde2.round(1).to_csv(OUT / "mde_2month_by_metros.csv")
    print(mde2.round(1).to_string())
    print(RES.groupby(["source", "estimator"]).false_positive_rate.agg(["min", "max"]).round(3).to_string())

    # ------------------------------------------------------------------ figure: MDE vs metros, 2-month test
    figstyle.apply()
    SHOW = ["CR: year-over-year difference", "CR: ANCOVA (CUPED)", "MP: pair ANCOVA"]
    fig, ax = plt.subplots(figsize=(5.6, 4.0))
    src = next(iter(pools))
    d = RES[(RES.source == src) & (RES.test_months == 2)]
    for i, k in enumerate(SHOW):
        g = d[d.estimator == k].sort_values("metros")
        ax.plot(g.metros, g.mde_80_pct, marker="o", color=figstyle.SERIES[i], label=k)
    xt = sorted(d.metros.unique()); ax.set_xscale("log"); ax.set_xticks(xt); ax.set_xticklabels([str(n) for n in xt]); ax.minorticks_off()
    ax.set_xlabel("Metros in the test (half treated)"); ax.set_ylabel("Minimum detectable effect, % (80% power)")
    ax.set_title(f"{src}: 2-month test"); ax.legend(loc="upper right")
    figstyle.note(fig, "Placebo experiments on historical data (5,000 draws per point); two-sided 5% tests. Newly pending "
                  "listings, metro monthly 2018-01..2026-09 (largest point = all eligible metros). Data Provided by Zillow Group.")
    fig.tight_layout(); fig.savefig(OUT / "fig1_mde_by_metros.png")

    json.dump({"draws_per_cell": R, "metros_grid": NS, "test_months": DS, "break_rule": [BREAK_LO, BREAK_HI],
               "pools": summs, "runtime_s": round(time.time() - t0)}, open(OUT / "meta.json", "w"), indent=1, default=str)
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_ZFILE)
