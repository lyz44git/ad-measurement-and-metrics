import sys, json
import numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
OUT = sys.argv[1]; r = json.load(open(f"{OUT}/12_ltv_segments.json"))
fig, ax = plt.subplots(figsize=(5.6, 4))
for k, lab in [("ML_lgbm_tweedie", "LightGBM Tweedie (6-month look-back)"), ("BGNBD_GG", "BG/NBD x Gamma-Gamma (full history)")]:
    c = r[f"calib_{k}"]; ax.plot([d["pred"] for d in c], [d["actual"] for d in c], "o-", label=lab)
mx = max(d["actual"] for d in r["calib_BGNBD_GG"]) * 1.05; ax.plot([100, mx], [100, mx], "k--", lw=1, label="perfect calibration")
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("Mean predicted next-6-month sales (GBP), by predicted decile"); ax.set_ylabel("Mean actual (GBP)")
ax.set_title("Out-of-time calibration, existing accounts (cutoff 2011-06-01)", fontsize=10); ax.legend(fontsize=7); fig.tight_layout(); fig.savefig(f"{OUT}/fig/fig4_ltv_calibration.png", dpi=160)
segs = r["rule_segments"]
fig, ax = plt.subplots(figsize=(7.5, 3.8)); x = np.arange(len(segs))
ax.bar(x - 0.2, [s["share_accounts"] * 100 for s in segs], 0.4, label="% of active existing accounts"); ax.bar(x + 0.2, [s["share_next6m_sales_existing"] * 100 for s in segs], 0.4, label="% of their next-6-month sales")
ax.set_xticks(x); ax.set_xticklabels([s["segment"].replace("|", "\n") for s in segs], fontsize=7); ax.set_ylabel("%"); ax.legend(fontsize=8)
ax.set_title("Recency x value rule segments at 2011-06-01 vs realized next-6-month sales", fontsize=10); fig.tight_layout(); fig.savefig(f"{OUT}/fig/fig5_segments.png", dpi=160)
c = r["cohorts_new_accounts"]; cms = list(c["repeat_rate"].keys())
M = np.array([[np.nan if c["repeat_rate"][cm].get(str(k)) is None else c["repeat_rate"][cm][str(k)] for k in range(1, 12)] for cm in cms])
fig, ax = plt.subplots(figsize=(7, 3.6)); im = ax.imshow(M * 100, aspect="auto", cmap="Blues")
ax.set_yticks(range(len(cms))); ax.set_yticklabels([f"{cm} (n={c['size'][cm]})" for cm in cms], fontsize=7); ax.set_xticks(range(11)); ax.set_xticklabels(range(1, 12), fontsize=7)
ax.set_xlabel("Months since first purchase (blank = censored at 2011-11)"); ax.set_title("Monthly repeat-purchase rate, NEW accounts (no purchase in prior 12 months), %", fontsize=9)
fig.colorbar(im, ax=ax); fig.tight_layout(); fig.savefig(f"{OUT}/fig/fig6_cohort_retention.png", dpi=160); print("ok")
