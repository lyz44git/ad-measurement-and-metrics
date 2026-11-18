"""Figures 1 to 6 of the README, drawn from the committed result files in the shared style (figures/figstyle.py).

Usage: python figures/make_figures.py   (writes figures/figure1.png to figure6.png)
"""
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from figstyle import *  # noqa: E402,F401,F403


# ------------------------------------------------------------------ Figure 1
def figure1():
    inc = load(f"{S01A}/out/criteo/a_incrementality.json"); at = load(f"{S02A}/out/attribution_vs_experiment.json"); n1 = at["n_treated"]
    fig = plt.figure(figsize=(W, 3.1), dpi=300)
    gs = fig.add_gridspec(2, 2, width_ratios=[1, 1.12], hspace=0.5, wspace=0.62, left=0.11, right=0.99, top=0.76, bottom=0.07)
    H = 0.42
    for i, (key, name, unit) in enumerate((("conversion", "Conversions", "conversions"), ("visit", "Visits", "visits"))):
        r = inc[key]["itt"]; p0, p1 = 100 * r["control_mean"], 100 * (r["control_mean"] + r["est"])
        a = fig.add_subplot(gs[i, 0])
        a.barh(1, p0, height=H, color=GREY); a.barh(0, p0, height=H, color=GREY); a.barh(0, p1 - p0, left=p0, height=H, color=NAVY)
        a.plot([p0, p0], [-H / 2, H / 2], color="white", lw=0.8)
        d = 3 if key == "conversion" else 2
        a.text(p0 + p1 * 0.015, 1, f"{p0:.{d}f}%", va="center"); a.text(p1 + p1 * 0.015, 0, f"{p1:.{d}f}%", va="center", fontweight="bold")
        y = -0.36; a.plot([p0, p0, p1, p1], [y + 0.06, y, y, y + 0.06], color=NAVY, lw=0.5)
        a.text((p0 + p1) / 2, y - 0.07, f"+{p1 - p0:.{d}f} percentage points ({100 * (p1 / p0 - 1):.0f}% relative)", ha="center", va="top", color=NAVY, fontweight="bold", fontsize=7, linespacing=1.15)
        a.set_yticks([1, 0], ["Control\n(no ads)", "Eligible\nfor ads"]); a.tick_params(axis="y", length=0); a.spines["left"].set_visible(False); a.spines["bottom"].set_visible(False); a.set_xticks([])
        a.set_xlim(0, p1 * 1.2); a.set_ylim(-1.15, 1.75)
        a.text(0, 1.5, f"{name}  (% of users assigned to each group)", fontsize=7.5, color=MID, va="center")
        if i == 0:
            head(a, "a", "In Criteo's randomized experiment, users eligible for ads converted and visited more", 46, dx=-0.5)
        b = fig.add_subplot(gs[i, 1]); q = at[key]; c, cr = q["incremental"], q["attributed"]; ci = 1.96 * r["se"] * n1
        b.barh(1, c, height=H, color=NAVY); b.plot([c - ci, c + ci], [1, 1], color=LIGHTBLUE, lw=1.2, solid_capstyle="butt", zorder=3)
        b.barh(0, c, height=H, color=LIGHTBLUE); b.barh(0, cr - c, left=c, height=H, color=ORANGE)
        b.plot([c, c], [-H / 2 - 0.05, 1 - H / 2], color=NAVY, lw=0.6, ls=(0, (2, 2)))
        b.text(c + ci + cr * 0.015, 1, f"{c:,.0f}", va="center", fontweight="bold", color=NAVY)
        b.text(c - cr * 0.02, 1 - H / 2 - 0.06, f"95% range: {c - ci:,.0f} to {c + ci:,.0f}", ha="right", va="top", fontsize=6.3, color=MID)
        b.text(cr + cr * 0.012, 0, f"{cr:,.0f}", va="center", fontweight="bold")
        b.text((c + cr) / 2, 0, f"+{cr - c:,.0f}", ha="center", va="center", color="white", fontweight="bold")
        b.text((c + cr) / 2, -0.36, "excess over the estimate\n(a group-level comparison)", ha="center", va="top", color=ORANGE, fontweight="bold", fontsize=7, linespacing=1.15)
        b.set_yticks([1, 0], ["Estimated additional\n(from the experiment)", "Credited to ads\n(exposure count)"]); b.tick_params(axis="y", length=0)
        b.spines["left"].set_visible(False); b.spines["bottom"].set_visible(False); b.set_xticks([])
        b.set_xlim(0, cr * 1.16); b.set_ylim(-1.15, 1.75)
        b.text(0, 1.5, f"{name}  (number, eligible group)", fontsize=7.5, color=MID, va="center")
        if i == 0:
            head(b, "b", "Counting every outcome of a user shown an ad credits ads with more than that estimate", 46, dx=-1.05)
    out(fig, "figures/figure1.png")


# ------------------------------------------------------------------ Figure 2
def figure2():
    fig, ax = plt.subplots(1, 3, figsize=(W, 2.85), dpi=300, gridspec_kw=dict(width_ratios=[1.1, 1, 1.1]))
    fig.subplots_adjust(left=0.07, right=0.96, top=0.79, bottom=0.2, wspace=0.52)
    tg = load(f"{S01A}/out/criteo/c_targeting.json"); cal = tg["calibration_selected"]
    a = ax[0]; x = [r["decile"] for r in cal]; y = [100 * r["realized"] for r in cal]
    a.bar(x, y, width=0.55, color=[NAVY, BLUE] + [GREY] * 8); a.axhline(0, color=AX, lw=0.5)
    a.text(1, y[0] + 0.12, f"+{y[0]:.1f}", ha="center", fontweight="bold", color=NAVY); a.text(2, y[1] + 0.12, f"{y[1]:.1f}", ha="center", color=BLUE)
    a.text(10, y[9] + 0.12, f"{y[9]:.1f}", ha="center", color=DGREY)
    a.plot([2.75, 2.95, 2.95, 2.75], [5.9, 5.9, 3.6, 3.6], color=NAVY, lw=0.5)
    a.text(3.2, 4.75, "Top 20% of users drive\nthree-quarters of all\nextra visits", va="center", color=NAVY, fontweight="bold", fontsize=7, linespacing=1.2)
    a.text(6.6, 1.5, "Remaining 80%:\n0.7 points or less", ha="center", color=DGREY, fontsize=7, linespacing=1.2)
    a.set_xticks(x); a.set_ylim(-0.3, 6.9); a.set_xlim(0.3, 10.7)
    a.set_xlabel("Users ranked by a model's predicted response\n(1 = top 10%, 10 = bottom 10%)"); a.set_ylabel("Extra visits caused by ads\n(percentage points)")
    head(a, "a", "The effect of ads is concentrated in the top 10% of users", 32)

    p = load(f"{S01B}/out/part2_segments.json"); p.update(load(f"{S01B}/out/part2_segments_rerun.json")); order = sorted(p, key=int); b = ax[1]
    v0 = [100 * p[r]["rmse"]["cpool"] for r in order]; v1 = [100 * p[r]["rmse"]["nopool"] for r in order]; v2 = [100 * p[r]["rmse"]["bayes"] for r in order]
    for u, v in zip(v1, v2):
        b.plot([1, 2], [u, v], color=LIGHTBLUE, lw=0.8, zorder=1)
    b.plot([1] * 10, v1, "o", color=GREY, ms=3.6, zorder=2); b.plot([2] * 10, v2, "o", color=NAVY, ms=3.6, zorder=2)
    for xx, v, col, bold in ((0, v0, DGREY, False), (1, v1, DGREY, False), (2, v2, NAVY, True)):
        m = sum(v) / len(v)
        if xx == 0:
            b.plot([-0.22, 0.22], [m, m], color=GREY, lw=2.2, solid_capstyle="butt"); b.text(0, m - 0.07, f"{m:.2f}", ha="center", va="top", color=col)
        else:
            sx = -1 if xx == 1 else 1
            b.plot([xx + sx * 0.12, xx + sx * 0.3], [m, m], color=col if bold else GREY, lw=2.2, solid_capstyle="butt")
            b.text(xx + sx * 0.36, m, f"{m:.2f}", ha="right" if sx < 0 else "left", va="center", color=col, fontweight="bold" if bold else "normal")
    b.text(1.5, 1.52, "Lower error in\n10 of 10 samples", ha="center", va="center", color=NAVY, fontweight="bold", fontsize=7, linespacing=1.2)
    b.set_xticks([0, 1, 2], ["Complete\npooling", "No\npooling", "Multilevel\n(partial)"]); b.tick_params(axis="x", length=0)
    b.set_xlim(-0.5, 2.8); b.set_ylim(0.4, 2.05); b.set_yticks([0.5, 1.0, 1.5, 2.0])
    b.set_ylabel("Error of segment estimates\n(percentage points, lower is better)")
    b.text(2.75, 0.44, "dot = one sample\nbar = average", ha="right", va="bottom", fontsize=6, color=MID, linespacing=1.2)
    head(b, "b", "Pooling lowered the segment error in all ten 2% samples", 30)

    pr = load(f"{S01D}/out/a_private_summary.json"); eps = ["0.1", "0.5", "1.0", "5.0", "inf"]; xe = list(range(5)); c = ax[2]
    base = 100 * pr["nonprivate_nopool_rmse"]; vn = [100 * pr["by_eps"][e]["rmse_nopool"] for e in eps]; vm = [100 * pr["by_eps"][e]["rmse_ml"] for e in eps]
    band(c, xe, vm, vn, logy=True, color=PALE); curve(c, xe, vn, GREY, logy=True); curve(c, xe, vm, NAVY, logy=True)
    c.axhline(base, color=DGREY, lw=0.7, ls=(0, (3, 2)), zorder=1)
    c.set_xlim(-0.25, 4.35)
    c.text(0.2, vn[0], f"{vn[0]:.1f}  No pooling", va="center", color=DGREY, fontweight="bold", fontsize=7)
    c.text(0.12, vm[0] * 1.07, f"{vm[0]:.1f}  Multilevel model", va="bottom", color=NAVY, fontweight="bold", fontsize=7)
    c.text(-0.2, base / 1.05, f"dashed: separate,\nno noise ({base:.2f})", ha="left", va="top", color=DGREY, fontsize=6, linespacing=1.15)
    c.text(4.12, vm[4] / 1.12, f"{vm[4]:.2f}", ha="center", va="top", color=NAVY, fontsize=6.5, fontweight="bold")
    c.annotate(f"Pooled at ε = 1: {vm[2]:.2f}", (2, vm[2]), xytext=(3.0, 0.63), ha="center", va="center", color=NAVY, fontsize=6.5, fontweight="bold",
               arrowprops=dict(arrowstyle="-", color=NAVY, lw=0.5, shrinkA=0, shrinkB=3), linespacing=1.2)
    c.set_yscale("log"); c.set_yticks([0.5, 1, 2, 4, 8], ["0.5", "1", "2", "4", "8"]); c.minorticks_off(); c.set_ylim(0.5, 9.5)
    c.set_xticks(xe, ["ε = 0.1", "0.5", "1", "5", "none"]); c.set_xlim(-0.25, 4.35)
    c.set_xlabel("Privacy budget ε  (smaller = more noise\nadded to protect individual users)"); c.set_ylabel("Error of segment estimates\n(percentage points, log scale)")
    head(c, "c", "At ε = 1, pooled estimates match noise-free separate ones", 28)
    out(fig, "figures/figure2.png")


# ------------------------------------------------------------------ Figure 3
def figure3():
    fig = plt.figure(figsize=(W, 2.9), dpi=300)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.05, 1.35, 0.9], wspace=0.8, left=0.165, right=0.97, top=0.76, bottom=0.2)
    pe_ = load(f"{S02A}/out/attribution_vs_experiment.json")["per_exposed_user_visit_effect"]; cace = load(f"{S01A}/out/criteo/a_incrementality.json")
    lo_, hi_ = 100 * cace["cace_visit_adjusted"]["est"], 100 * cace["cace_visit_unadjusted"]["est"]
    a = fig.add_subplot(gs[0])
    for xx, lab, ha in ((lo_, f"adjusted\n{lo_:.1f}", "right"), (hi_, f"unadjusted\n{hi_:.1f}", "left")):
        a.plot([xx, xx], [-0.5, 2.55], color=BLUE, lw=0.7, ls=(0, (2, 2)))
        a.text(xx + (-0.8 if ha == "right" else 0.8), 2.62, lab, ha=ha, va="bottom", fontsize=6.3, color=BLUE, linespacing=1.15)
    a.text((lo_ + hi_) / 2, 3.38, "Two estimates from the experiment", ha="center", va="bottom", fontsize=6.5, color=BLUE, fontweight="bold")
    rows_ = [("Raw comparison:\nexposed vs. unexposed", 100 * pe_["naive"], ORANGE), ("Regression\nadjustment", 100 * pe_["ols_adjusted"], NAVY), ("Double machine\nlearning", 100 * pe_["dml"], NAVY)]
    for i, (name, v, col) in enumerate(rows_):
        y = 2 - i
        if col == ORANGE:
            a.plot([hi_, v], [y, y], color=ORANGE, lw=1.0, ls=(0, (2, 1.5)), zorder=2)
        a.plot(v, y, "o", color=col, ms=5.5, zorder=3)
        a.text(v + 2.6, y, f"{v:.1f}" + ("\nfar above" if col == ORANGE else ""), ha="left", va="center", fontweight="bold", color=col, path_effects=HALO, linespacing=1.15)
    a.set_yticks([2, 1, 0], [r[0] for r in rows_]); a.tick_params(axis="y", length=0); a.spines["left"].set_visible(False)
    a.set_xlim(0, 58); a.set_ylim(-0.5, 3.9); a.set_xticks([0, 10, 20, 30, 40]); a.set_xlabel("Effect on visits among users who\nactually saw an ad (percentage points)")
    head(a, "a", "The raw exposed–unexposed gap far exceeds the experiment", 28, dx=-0.85)

    cr = load(f"{S02B}/out/mta.json")["credit_by_recency_bucket"]; keys = ["last", "<1d", "1-7d", ">7d"]
    cols = ["Last ad", "<1 day", "1–7 days", ">7 days"]; rules = [("cr_last", "Last touch"), ("cr_decay", "Time decay"), ("cr_linear", "Linear"), ("cr_first", "First touch")]
    b = fig.add_subplot(gs[1]); CW, BW = 1.0, 0.6
    for j, cname in enumerate(cols):
        b.text(j * CW, 3.62, cname, ha="left", va="bottom", fontsize=6.2, color=INK, fontweight="bold", linespacing=1.15)
        b.plot([j * CW, j * CW], [-0.42, 3.45], color="#c9cfd6", lw=0.5)
    for q, (rk, _) in enumerate(rules):
        y = 3 - q; vals = [100 * cr[rk][k] for k in keys]; top = max(vals)
        for j, v in enumerate(vals):
            if round(v) == 0:
                b.text(j * CW + 0.05, y, "0%", va="center", color=GREY, fontsize=7)
            else:
                b.barh(y, BW * v / 100, left=j * CW, height=0.44, color=NAVY if v == top else LIGHTBLUE)
                if v > 60:
                    b.text(j * CW + BW * v / 200, y, f"{v:.0f}%", ha="center", va="center", fontsize=7, fontweight="bold", color="white")
                else:
                    b.text(j * CW + BW * v / 100 + 0.04, y, f"{v:.0f}%", va="center", fontsize=7, fontweight="bold" if v == top else "normal", color=NAVY if v == top else INK)
    b.set_yticks([3, 2, 1, 0], [r[1] for r in rules]); b.tick_params(axis="y", length=0); b.set_xlim(0, 4 * CW - 0.1); b.set_ylim(-0.5, 4.25)
    b.set_xticks([]); b.spines["bottom"].set_visible(False); b.spines["left"].set_visible(False)
    b.set_xlabel("Share of conversion credit by time before the last ad\n(64,159 multi-touch conversions; rows add to 100%)", labelpad=8)
    head(b, "b", "Four rules divide the same credit very differently", 44, dx=-0.62)

    bd = load(f"{S02D}/out/bidding.json")["budgets"]; c = fig.add_subplot(gs[2]); ks = ("0.25", "0.5", "0.75")
    c.plot([0.55, 1.45], [5, 5], color=ORANGE, lw=1.2, ls=(0, (4, 2))); c.text(1.0, 5.15, "limit set in advance\nfor the 50% budget: 5%", ha="center", va="bottom", fontsize=6.3, color=ORANGE, fontweight="bold", linespacing=1.15)
    c.axhline(0, color=AX, lw=0.5)
    for rule, col, name, dy, va in (("cr_decay", NAVY, "counted by\ntime decay", 0.3, "bottom"), ("cr_last", BLUE, "counted by last touch", -0.3, "top")):
        m = [100 * bd[k]["cross_rule_loss"][rule][0] for k in ks]; curve(c, range(3), m, col)
        for q, v in enumerate(m):
            c.text(q, v + dy, f"{v:.1f}%".replace("-", "−"), ha="center", va=va, fontsize=7, color=col, path_effects=HALO)
        c.text(2.3 if col == NAVY else -0.25, m[1] + 1.5 if col == NAVY else -1.6, name, ha="right" if col == NAVY else "left", va="center", linespacing=1.15, fontsize=6.5, color=col, fontweight="bold")
    c.set_xticks(range(3), ["25%", "50%", "75%"]); c.set_xlim(-0.35, 2.35); c.set_ylim(-2.2, 6.9); c.set_yticks([0, 2, 4], ["0 (no loss)", "2%", "4%"])
    c.set_xlabel("Budget (share of\nlogged spend)"); c.set_ylabel("Credit lost when bids are\ntrained on the other rule")
    head(c, "c", "Bids change little with the rule", 18)
    out(fig, "figures/figure3.png")


# ------------------------------------------------------------------ Figure 4
def figure4():
    fig, ax = plt.subplots(1, 2, figsize=(W, 2.85), dpi=300, gridspec_kw=dict(width_ratios=[1.45, 1]))
    fig.subplots_adjust(left=0.115, right=0.975, top=0.79, bottom=0.2, wspace=0.42)
    rr = [r for r in rows(f"{S02C}/out/detectability.csv") if r["sim"] == "brand_shapes"]
    idx = {(r["org"], r["channel"]): float(r["index"]) for r in rr if r["freq"] == "D"}
    rec = [r for r in rows(f"{S02C}/out/mmm_pooled_recovery_daily.csv") if r["sim"] == "brand_shapes" and r["single_converged"] == "True"]
    t1 = load(f"{S02C}/out/detectability.json")["tests"]["T1"]; mw, ms = 100 * t1["index_below_2"]["median_err"], 100 * t1["index_2_or_more"]["median_err"]
    px = [max(idx[(r["org"], r["channel"])], 0.06) for r in rec]; py = [100 * abs(float(r["single"]) - float(r["true"])) / float(r["true"]) for r in rec]
    a = ax[0]; a.axvspan(2, 25, color=PALE, alpha=0.7, lw=0)
    a.plot([u for u in px if u < 2], [v for u, v in zip(px, py) if u < 2], "o", color=GREY, ms=3.8, alpha=0.8); a.plot([u for u in px if u >= 2], [v for u, v in zip(px, py) if u >= 2], "o", color=NAVY, ms=3.8, alpha=0.85)
    a.plot([0.05, 2], [mw, mw], color=ORANGE, lw=2); a.plot([2, 25], [ms, ms], color=NAVY, lw=2); a.plot([2, 2], [ms, mw], color=DGREY, lw=0.8)
    a.text(0.058, 0.13, f"Weak signal (index < 2):\nmedian error {mw:.0f}%", color=ORANGE, fontweight="bold", fontsize=7, va="bottom", linespacing=1.2, path_effects=HALO)
    a.text(23, 1300, f"Strong signal (index ≥ 2):\nmedian error {ms:.0f}%", color=NAVY, fontweight="bold", fontsize=7, va="top", ha="right", linespacing=1.2, path_effects=HALO)
    a.text(23, 2600, "each dot = one brand's channel", ha="right", va="center", fontsize=6, color=MID)
    a.set_xscale("log"); a.set_yscale("log"); a.set_xlim(0.05, 25); a.set_ylim(0.1, 4000)
    a.set_xticks([0.1, 1, 2, 10], ["0.1", "1", "2", "10"]); a.set_yticks([0.1, 1, 10, 100, 1000], ["0.1%", "1%", "10%", "100%", "1,000%"]); a.minorticks_off()
    a.set_xlabel("Signal-to-noise index: how much a channel's spend varies,\nrelative to the noise in sales (log scale)"); a.set_ylabel("Error of the estimated return on ad spend\n(% of the known simulated value, log scale)")
    head(a, "a", "In a simulation with known returns, a higher signal index goes with smaller errors", 50)
    b = ax[1]
    for i, (freq, name) in enumerate((("W", "Weekly data"), ("D", "Daily data"))):
        v = [float(r["index"]) for r in rr if r["freq"] == freq]; k = sum(u >= 2 for u in v); s = 100 * k / len(v); y = 1 - i
        b.barh(y, 100, height=0.3, color=PALE); b.barh(y, s, height=0.3, color=NAVY)
        b.text(s + 2.5, y, f"{s:.0f}%", va="center", fontsize=9, fontweight="bold", color=NAVY)
        b.text(0, y - 0.22, f"{k} of {len(v)} brand–channel pairs", ha="left", va="top", fontsize=6.5, color=MID)
    b.text(0, 1.3, "index of 2 or more", ha="left", va="center", fontsize=6.5, color=NAVY, fontweight="bold"); b.text(100, 1.3, "below 2", ha="right", va="center", fontsize=6.5, color=DGREY)
    b.set_yticks([1, 0], ["Weekly\ndata", "Daily\ndata"]); b.tick_params(axis="y", length=0); b.set_xlim(0, 100); b.set_ylim(-0.55, 1.5); b.set_xticks([0, 50, 100], ["0%", "50%", "100%"]); b.spines["left"].set_visible(False)
    b.set_xlabel("Share of simulated brand–channel pairs")
    head(b, "b", "In the simulation, daily data clears the index threshold more often", 34, dx=-0.45)
    out(fig, "figures/figure4.png")


# ------------------------------------------------------------------ Figure 5
def figure5():
    fig = plt.figure(figsize=(W, 2.9), dpi=300)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 1, 1.0], wspace=0.6, left=0.145, right=0.97, top=0.78, bottom=0.2)
    cov = load(f"{S03A}/out/covariate_adjustment.json")["required_n_one_point_lift"]; D, L, M = cov["D"], cov["L"], cov["M"]; a = fig.add_subplot(gs[0])
    for i, (v, col) in enumerate(((D, GREY), (L, BLUE), (M, NAVY))):
        y = 2 - i
        if i:
            a.barh(y, D - v, left=v, height=0.42, color=PALE); a.text((v + D) / 2, y, f"{100 * (D - v) / D:.0f}%\nfewer", ha="center", va="center", fontsize=6.5, color=NAVY, fontweight="bold", linespacing=1.05)
        a.barh(y, v, height=0.42, color=col); a.text(v - D * 0.03, y, f"{v:,.0f}", ha="right", va="center", color="white", fontweight="bold")
    a.axvline(D, color=DGREY, lw=0.5, ls=(0, (2, 2)), ymin=0.08, ymax=0.9)
    a.set_yticks([2, 1, 0], ["No adjustment", "Adjust for 12\nuser features", "Adjust for a\nmodel's prediction"]); a.tick_params(axis="y", length=0); a.spines["left"].set_visible(False)
    a.set_xlim(0, D * 1.04); a.set_ylim(-0.6, 2.6); a.set_xticks([0, 2000, 4000, 6000], ["0", "2,000", "4,000", "6,000"])
    a.set_xlabel("Estimated users per group to detect a one-percentage-\npoint increase in visits with 80% power")
    head(a, "a", "Adjusting for pre-test data lowers the planned sample by up to 31%", 30, dx=-0.7)

    eff = load(f"{S01C}/out/readout.json")["effects"]; b = fig.add_subplot(gs[1])
    n = lambda p0, l: Z_POWER ** 2 * (p0 * (1 - p0) + p0 * (1 + l) * (1 - p0 * (1 + l))) / (p0 * l) ** 2
    ls = [0.05 + 0.005 * i for i in range(91)]; pv, pc = eff["visit"]["control_rate"], eff["conversion"]["control_rate"]; xs = [100 * l for l in ls]
    b.fill_between(xs, [n(pv, l) for l in ls], [n(pc, l) for l in ls], color=PALE, lw=0)
    b.plot(xs, [n(pc, l) for l in ls], color=NAVY); b.plot(xs, [n(pv, l) for l in ls], color=BLUE)
    nc, nv = n(pc, 0.1), n(pv, 0.1); b.plot(10, nc, "o", color=NAVY, ms=5); b.plot(10, nv, "o", color=BLUE, ms=5)
    b.annotate("", (10, nc / 1.35), (10, nv * 1.35), arrowprops=dict(arrowstyle="<->", color=NAVY, lw=0.7))
    b.text(9.3, math.sqrt(nc * nv), f"{nc / nv:.0f}× more\nusers", va="center", ha="right", linespacing=1.15, color=NAVY, fontweight="bold", fontsize=7)
    b.text(11, nc * 1.5, f"{nc:,.0f}", va="bottom", color=NAVY, fontsize=7, fontweight="bold"); b.text(9.3, nv / 1.7, f"{nv:,.0f}", va="top", ha="right", color=BLUE, fontsize=7, fontweight="bold")
    b.text(22, n(pc, 0.22) * 1.9, "Conversions", ha="left", va="bottom", color=NAVY, fontweight="bold", fontsize=7); b.text(30, n(pv, 0.3) / 2.2, "Visits", ha="right", va="top", color=BLUE, fontweight="bold", fontsize=7)
    b.set_xscale("log"); b.set_yscale("log"); b.set_xticks([5, 10, 25, 50], ["5%", "10%", "25%", "50%"]); b.minorticks_off(); b.set_xlim(4.6, 52)
    b.set_yticks([1e3, 1e4, 1e5, 1e6], ["1,000", "10,000", "100,000", "1 million"]); b.set_ylim(1e3, 1.2e7)
    b.set_xlabel("Relative lift to detect (log scale);\nlabelled values are for a 10% lift"); b.set_ylabel("Users needed per group (log scale)")
    head(b, "b", "For a 10% lift, conversions need about 20 times the sample of visits", 30)

    keys = {"CR: year-over-year difference": GREY, "CR: ANCOVA (CUPED)": NAVY}; md = {k: {} for k in keys}
    for r in rows(f"{S03B}/out/design_summary.csv"):
        if r["estimator"] in keys and r["test_months"] == "2":
            md[r["estimator"]][int(r["metros"])] = float(r["mde_80_pct"])
    c = fig.add_subplot(gs[2]); ms_ = [20, 50, 100, 150]; xp = [0, 1, 2, 3]; yy = [md["CR: year-over-year difference"][m] for m in ms_]; ya = [md["CR: ANCOVA (CUPED)"][m] for m in ms_]
    band(c, xp, ya, yy, color=PALE); curve(c, xp, yy, GREY); curve(c, xp, ya, NAVY)
    for q, (u, v) in enumerate(zip(yy, ya)):
        c.text(q + (0.12 if q < 2 else 0), u + (0.4 if q < 2 else 0.9), f"{u:.1f}%", ha="left" if q < 2 else "center", va="bottom", fontsize=7, color=DGREY); c.text(q - (0.1 if q == 0 else 0), v - (0 if q == 0 else 1.3), f"{v:.1f}%", ha="right" if q == 0 else "center", va="center" if q == 0 else "top", fontsize=7, color=NAVY, fontweight="bold")
    c.text(3.2, 19.5, "Year-over-year\ndifference", ha="right", va="center", color=DGREY, fontweight="bold", fontsize=7, linespacing=1.2)
    c.text(-0.9, 3.6, "ANCOVA\n(CUPED)", ha="left", va="center", color=NAVY, fontweight="bold", fontsize=7, linespacing=1.2)
    c.set_xticks(xp, [str(m) for m in ms_]); c.set_xlim(-1.0, 3.3); c.set_ylim(2, 26); c.set_yticks([5, 10, 15, 20, 25], ["5%", "10%", "15%", "20%", "25%"])
    c.set_xlabel("Number of metros in a two-month test\n(housing-market series, not ad data)"); c.set_ylabel("Smallest change the test detects\nwith 80% power (lower is better)")
    head(c, "c", "Adjusting for market history detects smaller changes", 28)
    out(fig, "figures/figure5.png")


# ------------------------------------------------------------------ Figure 6
def figure6():
    seg = load(f"{S04}/out/12_ltv_segments.json"); ext = load(f"{S04}/out/14_ltv_extension.json")
    fig = plt.figure(figsize=(W, 2.75), dpi=300)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.25, 1.2, 1.0], wspace=0.45, left=0.03, right=0.97, top=0.77, bottom=0.2)
    burn = seg["burnin3_contamination"]; n, old = burn["apparent_new"], burn["bought_in_prior_12m"]; a = fig.add_subplot(gs[0])
    a.barh(0, old, height=0.3, color=ORANGE); a.barh(0, n - old, left=old, height=0.3, color=NAVY); a.plot([old, old], [-0.15, 0.15], color="white", lw=0.8)
    a.text(old / 2, 0, f"{old} accounts", ha="center", va="center", color="white", fontweight="bold"); a.text(old + (n - old) / 2, 0, f"{n - old}", ha="center", va="center", color="white", fontweight="bold")
    a.text(0, 0.22, "Had bought in\nDec 2009–Nov 2010", ha="left", va="bottom", color=ORANGE, fontweight="bold", fontsize=7, linespacing=1.2)
    a.text(n, 0.22, "No earlier\npurchase found", ha="right", linespacing=1.2, va="bottom", color=NAVY, fontweight="bold", fontsize=7)
    a.plot([0, 0, n, n], [-0.22, -0.28, -0.28, -0.22], color=AX, lw=0.5)
    a.text(n / 2, -0.33, f"{n:,} accounts that bought in Mar–May 2011\nbut not in Dec 2010–Feb 2011, so a\n3-month check calls them new", ha="center", va="top", fontsize=7, linespacing=1.2)
    a.set_xlim(-n * 0.02, n * 1.02); a.set_ylim(-1.15, 1.0); bare(a)
    head(a, "a", "Most “new” accounts had bought the year before", 26, dx=0.2)

    e2 = ext["E2"]; b = fig.add_subplot(gs[1])
    for y, v, ci, col, band, tc in ((1, e2["auc_recency"], e2["auc_recency_ci"], GREY, "#d9dde2", DGREY), (0, e2["auc_model"], e2["auc_model_ci"], NAVY, LIGHTBLUE, NAVY)):
        b.plot(ci, [y, y], color=band, lw=7, solid_capstyle="round"); b.plot(v, y, "o", color=col, ms=6, zorder=3)
        b.text(v, y + 0.2, f"{v:.2f}", ha="center", va="bottom", fontweight="bold", color=tc)
        b.text(ci[0] - 0.006, y, f"{ci[0]:.2f}", ha="right", va="center", fontsize=6.5, color=MID); b.text(ci[1] + 0.006, y, f"{ci[1]:.2f}", ha="left", va="center", fontsize=6.5, color=MID)
    b.text(0.845, -0.42, "band = 95% interval", ha="right", va="center", fontsize=6, color=MID)
    b.set_yticks([1, 0], ["Recency\n(days since\nlast purchase)", "BG/NBD +\nGamma-Gamma\nmodel"]); b.tick_params(axis="y", length=0); b.spines["left"].set_visible(False)
    b.set_xlim(0.69, 0.85); b.set_ylim(-0.6, 1.6); b.set_xticks([0.70, 0.75, 0.80, 0.85]); b.set_xlabel("Ranking of who buys again within 6 months\n(AUC; 1,442 high-value accounts)")
    head(b, "b", "A purchase model ranks repeat buyers somewhat better; intervals overlap", 31, dx=-0.62)

    e6, e12 = seg["eval"], ext["E1"]["eval"]; c = fig.add_subplot(gs[2])
    for src, col, tc, name in (((e6["BGNBD_GG"], e12["bgnbd_gg"]), NAVY, NAVY, "BG/NBD + Gamma-Gamma"), ((e6["P0_last6m"], e12["past_sales"]), GREY, DGREY, "Past-sales rule")):
        v = [s["spearman"] for s in src]; c.plot([0, 1], v, color=col, marker="o", ms=5.5)
        c.text(-0.07, v[0], f"{v[0]:.2f}", ha="right", va="center", fontweight="bold", color=tc); c.text(1.07, v[1], f"{v[1]:.2f}", ha="left", va="center", fontweight="bold", color=tc)
    c.text(0.02, 0.662, "BG/NBD + Gamma-Gamma", ha="left", va="bottom", color=NAVY, fontweight="bold", fontsize=7); c.text(0.02, 0.574, "Past-sales rule (repeat last\nperiod's sales)", ha="left", va="top", color=DGREY, fontweight="bold", fontsize=7)
    c.set_xticks([0, 1], ["6 months from\nJun 2011\n(2,716 accounts)", "12 months from\nDec 2010\n(4,239 accounts)"]); c.tick_params(axis="x", length=0); c.set_xlim(-0.35, 1.35); c.set_ylim(0.555, 0.675); c.set_yticks([0.56, 0.60, 0.64])
    c.set_ylabel("Rank correlation with actual sales\n(Spearman ρ, higher is better)")
    head(c, "c", "The model leads in one holdout, past sales in the other", 25)
    out(fig, "figures/figure6.png")


if __name__ == "__main__":
    setup()
    for k in (sys.argv[1:] or ["1", "2", "3", "4", "5", "6"]):
        globals()[f"figure{k}"]()
