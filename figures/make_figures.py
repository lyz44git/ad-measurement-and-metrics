"""Figures 1 to 6 of the README, drawn from the result files in the shared style (figures/figstyle.py).

Usage: python figures/make_figures.py   (writes figures/figure1.png to figure6.png)
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from figstyle import *  # noqa: E402,F401,F403


def figure1():
    """The experiment's result, and outcomes credited by a simple count against outcomes caused."""
    inc = load(f"{S01A}/out/criteo/a_incrementality.json"); at = load(f"{S02A}/out/attribution_vs_experiment.json")
    n1 = at["n_treated"]
    fig, ax = plt.subplots(1, 4, figsize=(7.2, 2.6), dpi=300)
    for a, key, name, letter in ((ax[0], "visit", "Visit rate", "A"), (ax[1], "conversion", "Conversion rate", "B")):
        r = inc[key]["itt"]; p0, p1 = r["control_mean"], r["control_mean"] + r["est"]
        se = [1.96 * 100 * (p * (1 - p) / n) ** 0.5 for p, n in ((p0, r["n0"]), (p1, r["n1"]))]
        bars(a, ["Control", "Ad arm"], [100 * p0, 100 * p1], se, [GREY, NAVY], lambda v: f"{v:.2f}%")
        a.set_ylim(0, 100 * p1 * 1.42); bracket(a, 0, 1, 100 * p1 * 1.13, f"+{100 * r['relative_lift']:.0f}%")
        a.set_ylabel("Percent of users"); panel(a, letter, name)
    for a, key, name, letter in ((ax[2], "conversion", "Conversions", "C"), (ax[3], "visit", "Visits", "D")):
        r = at[key]; ci = 1.96 * inc[key]["itt"]["se"] * n1
        bars(a, ["Credited", "Caused"], [r["attributed"] / 1e3, r["incremental"] / 1e3], [0, ci / 1e3], [ORANGE, NAVY], lambda v: f"{1e3 * v:,.0f}")
        a.set_ylim(0, r["attributed"] / 1e3 * 1.42)
        bracket(a, 0, 1, r["attributed"] / 1e3 * 1.13, f"{100 * (r['attributed_over_incremental'] - 1):.0f}% more credited", color=ORANGE)
        a.set_ylabel("Thousands, ad arm"); panel(a, letter, name)
    fig.tight_layout(w_pad=1.6)
    save(fig, "figures/figure1.png")


def figure2():
    """Who the ads moved, and segment-level estimates from a small sample."""
    fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.6), dpi=300, gridspec_kw=dict(width_ratios=[1.25, 1, 1.1]))
    tg = load(f"{S01A}/out/criteo/c_targeting.json"); cal = tg["calibration_selected"]
    a = ax[0]; x = [r["decile"] for r in cal]
    a.axhline(0, color="#444444", lw=0.6)
    a.axhline(100 * tg["test_overall_itt"]["est"], color=GREY, lw=0.9, ls="--", label="Average effect")
    y = [100 * r["realized"] for r in cal]; h = [196 * r["se"] for r in cal]
    a.fill_between(x, [u - v for u, v in zip(y, h)], [u + v for u, v in zip(y, h)], color=NAVY, alpha=0.18, lw=0)
    a.plot(x, y, color=NAVY, marker="o", label="Realized (band: 95% CI)")
    a.plot(x, [100 * r["predicted"] for r in cal], color=ORANGE, marker="o", ms=3.6, lw=1.0, label="Predicted by uplift model")
    a.set_xticks(x); a.set_xlabel("Decile of predicted uplift (1 = highest)"); a.set_ylabel("Effect on visit rate (pp)")
    a.legend(loc="upper right"); panel(a, "A", "Effect by decile of predicted uplift")

    p = load(f"{S01B}/out/part2_segments.json"); p.update(load(f"{S01B}/out/part2_segments_rerun.json"))
    names = [("cpool", "Overall\neffect"), ("nopool", "Each\nsegment"), ("bayes", "Multilevel\nmodel")]
    vals, errs = [], []
    for k, _ in names:
        v = [100 * p[r]["rmse"][k] for r in p]; m = sum(v) / len(v)
        sd = (sum((u - m) ** 2 for u in v) / (len(v) - 1)) ** 0.5
        vals.append(m); errs.append(1.96 * sd / len(v) ** 0.5)
    bars(ax[1], [n for _, n in names], vals, errs, [LIGHTBLUE, GREY, NAVY], lambda v: f"{v:.2f}")
    ax[1].set_ylabel("RMSE of segment effects (pp)"); panel(ax[1], "B", "Error of segment estimates")

    pr = load(f"{S01D}/out/a_private_summary.json"); eps = ["0.1", "0.5", "1.0", "5.0", "inf"]; xe = list(range(len(eps)))
    c = ax[2]
    c.plot(xe, [100 * pr["by_eps"][e]["rmse_nopool"] for e in eps], color=GREY, marker="o", label="Each segment")
    c.plot(xe, [100 * pr["by_eps"][e]["rmse_ml"] for e in eps], color=NAVY, marker="o", label="Multilevel model")
    c.axhline(100 * pr["nonprivate_nopool_rmse"], color=GREY, lw=0.9, ls="--", label="Each segment, no noise")
    c.set_yscale("log"); c.set_yticks([1, 2, 4, 8], ["1", "2", "4", "8"]); c.minorticks_off()
    c.set_xticks(xe, ["0.1", "0.5", "1", "5", "None"]); c.set_xlabel("Privacy budget (epsilon)"); c.set_ylabel("RMSE of segment effects (pp)")
    c.legend(loc="upper right"); panel(c, "C", "Error under privacy noise")
    fig.tight_layout(w_pad=1.4)
    save(fig, "figures/figure2.png")


def figure3():
    """Attribution without an experiment: estimates of the exposure effect, credit by rule, and the bidding test."""
    fig, ax = plt.subplots(1, 3, figsize=(7.2, 3.3), dpi=300, gridspec_kw=dict(width_ratios=[1.0, 1.1, 1.0]))
    pe = load(f"{S02A}/out/attribution_vs_experiment.json")["per_exposed_user_visit_effect"]
    cace = load(f"{S01A}/out/criteo/a_incrementality.json")
    est = [("Experiment,\nunadjusted", cace["cace_visit_unadjusted"]["est"], cace["cace_visit_unadjusted"]["se"], NAVY),
           ("Experiment,\nadjusted", cace["cace_visit_adjusted"]["est"], cace["cace_visit_adjusted"]["se"], NAVY),
           ("Exposed vs.\nunexposed", pe["naive"], pe["naive_se"], ORANGE), ("Regression\nadjustment", pe["ols_adjusted"], pe["ols_se"], BLUE),
           ("Double machine\nlearning", pe["dml"], pe["dml_se"], BLUE)]
    a = ax[0]
    for i, (name, v, se, col) in enumerate(est):
        y = len(est) - 1 - i
        a.errorbar(100 * v, y, xerr=196 * se, color=col, marker="o", ms=4.5, lw=1.0)
        a.text(100 * v + 196 * se + 0.9, y, f"{100 * v:.1f}", va="center", fontsize=7.5)
    a.axhline(2.5, color="#bbbbbb", lw=0.6)
    a.set_yticks(range(len(est) - 1, -1, -1), [e[0] for e in est]); a.set_ylim(-0.6, len(est) - 0.4); a.set_xlim(18, 43); a.tick_params(axis="y", length=0)
    a.grid(axis="y", visible=False); a.grid(axis="x", visible=True)
    a.set_xlabel("Effect of exposure on visit rate (pp)"); panel(a, "A", "Estimates of the exposure effect")

    cr = load(f"{S02B}/out/mta.json")["credit_by_recency_bucket"]
    keys = ["last", "<1d", "1-7d", ">7d"]; names = ["Last touch", "< 1 day earlier", "1-7 days earlier", "> 7 days earlier"]
    rules = [("cr_last", "Last\ntouch"), ("cr_decay", "Time\ndecay"), ("cr_linear", "Linear"), ("cr_first", "First\ntouch")]
    b = ax[1]
    for q, (rk, _) in enumerate(rules):
        left = 0.0
        for kk, col, nm in zip(keys, SHADES, names):
            v = 100 * cr[rk][kk]
            b.bar(q, v, bottom=left, color=col, width=0.6, label=nm if q == 0 else None)
            if v >= 12:
                b.text(q, left + v / 2, f"{v:.0f}", ha="center", va="center", fontsize=7, color="white" if col in SHADES[:2] else INK)
            left += v
    b.set_xticks(range(len(rules)), [r[1] for r in rules]); b.tick_params(axis="x", length=0); b.set_ylim(0, 100)
    b.set_ylabel("Share of conversion credit (%)"); b.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, columnspacing=1.2, handlelength=1.0)
    panel(b, "B", "Credit by attribution rule")

    bd = load(f"{S02D}/out/bidding.json")["budgets"]; c = ax[2]
    for rule, col, off, name in (("cr_last", GREY, -0.12, "Last-touch credit"), ("cr_decay", NAVY, 0.12, "Time-decay credit")):
        v = [[100 * u for u in bd[k]["cross_rule_loss"][rule]] for k in ("0.25", "0.5", "0.75")]
        c.errorbar([q + off for q in range(3)], [u[0] for u in v], yerr=[[u[0] - u[1] for u in v], [u[2] - u[0] for u in v]], color=col, marker="o", ls="none", lw=1.0, label=name)
    c.axhline(5, color=ORANGE, lw=1.0, ls="--", label="Pre-specified threshold"); c.axhline(0, color="#444444", lw=0.6)
    c.set_xticks(range(3), ["25%", "50%", "75%"]); c.set_xlim(-0.5, 2.5); c.set_ylim(-1, 10)
    c.set_xlabel("Budget (share of logged spend)"); c.set_ylabel("Credit lost with the other rule (%)")
    c.legend(loc="upper right"); panel(c, "C", "Bidding with the other rule")
    fig.tight_layout(w_pad=1.3)
    save(fig, "figures/figure3.png")


def figure4():
    """Marketing mix models: error against the signal-to-noise index, and the index by data frequency."""
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.7), dpi=300)
    rr = [r for r in rows(f"{S02C}/out/detectability.csv") if r["sim"] == "brand_shapes"]
    idx = {(r["org"], r["channel"]): float(r["index"]) for r in rr if r["freq"] == "D"}
    rec = [r for r in rows(f"{S02C}/out/mmm_pooled_recovery_daily.csv") if r["sim"] == "brand_shapes" and r["single_converged"] == "True"]
    t1 = load(f"{S02C}/out/detectability.json")["tests"]["T1"]
    px = [max(idx[(r["org"], r["channel"])], 0.06) for r in rec]
    py = [100 * abs(float(r["single"]) - float(r["true"])) / float(r["true"]) for r in rec]
    a = ax[0]
    a.scatter([u for u in px if u < 2], [v for u, v in zip(px, py) if u < 2], s=12, color=GREY, label=f'Index < 2 (median error {100 * t1["index_below_2"]["median_err"]:.0f}%)')
    a.scatter([u for u in px if u >= 2], [v for u, v in zip(px, py) if u >= 2], s=12, color=NAVY, label=f'Index ≥ 2 (median error {100 * t1["index_2_or_more"]["median_err"]:.0f}%)')
    a.axvline(2, color=ORANGE, lw=1.0, ls="--"); a.axvspan(2, 60, color=NAVY, alpha=0.05, lw=0)
    a.set_xscale("log"); a.set_yscale("log"); a.set_xlim(0.05, 60); a.set_ylim(0.6, 4000)
    a.set_xticks([0.1, 1, 2, 10], ["0.1", "1", "2", "10"]); a.set_yticks([1, 10, 100, 1000], ["1", "10", "100", "1,000"]); a.minorticks_off()
    a.set_xlabel("Signal-to-noise index"); a.set_ylabel("Absolute error of estimated ROAS (%)")
    a.legend(loc="upper right", handletextpad=0.2); panel(a, "A", "Recovery error and the signal-to-noise index")
    b = ax[1]
    for freq, name, col in (("W", "Weekly data", GREY), ("D", "Daily data", NAVY)):
        v = sorted(max(float(r["index"]), 0.05) for r in rr if r["freq"] == freq)
        share = 100 * sum(u >= 2 for u in v) / len(v)
        b.step(v, [100 * (q + 1) / len(v) for q in range(len(v))], where="post", color=col, label=f"{name} ({share:.0f}% at 2 or more)")
    b.axvline(2, color=ORANGE, lw=1.0, ls="--"); b.axvspan(2, 20, color=NAVY, alpha=0.05, lw=0)
    b.set_xscale("log"); b.set_xlim(0.05, 20); b.set_xticks([0.1, 1, 2, 10], ["0.1", "1", "2", "10"]); b.minorticks_off(); b.set_ylim(0, 100)
    b.set_xlabel("Signal-to-noise index"); b.set_ylabel("Cumulative share of brand-channels (%)")
    b.legend(loc="upper left"); panel(b, "B", "Distribution of the index")
    fig.tight_layout(w_pad=2.0)
    save(fig, "figures/figure4.png")


def figure5():
    """Planning a test: sample size with covariate adjustment, by endpoint, by market, and forecasts by level."""
    fig, ax = plt.subplots(2, 2, figsize=(7.2, 4.9), dpi=300)
    cov = load(f"{S03A}/out/covariate_adjustment.json"); ns = sorted(int(k) for k in cov["by_n"])
    a = ax[0, 0]
    for k, name, col in (("D", "Unadjusted", GREY), ("L", "Adjusted, 12 features", BLUE), ("M", "Adjusted, model prediction", NAVY)):
        a.plot(ns, [100 * cov["by_n"][str(n)][k]["mde80"] for n in ns], color=col, marker="o", label=name)
    a.axhline(1, color=ORANGE, lw=1.0, ls="--", label="One-point lift")
    a.set_xscale("log"); a.set_xticks(ns, [f"{n:,}" for n in ns]); a.minorticks_off(); a.set_ylim(0, 3)
    a.set_xlabel("Users per arm"); a.set_ylabel("Minimum detectable lift (pp)"); a.legend(loc="upper right")
    panel(a, "A", "Covariate adjustment")

    eff = load(f"{S01C}/out/readout.json")["effects"]; b = ax[0, 1]
    n = lambda p0, l: Z_POWER ** 2 * (p0 * (1 - p0) + p0 * (1 + l) * (1 - p0 * (1 + l))) / (p0 * l) ** 2
    ls = [0.05, 0.10, 0.25, 0.50]
    for key, name, col in (("conversion", "Conversion rate", NAVY), ("visit", "Visit rate", GREY)):
        p0 = eff[key]["control_rate"]
        b.plot([100 * l for l in ls], [n(p0, l) for l in ls], color=col, marker="o", label=f"{name} (control {100 * p0:.2f}%)")
    b.set_xscale("log"); b.set_yscale("log"); b.set_xticks([5, 10, 25, 50], ["5", "10", "25", "50"]); b.minorticks_off()
    b.set_yticks([1e3, 1e4, 1e5, 1e6], ["1,000", "10,000", "100,000", "1,000,000"]); b.set_ylim(1e3, 6e6)
    b.set_xlabel("Relative lift to detect (%)"); b.set_ylabel("Users per arm"); b.legend(loc="upper right")
    panel(b, "B", "Visit and conversion endpoints")

    keys = {"CR: year-over-year difference": ("Year-over-year difference", GREY), "CR: ANCOVA (CUPED)": ("Regression-adjusted", NAVY)}
    md = {k: {} for k in keys}
    for r in rows(f"{S03B}/out/design_summary.csv"):
        if r["estimator"] in keys and r["test_months"] == "2":
            md[r["estimator"]][int(r["metros"])] = float(r["mde_80_pct"])
    c = ax[1, 0]; xs = [20, 50, 100, 150]
    for k, (name, col) in keys.items():
        c.plot(xs, [md[k][m] for m in xs], color=col, marker="o", label=name)
    c.set_xticks(xs); c.set_ylim(0, 25); c.set_xlabel("Metros in the test"); c.set_ylabel("Minimum detectable effect (%)")
    c.legend(loc="upper right"); panel(c, "C", "Market-level tests (two months)")

    tab = rows(f"{S03C}/reports/tables/inventory_ets_headline.csv")
    inc = {r["level"]: 100 * float(r["incoherence_mean"]) for r in tab if r["method"] == "base" and r["incoherence_mean"]}
    bars(ax[1, 1], ["Nation vs.\ndivisions", "Divisions vs.\nstates", "States vs.\nmetros"], [inc["US"], inc["division"], inc["state"]], None,
         [NAVY, NAVY, NAVY], lambda v: f"{v:.1f}%")
    ax[1, 1].set_ylabel("Mean gap before reconciliation (%)"); panel(ax[1, 1], "D", "Forecasts across levels")
    fig.tight_layout(w_pad=2.0, h_pad=1.6)
    save(fig, "figures/figure5.png")


def figure6():
    """Customer counts and customer models."""
    seg = load(f"{S04}/out/12_ltv_segments.json"); ext = load(f"{S04}/out/14_ltv_extension.json")
    fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.6), dpi=300, gridspec_kw=dict(width_ratios=[0.8, 1, 1.25]))
    burn = seg["burnin3_contamination"]; n, old = burn["apparent_new"], burn["bought_in_prior_12m"]
    a = ax[0]
    a.bar(0, n - old, color=NAVY, width=0.5, label="No purchase in prior 12 months"); a.bar(0, old, bottom=n - old, color=ORANGE, width=0.5, label="Purchase in prior 12 months")
    a.text(0, (n - old) / 2, f"{n - old}", ha="center", va="center", color="white", fontsize=7.5)
    a.text(0, n - old + old / 2, f"{old} ({100 * old / n:.0f}%)", ha="center", va="center", color="white", fontsize=7.5)
    a.set_xticks([0], ["3-month look-back"]); a.tick_params(axis="x", length=0); a.set_xlim(-0.6, 0.6); a.set_ylim(0, 1150)
    a.set_ylabel("Accounts labeled new"); a.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=1)
    panel(a, "A", "New-customer definition")

    e2 = ext["E2"]; b = ax[1]
    v = [e2["auc_recency"], e2["auc_model"]]; ci = [e2["auc_recency_ci"], e2["auc_model_ci"]]
    b.errorbar([0, 1], v, yerr=[[v[i] - ci[i][0] for i in range(2)], [ci[i][1] - v[i] for i in range(2)]], color=NAVY, marker="o", ls="none", ms=5, lw=1.0)
    for i in range(2):
        b.text(i + 0.1, v[i], f"{v[i]:.2f}", va="center", fontsize=7.5)
    b.set_xticks([0, 1], ["Recency", "Purchase model"]); b.set_xlim(-0.5, 1.6); b.set_ylim(0.70, 0.84); b.tick_params(axis="x", length=0)
    b.set_ylabel("AUC, repeat purchase in 6 months"); panel(b, "B", "Ranking repeat buyers")

    e6, e12 = seg["eval"], ext["E1"]["eval"]; c = ax[2]
    for src, col, off, name in (((e6["BGNBD_GG"], e12["bgnbd_gg"]), NAVY, -0.1, "Purchase model"), ((e6["P0_last6m"], e12["past_sales"]), GREY, 0.1, "Past-sales rule")):
        y = [s["spearman"] for s in src]
        c.errorbar([q + off for q in range(2)], y, yerr=[[y[i] - src[i]["spearman_ci"][0] for i in range(2)], [src[i]["spearman_ci"][1] - y[i] for i in range(2)]],
                   color=col, marker="o", ls="none", ms=5, lw=1.0, label=name)
        for i in range(2):
            c.text(i + off + (0.07 if off > 0 else -0.07), y[i], f"{y[i]:.2f}", va="center", ha="left" if off > 0 else "right", fontsize=7.5)
    c.set_xticks([0, 1], ["6 months ahead", "12 months ahead"]); c.set_xlim(-0.6, 1.6); c.set_ylim(0.54, 0.70); c.tick_params(axis="x", length=0)
    c.set_ylabel("Rank correlation with actual sales"); c.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2)
    panel(c, "C", "Ranking future sales")
    fig.tight_layout(w_pad=1.5)
    save(fig, "figures/figure6.png")


if __name__ == "__main__":
    style()
    for f in (figure1, figure2, figure3, figure4, figure5, figure6):
        f()
