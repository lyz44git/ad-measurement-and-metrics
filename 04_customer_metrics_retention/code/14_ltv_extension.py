# Extension E1-E4 (see design/analysis_plan.md, hashed before this script was run).
# E1 12-month holdout of BG/NBD x Gamma-Gamma; E2 retention risk among high-value accounts;
# E3 early value of newly acquired accounts; E4 DuckDB SQL reconciliation with the pandas results of 12_ltv_segments.py.
# Sales are gross, from non-credit-note invoices. Predictive / descriptive only: no marketing treatment in the data.
import sys, json
import numpy as np, pandas as pd, duckdb
from scipy import stats
from sklearn.metrics import roc_auc_score
DER, OUT, CODE = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, CODE); from btyd_impl import fit_bgnbd, bgnbd_expected, fit_gg, gg_expected
L = pd.read_parquet(f"{DER}/uci_lines.parquet")
inv = L.groupby(["cid", "Invoice", "is_cancel"], as_index=False).agg(t=("InvoiceDate", "min"), rev=("revenue", "sum"))
inv["day"] = inv.t.dt.normalize()
sales = inv[~inv.is_cancel]
days = sales.groupby(["cid", "day"]).rev.sum().reset_index()
res = {}


def btyd_inputs(cut):
    d = days[days.day < cut]; g = d.groupby("cid")
    b = pd.DataFrame({"first": g.day.min(), "last": g.day.max(), "n": g.day.size(), "past": g.rev.sum()})
    b["x"] = b.n - 1; b["tx_w"] = (b["last"] - b["first"]).dt.days / 7; b["T_w"] = (cut - b["first"]).dt.days / 7
    rep = d.merge(b[["first"]], left_on="cid", right_index=True); rep = rep[rep.day > rep["first"]]
    b["m_rep"] = rep.groupby("cid").rev.mean().reindex(b.index)
    b["recency_d"] = (cut - b["last"]).dt.days
    return b


def window_sales(lo, hi, ids):
    w = days[(days.day >= lo) & (days.day < hi)]
    return w.groupby("cid").rev.sum().reindex(ids).fillna(0).values


def top_decile_capture(p, y, rng, reps=20):
    n = len(y); k = max(1, int(0.1 * n)); out = []
    for _ in range(reps):
        o = np.lexsort((rng.random(n), -p)); out.append(y[o[:k]].sum() / y.sum())
    return float(np.mean(out))


# ---------------- E1: 12-month holdout
cut = pd.Timestamp("2010-12-01"); end = pd.Timestamp("2011-12-01")
b = btyd_inputs(cut)
y = window_sales(cut, end, b.index)
bg, ll = fit_bgnbd(b.x.values, b.tx_w.values, b.T_w.values)
rep = b.x > 0; gg = fit_gg(b.x[rep].values, b.m_rep[rep].values)
ex = bgnbd_expected(bg, 365 / 7, b.x.values, b.tx_w.values, b.T_w.values)
pred = {"past_sales": b.past.values, "bgnbd_gg": ex * gg_expected(gg, b.x.values, np.nan_to_num(b.m_rep.values, nan=1.0))}
rng = np.random.default_rng(1)


def e1_metrics(p, yy, r):
    return dict(spearman=float(stats.spearmanr(p, yy)[0]), auc_any=float(roc_auc_score(yy > 0, p)),
                top10_capture=top_decile_capture(p, yy, r), agg_ratio=float(p.sum() / yy.sum()))


ev = {k: e1_metrics(p, y, rng) for k, p in pred.items()}
B = 500; boots = {k: [] for k in pred}
for _ in range(B):
    i = rng.integers(0, len(y), len(y))
    for k, p in pred.items():
        pp, yy = p[i], y[i]
        boots[k].append(dict(spearman=stats.spearmanr(pp, yy)[0], auc_any=roc_auc_score(yy > 0, pp),
                             top10_capture=top_decile_capture(pp, yy, rng, reps=1), agg_ratio=pp.sum() / yy.sum()))
for k in pred:
    for m in ["spearman", "auc_any", "top10_capture", "agg_ratio"]:
        v = [d[m] for d in boots[k]]; ev[k][m + "_ci"] = [float(np.quantile(v, .025)), float(np.quantile(v, .975))]
diff = {}
for m in ["spearman", "auc_any", "top10_capture"]:
    d = np.array([a[m] - c[m] for a, c in zip(boots["bgnbd_gg"], boots["past_sales"])])
    diff[m] = dict(observed=ev["bgnbd_gg"][m] - ev["past_sales"][m], ci=[float(np.quantile(d, .025)), float(np.quantile(d, .975))])
q = pd.qcut(pd.Series(pred["bgnbd_gg"]).rank(method="first"), 10, labels=False).values
res["E1"] = dict(cutoff="2010-12-01", holdout="2010-12-01..2011-11-30", n_accounts=int(len(b)), share_any_purchase=float((y > 0).mean()),
                 holdout_sales_total=float(y.sum()), bgnbd_params=dict(zip(["r", "alpha", "a", "b"], [float(v) for v in bg])),
                 gg_params=dict(zip(["p", "q", "gamma"], [float(v) for v in gg])), eval=ev, paired_diff_bgnbd_minus_past=diff,
                 rule_met=bool(diff["spearman"]["ci"][0] > 0),
                 calibration_deciles=[dict(pred=float(pred["bgnbd_gg"][q == j].mean()), actual=float(y[q == j].mean())) for j in range(10)],
                 top_decile_actual_share_bgnbd=ev["bgnbd_gg"]["top10_capture"])

# ---------------- E2: retention risk among high-value accounts
cut2 = pd.Timestamp("2011-06-01"); b2 = btyd_inputs(cut2)
bg2, _ = fit_bgnbd(b2.x.values, b2.tx_w.values, b2.T_w.values)
b2["exp26"] = bgnbd_expected(bg2, 26.0, b2.x.values, b2.tx_w.values, b2.T_w.values)
b2["sales12"] = window_sales(cut2 - pd.DateOffset(months=12), cut2, b2.index)
act = b2[b2.sales12 > 0].copy()
thr = act.sales12.quantile(2 / 3); hv = act[act.sales12 >= thr].copy()
hv["repurchase"] = (window_sales(cut2, cut2 + pd.DateOffset(months=6), hv.index) > 0).astype(int)
yb = hv.repurchase.values; s_model = hv.exp26.values; s_rec = -hv.recency_d.values.astype(float)
a_model, a_rec = roc_auc_score(yb, s_model), roc_auc_score(yb, s_rec)
bm, br, bd = [], [], []
for _ in range(1000):
    i = rng.integers(0, len(yb), len(yb))
    if yb[i].min() == yb[i].max(): continue
    m_, r_ = roc_auc_score(yb[i], s_model[i]), roc_auc_score(yb[i], s_rec[i]); bm.append(m_); br.append(r_); bd.append(m_ - r_)
ter = pd.qcut(hv.exp26.rank(method="first"), 3, labels=["low", "mid", "high"])
tt = []
for lab in ["low", "mid", "high"]:
    d = hv[ter == lab]; p_ = d.repurchase.mean(); se = np.sqrt(p_ * (1 - p_) / len(d))
    tt.append(dict(tercile=lab, n=int(len(d)), repurchase_rate=float(p_), ci=[float(p_ - 1.96 * se), float(p_ + 1.96 * se)],
                   median_recency_d=float(d.recency_d.median()), median_purchase_days=float(d.n.median()),
                   share_of_group_sales12=float(d.sales12.sum() / hv.sales12.sum())))
res["E2"] = dict(cutoff="2011-06-01", n_active_12m=int(len(act)), n_high_value=int(len(hv)), sales12_threshold=float(thr),
                 high_value_share_of_sales12=float(hv.sales12.sum() / act.sales12.sum()), repurchase_rate=float(yb.mean()),
                 auc_model=float(a_model), auc_model_ci=[float(np.quantile(bm, .025)), float(np.quantile(bm, .975))],
                 auc_recency=float(a_rec), auc_recency_ci=[float(np.quantile(br, .025)), float(np.quantile(br, .975))],
                 auc_diff=float(a_model - a_rec), auc_diff_ci=[float(np.quantile(bd, .025)), float(np.quantile(bd, .975))], by_tercile=tt)

# ---------------- E3: early value of newly acquired accounts (12-month look-back), cohorts 2010-12..2011-05
days["mon"] = days.day.dt.to_period("M")
firsts = []
for cm in pd.period_range("2010-12", "2011-05", freq="M"):
    start = cm.to_timestamp(); prev = days[(days.day < start) & (days.day >= start - pd.DateOffset(months=12))].cid.unique()
    firsts.append(pd.DataFrame({"cid": np.setdiff1d(days[days.mon == cm].cid.unique(), prev), "cm": cm}))
F = pd.concat(firsts).drop_duplicates("cid", keep="first")
dd = days.merge(F, on="cid"); dd = dd[dd.mon >= dd.cm]; dd["k"] = (dd.mon - dd.cm).apply(lambda x: x.n)
acc = F.set_index("cid")
acc["first_month_sales"] = dd[dd.k == 0].groupby("cid").rev.sum().reindex(acc.index).fillna(0)
later = dd[dd.k.between(1, 5)].groupby("cid").rev.sum()
acc["later_sales"] = later.reindex(acc.index).fillna(0); acc["repeat"] = (acc.later_sales > 0).astype(int)
acc["q"] = pd.qcut(acc.first_month_sales.rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
top = acc.q == 4
share_top = float(acc.later_sales[top].sum() / acc.later_sales.sum())
bs, bsp = [], []
for _ in range(1000):
    s_ = acc.sample(len(acc), replace=True, random_state=int(rng.integers(1 << 31)))
    bs.append(s_.later_sales[s_.q == 4].sum() / s_.later_sales.sum()); bsp.append(stats.spearmanr(s_.first_month_sales, s_.later_sales)[0])
res["E3"] = dict(cohorts="2010-12..2011-05", n_new_accounts=int(len(acc)), repeat_rate_all=float(acc.repeat.mean()),
                 top_quartile_share_of_later_sales=share_top, top_quartile_share_ci=[float(np.quantile(bs, .025)), float(np.quantile(bs, .975))],
                 spearman_first_vs_later=float(stats.spearmanr(acc.first_month_sales, acc.later_sales)[0]),
                 spearman_ci=[float(np.quantile(bsp, .025)), float(np.quantile(bsp, .975))],
                 by_quartile=[dict(quartile=int(k), n=int((acc.q == k).sum()), median_first_month_sales=float(acc.first_month_sales[acc.q == k].median()),
                                   repeat_rate=float(acc.repeat[acc.q == k].mean()), mean_later_sales=float(acc.later_sales[acc.q == k].mean()),
                                   share_of_later_sales=float(acc.later_sales[acc.q == k].sum() / acc.later_sales.sum())) for k in [1, 2, 3, 4]])

# ---------------- E4: DuckDB SQL reconciliation with out/12_ltv_segments.json
con = duckdb.connect()
con.execute(f"CREATE VIEW lines AS SELECT * FROM read_parquet('{DER}/uci_lines.parquet')")
con.execute("""
CREATE TABLE inv AS SELECT cid, Invoice, is_cancel, MIN(InvoiceDate) AS t, SUM(revenue) AS rev FROM lines GROUP BY 1, 2, 3;
CREATE TABLE days AS SELECT cid, CAST(t AS DATE) AS day, SUM(rev) AS rev FROM inv WHERE NOT is_cancel GROUP BY 1, 2;
""")
SQL_SEG = """
WITH rfm AS (
  SELECT cid, COUNT(*) AS n6, SUM(rev) AS gross6, date_diff('day', MAX(day), DATE '2011-06-01') AS recency_d
  FROM days WHERE day >= DATE '2010-12-01' AND day < DATE '2011-06-01' GROUP BY cid),
fut AS (SELECT cid, SUM(rev) AS y FROM days WHERE day >= DATE '2011-06-01' AND day < DATE '2011-12-01' GROUP BY cid),
ranked AS (
  SELECT r.*, COALESCE(f.y, 0) AS y,
         CASE WHEN recency_d <= 60 THEN 'recent<=60d' WHEN recency_d <= 120 THEN '61-120d' ELSE '>120d' END AS rband,
         -- value terciles by rank; boundary accounts go to the upper tercile (same convention as pandas qcut on ranks,
         -- which gives 905/905/906 here; NTILE(3) gives 906/905/905 and moved 3 boundary accounts in the first run)
         CASE WHEN ROW_NUMBER() OVER (ORDER BY gross6, cid) < 1 + (COUNT(*) OVER () - 1) / 3.0 THEN 1
              WHEN ROW_NUMBER() OVER (ORDER BY gross6, cid) < 1 + 2 * (COUNT(*) OVER () - 1) / 3.0 THEN 2 ELSE 3 END AS vtile
  FROM rfm r LEFT JOIN fut f USING (cid))
SELECT rband, vtile, COUNT(*) AS n, SUM(y) AS y_sum, AVG(CASE WHEN y > 0 THEN 1.0 ELSE 0.0 END) AS repeat_rate,
       COUNT(*) * 1.0 / SUM(COUNT(*)) OVER () AS share_accounts, SUM(y) / SUM(SUM(y)) OVER () AS share_sales
FROM ranked GROUP BY 1, 2 ORDER BY share_sales DESC
"""
seg = con.execute(SQL_SEG).df()
SQL_COH = """
WITH m AS (SELECT DISTINCT cid, date_trunc('month', day) AS mon FROM days),
cand AS (
  SELECT a.cid, a.mon FROM m a
  WHERE a.mon BETWEEN DATE '2010-12-01' AND DATE '2011-06-01'
    AND NOT EXISTS (SELECT 1 FROM days d WHERE d.cid = a.cid AND d.day < a.mon AND d.day >= a.mon - INTERVAL 12 MONTH)),
firsts AS (SELECT cid, MIN(mon) AS cm FROM cand GROUP BY cid),
sizes AS (SELECT cm, COUNT(*) AS n FROM firsts GROUP BY cm),
act AS (SELECT f.cm, date_diff('month', f.cm, m.mon) AS k, COUNT(DISTINCT m.cid) AS buyers
        FROM firsts f JOIN m USING (cid) WHERE m.mon > f.cm AND m.mon <= DATE '2011-11-01' GROUP BY 1, 2)
SELECT strftime(a.cm, '%Y-%m') AS cm, a.k, a.buyers * 1.0 / s.n AS repeat_rate, s.n FROM act a JOIN sizes s USING (cm) ORDER BY 1, 2
"""
coh = con.execute(SQL_COH).df()
ref = json.load(open(f"{OUT}/12_ltv_segments.json"))
ref_seg = {r["segment"]: r for r in ref["rule_segments"]}; vname = {1: "low", 2: "mid", 3: "high"}
dmax = 0.0; n_cmp = 0
for _, r in seg.iterrows():
    k = f"{r.rband}|{vname[int(r.vtile)]}"
    for a_, b_ in [(r.n, ref_seg[k]["n"]), (r.share_accounts, ref_seg[k]["share_accounts"]), (r.share_sales, ref_seg[k]["share_next6m_sales_existing"]), (r.repeat_rate, ref_seg[k]["any_purchase_next6m"])]:
        dmax = max(dmax, abs(float(a_) - float(b_))); n_cmp += 1
ref_c = ref["cohorts_new_accounts"]; dmax_c = 0.0; n_c = 0
for _, r in coh.iterrows():
    v = ref_c["repeat_rate"][r.cm].get(str(int(r.k)))
    if v is not None:
        dmax_c = max(dmax_c, abs(float(r.repeat_rate) - v)); n_c += 1
    assert int(r.n) == ref_c["size"][r.cm]
top_seg = seg.iloc[0]
res["E4"] = dict(engine=f"duckdb {duckdb.__version__}", segment_cells_compared=n_cmp, segment_max_abs_diff=dmax,
                 cohort_cells_compared=n_c, cohort_max_abs_diff_vs_4dp_rounded=dmax_c,
                 top_segment_sql=dict(rband=top_seg.rband, vtile=int(top_seg.vtile), n=int(top_seg.n), share_accounts=float(top_seg.share_accounts),
                                      share_sales=float(top_seg.share_sales), repeat_rate=float(top_seg.repeat_rate)),
                 n_lines=int(con.execute("SELECT COUNT(*) FROM lines").fetchone()[0]), n_accounts_rfm=int(seg.n.sum()))
json.dump(res, open(f"{OUT}/14_ltv_extension.json", "w"), indent=1, default=float)
open(f"{OUT}/14_sql_queries.sql", "w").write("-- inv/days tables: see 14_ltv_extension.py\n-- Rule segments at 2011-06-01\n" + SQL_SEG + "\n-- New-account cohorts\n" + SQL_COH)
print(json.dumps(res, indent=1, default=float))
