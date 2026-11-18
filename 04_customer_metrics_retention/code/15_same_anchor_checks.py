"""Two same-anchor checks added after review; no change to steps 10-14 or their outputs.

A. New-customer look-back at a fixed anchor. For each target month 2010-12 to 2011-11, take the accounts that bought in
   that month and flag whether they bought in the previous 3 and the previous 12 months (same accounts, same anchor).
   Counts are per month; the pooled total counts account-months, so an account can appear in more than one month.
B. Horizon at a fixed cutoff. At 2010-12-01, on the same accounts as E1 (every account with a purchase before the
   cutoff), the BG/NBD x Gamma-Gamma model and the past-sales rule (all sales before the cutoff) are scored by Spearman
   rank correlation against sales in the next 6 and the next 12 months. Customer bootstrap, 500 draws, models fixed.

Usage: python code/15_same_anchor_checks.py derived out code   (needs derived/uci_lines.parquet from 10_ltv_load.py)
Output: out/15_same_anchor_checks.json
"""
import sys, json
import numpy as np, pandas as pd
from scipy import stats
DER, OUT, CODE = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, CODE); from btyd_impl import fit_bgnbd, bgnbd_expected, fit_gg, gg_expected
L = pd.read_parquet(f"{DER}/uci_lines.parquet")
inv = L.groupby(["cid", "Invoice", "is_cancel"], as_index=False).agg(t=("InvoiceDate", "min"), rev=("revenue", "sum"))
inv["day"] = inv.t.dt.normalize()
days = inv[~inv.is_cancel].groupby(["cid", "day"]).rev.sum().reset_index()
days["mon"] = days.day.dt.to_period("M")
res = {}

# ---- A. 3- vs 12-month look-back, same target month and accounts
rows = []
for m in pd.period_range("2010-12", "2011-11", freq="M"):
    start = m.to_timestamp()
    buyers = days[days.mon == m].cid.unique()
    def seen(k):
        return set(days[(days.day < start) & (days.day >= start - pd.DateOffset(months=k))].cid.unique())
    s3, s12 = seen(3), seen(12)
    new3 = np.array([c not in s3 for c in buyers]); new12 = np.array([c not in s12 for c in buyers])
    rows.append(dict(month=str(m), buyers=int(len(buyers)), new_3m=int(new3.sum()), new_12m=int(new12.sum()),
                     new_3m_but_bought_in_12m=int((new3 & ~new12).sum()),
                     share_of_new_3m_bought_in_12m=float((new3 & ~new12).sum() / max(new3.sum(), 1))))
tot = {k: int(sum(r[k] for r in rows)) for k in ["buyers", "new_3m", "new_12m", "new_3m_but_bought_in_12m"]}
tot["share_of_new_3m_bought_in_12m"] = tot["new_3m_but_bought_in_12m"] / tot["new_3m"]
res["A_lookback_same_anchor"] = dict(definition="buyers in target month; new_k = no purchase day in the k months before the month start",
                                     by_month=rows, pooled_account_months=tot)

# ---- B. 6- vs 12-month horizon, same cutoff and accounts
cut = pd.Timestamp("2010-12-01")
d = days[days.day < cut]; g = d.groupby("cid")
b = pd.DataFrame({"first": g.day.min(), "last": g.day.max(), "n": g.day.size(), "past": g.rev.sum()})
b["x"] = b.n - 1; b["tx_w"] = (b["last"] - b["first"]).dt.days / 7; b["T_w"] = (cut - b["first"]).dt.days / 7
rep = d.merge(b[["first"]], left_on="cid", right_index=True); rep = rep[rep.day > rep["first"]]
b["m_rep"] = rep.groupby("cid").rev.mean().reindex(b.index)
bg, _ = fit_bgnbd(b.x.values, b.tx_w.values, b.T_w.values)
r_ = b.x > 0; gg = fit_gg(b.x[r_].values, b.m_rep[r_].values)
spend = gg_expected(gg, b.x.values, np.nan_to_num(b.m_rep.values, nan=1.0))
rng = np.random.default_rng(1)
out = {}
for name, months, weeks in [("6_months", 6, 26.0), ("12_months", 12, 365 / 7)]:
    hi = cut + pd.DateOffset(months=months)
    y = days[(days.day >= cut) & (days.day < hi)].groupby("cid").rev.sum().reindex(b.index).fillna(0).values
    pm = bgnbd_expected(bg, weeks, b.x.values, b.tx_w.values, b.T_w.values) * spend; pr = b.past.values
    sm, sr = stats.spearmanr(pm, y)[0], stats.spearmanr(pr, y)[0]
    bd = []
    for _ in range(500):
        i = rng.integers(0, len(y), len(y)); bd.append(stats.spearmanr(pm[i], y[i])[0] - stats.spearmanr(pr[i], y[i])[0])
    out[name] = dict(window=f"{cut.date()}..{(hi - pd.Timedelta(days=1)).date()}", spearman_model=float(sm), spearman_past_sales=float(sr),
                     diff_model_minus_rule=float(sm - sr), diff_ci95=[float(np.quantile(bd, .025)), float(np.quantile(bd, .975))])
res["B_horizon_same_cutoff"] = dict(cutoff=str(cut.date()), n_accounts=int(len(b)),
                                    bgnbd_params=dict(zip(["r", "alpha", "a", "b"], [float(v) for v in bg])), by_horizon=out)
json.dump(res, open(f"{OUT}/15_same_anchor_checks.json", "w"), indent=1)
print(json.dumps(res, indent=1))
