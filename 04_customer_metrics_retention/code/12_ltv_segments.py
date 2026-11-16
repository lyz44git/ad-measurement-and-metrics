# Short-horizon customer-value forecast (NOT a lifetime value): sales over the next 6 calendar months per EXISTING account,
# UCI Online Retail II (real UK online gift retailer; many customers are wholesalers; gross sales, no margin).
# Revised after independent review (the first version is not included):
#  - Target = sales on non-credit-note invoices in [cut, cut + 6 calendar months) (orders later cancelled are included);
#    net-of-credit-notes target evaluated as secondary.
#  - Evaluation population at each cutoff = accounts with >=1 purchase in the prior 6 months (comparable across cutoffs).
#  - ML: season-matched training cutoff 2010-06-01 (target Jun-Nov 2010, ends 2010-12-01 < test cutoff); history-length-invariant
#    features from a fixed 6-month look-back only. Test cutoff 2011-06-01 (target Jun-Nov 2011).
#  - BG/NBD uses full observed history; accounts first seen in Dec 2009 (data start) are left-truncated and flagged; results shown
#    with and without them. Gamma-Gamma fitted with rescaled spend (interior optimum checked).
#  - Ranking metrics average over 20 random tie-breaks; customer bootstrap (models not refit, so CIs cover test-sample variability only);
#    observed differences reported with percentile CIs.
#  - Cohorts: NEW accounts = first purchase with no purchase in the previous 12 months (cohorts 2010-12..2011-06), censored at 2011-11;
#    contamination of a 3-month burn-in rule measured at a pseudo data start.
import sys, json
import numpy as np, pandas as pd
from sklearn.cluster import KMeans   # import before lightgbm: their OpenMP runtimes can conflict and crash on some macOS setups
from sklearn.metrics import silhouette_score, adjusted_rand_score, roc_auc_score
import lightgbm as lgb
from scipy import stats
sys.path.insert(0, sys.argv[3]); from btyd_impl import fit_bgnbd, bgnbd_expected, fit_gg, gg_expected
DER, OUT = sys.argv[1], sys.argv[2]
L = pd.read_parquet(f"{DER}/uci_lines.parquet")
inv = L.groupby(["cid", "Invoice", "is_cancel"], as_index=False).agg(t=("InvoiceDate", "min"), rev=("revenue", "sum"), lines=("StockCode", "size"), nprod=("StockCode", "nunique"))
inv["day"] = inv.t.dt.normalize()
cty = L[["cid", "InvoiceDate", "Country"]]
M6 = pd.DateOffset(months=6)
def look(cut, months=6):
    lo = cut - pd.DateOffset(months=months)
    return inv[(inv.t >= lo) & (inv.t < cut)]
def features6(cut):
    w = look(cut); s = w[~w.is_cancel]; c = w[w.is_cancel]
    days = s.groupby(["cid", "day"]).rev.sum().reset_index(); g = days.groupby("cid")
    f = pd.DataFrame({"n6": g.day.size(), "gross6": g.rev.sum(), "mean_txn6": g.rev.mean(), "max_txn6": g.rev.max(), "last": g.day.max(), "first6": g.day.min()})
    f["recency6_d"] = (cut - f["last"]).dt.days; f["span6_d"] = (f["last"] - f["first6"]).dt.days
    f["ret6"] = -c.groupby("cid").rev.sum().reindex(f.index).fillna(0); f["return_ratio6"] = (f.ret6 / f.gross6).clip(0, 1)
    d3 = days[days.day >= cut - pd.DateOffset(months=3)].groupby("cid")
    f["gross3"] = d3.rev.sum().reindex(f.index).fillna(0); f["n3"] = d3.day.size().reindex(f.index).fillna(0)
    ss = s.groupby("cid"); f["nprod6"] = ss.nprod.mean(); f["lines6"] = ss.lines.mean()
    cc = cty[cty.InvoiceDate < cut].groupby("cid").Country.agg(lambda x: x.mode().iat[0])
    f["uk"] = (cc.reindex(f.index) == "United Kingdom").astype(int)
    return f
def btyd_inputs(cut, ids):
    s = inv[(inv.t < cut) & (~inv.is_cancel)]
    days = s.groupby(["cid", "day"]).rev.sum().reset_index(); g = days.groupby("cid")
    b = pd.DataFrame({"first": g.day.min(), "last": g.day.max(), "n": g.day.size(), "mean_all": g.rev.mean()}).reindex(ids)
    b["x"] = b.n - 1; b["tx_w"] = (b["last"] - b["first"]).dt.days / 7; b["T_w"] = (cut - b["first"]).dt.days / 7
    rep = days.merge(b[["first"]], left_on="cid", right_index=True); rep = rep[rep.day > rep["first"]]
    b["m_rep"] = rep.groupby("cid").rev.mean().reindex(ids)
    b["left_trunc"] = (b["first"] < pd.Timestamp("2010-01-01")).astype(int)
    return b
def target(cut, ids):
    w = inv[(inv.t >= cut) & (inv.t < cut + M6)]
    return w[~w.is_cancel].groupby("cid").rev.sum().reindex(ids).fillna(0).values, w.groupby("cid").rev.sum().reindex(ids).fillna(0).values
FEATS = ["n6", "gross6", "mean_txn6", "max_txn6", "recency6_d", "span6_d", "return_ratio6", "gross3", "n3", "nprod6", "lines6", "uk"]
c_tr, c_te = pd.Timestamp("2010-06-01"), pd.Timestamp("2011-06-01")
TR = features6(c_tr); TR["y"], _ = target(c_tr, TR.index)
TE = features6(c_te); TE["y"], TE["y_net"] = target(c_te, TE.index)
BT = btyd_inputs(c_te, TE.index)
res = {"population": "accounts with >=1 purchase in the 6 months before the cutoff", "n_train": int(len(TR)), "n_test": int(len(TE)),
       "test_share_any_purchase": float((TE.y > 0).mean()), "test_target_total": float(TE.y.sum()), "test_share_left_truncated": float(BT.left_trunc.mean()),
       "test_target_share_left_truncated": float(TE.y[BT.left_trunc == 1].sum() / TE.y.sum())}
w_new = inv[(inv.t >= c_te) & (inv.t < c_te + M6) & (~inv.is_cancel)]
res["share_window_sales_from_population"] = float(TE.y.sum() / w_new.rev.sum())
preds = {}
preds["P0_last6m"] = TE.gross6.values
# BG/NBD on ALL accounts observed before the test cutoff (full history), predictions for the test population
ALLB = btyd_inputs(c_te, inv[(inv.t < c_te) & (~inv.is_cancel)].cid.unique())
bg, llbg = fit_bgnbd(ALLB.x.values, ALLB.tx_w.values, ALLB.T_w.values)
ex = bgnbd_expected(bg, 26.0, BT.x.values, BT.tx_w.values, BT.T_w.values)   # 6 months ~ 26 weeks
rep = ALLB.x > 0; gg = fit_gg(ALLB.x[rep].values, ALLB.m_rep[rep].values)
res["bgnbd_params"] = dict(zip(["r", "alpha", "a", "b"], [float(v) for v in bg])); res["gg_params"] = dict(zip(["p", "q", "gamma"], [float(v) for v in gg]))
res["gg_population_mean_spend"] = float(gg[0] * gg[2] / (gg[1] - 1)); res["gg_assumption_corr_freq_spend"] = float(stats.spearmanr(ALLB.x[rep], ALLB.m_rep[rep])[0])
preds["BGNBD_GG"] = ex * gg_expected(gg, BT.x.values, np.nan_to_num(BT.m_rep.values, nan=1.0))
rng = np.random.default_rng(0); vmask = rng.random(len(TR)) < 0.2
prm = dict(objective="tweedie", tweedie_variance_power=1.5, n_estimators=3000, learning_rate=0.02, num_leaves=15, min_child_samples=40, subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=5.0, verbose=-1, n_jobs=8, random_state=0)
m = lgb.LGBMRegressor(**prm).fit(TR.loc[~vmask, FEATS], TR.y[~vmask], eval_X=TR.loc[vmask, FEATS], eval_y=TR.y[vmask], callbacks=[lgb.early_stopping(100, verbose=False)])
preds["ML_lgbm_tweedie"] = m.predict(TE[FEATS]); res["ml_best_iter"] = int(m.best_iteration_)
imp = pd.Series(m.booster_.feature_importance("gain"), index=FEATS); res["ml_gain_importance_share"] = (imp / imp.sum()).sort_values(ascending=False).round(3).to_dict()
res["season_ratio_future_over_past6"] = {"train_cut_2010-06-01": float(TR.y.sum() / TR.gross6.sum()), "test_cut_2011-06-01": float(TE.y.sum() / TE.gross6.sum())}
# ---- metrics (random tie-break averaged for order-based metrics)
def order_metrics(p, y, reps=20, seed=0):
    rs_ = np.random.default_rng(seed); n = len(y); k = max(1, int(0.1 * n)); caps, ginis = [], []
    perfect = np.cumsum(np.sort(y)[::-1]) / y.sum(); gmax = 2 * (perfect.mean() - 0.5)
    for _ in range(reps):
        o = np.lexsort((rs_.random(n), -p)); cum = np.cumsum(y[o]) / y.sum()
        caps.append(y[o[:k]].sum() / y.sum()); ginis.append(2 * (cum.mean() - 0.5) / gmax)
    return float(np.mean(caps)), float(np.mean(ginis))
def metrics(p, y):
    cap, gini = order_metrics(p, y)
    return dict(spearman=float(stats.spearmanr(p, y)[0]), top10_capture=cap, norm_gini=gini, mae=float(np.mean(np.abs(p - y))), agg_ratio=float(p.sum() / y.sum()), auc_any=float(roc_auc_score(y > 0, p)))
y = TE.y.values
ev = {k: metrics(p, y) for k, p in preds.items()}
ev_net = {k: metrics(p, TE.y_net.values.clip(min=0)) for k, p in preds.items()}
nt = BT.left_trunc.values == 0
ev_excl_trunc = {k: metrics(p[nt], y[nt]) for k, p in preds.items()}
B = 300; boots = {k: [] for k in preds}; rs = np.random.default_rng(1)
def fast(p, y):   # bootstrap uses one random tie-break per replicate
    o = np.lexsort((rs.random(len(y)), -p)); k = max(1, int(0.1 * len(y))); cum = np.cumsum(y[o]) / y.sum()
    perfect = np.cumsum(np.sort(y)[::-1]) / y.sum()
    return dict(spearman=stats.spearmanr(p, y)[0], top10_capture=y[o[:k]].sum() / y.sum(), norm_gini=(cum.mean() - 0.5) / (perfect.mean() - 0.5), agg_ratio=p.sum() / y.sum(), auc_any=roc_auc_score(y > 0, p))
for b in range(B):
    i = rs.integers(0, len(y), len(y))
    for k, p in preds.items(): boots[k].append(fast(p[i], y[i]))
for k in preds:
    for mname in ["spearman", "top10_capture", "norm_gini", "agg_ratio", "auc_any"]:
        v = [d[mname] for d in boots[k]]; ev[k][mname + "_ci"] = [float(np.quantile(v, .025)), float(np.quantile(v, .975))]
diffs = {}
for a_, b_ in [("ML_lgbm_tweedie", "BGNBD_GG"), ("ML_lgbm_tweedie", "P0_last6m"), ("BGNBD_GG", "P0_last6m")]:
    for mname in ["spearman", "top10_capture", "norm_gini", "auc_any"]:
        d = np.array([x[mname] - z_[mname] for x, z_ in zip(boots[a_], boots[b_])])
        diffs[f"{a_}-{b_}:{mname}"] = dict(observed=ev[a_][mname] - ev[b_][mname], ci=[float(np.quantile(d, .025)), float(np.quantile(d, .975))])
res.update(eval=ev, eval_net_target=ev_net, eval_excluding_left_truncated=ev_excl_trunc, paired_diffs=diffs,
           note_ci="customer bootstrap with fitted models held fixed: CIs cover test-sample variability only; 12 comparisons, descriptive")
for k in ["ML_lgbm_tweedie", "BGNBD_GG"]:
    q = pd.qcut(pd.Series(preds[k]).rank(method="first"), 10, labels=False).values
    res[f"calib_{k}"] = [dict(pred=float(preds[k][q == j].mean()), actual=float(y[q == j].mean())) for j in range(10)]
# ---- segmentation on test-cutoff features (6-month look-back), validated on next-6-month sales of existing accounts
seg = pd.DataFrame(index=TE.index)
seg["R"] = np.log1p(TE.recency6_d); seg["F"] = np.log1p(TE.n6); seg["M"] = np.log1p(TE.mean_txn6.clip(lower=0)); seg["Ret"] = TE.return_ratio6
Z = ((seg - seg.mean()) / seg.std()).values
ks = {}; rk = np.random.default_rng(5)
for k in range(2, 9):
    km = KMeans(k, n_init=10, random_state=0).fit(Z)
    sil = silhouette_score(Z, km.labels_, sample_size=min(4000, len(Z)), random_state=0); aris = []
    for b in range(50):   # out-of-bag stability: fit on bootstrap sample, compare labels on out-of-bag points
        i = rk.integers(0, len(Z), len(Z)); oob = np.setdiff1d(np.arange(len(Z)), i)
        kb = KMeans(k, n_init=3, random_state=b).fit(Z[i]); aris.append(adjusted_rand_score(km.labels_[oob], kb.predict(Z[oob])))
    ks[k] = dict(silhouette=float(sil), ari_mean=float(np.mean(aris)), ari_p10=float(np.quantile(aris, 0.1)))
res["kmeans_selection"] = ks
kbest = max((k for k in ks if ks[k]["ari_p10"] >= 0.8), key=lambda k: ks[k]["silhouette"], default=max(ks, key=lambda k: ks[k]["silhouette"]))
km = KMeans(kbest, n_init=20, random_state=0).fit(Z); TE["seg"] = km.labels_; res["kmeans_k"] = kbest
def seg_table(lab):
    out = []; rb = np.random.default_rng(9)
    for s_, d in TE.groupby(lab):
        yy = d.y.values; bm = [yy[rb.integers(0, len(yy), len(yy))].mean() for _ in range(500)]
        out.append(dict(segment=str(s_), n=int(len(d)), share_accounts=len(d) / len(TE), share_next6m_sales_existing=float(yy.sum() / TE.y.sum()),
                        any_purchase_next6m=float((yy > 0).mean()), mean_next6m_sales=float(yy.mean()), mean_ci_boot=[float(np.quantile(bm, .025)), float(np.quantile(bm, .975))],
                        median_recency_d=float(d.recency6_d.median()), median_purchase_days6=float(d.n6.median()), median_mean_txn6=float(d.mean_txn6.median()),
                        mean_return_ratio6=float(d.return_ratio6.mean()), share_uk=float(d.uk.mean())))
    return sorted(out, key=lambda r: -r["mean_next6m_sales"])
res["kmeans_segments"] = seg_table("seg")
TE["rband"] = pd.cut(TE.recency6_d, [-1, 60, 120, 1000], labels=["recent<=60d", "61-120d", ">120d"])
TE["vband"] = pd.qcut(TE.gross6.rank(method="first"), 3, labels=["low", "mid", "high"])
TE["rule_seg"] = TE.rband.astype(str) + "|" + TE.vband.astype(str)
res["rule_segments"] = seg_table("rule_seg")
top = TE.assign(p=preds["ML_lgbm_tweedie"]).nlargest(int(0.1 * len(TE)), "p")
res["top_decile_profile_ml"] = dict(n=int(len(top)), share_next6m_sales_existing=float(top.y.sum() / TE.y.sum()), share_uk=float(top.uk.mean()),
                                    rule_seg_mix=top.rule_seg.value_counts(normalize=True).round(3).to_dict())
# ---- cohorts of NEW accounts (no purchase in the previous 12 months), 2010-12..2011-06, censored at 2011-11
d0 = inv[~inv.is_cancel].groupby(["cid", "day"]).rev.sum().reset_index()
d0["mon"] = d0.day.dt.to_period("M")
firsts = []
for cm in pd.period_range("2010-12", "2011-06", freq="M"):
    start = cm.to_timestamp(); prev = d0[(d0.day < start) & (d0.day >= start - pd.DateOffset(months=12))].cid.unique()
    # first purchase in month cm, with no purchase in the 12 months before the month (data start 2009-12 gives >=12 months of look-back)
    inm = d0[d0.mon == cm].cid.unique(); new = np.setdiff1d(inm, prev)
    firsts.append(pd.DataFrame({"cid": new, "cm": cm}))
F = pd.concat(firsts); F = F.drop_duplicates("cid", keep="first")
dd = d0.merge(F, on="cid"); dd = dd[dd.mon >= dd.cm]; dd["k"] = (dd.mon - dd.cm).apply(lambda x: x.n)
size = F.groupby("cm").cid.nunique()
ret = dd[dd.k >= 1].groupby(["cm", "k"]).cid.nunique().unstack().div(size, axis=0)
rev = dd.groupby(["cm", "k"]).rev.sum().unstack().div(size, axis=0)
maxk = {cm: (pd.Period("2011-11", "M") - cm).n for cm in size.index}
for cm in size.index:
    ret.loc[cm, [c for c in ret.columns if c > maxk[cm]]] = np.nan; rev.loc[cm, [c for c in rev.columns if c > maxk[cm]]] = np.nan
cum = rev.cumsum(axis=1, skipna=False)
res["cohorts_new_accounts"] = dict(definition="first purchase in month with no purchase in the previous 12 months; censored at 2011-11",
    size={str(k): int(v) for k, v in size.items()},
    repeat_rate={str(cm): {int(k): (None if pd.isna(v) else round(float(v), 4)) for k, v in row.items()} for cm, row in ret.iterrows()},
    cum_sales_per_account={str(cm): {int(k): (None if pd.isna(v) else round(float(v), 1)) for k, v in row.items()} for cm, row in cum.iterrows()})
# contamination of a 3-month burn-in rule: pretend data start at 2010-12-01; "new" in 2011-03..2011-05 = not seen 2010-12..2011-02;
# check how many of them bought in the real 12 months before 2010-12-01
seen_bi = d0[(d0.day >= "2010-12-01") & (d0.day < "2011-03-01")].cid.unique()
cand = np.setdiff1d(d0[(d0.day >= "2011-03-01") & (d0.day < "2011-06-01")].cid.unique(), seen_bi)
had = d0[(d0.day >= "2009-12-01") & (d0.day < "2010-12-01") & d0.cid.isin(cand)].cid.unique()
res["burnin3_contamination"] = dict(apparent_new=int(len(cand)), bought_in_prior_12m=int(len(had)), share=float(len(had) / max(len(cand), 1)))
json.dump(res, open(f"{OUT}/12_ltv_segments.json", "w"), indent=1, default=float)
pd.DataFrame(preds, index=TE.index).assign(y=y, left_trunc=BT.left_trunc.values).to_parquet(f"{DER}/ltv_test_preds.parquet")
print(json.dumps({k: res[k] for k in ["n_train", "n_test", "test_share_any_purchase", "test_share_left_truncated", "test_target_share_left_truncated", "share_window_sales_from_population", "bgnbd_params", "gg_params", "gg_population_mean_spend", "gg_assumption_corr_freq_spend", "ml_best_iter", "season_ratio_future_over_past6", "kmeans_k", "burnin3_contamination"]}, indent=1, default=float))
for k, v in ev.items(): print(k, {m_: round(v[m_], 3) for m_ in ["spearman", "top10_capture", "norm_gini", "mae", "agg_ratio", "auc_any"]})
for k, v in diffs.items(): print(k, round(v["observed"], 4), [round(x, 4) for x in v["ci"]])
