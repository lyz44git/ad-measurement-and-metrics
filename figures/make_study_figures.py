"""Figures shown on the study pages, drawn from the committed result files in the shared style (figures/figstyle.py).

Usage: python figures/make_study_figures.py   (writes the PNG files into each study's output folder)

Intervals are 95% unless a label says otherwise. Where a result file reports a rate over a known number of simulated
studies, the interval is the binomial one for that number of studies.
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from figstyle import *  # noqa: E402,F401,F403

EDGE = "#444444"
ZILLOW = "Data Provided by Zillow Group."


def binom(p, n):
    return 196 * (p * (1 - p) / n) ** 0.5


def points(ax, x, y, lo, hi, color, label=None, ms=4.5, **kw):
    """Point estimates with an interval given by its lower and upper ends."""
    ax.errorbar(x, y, yerr=[[a - b for a, b in zip(y, lo)], [b - a for a, b in zip(y, hi)]], color=color, marker="o", ms=ms, lw=1.0, label=label, **kw)


def footer(fig, text):
    fig.text(0.995, 0.008, text, ha="right", va="bottom", fontsize=6, color="#777777")


def fig01a():
    """Visit and conversion rates by arm, and the effect of assignment with and without regression adjustment."""
    inc = load(f"{S01A}/out/criteo/a_incrementality.json")
    fig, ax = plt.subplots(1, 4, figsize=(7.2, 2.6), dpi=300)
    for a, key, name, letter in ((ax[0], "visit", "Visit rate", "A"), (ax[1], "conversion", "Conversion rate", "B")):
        r = inc[key]["itt"]; p0, p1 = r["control_mean"], r["control_mean"] + r["est"]
        ci = [binom(p, n) for p, n in ((p0, r["n0"]), (p1, r["n1"]))]
        bars(a, ["Control", "Ad arm"], [100 * p0, 100 * p1], ci, [GREY, NAVY], lambda v: f"{v:.2f}%")
        a.set_ylim(0, 100 * p1 * 1.42); bracket(a, 0, 1, 100 * p1 * 1.13, f"+{100 * r['est']:.2f} pp")
        a.set_ylabel("Percent of users"); panel(a, letter, name)
    for a, key, name, letter in ((ax[2], "visit", "Visit effect", "C"), (ax[3], "conversion", "Conversion effect", "D")):
        est = [inc[key]["itt"], inc[key]["aipw_linear"]]
        v = [100 * e["est"] for e in est]; h = [196 * e["se"] for e in est]
        a.errorbar([0, 1], v, yerr=h, color=NAVY, marker="o", ls="none", ms=5, lw=1.0)
        for i in range(2):
            a.text(i + 0.13, v[i], f"{v[i]:.2f}", va="center", fontsize=7.5)
        a.set_xticks([0, 1], ["Unadjusted", "Adjusted"]); a.set_xlim(-0.5, 1.6); a.set_ylim(0, max(v) * 1.42)
        a.tick_params(axis="x", length=0); a.set_ylabel("Percentage points"); panel(a, letter, name)
    fig.tight_layout(w_pad=1.6)
    save(fig, f"{S01A}/out/fig_rates_by_arm.png")


def fig01b():
    """Error of the segment estimates in each of the ten samples, and one sample's estimates against the benchmark."""
    p = load(f"{S01B}/out/part2_segments.json"); p.update(load(f"{S01B}/out/part2_segments_rerun.json"))
    reps = sorted(p, key=int); x = [int(r) + 1 for r in reps]
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.9), dpi=300, gridspec_kw=dict(width_ratios=[1.15, 1]))
    a = ax[0]
    a.vlines(x, [100 * p[r]["rmse"]["bayes"] for r in reps], [100 * p[r]["rmse"]["nopool"] for r in reps], color="#c9cfd6", lw=1.2)
    for k, name, col in (("cpool", "Overall effect", LIGHTBLUE), ("nopool", "Each segment", GREY), ("bayes", "Multilevel model", NAVY)):
        a.plot(x, [100 * p[r]["rmse"][k] for r in reps], color=col, marker="o", ls="none", ms=5, label=name)
    a.set_xticks(x); a.set_xlim(0.4, 10.6); a.set_ylim(0, 2.6); a.set_xlabel("2% sample"); a.set_ylabel("RMSE of segment effects (pp)")
    a.legend(loc="upper center", ncol=3, columnspacing=1.2, handletextpad=0.2); panel(a, "A", "Error in each sample")
    b = ax[1]; s = p[reps[0]]["seg"]; bench = [100 * v for v in s["bench"]]
    b.plot([-1, 9], [-1, 9], color=EDGE, lw=0.7, ls="--", label="Estimate = benchmark")
    b.scatter(bench, [100 * v for v in s["nopool"]], s=10, color=GREY, label="Each segment", lw=0)
    b.scatter(bench, [100 * v for v in s["bayes"]], s=10, color=NAVY, label="Multilevel model", lw=0)
    b.set_xlim(-1, 9); b.set_ylim(-3, 11); b.set_xlabel("Benchmark effect, other 98% of users (pp)"); b.set_ylabel("Estimate from the sample (pp)")
    b.legend(loc="upper left"); panel(b, "B", "Segment estimates, sample 1")
    fig.tight_layout(w_pad=2.0)
    save(fig, f"{S01B}/out/fig_segment_error.png")


def fig01d():
    """Error of segment effects by privacy budget, and incremental visits captured by budget and ranking."""
    pr = load(f"{S01D}/out/a_private_summary.json"); al = load(f"{S01D}/out/c_allocation.json")
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.9), dpi=300)
    eps = ["0.1", "0.5", "1.0", "5.0", "inf"]; xe = list(range(len(eps))); a = ax[0]
    a.plot(xe, [100 * pr["by_eps"][e]["rmse_nopool"] for e in eps], color=GREY, marker="o", label="Each segment")
    a.plot(xe, [100 * pr["by_eps"][e]["rmse_ml"] for e in eps], color=NAVY, marker="o", label="Multilevel model")
    a.axhline(100 * pr["nonprivate_nopool_rmse"], color=GREY, lw=0.9, ls="--", label="Each segment, no noise")
    a.set_yscale("log"); a.set_yticks([1, 2, 4, 8], ["1", "2", "4", "8"]); a.minorticks_off()
    a.set_xticks(xe, ["0.1", "0.5", "1", "5", "None"]); a.set_xlabel("Privacy budget (epsilon)"); a.set_ylabel("RMSE of segment effects (pp)")
    a.legend(loc="upper right"); panel(a, "A", "Error under privacy noise")
    b = ax[1]; bud = ["10", "20", "30"]; xb = [10, 20, 30]
    for k, name, col, ls in (("oracle", "True segment effects", INK, ":"), ("multilevel", "Lift, multilevel model", NAVY, "-"),
                             ("nopool", "Lift, each segment", GREY, "-"), ("response", "Response rate", ORANGE, "-")):
        b.plot(xb, [100 * al[q]["mean_share"][k] for q in bud], color=col, ls=ls, marker="o", label=name)
    b.plot(xb, [100 * al[q]["random"] for q in bud], color="#c9cfd6", lw=1.2, label="Random order")
    b.set_xticks(xb, ["10%", "20%", "30%"]); b.set_xlim(8, 32); b.set_ylim(0, 100)
    b.set_xlabel("Budget (share of users)"); b.set_ylabel("Incremental visits captured (%)")
    b.legend(loc="lower right", bbox_to_anchor=(1.0, 0.3), labelspacing=0.3); panel(b, "B", "Allocation by segment ranking")
    fig.tight_layout(w_pad=2.0)
    save(fig, f"{S01D}/out/fig_privacy_and_allocation.png")


def fig02a():
    """Outcomes credited by attribution against outcomes caused, and estimates of the effect of exposure."""
    at = load(f"{S02A}/out/attribution_vs_experiment.json"); inc = load(f"{S01A}/out/criteo/a_incrementality.json"); n1 = at["n_treated"]
    fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.9), dpi=300, gridspec_kw=dict(width_ratios=[0.75, 0.75, 1.5]))
    for a, key, name, letter in ((ax[0], "visit", "Visits", "A"), (ax[1], "conversion", "Conversions", "B")):
        r = at[key]; ci = 1.96 * inc[key]["itt"]["se"] * n1
        bars(a, ["Credited", "Caused"], [r["attributed"] / 1e3, r["incremental"] / 1e3], [0, ci / 1e3], [ORANGE, NAVY], lambda v: f"{1e3 * v:,.0f}")
        a.set_ylim(0, r["attributed"] / 1e3 * 1.42)
        bracket(a, 0, 1, r["attributed"] / 1e3 * 1.13, f"{100 * (r['attributed_over_incremental'] - 1):.0f}% more credited", color=ORANGE)
        a.set_ylabel("Thousands, ad arm"); panel(a, letter, name)
    pe = at["per_exposed_user_visit_effect"]
    est = [("Experiment, unadjusted", inc["cace_visit_unadjusted"]["est"], inc["cace_visit_unadjusted"]["se"], NAVY),
           ("Experiment, adjusted", inc["cace_visit_adjusted"]["est"], inc["cace_visit_adjusted"]["se"], NAVY),
           ("Exposed vs. unexposed", pe["naive"], pe["naive_se"], ORANGE), ("Regression adjustment", pe["ols_adjusted"], pe["ols_se"], BLUE),
           ("Double machine learning", pe["dml"], pe["dml_se"], BLUE)]
    c = ax[2]
    for i, (name, v, se, col) in enumerate(est):
        y = len(est) - 1 - i
        c.errorbar(100 * v, y, xerr=196 * se, color=col, marker="o", ms=4.5, lw=1.0)
        c.text(100 * v + 196 * se + 0.7, y, f"{100 * v:.1f}", va="center", fontsize=7.5)
    c.axhline(2.5, color="#bbbbbb", lw=0.6)
    c.set_yticks(range(len(est) - 1, -1, -1), [e[0] for e in est]); c.set_ylim(-0.6, len(est) - 0.4); c.set_xlim(18, 43); c.tick_params(axis="y", length=0)
    c.grid(axis="y", visible=False); c.grid(axis="x", visible=True)
    c.set_xlabel("Effect of exposure on visit rate (pp)"); panel(c, "C", "Effect of exposure")
    fig.tight_layout(w_pad=1.5)
    save(fig, f"{S02A}/out/fig_attributed_vs_incremental.png")


def fig02b():
    """Where each rule puts the credit: by how long before the last touch a touch occurred, and on clicked touches."""
    m = load(f"{S02B}/out/mta.json"); cr = m["credit_by_recency_bucket"]
    keys = ["last", "<1d", "1-7d", ">7d"]; names = ["Last touch", "< 1 day earlier", "1-7 days earlier", "> 7 days earlier"]
    rules = [("cr_last", "Last\ntouch"), ("cr_decay", "Time\ndecay"), ("cr_linear", "Linear"), ("cr_first", "First\ntouch")]
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.3), dpi=300, gridspec_kw=dict(width_ratios=[1.15, 1]))
    a = ax[0]
    for q, (rk, _) in enumerate(rules):
        base = 0.0
        for kk, col, nm in zip(keys, SHADES, names):
            v = 100 * cr[rk][kk]
            a.bar(q, v, bottom=base, color=col, width=0.6, label=nm if q == 0 else None)
            if v >= 9:
                a.text(q, base + v / 2, f"{v:.0f}", ha="center", va="center", fontsize=7, color="white" if col in SHADES[:2] else INK)
            base += v
    a.set_xticks(range(len(rules)), [r[1] for r in rules]); a.tick_params(axis="x", length=0); a.set_ylim(0, 100)
    a.set_ylabel("Share of conversion credit (%)"); a.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, columnspacing=1.2, handlelength=1.0)
    panel(a, "A", "Credit by timing of the touch")
    b = ax[1]; v = [100 * m["credit_on_clicked_touches"][rk] for rk, _ in rules]
    b.bar(range(len(rules)), v, color=NAVY, width=0.58)
    for q, u in enumerate(v):
        b.text(q, u / 2, f"{u:.0f}%", ha="center", va="center", fontsize=7.5, color="white")
    b.set_xticks(range(len(rules)), [r[1] for r in rules]); b.set_xlim(-0.6, len(rules) - 0.4); b.tick_params(axis="x", length=0)
    b.axhline(100 * m["share_touches_clicked"], color=ORANGE, lw=1.0, ls="--", label=f'Share of touches that were clicked ({100 * m["share_touches_clicked"]:.0f}%)')
    b.set_ylim(0, 100); b.set_ylabel("Share of credit on clicked touches (%)"); b.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2))
    panel(b, "B", "Credit on clicked touches")
    fig.tight_layout(w_pad=2.0)
    save(fig, f"{S02B}/out/fig_credit_by_rule.png")


def fig02c_recovery():
    """Estimated against known channel ROAS in the recovery test, weekly and daily data (logarithmic axes)."""
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.2), dpi=300)
    for a, suf, name, letter in ((ax[0], "", "Weekly data", "A"), (ax[1], "_daily", "Daily data", "B")):
        r = [u for u in rows(f"{S02C}/out/mmm_recovery{suf}.csv") if u["converged"] == "True"]
        rho = load(f"{S02C}/out/mmm_summary{suf}.json")["recovery"]["spearman"]
        a.plot([0.4, 5], [0.4, 5], color=EDGE, lw=0.7, ls="--", label="Estimate = known value")
        points(a, [float(u["true"]) for u in r], [float(u["est"]) for u in r], [float(u["lo"]) for u in r], [float(u["hi"]) for u in r],
               NAVY, label="Estimate, 90% interval", ms=3.6, ls="none", capsize=0, elinewidth=0.7)
        a.set_xscale("log"); a.set_yscale("log"); a.set_xlim(0.4, 5); a.set_ylim(0.03, 1000)
        a.set_xticks([0.5, 1, 2, 4], ["0.5", "1", "2", "4"]); a.set_yticks([0.1, 1, 10, 100, 1000], ["0.1", "1", "10", "100", "1,000"]); a.minorticks_off()
        a.set_xlabel("Known channel ROAS (simulated)"); a.set_ylabel("Estimated ROAS")
        panel(a, letter, f"{name} (rank correlation {rho:.2f})")
    h, l = ax[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=2, bbox_to_anchor=(0.5, 0.0), columnspacing=2.0)
    fig.tight_layout(w_pad=2.0, rect=(0, 0.07, 1, 1))
    save(fig, f"{S02C}/out/fig_roas_recovery.png")


def fig02c_detect():
    """Recovery error against the signal-to-noise index, and the smallest detectable ROAS on real spend."""
    det = rows(f"{S02C}/out/detectability.csv"); rr = [r for r in det if r["sim"] == "brand_shapes"]
    idx = {(r["org"], r["channel"]): float(r["index"]) for r in rr if r["freq"] == "D"}
    rec = [r for r in rows(f"{S02C}/out/mmm_pooled_recovery_daily.csv") if r["sim"] == "brand_shapes" and r["single_converged"] == "True"]
    s = load(f"{S02C}/out/detectability.json"); t1 = s["tests"]["T1"]
    px = [max(idx[(r["org"], r["channel"])], 0.06) for r in rec]
    py = [100 * abs(float(r["single"]) - float(r["true"])) / float(r["true"]) for r in rec]
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.9), dpi=300)
    a = ax[0]
    a.scatter([u for u in px if u < 2], [v for u, v in zip(px, py) if u < 2], s=12, color=GREY, label=f'Index < 2 (median error {100 * t1["index_below_2"]["median_err"]:.0f}%)')
    a.scatter([u for u in px if u >= 2], [v for u, v in zip(px, py) if u >= 2], s=12, color=NAVY, label=f'Index ≥ 2 (median error {100 * t1["index_2_or_more"]["median_err"]:.0f}%)')
    a.axvline(2, color=ORANGE, lw=1.0, ls="--"); a.axvspan(2, 60, color=NAVY, alpha=0.05, lw=0)
    a.set_xscale("log"); a.set_yscale("log"); a.set_xlim(0.02, 60); a.set_ylim(0.6, 4000)
    a.set_xticks([0.1, 1, 2, 10], ["0.1", "1", "2", "10"]); a.set_yticks([1, 10, 100, 1000], ["1", "10", "100", "1,000"]); a.minorticks_off()
    a.set_xlabel("Signal-to-noise index, computed before fitting"); a.set_ylabel("Absolute error of estimated ROAS (%)")
    a.legend(loc="lower left", handletextpad=0.1, borderaxespad=0.2, fontsize=7); panel(a, "A", "Daily data, held-out simulation")
    b = ax[1]
    for freq, name, col in (("W", "Weekly data", GREY), ("D", "Daily data", NAVY)):
        v = sorted(float(r["min_detectable_roas"]) for r in rr if r["freq"] == freq)
        share = s[freq]["real_spend"]["share_at_most"]["2"]
        b.step(v, [100 * (q + 1) / len(v) for q in range(len(v))], where="post", color=col, label=f"{name} ({100 * share:.0f}% at 2 or below)")
    b.axvline(2, color=ORANGE, lw=1.0, ls="--"); b.axvspan(0, 2, color=NAVY, alpha=0.05, lw=0)
    b.set_xlim(0, 16); b.set_ylim(0, 100); b.set_xlabel("Smallest detectable ROAS (80% power)"); b.set_ylabel("Cumulative share of brand-channels (%)")
    b.legend(loc="lower right"); panel(b, "B", "Real spend: smallest detectable ROAS")
    fig.tight_layout(w_pad=2.0)
    save(fig, f"{S02C}/out/fig_detectability.png")


def fig03a_power():
    """Share of resampled studies that detect the lift, and that report a lift when there is none, by users per arm."""
    d = load(f"{S03A}/out/lift_study_sizing.json"); k = d["studies_per_n"]; d = d["by_n"]; ns = sorted(d, key=int); x = list(range(len(ns)))
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.8), dpi=300)
    for a, keys, ref, name, letter in ((ax[0], ("power_z", "bayes_detect"), 80, "Power to detect a one-point lift", "A"),
                                       (ax[1], ("aa_false_positive_z", "aa_false_positive_bayes"), 5, "False positives with no true lift", "B")):
        for key, lab, col, off in zip(keys, ("z-test at 5%", "Bayesian, P(lift > 0) > 0.95"), (NAVY, BLUE), (-0.05, 0.05)):
            y = [100 * d[n][key] for n in ns]; h = [binom(d[n][key], k) for n in ns]
            a.errorbar([q + off for q in x], y, yerr=h, color=col, marker="o", lw=1.2, elinewidth=0.9, label=lab)
        a.axhline(ref, color=ORANGE, lw=1.0, ls="--", label="80% power" if ref == 80 else "Nominal 5%")
        a.set_xticks(x, [f"{int(n):,}" for n in ns]); a.set_xlabel("Users per arm"); panel(a, letter, name)
    ax[0].set_ylim(0, 105); ax[0].set_ylabel("Studies detecting the lift (%)"); ax[0].legend(loc="lower right")
    ax[1].set_ylim(0, 10); ax[1].set_ylabel("A/A studies reporting a lift (%)"); ax[1].legend(loc="upper right")
    fig.tight_layout(w_pad=2.0)
    save(fig, f"{S03A}/out/fig_power_by_sample_size.png")


def fig03a_mde():
    """Minimum detectable lift, and sampling variance of the adjusted readouts relative to the unadjusted one."""
    d = load(f"{S03A}/out/covariate_adjustment.json")["by_n"]; ns = sorted(d, key=int); x = list(range(len(ns)))
    series = (("D", "Unadjusted", GREY), ("L", "Adjusted, 12 features", BLUE), ("M", "Adjusted, model prediction", NAVY))
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.8), dpi=300)
    a = ax[0]
    for key, name, col in series:
        a.plot(x, [100 * d[n][key]["mde80"] for n in ns], color=col, marker="o", label=name)
    a.axhline(1, color=ORANGE, lw=1.0, ls="--", label="One-point lift")
    a.set_xticks(x, [f"{int(n):,}" for n in ns]); a.set_ylim(0, 3); a.set_xlabel("Users per arm"); a.set_ylabel("Minimum detectable lift (pp)")
    a.legend(loc="upper right"); panel(a, "A", "Minimum detectable lift")
    b = ax[1]
    b.axhline(1, color=GREY, lw=0.9, ls="--", label="Unadjusted")
    for (key, name, col), off in zip(series[1:], (-0.07, 0.07)):
        y = [d[n][key]["variance_ratio_to_D"] for n in ns]
        points(b, [q + off for q in x], y, [d[n][key]["variance_ratio_ci"][0] for n in ns], [d[n][key]["variance_ratio_ci"][1] for n in ns], col, label=name, ls="none")
    b.set_xticks(x, [f"{int(n):,}" for n in ns]); b.set_xlim(-0.5, len(ns) - 0.5); b.set_ylim(0.4, 1.1)
    b.set_xlabel("Users per arm"); b.set_ylabel("Variance relative to unadjusted"); b.legend(loc="lower right")
    panel(b, "B", "Sampling variance of the readout")
    fig.tight_layout(w_pad=2.0)
    save(fig, f"{S03A}/out/fig_mde_by_adjustment.png")


def fig03b():
    """Minimum detectable effect by number of metros and by test length, and false positives of the volume-weighted estimate."""
    tab = rows(f"{S03B}/out/design_summary.csv"); ri = rows(f"{S03B}/out/randomization_inference_check.csv")
    series = (("CR: year-over-year difference", "Year-over-year difference", GREY), ("MP: pair ANCOVA", "Matched pairs, adjusted", BLUE),
              ("CR: ANCOVA (CUPED)", "Regression-adjusted", NAVY))
    mde = {(r["estimator"], int(r["metros"]), int(r["test_months"])): float(r["mde_80_pct"]) for r in tab if r["mde_80_pct"]}
    xs = [20, 50, 100, 150]
    fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.9), dpi=300, gridspec_kw=dict(width_ratios=[1.15, 0.85, 1.1]))
    a = ax[0]
    for k, name, col in series:
        a.plot(xs, [mde[(k, m, 2)] for m in xs], color=col, marker="o", label=name)
    a.set_xticks(xs); a.set_ylim(0, 28); a.set_xlabel("Metros in the test"); a.set_ylabel("Minimum detectable effect (%)")
    a.legend(loc="upper right"); panel(a, "A", "By number of metros (two months)")
    b = ax[1]
    for k, name, col in series:
        b.plot([1, 2, 3], [mde[(k, 100, t)] for t in (1, 2, 3)], color=col, marker="o")
    b.set_xticks([1, 2, 3]); b.set_xlim(0.7, 3.3); b.set_ylim(0, 28); b.set_xlabel("Test length (months)"); b.set_ylabel("Minimum detectable effect (%)")
    panel(b, "B", "By test length (100 metros)")
    c = ax[2]; vw = {int(r["metros"]): r for r in ri if r["estimator"] == "CR: volume-weighted ANCOVA"}
    n_t = {int(r["metros"]): int(r["draws"]) for r in tab if r["estimator"] == "CR: volume-weighted ANCOVA" and r["test_months"] == "2"}
    q = list(range(len(xs)))
    y = [100 * float(vw[m]["false_positive_rate_t_test"]) for m in xs]
    c.errorbar([u - 0.06 for u in q], y, yerr=[binom(v / 100, n_t[m]) for v, m in zip(y, xs)], color=ORANGE, marker="o", lw=1.2, elinewidth=0.9, label="t-test")
    y = [100 * float(vw[m]["false_positive_rate"]) for m in xs]
    c.errorbar([u + 0.06 for u in q], y, yerr=[binom(v / 100, int(vw[m]["draws"])) for v, m in zip(y, xs)], color=NAVY, marker="o", lw=1.2, elinewidth=0.9, label="Randomization inference")
    c.axhline(5, color=GREY, lw=0.9, ls="--", label="Nominal 5%")
    c.set_xticks(q, [str(m) for m in xs]); c.set_xlim(-0.4, 3.4); c.set_ylim(0, 12); c.set_xlabel("Metros in the test"); c.set_ylabel("Placebo tests rejecting (%)")
    c.legend(loc="upper right"); panel(c, "C", "Volume-weighted estimate")
    fig.tight_layout(w_pad=1.4, rect=(0, 0.03, 1, 1)); footer(fig, ZILLOW)
    save(fig, f"{S03B}/out/fig1_mde_by_metros.png")


def fig03c():
    """Forecast error relative to a no-change forecast, by horizon, at the four levels of the hierarchy."""
    tab = rows(f"{S03C}/reports/tables/inventory_ets_by_horizon.csv")
    val = {(r["level"], r["method"], int(r["h"])): float(r["rel_to_no_change"]) for r in tab}; hs = list(range(1, 13))
    fig, ax = plt.subplots(1, 4, figsize=(7.2, 2.9), dpi=300, sharey=True)
    for a, lev, name, letter in zip(ax, ("US", "division", "state", "metro"), ("Nation", "Divisions", "States", "Metros"), "ABCD"):
        a.axhline(1, color=ORANGE, lw=1.0, ls="--", label="No-change forecast")
        for m, lab, col, ls in (("base", "Unreconciled", GREY, "-"), ("bu", "Bottom-up", BLUE, (0, (3, 2))), ("mint_shrink", "MinT-shrink", NAVY, "-")):
            a.plot(hs, [val[(lev, m, h)] for h in hs], color=col, ls=ls, label=lab)
        a.set_xticks([1, 3, 6, 9, 12]); a.set_ylim(0.3, 1.4); a.set_xlabel("Horizon (months)"); panel(a, letter, name)
    ax[0].set_ylabel("RMSSE relative to no-change")
    h, l = ax[0].get_legend_handles_labels()
    fig.legend(h[1:] + h[:1], l[1:] + l[:1], loc="lower center", ncol=4, bbox_to_anchor=(0.5, 0.035), columnspacing=1.6)
    fig.tight_layout(w_pad=1.2, rect=(0, 0.11, 1, 1)); footer(fig, ZILLOW)
    save(fig, f"{S03C}/reports/figures/relative_rmsse_by_horizon_inventory_ets.png")


def fig04_segments():
    """Rule segments: share of accounts against share of next-six-month sales, and mean sales per account."""
    seg = {s["segment"]: s for s in load(f"{S04}/out/12_ltv_segments.json")["rule_segments"]}
    rec = [("recent<=60d", "≤60"), ("61-120d", "61-120"), (">120d", ">120")]; tiers = [("high", "High value"), ("mid", "Mid value"), ("low", "Low value")]
    order = [(f"{r}|{t}", rl) for t, _ in tiers for r, rl in rec]; x = [q + q // 3 * 0.6 for q in range(9)]
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.0), dpi=300, gridspec_kw=dict(width_ratios=[1.1, 1]))
    a = ax[0]; w = 0.38
    for key, name, col, off in (("share_accounts", "Share of accounts", GREY, -w / 2), ("share_next6m_sales_existing", "Share of next-six-month sales", NAVY, w / 2)):
        v = [100 * seg[k][key] for k, _ in order]
        a.bar([u + off for u in x], v, width=w, color=col, label=name)
        for u, val in zip(x, v):
            a.text(u + off, val + 1.2, f"{val:.0f}", ha="center", va="bottom", fontsize=6.5)
    a.set_ylim(0, 85); a.set_ylabel("Percent"); a.legend(loc="upper right"); panel(a, "A", "Accounts and later sales")
    b = ax[1]
    m = [seg[k]["mean_next6m_sales"] for k, _ in order]
    points(b, x, m, [seg[k]["mean_ci_boot"][0] for k, _ in order], [seg[k]["mean_ci_boot"][1] for k, _ in order], NAVY, ls="none")
    b.set_yscale("log"); b.set_yticks([200, 500, 1000, 2000, 5000], ["200", "500", "1,000", "2,000", "5,000"]); b.minorticks_off(); b.set_ylim(120, 7000)
    b.set_ylabel("Mean next-six-month sales (GBP)"); panel(b, "B", "Sales per account")
    for q in (a, b):
        q.set_xticks(x, [rl for _, rl in order]); q.tick_params(axis="x", length=0, labelsize=6.2); q.set_xlim(x[0] - 0.6, x[-1] + 0.6)
        for g, (_, tl) in enumerate(tiers):
            q.text(x[3 * g + 1], -0.115, tl, transform=q.get_xaxis_transform(), ha="center", va="top", fontsize=7.5)
        q.set_xlabel("Days since last purchase, by value tier", labelpad=19)
    fig.tight_layout(w_pad=2.0)
    save(fig, f"{S04}/out/fig/fig5_segments.png")


def fig04_cohorts():
    """Monthly repeat-purchase rate of new-account cohorts."""
    c = load(f"{S04}/out/12_ltv_segments.json")["cohorts_new_accounts"]; cms = list(c["repeat_rate"]); ks = list(range(1, 12))
    grid = [[c["repeat_rate"][cm].get(str(k)) for k in ks] for cm in cms]
    fig, a = plt.subplots(figsize=(7.2, 2.9), dpi=300); a.set_label("heat")
    top = 100 * max(v for r in grid for v in r if v is not None)
    im = a.imshow([[float("nan") if v is None else 100 * v for v in r] for r in grid], aspect="auto", cmap=SEQ, vmin=0, vmax=top)
    for i, r in enumerate(grid):
        for j, v in enumerate(r):
            if v is not None:
                a.text(j, i, f"{100 * v:.0f}", ha="center", va="center", fontsize=7, color="white" if 100 * v > 0.55 * top else INK)
    a.set_xticks(range(len(ks)), ks); a.set_yticks(range(len(cms)), [f"{cm}  (n = {c['size'][cm]})" for cm in cms])
    a.set_xticks([u - 0.5 for u in range(1, len(ks))], minor=True); a.set_yticks([u - 0.5 for u in range(1, len(cms))], minor=True)
    a.grid(False); a.grid(which="minor", color="white", lw=1.2); a.tick_params(which="both", length=0)
    for side in a.spines.values():
        side.set_visible(False)
    a.set_xlabel("Months since first purchase"); a.set_ylabel("Month of first purchase")
    cb = fig.colorbar(im, ax=a, pad=0.02, aspect=18); cb.set_label("Accounts buying again (%)"); cb.outline.set_visible(False); cb.ax.tick_params(length=0)
    cb.ax.set_label("heat")
    fig.tight_layout()
    save(fig, f"{S04}/out/fig/fig6_cohort_retention.png")


def fig04_calibration():
    """Predicted against actual next-six-month sales by decile of the prediction."""
    r = load(f"{S04}/out/12_ltv_segments.json")
    fig, a = plt.subplots(figsize=(3.6, 2.9), dpi=300)
    top = max(d["actual"] for d in r["calib_BGNBD_GG"]) * 1.3
    a.plot([100, top], [100, top], color=EDGE, lw=0.7, ls="--", label="Predicted = actual")
    for k, name, col in (("calib_ML_lgbm_tweedie", "Gradient boosting", GREY), ("calib_BGNBD_GG", "Purchase model", NAVY)):
        a.plot([d["pred"] for d in r[k]], [d["actual"] for d in r[k]], color=col, marker="o", label=name)
    a.set_xscale("log"); a.set_yscale("log"); a.set_xticks([100, 1000, 10000], ["100", "1,000", "10,000"]); a.set_yticks([100, 1000, 10000], ["100", "1,000", "10,000"]); a.minorticks_off()
    a.set_xlabel("Mean predicted sales by decile (GBP)"); a.set_ylabel("Mean actual sales (GBP)"); a.legend(loc="upper left")
    fig.tight_layout()
    save(fig, f"{S04}/out/fig/fig4_ltv_calibration.png")


if __name__ == "__main__":
    style()
    for f in (fig01a, fig01b, fig01d, fig02a, fig02b, fig02c_recovery, fig02c_detect, fig03a_power, fig03a_mde, fig03b, fig03c,
              fig04_segments, fig04_cohorts, fig04_calibration):
        f()
