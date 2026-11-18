"""Figures shown on the study pages, drawn from the committed result files in the shared style (figures/figstyle.py).

Usage: python figures/make_study_figures.py   (writes the PNG files into each study's output folder)

Intervals are 95% unless a label says otherwise. Where a result file reports a rate over a known number of simulated
studies, the interval is the binomial one for that number of studies.
"""
import random
import sys
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from figstyle import *  # noqa: E402,F401,F403

ZILLOW = "Data Provided by Zillow Group."


def binom(p, n):
    return 196 * (p * (1 - p) / n) ** 0.5


def footer(fig, text):
    fig.text(0.995, 0.008, text, ha="right", va="bottom", fontsize=6, color="#777777")


def capsule(ax, y, v, lo, hi, col, band, tc, fmt="{:.2f}", ends=True, pad=None):
    ax.plot([lo, hi], [y, y], color=band, lw=7, solid_capstyle="round"); ax.plot(v, y, "o", color=col, ms=6, zorder=3)
    ax.text(v, y + 0.22, fmt.format(v), ha="center", va="bottom", fontweight="bold", color=tc)
    if ends:
        pad = pad if pad is not None else (hi - lo) * 0.12
        ax.text(lo - pad, y, fmt.format(lo), ha="right", va="center", fontsize=6.5, color=MID); ax.text(hi + pad, y, fmt.format(hi), ha="left", va="center", fontsize=6.5, color=MID)


# ------------------------------------------------------------------ 01a
def s01a():
    inc = load(f"{S01A}/out/criteo/a_incrementality.json")
    fig, ax = plt.subplots(1, 2, figsize=(W, 2.4), dpi=300); fig.subplots_adjust(left=0.16, right=0.97, top=0.7, bottom=0.27, wspace=0.55)
    for a, key, name, letter, title in ((ax[0], "conversion", "conversions", "a", "Adjusting for user features lowers the estimate and tightens the interval slightly"),
                                        (ax[1], "visit", "visits", "b", "For visits, a far more common outcome, the adjusted estimate is also lower")):
        rows_ = [(1, inc[key]["itt"], GREY, BAND_G, DGREY), (0, inc[key]["aipw_linear"], NAVY, LIGHTBLUE, NAVY)]
        allv = []
        for y, e, col, band, tc in rows_:
            v, h = 100 * e["est"], 196 * e["se"]; allv += [v - h, v + h]
            capsule(a, y, v, v - h, v + h, col, band, tc, fmt="{:.3f}" if key == "conversion" else "{:.2f}", pad=0.0025 if key == "conversion" else 0.03)
        span = max(allv) - min(allv); a.set_xlim(min(allv) - span * 0.55, max(allv) + span * 0.55)
        a.set_yticks([1, 0], ["Unadjusted", "Regression-\nadjusted"]); a.tick_params(axis="y", length=0); a.spines["left"].set_visible(False); a.set_ylim(-0.6, 1.7)
        a.set_xlabel(f"Lift in {name} caused by ads (percentage points)"); a.locator_params(axis="x", nbins=4)
        head(a, letter, title, 44, dx=-0.75)
    ax[1].text(1.0, -0.52, "band = 95% interval", transform=ax[1].transAxes, ha="right", fontsize=6, color=MID)
    out(fig, f"{S01A}/out/fig_rates_by_arm.png")


# ------------------------------------------------------------------ 01b
def s01b():
    p = load(f"{S01B}/out/part2_segments.json"); p.update(load(f"{S01B}/out/part2_segments_rerun.json"))
    reps = sorted(p, key=lambda r: p[r]["rmse"]["nopool"], reverse=True)
    fig, ax = plt.subplots(1, 2, figsize=(W, 3.1), dpi=300, gridspec_kw=dict(width_ratios=[1.2, 1])); fig.subplots_adjust(left=0.1, right=0.975, top=0.78, bottom=0.17, wspace=0.42)
    a = ax[0]
    for i, r in enumerate(reps):
        y = len(reps) - 1 - i; e = {k: 100 * p[r]["rmse"][k] for k in ("cpool", "nopool", "bayes")}
        a.plot([min(e.values()), max(e.values())], [y, y], color=PALE, lw=2.2, zorder=1, solid_capstyle="round")
        a.plot(e["cpool"], y, "o", color=LIGHTBLUE, ms=4.5); a.plot(e["nopool"], y, "o", color=GREY, ms=4.5); a.plot(e["bayes"], y, "o", color=NAVY, ms=5)
        if i == 0:
            a.text(e["bayes"] - 0.02, y + 0.45, "Multilevel\n(partial pooling)", ha="right", va="bottom", color=NAVY, fontweight="bold", fontsize=6.5, linespacing=1.1)
            a.text(e["nopool"] + 0.02, y + 0.45, "No pooling\n(each alone)", ha="left", va="bottom", color=DGREY, fontweight="bold", fontsize=6.5, linespacing=1.1)
            a.text(e["cpool"], y + 0.45, "Complete\npooling", ha="center", va="bottom", color="#6f8fb3", fontweight="bold", fontsize=6.5, linespacing=1.1)
    a.set_yticks(range(len(reps)), [f"Sample {int(r) + 1}" for r in reps][::-1]); a.tick_params(axis="y", length=0, labelsize=6.5)
    a.spines["left"].set_visible(False); a.set_ylim(-0.6, len(reps) + 0.9); a.set_xlim(0.4, 2.1); a.set_xlabel("Error of segment estimates (percentage points, lower is better)")
    head(a, "a", "The pooled estimate has the lowest error in every one of ten samples", 44, dx=-0.5)
    b = ax[1]; s = p[sorted(p, key=int)[0]]["seg"]
    ds = [100 * abs(u - v) for u, v in zip(s["nopool"], s["bench"])]; dp = [100 * abs(u - v) for u, v in zip(s["bayes"], s["bench"])]
    lo, hi = 0.005, 8; closer = sum(v < u for u, v in zip(ds, dp))
    b.fill_between([lo, hi], [lo, lo], [lo, hi], color=PALE, alpha=0.7, lw=0); b.plot([lo, hi], [lo, hi], color=DGREY, lw=0.7, ls=(0, (3, 2)))
    b.plot([u for u, v in zip(ds, dp) if v >= u], [max(v, lo) for u, v in zip(ds, dp) if v >= u], "o", color=GREY, ms=3.4)
    b.plot([u for u, v in zip(ds, dp) if v < u], [max(v, lo) for u, v in zip(ds, dp) if v < u], "o", color=NAVY, ms=3.4)
    b.text(6.5, 0.0065, f"pooled estimate\nis closer:\n{closer} of {len(ds)}", ha="right", va="bottom", color=NAVY, fontweight="bold", fontsize=7, linespacing=1.2, path_effects=HALO, zorder=5)
    b.text(0.0065, 5.5, f"separate estimate is closer:\n{len(ds) - closer} of {len(ds)}", ha="left", va="top", color=DGREY, fontweight="bold", fontsize=7, linespacing=1.2)
    b.set_xscale("log"); b.set_yscale("log"); b.set_xlim(lo, hi); b.set_ylim(lo, hi); b.minorticks_off()
    b.set_xticks([0.01, 0.1, 1], ["0.01", "0.1", "1"]); b.set_yticks([0.01, 0.1, 1], ["0.01", "0.1", "1"])
    b.set_xlabel("Distance of the separate estimate from the benchmark\n(benchmark = effect in the other 98% of users; log scale)")
    b.set_ylabel("Distance of the pooled estimate\nfrom the benchmark")
    head(b, "b", "In most segments the pooled estimate lands closer to the benchmark", 34)
    out(fig, f"{S01B}/out/fig_segment_error.png")


# ------------------------------------------------------------------ 01d
def s01d():
    pr = load(f"{S01D}/out/a_private_summary.json"); al = load(f"{S01D}/out/c_allocation.json")
    fig, ax = plt.subplots(1, 2, figsize=(W, 2.95), dpi=300); fig.subplots_adjust(left=0.085, right=0.86, top=0.78, bottom=0.2, wspace=0.42)
    eps = ["0.1", "0.5", "1.0", "5.0", "inf"]; xe = list(range(5)); c = ax[0]
    base = 100 * pr["nonprivate_nopool_rmse"]; vn = [100 * pr["by_eps"][e]["rmse_nopool"] for e in eps]; vm = [100 * pr["by_eps"][e]["rmse_ml"] for e in eps]
    band(c, xe, vm, vn, logy=True, color=PALE); curve(c, xe, vn, GREY, logy=True); curve(c, xe, vm, NAVY, logy=True); c.axhline(base, color=DGREY, lw=0.7, ls=(0, (3, 2)), zorder=1)
    for q, (u, v) in enumerate(zip(vn, vm)):
        if q < 3:
            c.text(q + 0.08, u * 1.1, f"{u:.2f}", fontsize=6.5, color=DGREY, va="bottom", path_effects=HALO)
        if q in (0, 2, 4): c.text(q, v / 1.2, f"{v:.2f}", fontsize=6.5, color=NAVY, va="top", ha="center", fontweight="bold", path_effects=HALO)
    c.text(0.5, 4.6, "No pooling (each segment alone)", color=DGREY, fontweight="bold", fontsize=7); c.text(0.25, 0.62, "Multilevel model (partial pooling)", color=NAVY, fontweight="bold", fontsize=7)
    c.text(4.3, 2.6, f"dashed line: separate\nwith no noise, {base:.2f}", ha="right", va="center", linespacing=1.2, fontsize=6, color=DGREY, path_effects=HALO)
    c.set_yscale("log"); c.set_yticks([0.5, 1, 2, 4, 8], ["0.5", "1", "2", "4", "8"]); c.minorticks_off(); c.set_ylim(0.5, 11); c.set_xticks(xe, ["ε = 0.1", "0.5", "1", "5", "no noise"]); c.set_xlim(-0.25, 4.35)
    c.set_xlabel("Privacy budget ε: the smaller it is, the more random noise\nis added to the counts to protect individual users")
    c.set_ylabel("Error of segment estimates\n(percentage points, log scale)")
    head(c, "a", "At ε = 1, pooled estimates from noisy counts match noise-free separate estimates", 42)
    b = ax[1]; bud = ["10", "20", "30"]; xb = [10, 20, 30]
    ser = (("multilevel", "uplift, multilevel\nestimates", NAVY, "-", True), ("nopool", "uplift, no-pooling\nestimates", GREY, "-", False), ("response", "response rate\n(visits anyway)", ORANGE, "-", True))
    b.plot(xb, [100 * al[q]["random"] for q in bud], color="#c9cfd6", lw=1.2, ls=(0, (3, 2)))
    b.text(31.3, 100 * al["30"]["random"], "random order", va="center", fontsize=6.5, color=DGREY)
    ends = []
    for k, name, col, ls, bold in ser:
        v = [100 * al[q]["mean_share"][k] for q in bud]; curve(b, xb, v, col); ends.append([v[-1], name, col])
    ends.sort(key=lambda e: e[0], reverse=True); ypos = []
    for v, name, col in ends:
        y = 93 if not ypos else ypos[-1] - 14; ypos.append(y)
        b.text(31.3, y, name, va="center", fontsize=6.5, color=col if col != GREY else DGREY, fontweight="bold", linespacing=1.1)
    for q, xx in zip(bud, xb):
        b.text(xx - 0.6, 100 * al[q]["mean_share"]["multilevel"] + 4, f"{100 * al[q]['mean_share']['multilevel']:.0f}%", ha="center", fontsize=6.5, color=NAVY, fontweight="bold", path_effects=HALO)
        b.text(xx, 100 * al[q]["random"] - 3.5, f"{100 * al[q]['random']:.0f}%", ha="center", va="top", fontsize=6.5, color=DGREY)
    b.set_xticks(xb, ["10%", "20%", "30%"]); b.set_xlim(8.5, 30.8); b.set_ylim(0, 100); b.set_yticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
    b.set_xlabel("Share of users shown ads\n(rankings use estimates without privacy noise)"); b.set_ylabel("Share of all extra visits captured")
    head(b, "b", "Choosing users by estimated effect captures far more extra visits than chance", 40)
    out(fig, f"{S01D}/out/fig_privacy_and_allocation.png")


# ------------------------------------------------------------------ 02a
def s02a():
    at = load(f"{S02A}/out/attribution_vs_experiment.json"); inc = load(f"{S01A}/out/criteo/a_incrementality.json"); n1 = at["n_treated"]
    fig = plt.figure(figsize=(W, 3.1), dpi=300); gs = fig.add_gridspec(2, 2, width_ratios=[1.05, 1], hspace=0.6, wspace=0.75, left=0.17, right=0.965, top=0.76, bottom=0.16); H = 0.42
    for i, (key, name, unit) in enumerate((("conversion", "Conversions", "conversions"), ("visit", "Visits", "visits"))):
        b = fig.add_subplot(gs[i, 0]); q = at[key]; c, cr = q["incremental"], q["attributed"]; ci = 1.96 * inc[key]["itt"]["se"] * n1
        b.barh(1, c, height=H, color=NAVY); b.plot([c - ci, c + ci], [1, 1], color=LIGHTBLUE, lw=1.2, solid_capstyle="butt", zorder=3)
        b.barh(0, c, height=H, color=LIGHTBLUE); b.barh(0, cr - c, left=c, height=H, color=ORANGE); b.plot([c, c], [-H / 2 - 0.05, 1 - H / 2], color=NAVY, lw=0.6, ls=(0, (2, 2)))
        b.text(c + ci + cr * 0.015, 1.03, f"{c:,.0f}", va="bottom", fontweight="bold", color=NAVY); b.text(c + ci + cr * 0.015, 0.97, f"95% range {c - ci:,.0f}–{c + ci:,.0f}", ha="left", va="top", fontsize=6.3, color=MID); b.text(cr + cr * 0.012, 0, f"{cr:,.0f}", va="center", fontweight="bold")
        b.text((c + cr) / 2, 0, f"+{cr - c:,.0f}", ha="center", va="center", color="white", fontweight="bold")
        b.text((c + cr) / 2, -0.36, "excess over the estimate", ha="center", va="top", color=ORANGE, fontweight="bold", fontsize=7)
        b.set_yticks([1, 0], ["Estimated additional\n(from the experiment)", "Credited to ads\n(exposure count)"]); b.tick_params(axis="y", length=0)
        b.spines["left"].set_visible(False); b.spines["bottom"].set_visible(False); b.set_xticks([]); b.set_xlim(0, cr * 1.3); b.set_ylim(-0.9, 1.95)
        b.text(0, 1.7, f"{name}  (number, group eligible for ads)", fontsize=7.5, color=MID, va="center")
        if i == 0:
            head(b, "a", "An exposure count credits ads with more than the experiment estimates they added", 42, dx=-1.05)
    pe_ = at["per_exposed_user_visit_effect"]; a = fig.add_subplot(gs[:, 1])
    est = [("Experiment,\nunadjusted", inc["cace_visit_unadjusted"], None, NAVY), ("Experiment,\nadjusted", inc["cace_visit_adjusted"], None, NAVY),
           ("Raw comparison:\nexposed vs. unexposed", pe_["naive"], pe_["naive_se"], ORANGE), ("Regression\nadjustment", pe_["ols_adjusted"], pe_["ols_se"], NAVY), ("Double machine\nlearning", pe_["dml"], pe_["dml_se"], NAVY)]
    lo_, hi_ = 100 * inc["cace_visit_adjusted"]["est"], 100 * inc["cace_visit_unadjusted"]["est"]
    for xx in (lo_, hi_):
        a.plot([xx, xx], [-0.5, 4.5], color=BLUE, lw=0.6, ls=(0, (2, 2)), zorder=1)
    a.text((lo_ + hi_) / 2, 4.6, "the two estimates from the experiment\n(two specifications, not an interval)", ha="center", va="bottom", fontsize=6.3, color=BLUE, linespacing=1.15)
    for i, (name, e, se, col) in enumerate(est):
        v, se = (100 * e["est"], e["se"]) if isinstance(e, dict) else (100 * e, se); y = 4 - i
        a.plot([v - 196 * se, v + 196 * se], [y, y], color=col, lw=1.0); a.plot(v, y, "o", color=col, ms=5.5, zorder=3)
        a.text(v + 196 * se + 2.2, y, f"{v:.1f}" + ("  far above" if col == ORANGE else ""), va="center", fontweight="bold", color=col, path_effects=HALO)
    a.set_yticks(range(4, -1, -1), [e[0] for e in est]); a.tick_params(axis="y", length=0); a.spines["left"].set_visible(False)
    a.set_xlim(0, 58); a.set_ylim(-0.5, 5.4); a.set_xticks([0, 10, 20, 30, 40]); a.set_xlabel("Effect on visits among users who saw an ad\n(percentage points)")
    head(a, "b", "Adjusted comparisons fall between the two experimental estimates; the raw one does not", 42, dx=-0.9)
    out(fig, f"{S02A}/out/fig_attributed_vs_incremental.png")


# ------------------------------------------------------------------ 02b
def s02b():
    m = load(f"{S02B}/out/mta.json"); cr = m["credit_by_recency_bucket"]; keys = ["last", "<1d", "1-7d", ">7d"]
    cols = ["Last ad", "<1 day\nbefore", "1–7 days\nbefore", ">7 days\nbefore"]; rules = [("cr_last", "Last touch"), ("cr_decay", "Time decay"), ("cr_linear", "Linear"), ("cr_first", "First touch")]
    fig, ax = plt.subplots(1, 2, figsize=(W, 2.9), dpi=300, gridspec_kw=dict(width_ratios=[1.45, 1])); fig.subplots_adjust(left=0.12, right=0.975, top=0.76, bottom=0.2, wspace=0.42)
    b = ax[0]; CW, BW = 1.0, 0.6
    for j, cname in enumerate(cols):
        b.text(j * CW, 3.62, cname, ha="left", va="bottom", fontsize=7, fontweight="bold", linespacing=1.15); b.plot([j * CW, j * CW], [-0.42, 3.45], color="#c9cfd6", lw=0.5)
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
    b.set_yticks([3, 2, 1, 0], [r[1] for r in rules]); b.tick_params(axis="y", length=0); b.set_xlim(0, 4 * CW - 0.1); b.set_ylim(-0.5, 4.25); b.set_xticks([])
    b.spines["bottom"].set_visible(False); b.spines["left"].set_visible(False)
    b.set_xlabel("Share of the credit for one conversion given to each ad,\nby when the ad was seen  (each row adds to 100%)", labelpad=8)
    head(b, "a", "Changing the rule moves the last ad's share of credit from 100% to 39%, 29% or 0%", 46, dx=-0.6)
    c = ax[1]; sc = 100 * m["share_touches_clicked"]
    for q, (rk, _) in enumerate(rules):
        y = 3 - q; v = 100 * m["credit_on_clicked_touches"][rk]; c.barh(y, 100, height=0.36, color=PALE); c.barh(y, v, height=0.36, color=NAVY)
        c.text(103, y, f"{v:.0f}%", va="center", ha="left", fontweight="bold", color=NAVY)
    c.plot([sc, sc], [-0.45, 3.45], color=DGREY, lw=0.8, ls=(0, (3, 2))); c.text(sc + 1.5, 3.62, f"{sc:.0f}% of the 349,355 ads\non these paths were clicked", ha="left", va="bottom", fontsize=6.5, color=DGREY, linespacing=1.15)
    c.set_yticks([3, 2, 1, 0], [r[1] for r in rules]); c.tick_params(axis="y", length=0); c.spines["left"].set_visible(False)
    c.set_xlim(0, 118); c.set_ylim(-0.5, 4.25); c.set_xticks([0, 50, 100], ["0%", "50%", "100%"]); c.spines["bottom"].set_bounds(0, 100); c.set_xlabel("Share of credit given to ads that were clicked", x=0.42)
    head(c, "b", "Which share of the credit goes to ads that were clicked?", 34, dx=-0.6)
    out(fig, f"{S02B}/out/fig_credit_by_rule.png")


# ------------------------------------------------------------------ 02c
def s02c_recovery():
    fig, ax = plt.subplots(1, 2, figsize=(W, 3.3), dpi=300); fig.subplots_adjust(left=0.09, right=0.975, top=0.79, bottom=0.2, wspace=0.34)
    for a, suf, name, letter, col, title in ((ax[0], "", "Weekly data", "a", GREY, "Weekly data (the planned analysis): estimates do not track the known returns"),
                                             (ax[1], "_daily", "Daily data", "b", NAVY, "Daily data (added afterwards): estimates track the known returns far better")):
        r = [u for u in rows(f"{S02C}/out/mmm_recovery{suf}.csv") if u["converged"] == "True"]; rho = load(f"{S02C}/out/mmm_summary{suf}.json")["recovery"]["spearman"]
        a.plot([0.4, 5], [0.4, 5], color=DGREY, lw=0.7, ls=(0, (3, 2)))
        for u in r:
            a.plot([float(u["true"])] * 2, [float(u["lo"]), float(u["hi"])], color=BAND_G if col == GREY else LIGHTBLUE, lw=0.7, zorder=1)
        a.plot([float(u["true"]) for u in r], [float(u["est"]) for u in r], "o", color=col, ms=3.6)
        a.set_xscale("log"); a.set_yscale("log"); a.set_xlim(0.4, 5); a.set_ylim(0.03, 1000)
        a.set_xticks([0.5, 1, 2, 4], ["0.5", "1", "2", "4"]); a.set_yticks([0.1, 1, 10, 100, 1000], ["0.1", "1", "10", "100", "1,000"]); a.minorticks_off()
        a.text(4.7, 0.05, "dashed line: estimate = true value", ha="right", va="bottom", fontsize=6.5, color=DGREY)
        a.text(0.04, 0.96, f"{name}\nrank agreement with the known return: {rho:.2f}", transform=a.transAxes, va="top", fontsize=7, fontweight="bold", color=DGREY if col == GREY else NAVY, linespacing=1.25, bbox=dict(fc="white", ec="none", alpha=0.85, pad=1.5), zorder=5)
        a.set_xlabel("True return on ad spend (known, simulated; log scale)"); a.set_ylabel("Estimated return on ad spend (log scale)")
        head(a, letter, title, 44)
    ax[1].text(1.0, -0.27, "each dot = one brand's channel; line = 90% interval", transform=ax[1].transAxes, ha="right", fontsize=6, color=MID)
    out(fig, f"{S02C}/out/fig_roas_recovery.png")


def s02c_detect():
    det = rows(f"{S02C}/out/detectability.csv"); rr = [r for r in det if r["sim"] == "brand_shapes"]
    idx = {(r["org"], r["channel"]): float(r["index"]) for r in rr if r["freq"] == "D"}
    rec = [r for r in rows(f"{S02C}/out/mmm_pooled_recovery_daily.csv") if r["sim"] == "brand_shapes" and r["single_converged"] == "True"]
    s = load(f"{S02C}/out/detectability.json"); t1 = s["tests"]["T1"]; mw, ms = 100 * t1["index_below_2"]["median_err"], 100 * t1["index_2_or_more"]["median_err"]
    px = [max(idx[(r["org"], r["channel"])], 0.06) for r in rec]; py = [100 * abs(float(r["single"]) - float(r["true"])) / float(r["true"]) for r in rec]
    fig, ax = plt.subplots(1, 2, figsize=(W, 2.95), dpi=300, gridspec_kw=dict(width_ratios=[1.2, 1])); fig.subplots_adjust(left=0.115, right=0.975, top=0.78, bottom=0.2, wspace=0.5)
    a = ax[0]; a.axvspan(2, 25, color=PALE, alpha=0.7, lw=0)
    a.plot([u for u in px if u < 2], [v for u, v in zip(px, py) if u < 2], "o", color=GREY, ms=3.8, alpha=0.8); a.plot([u for u in px if u >= 2], [v for u, v in zip(px, py) if u >= 2], "o", color=NAVY, ms=3.8, alpha=0.85)
    a.plot([0.05, 2], [mw, mw], color=ORANGE, lw=2); a.plot([2, 25], [ms, ms], color=NAVY, lw=2); a.plot([2, 2], [ms, mw], color=DGREY, lw=0.8)
    a.text(0.058, 0.13, f"Weak signal (index < 2):\nmedian error {mw:.0f}%", color=ORANGE, fontweight="bold", fontsize=7, va="bottom", linespacing=1.2, path_effects=HALO)
    a.text(23, 1300, f"Strong signal (index ≥ 2):\nmedian error {ms:.0f}%", color=NAVY, fontweight="bold", fontsize=7, va="top", ha="right", linespacing=1.2, path_effects=HALO)
    a.set_xscale("log"); a.set_yscale("log"); a.set_xlim(0.05, 25); a.set_ylim(0.1, 4000); a.set_xticks([0.1, 1, 2, 10], ["0.1", "1", "2", "10"]); a.set_yticks([0.1, 1, 10, 100, 1000], ["0.1%", "1%", "10%", "100%", "1,000%"]); a.minorticks_off()
    a.set_xlabel("Signal-to-noise index: how much a channel's spend varies,\nrelative to the noise in sales (computed before fitting; log scale)"); a.set_ylabel("Error of the estimated return\n(vs. the known true value, log scale)")
    head(a, "a", "In a simulation, estimates are more accurate where the index, known before fitting, is 2 or more", 46)
    b = ax[1]; rnd = random.Random(7)
    for y, freq, name, col in ((1, "W", "Weekly data", GREY), (0, "D", "Daily data", NAVY)):
        v = sorted(float(r["min_detectable_roas"]) for r in rr if r["freq"] == freq); med = v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] + v[len(v) // 2]) / 2
        b.plot(v, [y + rnd.uniform(-0.16, 0.16) for _ in v], "o", color=col, ms=3.2, alpha=0.75); b.plot([med, med], [y - 0.3, y + 0.3], color=col if col == NAVY else DGREY, lw=2)
        sh = 100 * s[freq]["real_spend"]["share_at_most"]["2"]
        b.text(med, y + 0.36, f"median {med:.1f}", ha="center", va="bottom", fontsize=7, fontweight="bold", color=col if col == NAVY else DGREY)
        b.text(1.85, y - 0.36, f"{sh:.0f}% at 2 or below", ha="right", va="top", fontsize=6.5, color=col if col == NAVY else DGREY)
    b.plot([2, 2], [-0.5, 1.5], color=DGREY, lw=0.7, ls=(0, (3, 2)), zorder=0); b.text(2.15, 1.62, "return of 2", fontsize=6.5, color=DGREY, va="center")
    b.set_yticks([1, 0], ["Weekly\ndata", "Daily\ndata"]); b.tick_params(axis="y", length=0); b.spines["left"].set_visible(False); b.set_ylim(-0.75, 1.8); b.set_xscale("log")
    b.set_xticks([1, 10, 100], ["1", "10", "100"]); b.minorticks_off(); b.text(1.0, -0.38, "each dot = one brand's channel", transform=b.transAxes, ha="right", fontsize=6, color=MID)
    b.set_xlabel("Smallest detectable return on ad spend (80% power)\n(real spend, assumed response curve; log scale)")
    head(b, "b", "On real spend, how small a return could be detected?", 32, dx=-0.45)
    out(fig, f"{S02C}/out/fig_detectability.png")


# ------------------------------------------------------------------ 03a
def s03a_power():
    d = load(f"{S03A}/out/lift_study_sizing.json"); k = d["studies_per_n"]; d = d["by_n"]; ns = sorted(d, key=int); x = list(range(len(ns)))
    fig = plt.figure(figsize=(W, 3.6), dpi=300); gs = fig.add_gridspec(2, 1, height_ratios=[2.2, 1], hspace=0.75, left=0.1, right=0.7, top=0.84, bottom=0.12)
    for a, keys, ref, letter, title, ylab, ylim, reft in ((fig.add_subplot(gs[0]), ("power_z", "bayes_detect"), 80, "a", "Larger tests detect a one-point lift more often", "Tests that detect\na true one-point lift", (0, 105), "80% target"),
                                                          (fig.add_subplot(gs[1]), ("aa_false_positive_z", "aa_false_positive_bayes"), 5, "b", "When there is no lift, both methods raise a false alarm about 5% of the time", "Tests reporting a lift\nwhen there is none", (0, 10), "5% by design")):
        a.axhline(ref, color=DGREY, lw=0.7, ls=(0, (3, 2))); a.text(len(ns) - 0.55, ref, reft, va="center", fontsize=6.5, color=DGREY)
        for key, lab, col, off in zip(keys, ("z-test", "Bayesian, P(lift > 0) > 0.95"), (NAVY, BLUE), (-0.03, 0.03)):
            y = [100 * d[n][key] for n in ns]; h = [binom(d[n][key], k) for n in ns]
            for q, (u, e) in enumerate(zip(y, h)):
                a.plot([q + off] * 2, [u - e, u + e], color=LIGHTBLUE, lw=1.0, zorder=1)
            curve(a, x, y, col)
            if letter == "a":
                a.text(len(ns) - 0.55, 62 if col == NAVY else 38, lab, va="center", fontsize=6.5, color=col, fontweight="bold", linespacing=1.15)
        a.set_xticks(x, [f"{int(n):,}" for n in ns]); a.set_xlim(-0.3, len(ns) - 0.7); a.set_ylim(*ylim); a.set_ylabel(ylab)
        a.set_yticks([0, 50, 100] if letter == "a" else [0, 5, 10], ["0%", "50%", "100%"] if letter == "a" else ["0%", "5%", "10%"])
        head(a, letter, title, 90)
    fig.axes[1].set_xlabel("Users per group"); fig.axes[1].text(1.0, -0.62, "vertical lines = 95% intervals", transform=fig.axes[1].transAxes, ha="right", fontsize=6, color=MID)
    out(fig, f"{S03A}/out/fig_power_by_sample_size.png")


def s03a_mde():
    d = load(f"{S03A}/out/covariate_adjustment.json")["by_n"]; ns = sorted(d, key=int); x = list(range(len(ns)))
    series = (("D", "No adjustment", GREY, DGREY), ("L", "Adjust for 12 user features", BLUE, BLUE), ("M", "Adjust for a model's prediction", NAVY, NAVY))
    fig, ax = plt.subplots(1, 2, figsize=(W, 2.95), dpi=300); fig.subplots_adjust(left=0.085, right=0.975, top=0.78, bottom=0.18, wspace=0.42)
    a = ax[0]; a.axhline(1, color=DGREY, lw=0.7, ls=(0, (3, 2))); a.text(len(ns) - 0.6, 1.07, "target: one point", ha="right", va="bottom", fontsize=6.5, color=DGREY)
    for (key, name, col, tc), yy in zip(series, (2.75, 2.45, 2.15)):
        curve(a, x, [100 * d[n][key]["mde80"] for n in ns], col); a.plot(1.55, yy, "o", color=col, ms=4); a.text(1.75, yy, name, va="center", fontsize=6.5, color=tc, fontweight="bold")
    a.set_xticks(x, [f"{int(n):,}" for n in ns]); a.set_ylim(0, 3); a.set_xlabel("Users per group"); a.set_ylabel("Smallest lift the test can detect\n(percentage points, lower is better)")
    head(a, "a", "With adjustment, a test reaches the one-point target with fewer users", 40)
    b = ax[1]; b.axhline(1, color=DGREY, lw=0.7, ls=(0, (3, 2))); b.text(len(ns) - 0.55, 1.012, "no adjustment = 1", ha="right", va="bottom", fontsize=6.5, color=DGREY)
    for (key, name, col, tc), off in zip(series[1:], (-0.07, 0.07)):
        y = [d[n][key]["variance_ratio_to_D"] for n in ns]
        for q, n in enumerate(ns):
            b.plot([q + off] * 2, d[n][key]["variance_ratio_ci"], color=LIGHTBLUE, lw=1.0, zorder=1)
        curve(b, [q + off for q in x], y, col); b.text(-0.35, 0.8 if col == BLUE else 0.6, name, ha="left", va="center", fontsize=6.5, color=tc, fontweight="bold")
    b.set_xticks(x, [f"{int(n):,}" for n in ns]); b.set_xlim(-0.5, len(ns) - 0.5); b.set_ylim(0.4, 1.1); b.set_xlabel("Users per group"); b.set_ylabel("Variance of the result relative to\nno adjustment (lower is better)")
    head(b, "b", "Adjustment removes about 30% of the variance at every size", 38)
    out(fig, f"{S03A}/out/fig_mde_by_adjustment.png")


# ------------------------------------------------------------------ 03b
def s03b():
    tab = rows(f"{S03B}/out/design_summary.csv"); ri = rows(f"{S03B}/out/randomization_inference_check.csv")
    series = (("CR: year-over-year difference", "Year-over-year difference", GREY, DGREY), ("MP: pair ANCOVA", "Matched-pair ANCOVA", BLUE, BLUE), ("CR: ANCOVA (CUPED)", "ANCOVA (CUPED)", NAVY, NAVY))
    mde = {(r["estimator"], int(r["metros"]), int(r["test_months"])): float(r["mde_80_pct"]) for r in tab if r["mde_80_pct"]}; xs = [20, 50, 100, 150]; xp = [0, 1, 2, 3]
    fig, ax = plt.subplots(1, 3, figsize=(W, 2.95), dpi=300, gridspec_kw=dict(width_ratios=[1.15, 0.8, 1.1])); fig.subplots_adjust(left=0.085, right=0.98, top=0.77, bottom=0.21, wspace=0.5)
    a = ax[0]
    for (k, name, col, tc), yy in zip(series, (25.5, 23.2, 20.9)):
        curve(a, xp, [mde[(k, m, 2)] for m in xs], col); a.plot(1.15, yy, "o", color=col, ms=4); a.text(1.3, yy, name, va="center", fontsize=6.5, color=tc, fontweight="bold")
    a.set_xticks(xp, [str(m) for m in xs]); a.set_ylim(0, 28); a.set_yticks([0, 10, 20], ["0", "10%", "20%"]); a.set_xlabel("Number of markets (two-month test)"); a.set_ylabel("Smallest effect the test can detect\n(lower is better)")
    head(a, "a", "More markets and adjustment both shrink the detectable effect", 34)
    b = ax[1]
    for k, name, col, tc in series:
        curve(b, [1, 2, 3], [mde[(k, 100, t)] for t in (1, 2, 3)], col)
    b.set_xticks([1, 2, 3]); b.set_xlim(0.7, 3.3); b.set_ylim(0, 28); b.set_yticks([0, 10, 20], ["0", "10%", "20%"]); b.set_xlabel("Test length in months\n(100 markets)")
    head(b, "b", "A longer test helps much less", 22)
    c = ax[2]; vw = {int(r["metros"]): r for r in ri if r["estimator"] == "CR: volume-weighted ANCOVA"}
    n_t = {int(r["metros"]): int(r["draws"]) for r in tab if r["estimator"] == "CR: volume-weighted ANCOVA" and r["test_months"] == "2"}
    c.axhline(5, color=DGREY, lw=0.7, ls=(0, (3, 2))); c.text(0.5, 4.2, "5% by design", ha="center", va="top", path_effects=HALO, fontsize=6.5, color=DGREY)
    yt = [100 * float(vw[m]["false_positive_rate_t_test"]) for m in xs]; yr = [100 * float(vw[m]["false_positive_rate"]) for m in xs]
    for q, m in enumerate(xs):
        e = binom(yt[q] / 100, n_t[m]); c.plot([q - 0.06] * 2, [yt[q] - e, yt[q] + e], color="#f6d9c4", lw=1.0, zorder=1)
        e = binom(yr[q] / 100, int(vw[m]["draws"])); c.plot([q + 0.06] * 2, [yr[q] - e, yr[q] + e], color=LIGHTBLUE, lw=1.0, zorder=1)
    curve(c, [q - 0.06 for q in xp], yt, ORANGE); curve(c, [q + 0.06 for q in xp], yr, NAVY)
    c.text(-0.3, 11.4, "t-test: false-positive rate above 5%", fontsize=6.5, color=ORANGE, fontweight="bold", va="center"); c.text(-0.3, 1.1, "randomization inference: near 5%", fontsize=6.5, color=NAVY, fontweight="bold", va="center")
    c.set_xticks(xp, [str(m) for m in xs]); c.set_xlim(-0.4, 3.4); c.set_ylim(0, 12); c.set_yticks([0, 5, 10], ["0", "5%", "10%"]); c.set_xlabel("Number of markets"); c.set_ylabel("Tests reporting an effect\nwhen there is none")
    head(c, "c", "Volume-weighted ANCOVA: the t-test over-rejects", 26)
    footer(fig, ZILLOW); out(fig, f"{S03B}/out/fig1_mde_by_metros.png")


# ------------------------------------------------------------------ 03c
def s03c():
    tab = rows(f"{S03C}/reports/tables/inventory_ets_by_horizon.csv"); val = {(r["level"], r["method"], int(r["h"])): float(r["rel_to_no_change"]) for r in tab}; hs = list(range(1, 13))
    hd = rows(f"{S03C}/reports/tables/inventory_ets_headline.csv"); inc = {r["level"]: 100 * float(r["incoherence_mean"]) for r in hd if r["method"] == "base" and r["incoherence_mean"]}
    fig = plt.figure(figsize=(W, 4.9), dpi=300)
    g1 = fig.add_gridspec(1, 1, left=0.27, right=0.8, top=0.86, bottom=0.62); g2 = fig.add_gridspec(1, 4, left=0.085, right=0.98, top=0.42, bottom=0.11, wspace=0.12)
    a = fig.add_subplot(g1[0]); lv = [("US", "Nation vs. sum of regions"), ("division", "Regions vs. sum of states"), ("state", "States vs. sum of metros")]
    a.axvline(0, color=NAVY, lw=1.0)
    for i, (k, name) in enumerate(lv):
        y = 2 - i; a.annotate("", (0.12, y), (inc[k] - 0.12, y), arrowprops=dict(arrowstyle="->", color=LIGHTBLUE, lw=1.0))
        a.plot(inc[k], y, "o", color=ORANGE, ms=6, zorder=3); a.plot(0, y, "o", color=NAVY, ms=6, zorder=4, clip_on=False)
        a.text(inc[k] + 0.18, y, f"{inc[k]:.1f}%", va="center", fontweight="bold", color=ORANGE)
    a.text(0.1, 2.62, "After reconciling: 0%", ha="left", va="bottom", color=NAVY, fontweight="bold", fontsize=7); a.text(inc["US"], 2.62, "Forecast separately", ha="center", va="bottom", color=ORANGE, fontweight="bold", fontsize=7)
    a.set_yticks([2, 1, 0], [n for _, n in lv]); a.tick_params(axis="y", length=0); a.spines["left"].set_visible(False); a.set_xlim(-0.15, 6.2); a.set_ylim(-0.5, 3.1)
    a.set_xticks([0, 2, 4, 6], ["0%", "2%", "4%", "6%"]); a.set_xlabel("Gap between a housing-inventory forecast and the sum of its parts")
    head(a, "a", "Separate forecasts do not add up; reconciling them removes the gap", 70, dx=-1.45)
    axs = [fig.add_subplot(g2[i]) for i in range(4)]
    for i, (a, lev, name) in enumerate(zip(axs, ("US", "division", "state", "metro"), ("Nation", "Regions", "States", "Metros"))):
        a.axhspan(0.3, 1, color=PALE, alpha=0.5, lw=0); a.axhline(1, color=DGREY, lw=0.7, ls=(0, (3, 2)))
        for m, col, ls in (("base", GREY, "-"), ("bu", BLUE, (0, (3, 2))), ("mint_shrink", NAVY, "-")):
            curve(a, hs, [val[(lev, m, h)] for h in hs], col, marker=False, ls=ls)
        a.set_xticks([1, 6, 12]); a.set_ylim(0.3, 1.4); a.set_xlabel("Months ahead"); a.text(0.05, 0.95, name, transform=a.transAxes, va="top", fontweight="bold", fontsize=7.5)
        if i:
            a.set_yticklabels([]); a.tick_params(axis="y", length=0); a.spines["left"].set_visible(False)
    axs[0].set_ylabel("Forecast error relative to\nassuming no change"); axs[1].text(1.2, 1.02, "no change = 1", ha="left", va="bottom", fontsize=6, color=DGREY); axs[0].text(11.8, 0.34, "better than no change", ha="right", va="bottom", fontsize=6, color=BLUE)
    for yy, name, col in ((0.5, "separate forecasts", DGREY), (0.42, "bottom-up sum (dashed)", BLUE), (0.34, "MinT-shrink (minimum trace)", NAVY)):
        axs[3].text(1.1, yy, name, ha="left", va="center", fontsize=6.3, color=col, fontweight="bold")
    head(axs[0], "b", "Reconciling lowers the error up to about nine months ahead; near twelve months no method beats assuming no change", 90)
    footer(fig, ZILLOW); out(fig, f"{S03C}/reports/figures/relative_rmsse_by_horizon_inventory_ets.png")


# ------------------------------------------------------------------ 04
def s04_segments():
    seg = {s["segment"]: s for s in load(f"{S04}/out/12_ltv_segments.json")["rule_segments"]}
    rec = [("recent<=60d", "bought ≤60 days ago"), ("61-120d", "61–120 days ago"), (">120d", ">120 days ago")]; tiers = [("high", "High value"), ("mid", "Mid value"), ("low", "Low value")]
    order = [(f"{r}|{t}", f"{tl} · {rl}") for t, tl in tiers for r, rl in rec]; ys = [8 - q - (q // 3) * 0.5 for q in range(9)]
    fig, ax = plt.subplots(1, 2, figsize=(W, 3.5), dpi=300, gridspec_kw=dict(width_ratios=[1.25, 1])); fig.subplots_adjust(left=0.27, right=0.975, top=0.8, bottom=0.14, wspace=0.12)
    a = ax[0]
    for (k, lab), y in zip(order, ys):
        u, v = 100 * seg[k]["share_accounts"], 100 * seg[k]["share_next6m_sales_existing"]
        a.plot([u, v], [y, y], color=PALE, lw=2.4, solid_capstyle="round", zorder=1); a.plot(u, y, "o", color=GREY, ms=5); a.plot(v, y, "o", color=NAVY, ms=5.5)
        a.text(max(u, v) + 2, y, f"{v:.0f}%", va="center", fontsize=7, fontweight="bold", color=NAVY) if v >= u else a.text(max(u, v) + 2, y, f"{u:.0f}%", va="center", fontsize=7, color=DGREY)
        a.text(min(u, v) - 2, y, f"{u:.0f}%" if v >= u else f"{v:.0f}%", va="center", ha="right", fontsize=7, color=DGREY if v >= u else NAVY, fontweight="normal" if v >= u else "bold")
    k0 = order[0][0]; a.text(100 * seg[k0]["share_accounts"], ys[0] + 0.45, "share of\ncustomers", ha="center", va="bottom", fontsize=6.5, color=DGREY, fontweight="bold", linespacing=1.1)
    a.text(100 * seg[k0]["share_next6m_sales_existing"], ys[0] + 0.45, "share of sales in\nthe next 6 months", ha="center", va="bottom", fontsize=6.5, color=NAVY, fontweight="bold", linespacing=1.1)
    a.set_yticks(ys, [lab for _, lab in order]); a.tick_params(axis="y", length=0, labelsize=7); a.spines["left"].set_visible(False); a.set_ylim(min(ys) - 0.6, max(ys) + 1.5); a.set_xlim(-6, 80)
    a.set_xticks([0, 25, 50, 75], ["0%", "25%", "50%", "75%"]); a.set_xlabel("Share of all customers and of all later sales")
    head(a, "a", "A quarter of customers, recent and high-value, bring 72% of later sales", 46, dx=-1.55)
    b = ax[1]
    for (k, lab), y in zip(order, ys):
        ci = seg[k]["mean_ci_boot"]; b.plot(ci, [y, y], color=LIGHTBLUE, lw=5, solid_capstyle="round", zorder=1); b.plot(seg[k]["mean_next6m_sales"], y, "o", color=NAVY, ms=5.5)
        b.text(ci[1] * 1.18, y, f"£{seg[k]['mean_next6m_sales']:,.0f}", va="center", fontsize=7, fontweight="bold", color=NAVY)
    b.set_xscale("log"); b.set_xticks([200, 500, 2000, 5000], ["£200", "£500", "£2,000", "£5,000"]); b.minorticks_off(); b.set_xlim(120, 14000)
    b.set_yticks([]); b.spines["left"].set_visible(False); b.set_ylim(min(ys) - 0.6, max(ys) + 1.5); b.set_xlabel("Average sales per customer in the next 6 months\n(log scale; band = 95% interval)")
    head(b, "b", "They also spend the most per customer", 34, dx=0.1)
    out(fig, f"{S04}/out/fig/fig5_segments.png")


def s04_cohorts():
    c = load(f"{S04}/out/12_ltv_segments.json")["cohorts_new_accounts"]; cms = list(c["repeat_rate"]); ks = list(range(1, 12))
    grid = [[c["repeat_rate"][cm].get(str(k)) for k in ks] for cm in cms]; top = 100 * max(v for r in grid for v in r if v is not None)
    fig, a = plt.subplots(figsize=(W, 3.3), dpi=300); fig.subplots_adjust(left=0.2, right=0.98, top=0.74, bottom=0.04)
    ramp = ["#f3f6fa", "#dfe6ee", "#a9c4de", "#3f78b0", "#1f3b5c"]
    for i, r in enumerate(grid):
        for j, v in enumerate(r):
            if v is None:
                continue
            q = min(4, int(5 * round(100 * v) / (round(top) + 1))); a.add_patch(plt.Rectangle((j + 0.03, i + 0.05), 0.94, 0.9, color=ramp[q], lw=0))
            a.text(j + 0.5, i + 0.5, f"{100 * v:.0f}%", ha="center", va="center", fontsize=6.8, color="white" if q >= 3 else INK)
    a.set_xlim(0, len(ks)); a.set_ylim(len(cms), 0); a.xaxis.tick_top(); a.xaxis.set_label_position("top")
    a.set_xticks([j + 0.5 for j in range(len(ks))], ks); a.set_yticks([i + 0.5 for i in range(len(cms))], [f"{cm}  ({c['size'][cm]} new customers)" for cm in cms])
    a.tick_params(length=0); a.set_xlabel("Months since first purchase", labelpad=5)
    for s_ in a.spines.values():
        s_.set_visible(False)
    a.text(len(ks), len(cms) - 0.4, "each cell: share of that month's new customers\nwho bought again in that later month\n(darker = higher)", ha="right", va="bottom", fontsize=6.5, color=MID, linespacing=1.2)
    y = 1 + 0.72 / (a.get_position().height * fig.get_figheight())
    a.text(0, y, "After the first cohort, roughly one new customer in five buys again in each later month", transform=a.transAxes, fontsize=8, fontweight="bold", va="top")
    out(fig, f"{S04}/out/fig/fig6_cohort_retention.png", offset=False)


def s04_calibration():
    r = load(f"{S04}/out/12_ltv_segments.json")
    fig, a = plt.subplots(figsize=(3.9, 3.3), dpi=300); fig.subplots_adjust(left=0.2, right=0.96, top=0.79, bottom=0.17)
    top = max(d["actual"] for d in r["calib_BGNBD_GG"]) * 1.6; a.plot([100, top], [100, top], color=DGREY, lw=0.7, ls=(0, (3, 2)))
    for k, name, col in (("calib_ML_lgbm_tweedie", "Gradient boosting (LightGBM)", BLUE), ("calib_BGNBD_GG", "BG/NBD + Gamma-Gamma", NAVY)):
        curve(a, [d["pred"] for d in r[k]], [d["actual"] for d in r[k]], col, logx=True, logy=True, ms=4)
    a.text(0.04, 0.96, "BG/NBD + Gamma-Gamma (purchase model)", transform=a.transAxes, va="top", color=NAVY, fontweight="bold", fontsize=7); a.text(0.04, 0.89, "Gradient boosting (LightGBM, Tweedie loss)", transform=a.transAxes, va="top", color=BLUE, fontweight="bold", fontsize=7)
    a.text(top / 1.1, top / 6, "dashed line:\npredicted = actual", ha="right", va="top", fontsize=6.5, color=DGREY, linespacing=1.2)
    a.set_xscale("log"); a.set_yscale("log"); a.set_xticks([100, 1000, 10000], ["£100", "£1,000", "£10,000"]); a.set_yticks([100, 1000, 10000], ["£100", "£1,000", "£10,000"]); a.minorticks_off()
    a.set_xlabel("Predicted sales in the next 6 months\n(average of each tenth of customers, log scale)"); a.set_ylabel("Actual sales (log scale)")
    head(a, "", "Predicted sales track actual sales, less closely at the two ends", 36)
    out(fig, f"{S04}/out/fig/fig4_ltv_calibration.png")


if __name__ == "__main__":
    setup()
    allf = ["s01a", "s01b", "s01d", "s02a", "s02b", "s02c_recovery", "s02c_detect", "s03a_power", "s03a_mde", "s03b", "s03c", "s04_segments", "s04_cohorts", "s04_calibration"]
    for k in (sys.argv[1:] or allf):
        globals()[k]()
