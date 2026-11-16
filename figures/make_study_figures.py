"""Result figures for studies 01, 02, 05, 06, 07 and 08, drawn from the committed result files.

Usage: python figures/make_study_figures.py   (writes one PNG into each study's out/ folder)
"""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from make_figure1 import T, style

ROOT = Path(__file__).resolve().parents[1]


def load(rel):
    return json.loads((ROOT / rel).read_text())


def rows(rel):
    with open(ROOT / rel) as f:
        return list(csv.DictReader(f))


def new(n, width=7.2, height=2.9):
    fig, axes = plt.subplots(1, n, figsize=(width, height), dpi=300)
    return fig, (axes if n > 1 else [axes])


def title(ax, letter, text):
    ax.set_title(f"{letter}   {text}" if letter else text, loc="left", fontsize=8.5, fontweight="bold", pad=8)


def save(fig, rel):
    fig.tight_layout(w_pad=2.2)
    fig.savefig(ROOT / rel, dpi=300)
    plt.close(fig)
    print("wrote", rel)


def fig01(t):
    """Visit and conversion rates by arm, with the regression-adjusted effect."""
    a = load("01_ad_incrementality/out/criteo/a_incrementality.json")
    fig, axes = new(2, height=2.7)
    for ax, key, name, letter in zip(axes, ("visit", "conversion"), ("Visit rate", "Conversion rate"), "ab"):
        itt, adj = a[key]["itt"], a[key]["aipw_linear"]
        c0 = 100 * itt["control_mean"]; c1 = c0 + 100 * itt["est"]
        bars = ax.bar(["Control", "Ad arm"], [c0, c1], color=[t["grey"], t["blue"]], width=0.55)
        ax.errorbar([1], [c1], yerr=[196 * itt["se"]], color=t["ink"], lw=0.9, capsize=0)
        for b, v in zip(bars, (c0, c1)):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.012 * c1, f"{v:.2f}%", ha="center", va="bottom")
        ax.text(0.03, 0.95, f"+{100 * itt['est']:.2f} pp unadjusted\n+{100 * adj['est']:.2f} pp regression-adjusted",
                transform=ax.transAxes, va="top", color=t["ink2"], fontsize=7)
        ax.set_ylim(0, c1 * 1.38); ax.set_ylabel(f"{name} (%)"); ax.tick_params(axis="x", length=0)
        title(ax, letter, name)
    save(fig, "01_ad_incrementality/out/fig_rates_by_arm.png")


def fig02(t):
    """Attributed against incremental outcomes."""
    a = load("02_attribution_metric_validation/out/attribution_vs_experiment.json")
    fig, axes = new(2, height=2.7)
    for ax, key, name, letter in zip(axes, ("visit", "conversion"), ("Visits", "Conversions"), "ab"):
        att, inc = a[key]["attributed"] / 1000, a[key]["incremental"] / 1000
        bars = ax.bar(["Credited by\nattribution", "Incremental\n(experiment)"], [att, inc],
                      color=[t["red"], t["blue"]], width=0.55)
        for b, v in zip(bars, (att, inc)):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.015 * att, f"{v:,.1f}K", ha="center", va="bottom")
        ax.text(0.97, 0.95, f"overstated by {100 * (att / inc - 1):.0f}%", transform=ax.transAxes, ha="right",
                va="top", color=t["ink2"], fontsize=7.5, fontweight="bold")
        ax.set_ylim(0, att * 1.3); ax.set_ylabel(f"{name} (thousands)"); ax.tick_params(axis="x", length=0)
        title(ax, letter, name)
    save(fig, "02_attribution_metric_validation/out/fig_attributed_vs_incremental.png")


def fig05(t):
    """Where each rule puts the credit, by how long before the last touch a touch occurred."""
    m = load("05_multi_touch_attribution/out/mta.json")
    rules = [("cr_last", "Last touch"), ("cr_linear", "Linear"), ("cr_decay", "Time decay"), ("cr_first", "First touch")]
    buckets = [("last", "Last touch", t["blue"]), ("<1d", "Under 1 day earlier", "#56B4E9"),
               ("1-7d", "1 to 7 days earlier", "#E69F00"), (">7d", "Over 7 days earlier", t["red"])]
    fig, axes = new(2, height=2.8)
    ax = axes[0]; left = [0.0] * len(rules)
    for key, name, col in buckets:
        vals = [100 * m["credit_by_recency_bucket"][r][key] for r, _ in rules]
        ax.barh([n for _, n in rules], vals, left=left, color=col, label=name, height=0.6)
        for i, (v, l) in enumerate(zip(vals, left)):
            if v >= 9:
                ax.text(l + v / 2, i, f"{v:.0f}", ha="center", va="center", color="white", fontsize=7)
        left = [l + v for l, v in zip(left, vals)]
    ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("Share of conversion credit (%)")
    ax.tick_params(axis="y", length=0)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.24), ncol=2, columnspacing=1.2, handlelength=1.1)
    title(ax, "a", "Credit by recency of the touch")
    ax = axes[1]
    vals = [100 * m["credit_on_clicked_touches"][r] for r, _ in rules]
    ax.barh([n for _, n in rules], vals, color=t["blue"], height=0.6)
    ax.axvline(100 * m["share_touches_clicked"], color=t["grey"], lw=0.8, ls=(0, (4, 3)))
    ax.text(100 * m["share_touches_clicked"] + 1.2, -0.62, f"{100 * m['share_touches_clicked']:.0f}% of touches were clicked",
            va="center", color=t["ink2"], fontsize=6.8)
    for i, v in enumerate(vals):
        ax.text(v + 1, i, f"{v:.0f}%", va="center")
    ax.set_ylim(3.5, -0.9); ax.set_xlim(0, 82); ax.set_xlabel("Share of credit on clicked touches (%)")
    ax.tick_params(axis="y", length=0)
    title(ax, "b", "Credit given to clicked touches")
    save(fig, "05_multi_touch_attribution/out/fig_credit_by_rule.png")


def fig06(t):
    """Parameter recovery: estimated against known channel ROAS, weekly and daily data."""
    fig, axes = new(2, height=3.0)
    for ax, suf, name, letter in zip(axes, ("", "_daily"), ("Weekly data", "Daily data"), "ab"):
        r = [x for x in rows(f"06_marketing_mix_modeling/out/mmm_recovery{suf}.csv") if x["converged"] == "True"]
        tr = [float(x["true"]) for x in r]; es = [float(x["est"]) for x in r]
        lo = [float(x["est"]) - float(x["lo"]) for x in r]; hi = [float(x["hi"]) - float(x["est"]) for x in r]
        ax.plot([0, 4.5], [0, 4.5], color=t["grey"], lw=0.8, ls=(0, (4, 3)))
        ax.errorbar(tr, es, yerr=[lo, hi], fmt="o", color=t["blue"], ms=3.2, elinewidth=0.6, alpha=0.85)
        rho = load(f"06_marketing_mix_modeling/out/mmm_summary{suf}.json")["recovery"]["spearman"]
        ax.text(0.04, 0.95, f"rank correlation {rho:.2f}", transform=ax.transAxes, va="top", fontweight="bold",
                bbox=dict(facecolor=t["bg"], edgecolor="none", pad=2.5), zorder=5)
        ax.set_xlim(0, 4.5); ax.set_ylim(0, 9); ax.set_xlabel("Known channel ROAS (simulated)")
        ax.set_ylabel("Estimated ROAS, 90% interval")
        title(ax, letter, name)
    save(fig, "06_marketing_mix_modeling/out/fig_roas_recovery.png")


def fig07(t):
    """Error of segment estimates by sample, and one sample's estimates against the benchmark."""
    p = load("07_bayesian_segment_effects/out/part2_segments.json")
    p.update(load("07_bayesian_segment_effects/out/part2_segments_rerun.json"))
    reps = sorted(p, key=int)
    fig, axes = new(2, height=3.0)
    ax = axes[0]
    for i, r in enumerate(reps):
        a, b = 100 * p[r]["rmse"]["nopool"], 100 * p[r]["rmse"]["bayes"]
        ax.plot([a, b], [i, i], color=t["grid"], lw=2, zorder=1)
        ax.scatter([a], [i], color=t["grey"], s=18, zorder=2, label="No pooling" if i == 0 else None)
        ax.scatter([b], [i], color=t["blue"], s=18, zorder=2, label="Multilevel" if i == 0 else None)
    ax.set_yticks(range(len(reps)), [str(int(r) + 1) for r in reps]); ax.invert_yaxis()
    ax.set_xlabel("RMSE of 100 segment effects (pp)"); ax.set_ylabel("2% sample"); ax.set_xlim(0.6, 1.3)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, columnspacing=1.6)
    ax.tick_params(axis="y", length=0)
    title(ax, "a", "Error against the benchmark")
    ax = axes[1]; s = p[reps[0]]["seg"]
    b = [100 * v for v in s["bench"]]
    ax.plot([-1, 9], [-1, 9], color=t["grey"], lw=0.8, ls=(0, (4, 3)))
    ax.scatter(b, [100 * v for v in s["nopool"]], color=t["grey"], s=9, alpha=0.7, label="No pooling", lw=0)
    ax.scatter(b, [100 * v for v in s["bayes"]], color=t["blue"], s=9, alpha=0.9, label="Multilevel", lw=0)
    ax.set_xlim(-1, 9); ax.set_ylim(-3, 11)
    ax.set_xlabel("Benchmark effect, other 98% of users (pp)"); ax.set_ylabel("Estimate from the 2% sample (pp)")
    ax.legend(loc="upper left")
    title(ax, "b", "Segment estimates, sample 1")
    save(fig, "07_bayesian_segment_effects/out/fig_segment_error.png")


def fig08(t):
    """Power and false-positive rate by users per arm."""
    d = load("08_lift_study_sizing/out/lift_study_sizing.json")["by_n"]
    ns = sorted(d, key=int); x = range(len(ns))
    fig, axes = new(2, height=2.8)
    ax = axes[0]
    ax.axhline(80, color=t["grey"], lw=0.8, ls=(0, (4, 3)))
    ax.text(len(ns) - 1, 81.5, "80% power", ha="right", color=t["ink2"], fontsize=7)
    ax.plot(x, [100 * d[n]["power_z"] for n in ns], color=t["blue"], marker="o", ms=3.8, label="z-test, 5%")
    ax.plot(x, [100 * d[n]["bayes_detect"] for n in ns], color=t["green"], marker="o", ms=3.8,
            label="Bayesian, P(lift > 0) > 0.95")
    for i, n in enumerate(ns):
        ax.text(i + 0.08, 100 * d[n]["power_z"] - 6, f"{100 * d[n]['power_z']:.0f}%", color=t["blue"], fontsize=7)
    ax.set_xticks(list(x), [f"{int(n):,}" for n in ns]); ax.set_ylim(0, 106); ax.set_xlim(-0.3, len(ns) - 0.55)
    ax.set_xlabel("Users per arm"); ax.set_ylabel("Studies detecting the lift (%)"); ax.legend(loc="lower right")
    title(ax, "a", "Power to detect a 1-point lift")
    ax = axes[1]
    ax.axhline(5, color=t["grey"], lw=0.8, ls=(0, (4, 3)))
    ax.plot(x, [100 * d[n]["aa_false_positive_z"] for n in ns], color=t["blue"], marker="o", ms=3.8, label="z-test")
    ax.plot(x, [100 * d[n]["aa_false_positive_bayes"] for n in ns], color=t["green"], marker="o", ms=3.8,
            label="Bayesian")
    ax.set_xticks(list(x), [f"{int(n):,}" for n in ns]); ax.set_ylim(0, 10)
    ax.set_xlabel("Users per arm"); ax.set_ylabel("A/A studies reporting a lift (%)"); ax.legend(loc="upper right")
    title(ax, "b", "False positives with no true lift")
    save(fig, "08_lift_study_sizing/out/fig_power_by_sample_size.png")


if __name__ == "__main__":
    style(T)
    for f in (fig01, fig02, fig05, fig06, fig07, fig08):
        f(T)
