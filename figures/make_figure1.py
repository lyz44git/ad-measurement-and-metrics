"""Figure 1 of the README: the experiment readout with three supporting panels, drawn from the result files.

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
HERO = [0.075, 0.095, 0.385, 0.815]             # large left panel
X0, W, H, ROWS = 0.60, 0.385, 0.20, (0.735, 0.41, 0.085)   # three stacked panels on the right


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
    fig = plt.figure(figsize=(7.2, 5.0), dpi=300)

    # ---- a: realized ad effect by decile of predicted uplift, held-out users
    tg = load("01_ad_incrementality/out/criteo/c_targeting.json")
    inc = load("01_ad_incrementality/out/criteo/a_incrementality.json")
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
    fig.text(0.012, 0.957, "a", fontsize=8, fontweight="bold", va="baseline")
    fig.text(0.028, 0.957, f'The ad effect is concentrated: {(itt["n1"] + itt["n0"]) / 1e6:.2f}M held-out users',
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

    b, c, d = (fig.add_axes([X0, yy, W, H]) for yy in ROWS)

    # ---- b: effect of exposure, observational estimators against the two experimental estimates
    at = load("02_attribution_metric_validation/out/attribution_vs_experiment.json")
    pe = at["per_exposed_user_visit_effect"]
    lo, hi = 100 * pe["cace_adjusted_study_01"], 100 * pe["cace_unadjusted"]
    b.axvspan(lo, hi, color=BLUE, alpha=0.10, lw=0)
    b.text((lo + hi) / 2, 2.62, "two experimental\nestimates", ha="center", va="center", fontsize=6.5, color=INK2,
           linespacing=1.05)
    est = [("Naive difference", pe["naive"], RED), ("OLS + covariates", pe["ols_adjusted"], BLUE),
           ("Double ML", pe["dml"], BLUE)]
    for i, (name, v, col) in enumerate(est):
        b.plot(100 * v, 2 - i, marker="o", ms=5, color=col)
        b.text(100 * v + 0.8, 2 - i, f"{100 * v:.1f}", va="center", fontsize=6.5, fontweight="bold" if i == 0 else "normal")
    b.annotate("", xy=(hi + 0.3, 2), xytext=(100 * pe["naive"] - 0.7, 2),
               arrowprops=dict(arrowstyle="<|-|>", lw=0.5, color=INK2, mutation_scale=5))
    b.text((hi + 100 * pe["naive"]) / 2, 2.3, "overstatement", ha="center", fontsize=6.3, color=INK2)
    b.set_yticks([2, 1, 0], [e[0] for e in est]); b.tick_params(axis="y", length=0)
    b.set_ylim(-0.55, 3.05); b.set_xlim(19, 41.5); b.set_xticks([20, 25, 30, 35, 40])
    b.set_xlabel("Effect of exposure on visit rate (pp)", labelpad=2)
    b.spines["left"].set_visible(False); b.spines["bottom"].set_position(("outward", 3))
    over = 100 * (at["conversion"]["attributed_over_incremental"] - 1)
    letter(fig, b, "b", f"Attribution overstates: {over:.0f}% more conversions than the experiment")

    # ---- c: minimum detectable effect by design and test length
    keys = {"CR: year-over-year difference": ("Year-over-year", GREY), "CR: ANCOVA (CUPED)": ("Regression-adjusted", BLUE)}
    mde = {(k, m): {} for k in keys for m in (1, 2, 3)}
    for r in rows(ROOT / "03_geo_experiment_design/out/design_summary.csv"):
        if r["estimator"] in keys:
            mde[(r["estimator"], int(r["test_months"]))][int(r["metros"])] = float(r["mde_80_pct"])
    xs = [20, 50, 100, 150]
    yo, ad = mde[("CR: year-over-year difference", 2)], mde[("CR: ANCOVA (CUPED)", 2)]
    c.fill_between(xs, [ad[m] for m in xs], [yo[m] for m in xs], color=BLUE, alpha=0.08, lw=0)
    for k, (name, col) in keys.items():
        for months in (1, 3):
            c.plot(xs, [mde[(k, months)][m] for m in xs], color=col, lw=0.6, alpha=0.55)
        c.plot(xs, [mde[(k, 2)][m] for m in xs], color=col, lw=1.3, marker="o", ms=3, mfc="white", mew=1.0)
        c.text(152, mde[(k, 2)][150] + (3.9 if col == GREY else -2.6), name, fontsize=6.5, va="center", ha="right")
    c.text(100, yo[100] + 4.6, f"{yo[100]:.1f}% → {ad[100]:.1f}%\nat 100 metros", fontsize=6.5, fontweight="bold", ha="center", linespacing=1.15)
    c.text(22, 2.4, "thin lines: 1- and 3-month tests", fontsize=6.3, color=INK2)
    c.set_xticks(xs); c.set_xlim(14, 156); c.set_ylim(0, 27); c.set_yticks([5, 15, 25])
    c.set_xlabel("Metros in the test", labelpad=2); c.set_ylabel("Detectable\neffect (%)")
    detach(c); letter(fig, c, "c", "Regression adjustment shrinks the detectable effect of a market test")

    # ---- d: monthly repeat-purchase rate of new-account cohorts
    co = load("04_customer_metrics_retention/out/12_ltv_segments.json")
    burn, co = co["burnin3_contamination"], co["cohorts_new_accounts"]
    cohorts, months = sorted(co["repeat_rate"]), list(range(1, 12))
    data = [[float("nan") if co["repeat_rate"][k].get(str(m)) is None else 100 * co["repeat_rate"][k][str(m)]
             for m in months] for k in cohorts]
    cmap = SEQ.copy(); cmap.set_bad("white")
    d.imshow(data, cmap=cmap, vmin=0, vmax=30, aspect="auto")
    for i, row in enumerate(data):
        for j, v in enumerate(row):
            if v == v:
                d.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=5.8, color="white" if v > 16 else INK)
    d.set_xticks(range(len(months)), months); d.set_yticks(range(len(cohorts)), cohorts); d.tick_params(length=0)
    for s in d.spines.values():
        s.set_visible(False)
    d.set_xticks([v - 0.5 for v in range(1, len(months))], minor=True)
    d.set_yticks([v - 0.5 for v in range(1, len(cohorts))], minor=True)
    d.grid(which="minor", color="white", lw=1.0); d.tick_params(which="minor", length=0)
    d.set_xlabel("Months since first purchase; monthly repeat-purchase rate (%)", labelpad=2)
    d.text(10.4, 5.4, f'3-month look-back:\n{100 * burn["share"]:.0f}% of {burn["apparent_new"]:,} "new"\naccounts had bought\nin the prior year',
           ha="right", va="center", fontsize=6.3, linespacing=1.2, color=INK2)
    letter(fig, d, "d", "New-account cohorts under a 12-month look-back")
    return fig


if __name__ == "__main__":
    style()
    draw().savefig(Path(__file__).parent / "figure1.png", dpi=300)
