"""Figure 1 of the README: one panel per step of the argument, in reading order, drawn from the result files.

a 01a experiment readout   b 02a attribution on the same users   c 02c when a marketing mix model can measure
d 03a size of the next test   e 04 the new-customer definition

Usage: python figures/make_figure1.py   (writes figures/figure1.png)
"""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
from matplotlib.colors import LinearSegmentedColormap

ROOT = Path(__file__).resolve().parents[1]
INK, INK2, AXIS = "#111111", "#5a5a5a", "#333333"
BLUE, RED, GREEN, GREY, SKY = "#0072B2", "#D55E00", "#009E73", "#9a9a9a", "#56B4E9"
SEQ = LinearSegmentedColormap.from_list("seq", ["#f6f1e4", "#8fd0c0", "#2b83ba", "#0b2a66"])
HERO = [0.075, 0.475, 0.385, 0.455]            # large left panel
X0, W = 0.60, 0.385                             # right column
B, C = [X0, 0.80, W, 0.105], [X0, 0.475, W, 0.20]
D, E = [0.075, 0.075, 0.385, 0.25], [X0, 0.075, W, 0.25]
S02A = "02_without_an_experiment/02a_attribution_metric_validation"
S02C = "02_without_an_experiment/02c_marketing_mix_modeling"
S03A = "03_planning_a_test/03a_lift_study_sizing"


def rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def style():
    plt.rcParams.update({
        "font.family": ["Arial", "Helvetica Neue", "DejaVu Sans"], "font.size": 7, "axes.labelsize": 7,
        "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "text.color": INK, "axes.labelcolor": INK,
        "axes.edgecolor": AXIS, "xtick.color": AXIS, "ytick.color": AXIS, "axes.linewidth": 0.5,
        "xtick.major.width": 0.5, "ytick.major.width": 0.5, "xtick.major.size": 2.2, "ytick.major.size": 2.2,
        "xtick.minor.size": 1.2, "ytick.minor.size": 1.2, "xtick.minor.width": 0.4, "ytick.minor.width": 0.4,
        "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": "white",
        "savefig.facecolor": "white"})


def detach(ax):
    """Axes drawn slightly away from the data, as in journal figures."""
    for side in ("left", "bottom"):
        ax.spines[side].set_position(("outward", 3))


def letter(fig, ax, s, title, x=0.497):
    box = ax.get_position()
    fig.text(x, box.y1 + 0.022, s, fontsize=8, fontweight="bold", va="baseline")
    fig.text(x + 0.016, box.y1 + 0.022, title, fontsize=7.5, va="baseline")


def leader(ax, xy, xytext, text, **kw):
    ax.annotate(text, xy=xy, xytext=xytext, fontsize=6.5, va="center",
                arrowprops=dict(arrowstyle="-", lw=0.5, color=AXIS, shrinkA=1.5, shrinkB=2), **kw)


def load(rel):
    return json.loads((ROOT / rel).read_text())


def draw():
    fig = plt.figure(figsize=(7.2, 6.4), dpi=300)

    # ---- a: realized ad effect by decile of predicted uplift, held-out users
    tg = load("01_with_an_experiment/01a_ad_incrementality/out/criteo/c_targeting.json")
    inc = load("01_with_an_experiment/01a_ad_incrementality/out/criteo/a_incrementality.json")
    cal, itt = tg["calibration_selected"], tg["test_overall_itt"]
    a = fig.add_axes(HERO)
    x = [r["decile"] for r in cal]
    y = [100 * r["realized"] for r in cal]
    se = [196 * r["se"] for r in cal]
    a.axhline(0, color=AXIS, lw=0.5)
    a.fill_between(x[:2], [0, 0], y[:2], color=BLUE, alpha=0.10, lw=0)
    a.fill_between(x, [v - s for v, s in zip(y, se)], [v + s for v, s in zip(y, se)], color=BLUE, alpha=0.22, lw=0)
    a.plot(x, [100 * r["predicted"] for r in cal], color=GREY, lw=0.9, marker="o", ms=3.2, mfc="white", mew=0.9)
    a.plot(x, y, color=BLUE, lw=1.4, marker="o", ms=3.8, mfc="white", mew=1.2)
    avg = 100 * itt["est"]
    a.axhline(avg, color=INK2, lw=0.6, ls=(0, (3, 3)))
    a.text(3.3, avg + 0.13, f"average effect {avg:.2f} pp", ha="left", fontsize=6.5, color=INK2)
    leader(a, (1, y[0]), (1.9, y[0] + 0.55), f"Top decile: +{y[0]:.1f} pp,\n{y[0] / avg:.1f}× the average", linespacing=1.15)
    leader(a, (1.55, 1.6), (2.7, 2.45),
           f'Top fifth of users:\n{100 * tg["test"]["t_learner"]["share_incremental_top20"]:.0f}% of incremental visits',
           linespacing=1.15)
    leader(a, (10, 100 * cal[-1]["predicted"]), (7.2, -0.75), "Predicted (T-learner)", ha="right")
    leader(a, (10, y[-1]), (8.9, 2.0), "Realized,\n95% interval", linespacing=1.15, ha="center")
    a.set_xticks(x); a.set_xlim(0.6, 10.4); a.set_ylim(-1.15, 7.3)
    a.set_xlabel("Decile of predicted uplift (1 = highest)"); a.set_ylabel("Effect of the ads on visit rate (pp)")
    detach(a)
    fig.text(0.012, 0.966, "a", fontsize=8, fontweight="bold", va="baseline")
    fig.text(0.028, 0.966, f'The ad effect is concentrated: {(itt["n1"] + itt["n0"]) / 1e6:.2f}M held-out users',
             fontsize=7.5, va="baseline")

    # inset: the experiment readout for all users, ad arm against control (control = 100)
    ins = a.inset_axes([0.40, 0.56, 0.58, 0.30])
    for i, (name, key) in enumerate((("Conversion rate", "conversion"), ("Visit rate", "visit"))):
        c0, est = inc[key]["itt"]["control_mean"], inc[key]["itt"]["est"]
        idx = 100 * (c0 + est) / c0
        ins.plot([100, idx], [i, i], color="#d9dde1", lw=2.6, solid_capstyle="round", zorder=1)
        ins.plot(100, i, marker="o", ms=4.2, mfc="white", mec=GREY, mew=1.0, zorder=2)
        ins.plot(idx, i, marker="o", ms=4.8, color=BLUE, zorder=3)
        ins.text(98, i + 0.36, f"{name}: {100 * c0:.2f}% → {100 * (c0 + est):.2f}%", fontsize=6.3, va="center")
        ins.text(idx + 3, i, f"+{idx - 100:.0f}%", fontsize=6.5, va="center", fontweight="bold")
    ins.set_xlim(96, 178); ins.set_ylim(-0.5, 1.75); ins.set_yticks([]); ins.set_xticks([100, 125, 150])
    ins.set_xlabel(f'Ad arm, control = 100 ({inc["n"] / 1e6:.1f}M users)', fontsize=6.3, labelpad=1.5)
    ins.tick_params(labelsize=6, length=1.8, pad=1.5); ins.spines["left"].set_visible(False); ins.set_facecolor("none")

    b, c, d, e = (fig.add_axes(v) for v in (B, C, D, E))

    # ---- b: outcomes credited by attribution against outcomes caused, same experiment (caused = 100)
    at = load(f"{S02A}/out/attribution_vs_experiment.json")
    for i, (name, key) in enumerate((("Visits", "visit"), ("Conversions", "conversion"))):
        r = at[key]
        idx = 100 * r["attributed_over_incremental"]
        b.plot([100, idx], [i, i], color="#f3d9c8", lw=2.6, solid_capstyle="round", zorder=1)
        b.plot(100, i, marker="o", ms=4.8, color=BLUE, zorder=3)
        b.plot(idx, i, marker="o", ms=4.8, color=RED, zorder=3)
        b.text(98, i + 0.37, f"{name}: {r['incremental']:,.0f} caused → {r['attributed']:,.0f} credited", fontsize=6.3, va="center")
        b.text(idx + 3, i, f"+{idx - 100:.0f}%", fontsize=6.5, va="center", fontweight="bold", color=RED)
    b.set_xlim(96, 186); b.set_ylim(-0.5, 1.8); b.set_yticks([]); b.set_xticks([100, 125, 150, 175])
    b.set_xlabel("Credited by exposure-based attribution, caused by the ads = 100", labelpad=2)
    b.spines["left"].set_visible(False); b.spines["bottom"].set_position(("outward", 3))
    letter(fig, b, "b", "Attribution credits more than the ads caused")

    # ---- c: error of a per-brand mix model against the signal-to-noise index, held-out daily simulation
    idx = {(r["org"], r["channel"]): float(r["index"]) for r in rows(ROOT / S02C / "out/detectability.csv")
           if r["freq"] == "D" and r["sim"] == "brand_shapes"}
    rec = [r for r in rows(ROOT / S02C / "out/mmm_pooled_recovery_daily.csv")
           if r["sim"] == "brand_shapes" and r["single_converged"] == "True"]
    t1 = load(f"{S02C}/out/detectability.json")["tests"]["T1"]
    x = [idx[(r["org"], r["channel"])] for r in rec]
    y = [100 * abs(float(r["single"]) - float(r["true"])) / float(r["true"]) for r in rec]
    c.axvspan(2, 60, color=BLUE, alpha=0.07, lw=0)
    c.axvline(2, color=INK2, lw=0.6, ls=(0, (3, 3)))
    c.scatter([u for u in x if u < 2], [v for u, v in zip(x, y) if u < 2], s=9, color=GREY, lw=0, zorder=3)
    c.scatter([u for u in x if u >= 2], [v for u, v in zip(x, y) if u >= 2], s=9, color=BLUE, lw=0, zorder=3)
    for grp, xs, col in ((t1["index_below_2"], (0.06, 2), GREY), (t1["index_2_or_more"], (2, 60), BLUE)):
        c.plot(xs, [100 * grp["median_err"]] * 2, color=col, lw=1.2, zorder=2)
    c.text(0.065, 100 * t1["index_below_2"]["median_err"] * 1.5, f'median error {100 * t1["index_below_2"]["median_err"]:.0f}%',
           fontsize=6.5, color=INK2)
    c.text(55, 100 * t1["index_2_or_more"]["median_err"] * 1.5, f'median error {100 * t1["index_2_or_more"]["median_err"]:.0f}%',
           fontsize=6.5, color=BLUE, ha="right", fontweight="bold")
    c.text(2.25, 1100, "measurable", fontsize=6.3, color=BLUE, va="center")
    c.set_xscale("log"); c.set_yscale("log"); c.set_xlim(0.06, 60); c.set_ylim(0.6, 2500)
    c.set_xticks([0.1, 1, 2, 10], ["0.1", "1", "2", "10"]); c.set_yticks([1, 10, 100, 1000], ["1", "10", "100", "1,000"])
    c.minorticks_off()
    c.set_xlabel("Signal-to-noise index of a brand-channel, computed before fitting", labelpad=2)
    c.set_ylabel("Error of estimated\nreturn (%)")
    detach(c); letter(fig, c, "c", "A marketing mix model measures a channel only with enough signal")

    # ---- d: smallest detectable lift by users per arm, unadjusted and adjusted readouts
    cov = load(f"{S03A}/out/covariate_adjustment.json")
    ns = sorted(int(k) for k in cov["by_n"])
    mde = {k: [100 * cov["by_n"][str(n)][k]["mde80"] for n in ns] for k in "DLM"}
    req = cov["required_n_one_point_lift"]
    d.fill_between(ns, mde["M"], mde["D"], color=BLUE, alpha=0.08, lw=0)
    d.axhline(1, color=INK2, lw=0.6, ls=(0, (3, 3)))
    for k, col, lw in (("D", GREY, 1.3), ("L", SKY, 0.9), ("M", BLUE, 1.3)):
        d.plot(ns, mde[k], color=col, lw=lw, marker="o", ms=3, mfc="white", mew=1.0)
    d.plot([req["D"], req["M"]], [1, 1], ls="none", marker="o", ms=3.6, color=INK, zorder=5)
    d.annotate("", xy=(req["M"] * 1.03, 0.84), xytext=(req["D"] * 0.97, 0.84),
               arrowprops=dict(arrowstyle="-|>", lw=0.5, color=INK2, mutation_scale=5))
    d.text((req["D"] * req["M"]) ** 0.5, 0.52, f'{100 * round(req["D"] / 100):,} → {100 * round(req["M"] / 100):,}\nusers per arm',
           fontsize=6.5, fontweight="bold", ha="center", va="center", linespacing=1.15)
    d.text(21500, 1.07, "one-point lift", fontsize=6.3, color=INK2, ha="right")
    leader(d, (ns[1], mde["D"][1]), (3900, 2.2), "Unadjusted")
    leader(d, (ns[1], mde["L"][1]), (1500, 0.75), "12 user features", ha="center")
    leader(d, (ns[0], mde["M"][0]), (1150, 1.45), "Model\nprediction", linespacing=1.15)
    d.set_xscale("log"); d.set_xlim(850, 23500); d.set_ylim(0, 3.0)
    d.set_xticks(ns, [f"{n:,}" for n in ns]); d.minorticks_off()
    d.set_xlabel("Users per arm", labelpad=2); d.set_ylabel("Smallest detectable lift\nin visit rate (pp)")
    detach(d); letter(fig, d, "d", "Covariate adjustment makes the next test smaller", x=0.012)

    # ---- e: monthly repeat-purchase rate of new-account cohorts
    co = load("04_customer_metrics_retention/out/12_ltv_segments.json")
    burn, co = co["burnin3_contamination"], co["cohorts_new_accounts"]
    cohorts, months = sorted(co["repeat_rate"]), list(range(1, 12))
    data = [[float("nan") if co["repeat_rate"][k].get(str(m)) is None else 100 * co["repeat_rate"][k][str(m)]
             for m in months] for k in cohorts]
    cmap = SEQ.copy(); cmap.set_bad("white")
    e.imshow(data, cmap=cmap, vmin=0, vmax=30, aspect="auto")
    for i, row in enumerate(data):
        for j, v in enumerate(row):
            if v == v:
                e.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=5.8, color="white" if v > 16 else INK)
    e.set_xticks(range(len(months)), months); e.set_yticks(range(len(cohorts)), cohorts); e.tick_params(length=0)
    for s in e.spines.values():
        s.set_visible(False)
    e.set_xticks([v - 0.5 for v in range(1, len(months))], minor=True)
    e.set_yticks([v - 0.5 for v in range(1, len(cohorts))], minor=True)
    e.grid(which="minor", color="white", lw=1.0); e.tick_params(which="minor", length=0)
    e.set_xlabel("Months since cohort entry; monthly repeat-purchase rate (%)", labelpad=2)
    e.text(10.4, 5.4, f'3-month look-back:\n{100 * burn["share"]:.0f}% of {burn["apparent_new"]:,} "new"\naccounts had bought\nin the prior year',
           ha="right", va="center", fontsize=6.3, linespacing=1.2, color=INK2)
    letter(fig, e, "e", "New-account cohorts under a 12-month look-back")
    return fig


if __name__ == "__main__":
    style()
    draw().savefig(Path(__file__).parent / "figure1.png", dpi=300)
