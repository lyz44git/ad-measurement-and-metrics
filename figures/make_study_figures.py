"""Figures shown on the study pages, drawn from the committed result files with the panels in figures/figstyle.py.

Usage: python figures/make_study_figures.py   (writes the PNG files into each study's output folder)

Intervals are 95% unless a label says otherwise. Where a result file reports a rate over a known number of simulated
studies, the interval is the binomial one for that number of studies.
"""
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from figstyle import *  # noqa: E402,F401,F403


def binom(p, n):
    return 196 * (p * (1 - p) / n) ** 0.5


def lines_ci(ax, x, ys, cis, color, label, off=0.0, lw=2.2):
    ax.plot([u + off for u in x], ys, color=color, lw=lw, zorder=3, label=label, marker="o", ms=5.5, mec="white", mew=1)
    for u, v, e in zip(x, ys, cis):
        ax.plot([u + off, u + off], [v - e, v + e], color=color, lw=1.3, zorder=2)


# ------------------------------------------------------------------ 01
def fig01a():
    fig = plt.figure(figsize=(7.4, 3.0), dpi=300)
    gs = fig.add_gridspec(1, 3, width_ratios=[0.95, 1.05, 1.05], wspace=0.55, left=0.03, right=0.975, top=0.83, bottom=0.17)
    p_rates(fig, gs[0], "A", "Rates by group")
    p_deciles(fig.add_subplot(gs[1]), "B", "Effect by decile of uplift")
    ax = fig.add_subplot(gs[2]); tg = load(f"{S01A}/out/criteo/c_targeting.json")["test"]
    names = {"response": "Response model", "t_learner": "T-learner (selected)", "x_learner": "X-learner", "dr_learner": "DR-learner", "causal_forest": "Causal forest", "random": "Random order"}
    q = sorted([(names[k], 1e4 * v["qini"], 1e4 * v["qini_ci"][0], 1e4 * v["qini_ci"][1], k) for k, v in tg.items() if k in names], key=lambda r: -r[1])
    col = {"response": ORANGE, "t_learner": NAVY}
    dotrows(ax, [r[0] for r in q], [r[1] for r in q], [r[2] for r in q], [r[3] for r in q], [col.get(r[4], GREY) for r in q], lambda u: f"{u:.1f}", (-2, 39),
            bold=["Response model", "T-learner (selected)"])
    ax.set_xlabel("Qini coefficient (×10⁻⁴ per user)"); panel(ax, "C", "Ranking users for targeting")
    save(fig, f"{S01A}/out/fig_rates_by_arm.png")


def fig01b():
    fig, ax = plt.subplots(1, 2, figsize=(7.4, 3.0), dpi=300, gridspec_kw=dict(width_ratios=[0.8, 1.15]))
    p_slope(ax[0], "A", "Error in each of ten samples")
    p_seg_scatter(ax[1], "B", "Segment estimates in sample 1")
    fig.subplots_adjust(left=0.09, right=0.98, top=0.86, bottom=0.18, wspace=0.32)
    save(fig, f"{S01B}/out/fig_segment_error.png")


def fig01d():
    al = load(f"{S01D}/out/c_allocation.json")
    fig, ax = plt.subplots(1, 2, figsize=(7.4, 3.0), dpi=300)
    p_privacy(ax[0], "A", "Error under privacy noise")
    a = ax[1]; b = ["10", "20", "30"]; x = [10, 20, 30]
    a.plot(x, [al[k]["random"] * 100 for k in b], color=PALE, lw=2.4, zorder=1)
    a.text(10, al["10"]["random"] * 100 - 4, "random order", va="top", fontsize=7, color=MUTED)
    for k, name, c, ls in (("oracle", "held-out benchmark", INK2, (0, (2, 2))), ("multilevel", "lift, multilevel model", NAVY, "-"),
                           ("nopool", "lift, each segment", BLUE, "-"), ("response", "response rate", ORANGE, "-")):
        y = [100 * al[q]["mean_share"][k] for q in b]
        a.plot(x, y, color=c, lw=2.2 if c != INK2 else 1.4, ls=ls, marker="o", ms=5.5, mec="white", mew=1, zorder=3, label=name)
    for q, xx in zip(b, x):
        a.text(xx, 117, f"lift beat\nresponse\n{al[q]['ml_gt_response']} of 10", ha="center", va="top", fontsize=6.8, color=ORANGE if al[q]["ml_gt_response"] < 8 else NAVY,
               fontweight="bold", linespacing=1.1)
    a.legend(loc="center right", bbox_to_anchor=(1.0, 0.42), labelcolor=INK2, fontsize=7, handlelength=1.8)
    a.set_xticks(x, ["10%", "20%", "30%"]); a.set_xlim(7, 37); a.set_ylim(0, 118); a.set_yticks(range(0, 101, 20)); a.set_xlabel("Budget (share of users)")
    a.set_ylabel("Incremental visits captured (%)"); clean(a); panel(a, "B", "Allocation by segment ranking")
    fig.subplots_adjust(left=0.08, right=0.98, top=0.86, bottom=0.18, wspace=0.3)
    save(fig, f"{S01D}/out/fig_privacy_and_allocation.png")


# ------------------------------------------------------------------ 02
def fig02a():
    fig = plt.figure(figsize=(7.4, 3.0), dpi=300)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.1, 1.0], wspace=0.62, left=0.03, right=0.975, top=0.83, bottom=0.17)
    p_gap(fig, gs[0], "A", "Credited by the count vs. caused")
    ax = fig.add_subplot(gs[1]); p_exposure(ax, "B", "Effect of exposure on visits")
    save(fig, f"{S02A}/out/fig_attributed_vs_incremental.png")


def fig02b():
    fig, ax = plt.subplots(1, 2, figsize=(7.4, 3.0), dpi=300, gridspec_kw=dict(width_ratios=[1.1, 1]))
    p_heat(ax[0], "A", "Credit by rule and touch timing")
    p_clicked(ax[1], "B", "Credit on clicked touches")
    fig.subplots_adjust(left=0.12, right=0.97, top=0.8, bottom=0.12, wspace=0.42)
    save(fig, f"{S02B}/out/fig_credit_by_rule.png")


def fig02c_recovery():
    fig, ax = plt.subplots(1, 2, figsize=(7.4, 3.1), dpi=300, sharey=True)
    for a, suf, name, letter in ((ax[0], "", "Weekly data", "A"), (ax[1], "_daily", "Daily data", "B")):
        r = [u for u in rows(f"{S02C}/out/mmm_recovery{suf}.csv") if u["converged"] == "True"]
        rho = load(f"{S02C}/out/mmm_summary{suf}.json")["recovery"]["spearman"]
        a.plot([0.4, 5], [0.4, 5], color=ORANGE, lw=1.1, ls=(0, (4, 3)), zorder=1)
        for u in r:
            t, e, lo, hi = (float(u[k]) for k in ("true", "est", "lo", "hi"))
            a.plot([t, t], [max(lo, 0.031), min(hi, 990)], color=NAVY, lw=0.9, alpha=0.35, zorder=2)
        a.scatter([float(u["true"]) for u in r], [float(u["est"]) for u in r], s=26, color=NAVY, edgecolor="white", lw=0.7, zorder=3)
        a.text(0.43, 500, f"rank correlation {rho:.2f}", fontsize=8, fontweight="bold", color=NAVY if rho > 0.5 else ORANGE, path_effects=HALO)
        a.text(4.6, 6.2, "estimate = known", ha="right", fontsize=7, color=ORANGE, path_effects=HALO)
        a.set_xscale("log"); a.set_yscale("log"); a.set_xlim(0.4, 5); a.set_ylim(0.03, 1000)
        nice_log(a, "x", [0.5, 1, 2, 4], ["0.5", "1", "2", "4"]); nice_log(a, "y", [0.1, 1, 10, 100, 1000], ["0.1", "1", "10", "100", "1,000"])
        a.set_xlabel("Known channel ROAS (simulated)"); clean(a); panel(a, letter, name)
    ax[0].set_ylabel("Estimated ROAS, 90% interval")
    fig.subplots_adjust(left=0.09, right=0.98, top=0.86, bottom=0.17, wspace=0.12)
    save(fig, f"{S02C}/out/fig_roas_recovery.png")


def fig02c_detect():
    fig, ax = plt.subplots(1, 2, figsize=(7.4, 3.0), dpi=300, gridspec_kw=dict(width_ratios=[1.2, 1]))
    p_mmm_scatter(ax[0], "A", "Daily data, held-out simulation")
    rr, _ = mmm_points(); s = load(f"{S02C}/out/detectability.json"); b = ax[1]
    b.axvspan(0, 2, color=PALE, alpha=0.55, lw=0)
    for f, name, c in (("W", "weekly data", GREY), ("D", "daily data", NAVY)):
        v = sorted(float(r["min_detectable_roas"]) for r in rr if r["freq"] == f)
        b.step(v, [100 * (q + 1) / len(v) for q in range(len(v))], where="post", color=c, lw=2.2)
        sh = 100 * s[f]["real_spend"]["share_at_most"]["2"]
        y_lab = 100 * sum(u <= 15.6 for u in v) / len(v) + 3 if f == "D" else 100 * sum(u <= 9 for u in v) / len(v) - 16  # weekly label sits below its curve
        b.text(15.6, y_lab, f"{name}: {sh:.0f}% at 2 or below", ha="right", fontsize=7.2, color=c, fontweight="bold", path_effects=HALO)
    b.axvline(2, color=ORANGE, lw=1.2, ls=(0, (4, 3)))
    off = {f: (sum(float(r["min_detectable_roas"]) > 16 for r in rr if r["freq"] == f), sum(r["freq"] == f for r in rr)) for f in ("W", "D")}
    b.text(15.6, 4, f"beyond 16, not shown: {off['W'][0]} of {off['W'][1]} weekly,\n{off['D'][0]} of {off['D'][1]} daily", ha="right", va="bottom", fontsize=6.5,
           color=MUTED, path_effects=HALO, linespacing=1.1)
    b.set_xlim(0, 16); b.set_ylim(0, 100); b.set_xlabel("Smallest detectable ROAS (80% power)"); b.set_ylabel("Brand-channels, cumulative (%)"); clean(b)
    panel(b, "B", "Real spend: what could be detected")
    fig.subplots_adjust(left=0.09, right=0.98, top=0.86, bottom=0.17, wspace=0.32)
    save(fig, f"{S02C}/out/fig_detectability.png")


# ------------------------------------------------------------------ 03
def fig03a_power():
    d = load(f"{S03A}/out/lift_study_sizing.json"); k = d["studies_per_n"]; by = d["by_n"]; ns = sorted(by, key=int); x = list(range(len(ns)))
    fig, ax = plt.subplots(1, 2, figsize=(7.4, 2.9), dpi=300)
    for a, keys, ref, ylim, title, letter in ((ax[0], ("power_z", "bayes_detect"), 80, (0, 105), "Power to detect a one-point lift", "A"),
                                              (ax[1], ("aa_false_positive_z", "aa_false_positive_bayes"), 5, (0, 10), "False positives with no true lift", "B")):
        a.axhline(ref, color=ORANGE, lw=1.1, ls=(0, (4, 3)), label="80% power" if ref == 80 else "nominal 5%")
        for key, name, c, off in zip(keys, ("z-test at 5%", "Bayesian, P(lift > 0) > 0.95"), (NAVY, BLUE), (-0.06, 0.06)):
            ys = [100 * by[n][key] for n in ns]
            lines_ci(a, x, ys, [binom(by[n][key], k) for n in ns], c, name, off)
        a.set_xticks(x, [fmt(int(n)) for n in ns]); a.set_ylim(*ylim); a.set_xlabel("Users per arm"); clean(a); panel(a, letter, title)
        a.legend(loc="lower right" if ref == 80 else "upper left", handlelength=1.6, labelcolor=INK2)
    ax[0].set_ylabel("Studies detecting the lift (%)"); ax[1].set_ylabel("A/A studies reporting a lift (%)")
    fig.subplots_adjust(left=0.08, right=0.98, top=0.86, bottom=0.18, wspace=0.3)
    save(fig, f"{S03A}/out/fig_power_by_sample_size.png")


def fig03a_mde():
    cv = load(f"{S03A}/out/covariate_adjustment.json"); by = cv["by_n"]; ns = sorted(by, key=int); req = cv["required_n_one_point_lift"]
    fig, ax = plt.subplots(1, 2, figsize=(7.4, 2.9), dpi=300, gridspec_kw=dict(width_ratios=[1.25, 1]))
    a = ax[0]; a.axhline(1, color=ORANGE, lw=1.1, ls=(0, (4, 3)))
    a.text(24000, 1.07, "one-point lift", ha="right", fontsize=7.2, color=ORANGE, fontweight="bold")
    for k, name, c in (("D", "unadjusted", GREY), ("L", "adjusted, 12 features", BLUE), ("M", "adjusted, model prediction", NAVY)):
        a.plot([int(n) for n in ns], [100 * by[n][k]["mde80"] for n in ns], color=c, lw=2.2, marker="o", ms=5, mec="white", mew=1, label=name)
    for k, c, dx, dy, ha in (("D", GREY, 0, 17, "center"), ("L", BLUE, 4, -14, "left"), ("M", NAVY, -4, -14, "right")):
        a.plot([req[k], req[k]], [0, 1], color=c, lw=1, ls=(0, (2, 2)))
        a.scatter([req[k]], [1], s=46, color=c, edgecolor="white", lw=1.2, zorder=5)
        a.annotate(fmt(req[k]), (req[k], 1), xytext=(dx, dy), textcoords="offset points", ha=ha, fontsize=7.5, color=c, fontweight="bold", path_effects=HALO)
    a.set_xscale("log"); a.set_xticks([int(n) for n in ns], [fmt(int(n)) for n in ns]); a.minorticks_off(); a.set_ylim(0, 3)
    a.set_xlabel("Users per arm (log scale)"); a.set_ylabel("Minimum detectable lift (pp)"); a.legend(loc="upper right", labelcolor=INK2); clean(a)
    panel(a, "A", "Minimum detectable lift")
    b = ax[1]; x = list(range(len(ns)))
    b.axhline(1, color=GREY, lw=1, ls=(0, (4, 3))); b.text(4.3, 1.01, "unadjusted", ha="right", va="bottom", fontsize=7, color=MUTED)
    for k, c, off, name in (("L", BLUE, -0.1, "12 features"), ("M", NAVY, 0.1, "model prediction")):
        v = [by[n][k]["variance_ratio_to_D"] for n in ns]; ci = [by[n][k]["variance_ratio_ci"] for n in ns]
        for i in x:
            b.plot([i + off, i + off], ci[i], color=c, lw=1.6)
        b.scatter([i + off for i in x], v, s=34, color=c, edgecolor="white", lw=1, zorder=3, label=name)
    b.set_xticks(x, [fmt(int(n)) for n in ns]); b.set_ylim(0.5, 1.08); b.set_xlabel("Users per arm"); b.set_ylabel("Variance relative to unadjusted")
    b.legend(loc="lower right", labelcolor=INK2); clean(b); panel(b, "B", "Sampling variance of the readout")
    fig.subplots_adjust(left=0.08, right=0.98, top=0.86, bottom=0.18, wspace=0.3)
    save(fig, f"{S03A}/out/fig_mde_by_adjustment.png")


def fig03b():
    g = geo_grid(); ms = [20, 50, 100, 150]
    fig = plt.figure(figsize=(7.4, 3.1), dpi=300)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.15, 1, 1], wspace=0.42, left=0.1, right=0.98, top=0.85, bottom=0.18)
    p_geo_grid(fig.add_subplot(gs[0]), "A", "adjusted", "Regression-adjusted MDE")
    b = fig.add_subplot(gs[1])
    for k, name, c in (("yoy", "year over year", GREY), ("pairs", "matched pairs, adjusted", BLUE), ("adjusted", "regression-adjusted", NAVY)):
        y = [g[k][(m, 2)] for m in ms]
        b.plot(ms, y, color=c, lw=2.2, marker="o", ms=5.5, mec="white", mew=1, label=name)
    b.set_xticks(ms); b.set_ylim(0, 25); b.set_xlabel("Metros (two-month test)"); b.set_ylabel("Minimum detectable effect (%)")
    b.legend(loc="upper right", labelcolor=INK2, fontsize=6.8); clean(b); panel(b, "B", "Three designs")
    c = fig.add_subplot(gs[2]); x = list(range(4))
    tab = {int(r["metros"]): r for r in rows(f"{S03B}/out/design_summary.csv") if r["estimator"] == "CR: volume-weighted ANCOVA" and r["test_months"] == "2"}
    ri = {int(r["metros"]): r for r in rows(f"{S03B}/out/randomization_inference_check.csv") if r["estimator"] == "CR: volume-weighted ANCOVA"}
    c.axhline(5, color=ORANGE, lw=1.1, ls=(0, (4, 3)), label="nominal 5%")
    tv = [100 * float(tab[m]["false_positive_rate"]) for m in ms]; rv = [100 * float(ri[m]["false_positive_rate"]) for m in ms]
    lines_ci(c, x, tv, [binom(v / 100, int(tab[m]["draws"])) for v, m in zip(tv, ms)], GREY, "t-test", -0.06)
    lines_ci(c, x, rv, [binom(v / 100, int(ri[m]["draws"])) for v, m in zip(rv, ms)], NAVY, "randomization inference", 0.06)
    c.set_xticks(x, [str(m) for m in ms]); c.set_ylim(0, 12); c.set_xlabel("Metros (two-month test)"); c.set_ylabel("Placebo tests rejected (%)")
    c.legend(loc="upper right", labelcolor=INK2, fontsize=6.8); clean(c); panel(c, "C", "Volume-weighted")
    fig.text(0.98, 0.01, "Data Provided by Zillow Group.", ha="right", fontsize=6, color=MUTED)
    save(fig, f"{S03B}/out/fig1_mde_by_metros.png")


def fig03c():
    byh = rows(f"{S03C}/reports/tables/inventory_ets_by_horizon.csv"); val = {(r["level"], r["method"], int(r["h"])): float(r["rel_to_no_change"]) for r in byh}
    fig = plt.figure(figsize=(7.4, 4.6), dpi=300)
    gs = fig.add_gridspec(2, 4, height_ratios=[0.62, 1], hspace=0.75, wspace=0.28, left=0.07, right=0.98, top=0.9, bottom=0.12)
    p_forecast_gap(fig.add_subplot(gs[0, 1:3]), "A", "Gap before reconciliation")
    hs = list(range(1, 13))
    for i, (lv, name) in enumerate((("US", "Nation"), ("division", "Divisions"), ("state", "States"), ("metro", "Metros"))):
        a = fig.add_subplot(gs[1, i])
        a.axhline(1, color=ORANGE, lw=1.1, ls=(0, (4, 3)))
        for m, lab, c, ls in (("base", "unreconciled", GREY, "-"), ("bu", "bottom-up", BLUE, (0, (4, 2))), ("mint_shrink", "MinT-shrink", NAVY, "-")):
            a.plot(hs, [val[(lv, m, h)] for h in hs], color=c, lw=2, ls=ls, label=lab)
        a.set_xticks([1, 6, 12]); a.set_ylim(0.35, 1.4); a.set_xlabel("Horizon (months)")
        if i == 0:
            a.set_ylabel("RMSSE relative to no-change")
        else:
            a.set_yticklabels([])
        clean(a); a.set_title(name, loc="left", fontweight="bold", fontsize=8.5, color=INK)
    fig.axes[1].legend(loc="upper left", fontsize=6.8, labelcolor=INK2, handlelength=1.6)
    fig.text(0.07, 0.535, "B   Forecast error by horizon, four levels", fontweight="bold", fontsize=9.5, color=INK)
    fig.text(0.98, 0.01, "Data Provided by Zillow Group.", ha="right", fontsize=6, color=MUTED)
    save(fig, f"{S03C}/reports/figures/relative_rmsse_by_horizon_inventory_ets.png")


# ------------------------------------------------------------------ 04
def seg_label(s):
    r, t = s.split("|")
    return f"{t.capitalize()} value · " + {"recent<=60d": "≤60 days", "61-120d": "61–120 days", ">120d": ">120 days"}[r]


def fig04_segments():
    segs = load(f"{S04}/out/12_ltv_segments.json")["rule_segments"]
    fig, ax = plt.subplots(1, 2, figsize=(7.4, 3.3), dpi=300, sharey=True)
    a, b = ax; n = len(segs)
    for i, s in enumerate(segs):
        y = n - 1 - i; acc, sal = 100 * s["share_accounts"], 100 * s["share_next6m_sales_existing"]
        a.plot([acc, sal], [y, y], color=NAVY if sal > acc else GREY, lw=3, alpha=0.35)
        dot(a, acc, y, GREY, s=44); dot(a, sal, y, NAVY, s=52)
        if i == 0:
            a.text(acc, y + 0.45, f"{acc:.1f}% of accounts", ha="center", fontsize=7, color=MUTED, fontweight="bold")
            a.text(sal, y + 0.45, f"{sal:.1f}% of sales", ha="center", fontsize=7, color=NAVY, fontweight="bold")
        b.plot([s["mean_ci_boot"][0], s["mean_ci_boot"][1]], [y, y], color=NAVY, lw=2)
        dot(b, s["mean_next6m_sales"], y, NAVY, s=46)
    a.set_yticks(range(n), [seg_label(s["segment"]) for s in segs][::-1]); a.tick_params(axis="y", labelcolor=INK, labelsize=7.8)
    a.set_xlim(0, 80); a.set_xticks([0, 20, 40, 60, 80], ["0%", "20%", "40%", "60%", "80%"]); a.grid(axis="x", color=GRID); a.grid(axis="y", visible=False)
    a.set_ylim(-0.6, n - 0.1 + 0.6); clean(a, x=False); panel(a, "A", "Accounts and later sales")
    a.scatter([], [], s=44, color=GREY, label="share of accounts"); a.scatter([], [], s=52, color=NAVY, label="share of next-six-month sales")
    a.legend(loc="lower right", labelcolor=INK2, fontsize=7.2, handletextpad=0.2)
    b.set_xscale("log"); nice_log(b, "x", [200, 500, 1000, 2000, 5000], ["£200", "£500", "£1k", "£2k", "£5k"]); b.set_xlim(150, 6500)
    b.grid(axis="x", color=GRID); b.grid(axis="y", visible=False); clean(b, x=False); b.set_xlabel("Mean next-six-month sales per account, 95% CI")
    panel(b, "B", "Sales per account")
    fig.subplots_adjust(left=0.2, right=0.98, top=0.88, bottom=0.15, wspace=0.12)
    save(fig, f"{S04}/out/fig/fig5_segments.png")


def fig04_cohorts():
    c = load(f"{S04}/out/12_ltv_segments.json")["cohorts_new_accounts"]; cms = list(c["repeat_rate"]); ks = list(range(1, 12))
    top = max(v for m in cms for v in c["repeat_rate"][m].values() if v is not None)
    fig, ax = plt.subplots(figsize=(7.4, 3.2), dpi=300)
    for i, m in enumerate(cms):
        y = len(cms) - 1 - i
        for j, k in enumerate(ks):
            v = c["repeat_rate"][m].get(str(k))
            if v is None:
                rbox(ax, j + 0.06, y + 0.08, 0.88, 0.84, "#f6f4ef", r=0.1, ec="#e4e0d7", lw=0.6)
                continue
            t = v / top
            rbox(ax, j + 0.06, y + 0.08, 0.88, 0.84, mix("#eef2f6", NAVY, 0.08 + 0.92 * t), r=0.1)
            ax.text(j + 0.5, y + 0.5, f"{100 * v:.0f}", ha="center", va="center", fontsize=7.8, fontweight="bold", color="white" if t > 0.55 else INK)
    ax.set_xlim(0, len(ks)); ax.set_ylim(0, len(cms))
    ax.set_xticks([j + 0.5 for j in range(len(ks))], ks); ax.set_xlabel("Months since first purchase  ·  empty cells: after the end of the data")
    ax.set_yticks([len(cms) - 1 - i + 0.5 for i in range(len(cms))], [f"{m}   n = {c['size'][m]}" for m in cms]); ax.tick_params(axis="y", labelcolor=INK, labelsize=7.8)
    ax.grid(False); clean(ax, x=False)
    ax.set_title("Accounts buying again in each month after their first purchase (%)", loc="left", fontweight="bold", color=INK, pad=10)
    fig.subplots_adjust(left=0.15, right=0.985, top=0.88, bottom=0.15)
    save(fig, f"{S04}/out/fig/fig6_cohort_retention.png")


def fig04_calibration():
    r = load(f"{S04}/out/12_ltv_segments.json")
    fig, a = plt.subplots(figsize=(3.8, 3.0), dpi=300)
    a.plot([100, 12000], [100, 12000], color=ORANGE, lw=1.1, ls=(0, (4, 3)))
    for k, name, c in (("calib_ML_lgbm_tweedie", "gradient boosting", GREY), ("calib_BGNBD_GG", "purchase model", NAVY)):
        a.plot([d["pred"] for d in r[k]], [d["actual"] for d in r[k]], color=c, lw=2, marker="o", ms=5, mec="white", mew=1, label=name)
    a.set_xscale("log"); a.set_yscale("log"); nice_log(a, "x", [100, 1000, 10000], ["£100", "£1k", "£10k"]); nice_log(a, "y", [100, 1000, 10000], ["£100", "£1k", "£10k"])
    a.set_xlabel("Mean predicted sales, by decile"); a.set_ylabel("Mean actual sales"); a.legend(loc="upper left", labelcolor=INK2); clean(a)
    a.set_title("Predicted against actual, next six months", loc="left", fontweight="bold", color=INK, pad=10)
    fig.subplots_adjust(left=0.17, right=0.97, top=0.88, bottom=0.16)
    save(fig, f"{S04}/out/fig/fig4_ltv_calibration.png")


# ------------------------------------------------------------------ 02e, 02f, 03d
def fig02e():
    fig, ax = plt.subplots(1, 3, figsize=(8.6, 4.1), dpi=300, gridspec_kw=dict(width_ratios=[1.15, 0.95, 0.95]))
    p_ope_error(ax[0], "A"); p_ope_coverage(ax[1], "B"); p_ope_adjustment(ax[2], "C")
    fig.subplots_adjust(left=0.15, right=0.985, top=0.82, bottom=0.18, wspace=0.85)
    save(fig, f"{S02E}/out/fig_ope.png")


def fig02f():
    fig, ax = plt.subplots(1, 3, figsize=(10.4, 3.3), dpi=300, gridspec_kw=dict(width_ratios=[1.15, 1, 1]))
    p_delay_daily(ax[0], "A"); p_delay_campaign(ax[1], "B"); p_delay_fit(ax[2], "C")
    fig.subplots_adjust(left=0.06, right=0.985, top=0.84, bottom=0.17, wspace=0.62)
    save(fig, f"{S02F}/out/fig_delay.png")


def fig03d():
    fig, ax = plt.subplots(1, 3, figsize=(10.6, 3.1), dpi=300, gridspec_kw=dict(width_ratios=[1.1, 1, 1]))
    p_surrogate(ax[0], "A"); p_surrogate_size(ax[1], "B"); p_surrogate_choice(ax[2], "C")
    fig.subplots_adjust(left=0.17, right=0.985, top=0.84, bottom=0.18, wspace=0.38)
    save(fig, f"{S03D}/out/fig_surrogate.png")


if __name__ == "__main__":
    style()
    for f in (fig01a, fig01b, fig01d, fig02a, fig02b, fig02c_recovery, fig02c_detect, fig03a_power, fig03a_mde, fig03b, fig03c,
              fig04_segments, fig04_cohorts, fig04_calibration, fig02e, fig02f, fig03d):
        f()
