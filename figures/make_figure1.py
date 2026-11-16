"""Figure 1 of the README: one panel per study, drawn from the committed result files.

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
T = dict(bg="#ffffff", ink="#111111", ink2="#555555", axis="#333333", grid="#e6e6e6", band="#e9eff5",
         blue="#0072B2", red="#D55E00", green="#009E73", grey="#8c8c8c")
FIGSIZE = (7.2, 5.6)
X0, W, H = (0.115, 0.625), 0.355, 0.30          # two equal columns
Y0 = (0.60, 0.085)                              # two equal rows


def rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def style(t):
    plt.rcParams.update({
        "font.family": ["Arial", "Helvetica Neue", "DejaVu Sans"], "font.size": 7.5, "axes.labelsize": 7.5,
        "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
        "figure.facecolor": t["bg"], "axes.facecolor": t["bg"], "savefig.facecolor": t["bg"],
        "text.color": t["ink"], "axes.labelcolor": t["ink"], "axes.edgecolor": t["axis"],
        "xtick.color": t["axis"], "ytick.color": t["axis"], "axes.linewidth": 0.6,
        "xtick.major.width": 0.6, "ytick.major.width": 0.6, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
        "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 1.2, "legend.frameon": False})


def grid(fig):
    """Four axes of equal size on a 2 x 2 grid."""
    return [fig.add_axes([x, y, W, H]) for y in Y0 for x in X0]


def panel(fig, ax, letter, title, legend_rows=1):
    """Panel letter and bold title above the legend strip; the strip holds `legend_rows` rows in this figure row."""
    box = ax.get_position()
    y = box.y1 + (7 + 10.5 * legend_rows) / 72 / fig.get_figheight()
    fig.text(box.x0 - 0.105, y, letter, fontsize=11.5, fontweight="bold", va="bottom")
    fig.text(box.x0, y, title, fontsize=8.5, fontweight="bold", va="bottom")


def legend(ax, ncol, handles=None, labels=None):
    """Legend in a strip between the title and the axes, clear of the data."""
    args = (handles, labels) if handles is not None else ()
    return ax.legend(*args, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=ncol, borderaxespad=0.35, borderpad=0,
                     handlelength=1.3, handletextpad=0.5, columnspacing=1.4, labelspacing=0.35)


def load(rel):
    return json.loads((ROOT / rel).read_text())


def draw(t):
    fig = plt.figure(figsize=FIGSIZE, dpi=300)
    a, b, c, d = grid(fig)

    # a: realized uplift by decile of predicted uplift, held-out users
    tg = load("01_ad_incrementality/out/criteo/c_targeting.json")
    cal, itt = tg["calibration_selected"], tg["test_overall_itt"]
    x = [r["decile"] for r in cal]
    a.axhline(100 * itt["est"], color=t["grey"], lw=0.8, ls=(0, (4, 3)))
    a.text(10.4, 100 * itt["est"] + 0.2, f'average effect, {100 * itt["est"]:.2f} pp', ha="right", color=t["ink2"], fontsize=7)
    a.errorbar(x, [100 * r["realized"] for r in cal], yerr=[196 * r["se"] for r in cal], color=t["blue"], lw=1.2,
               marker="o", ms=3.6, capsize=0, elinewidth=0.9, label="Realized, 95% CI", zorder=3)
    a.plot(x, [100 * r["predicted"] for r in cal], color=t["grey"], lw=0.9, marker="o", ms=3.4, mfc=t["bg"],
           mew=0.9, label="Predicted (T-learner)", zorder=2)
    a.set_xticks(x); a.set_xlim(0.5, 10.5); a.set_ylim(-1.2, 7.2)
    a.set_xlabel("Decile of predicted uplift (1 = highest)"); a.set_ylabel("Effect on visit rate (pp)")
    legend(a, 2)
    panel(fig, a, "a", "Ad effect by decile of predicted uplift")

    # b: per-exposed-user effect, observational estimators against the experimental range
    at = load("02_attribution_metric_validation/out/attribution_vs_experiment.json")["per_exposed_user_visit_effect"]
    lo, hi = 100 * at["cace_adjusted_study_01"], 100 * at["cace_unadjusted"]
    b.axvspan(lo, hi, color=t["band"], lw=0)
    b.text((lo + hi) / 2, 2.62, "experimental range", ha="center", va="center", color=t["ink2"], fontsize=7)
    est = [("Naive difference", at["naive"], at["naive_se"], t["red"]),
           ("OLS + covariates", at["ols_adjusted"], at["ols_se"], t["blue"]),
           ("Double ML", at["dml"], at["dml_se"], t["blue"])]
    for i, (name, v, se, col) in enumerate(est):
        b.errorbar(100 * v, 2 - i, xerr=196 * se, color=col, marker="o", ms=5, capsize=0, elinewidth=1.0)
        b.text(100 * v + 0.9, 2 - i, f"{100 * v:.1f}", va="center")
    b.set_yticks([2, 1, 0], [e[0] for e in est]); b.set_ylim(-0.55, 2.95); b.set_xlim(18, 42)
    b.tick_params(axis="y", length=0)
    b.set_xlabel("Effect of exposure on visit rate (pp)")
    panel(fig, b, "b", "Attribution against the experiment")

    # c: minimum detectable effect by design
    series = {"CR: year-over-year difference": ("Year-over-year", t["grey"]),
              "CR: ANCOVA (CUPED)": ("Regression-adjusted", t["blue"])}
    mde = {k: {} for k in series}
    for r in rows(ROOT / "03_geo_experiment_design/out/design_summary.csv"):
        if r["test_months"] == "2" and r["estimator"] in mde:
            mde[r["estimator"]][int(r["metros"])] = float(r["mde_80_pct"])
    for k, (name, col) in series.items():
        xs = sorted(mde[k])
        c.plot(xs, [mde[k][m] for m in xs], color=col, marker="o", ms=3.6, lw=1.3 if "CUPED" in k else 1.0, label=name)
    yo, ad = mde["CR: year-over-year difference"][100], mde["CR: ANCOVA (CUPED)"][100]
    c.text(100, yo + 1.0, f"{yo:.1f}%", ha="center", va="bottom", color=t["ink2"])
    c.text(100, ad - 1.0, f"{ad:.1f}%", ha="center", va="top", fontweight="bold")
    c.set_xticks([20, 50, 100, 150]); c.set_xlim(12, 158); c.set_ylim(0, 24)
    c.set_xlabel("Metros in the test"); c.set_ylabel("Minimum detectable effect (%)")
    c.yaxis.grid(True, color=t["grid"], lw=0.5); c.set_axisbelow(True)
    legend(c, 2)
    panel(fig, c, "c", "Detectable effect of a 2-month market test")

    # d: monthly repeat-purchase rate of new-account cohorts
    co = load("04_customer_metrics_retention/out/12_ltv_segments.json")["cohorts_new_accounts"]
    cohorts, months = sorted(co["repeat_rate"]), list(range(1, 12))
    data = [[float("nan") if co["repeat_rate"][k].get(str(m)) is None else 100 * co["repeat_rate"][k][str(m)]
             for m in months] for k in cohorts]
    cmap = LinearSegmentedColormap.from_list("seq", ["#f4f8fb", t["blue"]]); cmap.set_bad(t["bg"])
    d.imshow(data, cmap=cmap, vmin=0, vmax=30, aspect="auto")
    for i, row in enumerate(data):
        for j, v in enumerate(row):
            if v == v:
                d.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=6.3, color=(t["bg"] if v > 17 else t["ink"]))
    d.set_xticks(range(len(months)), months); d.set_yticks(range(len(cohorts)), cohorts)
    d.tick_params(length=0)
    for s in d.spines.values():
        s.set_visible(False)
    d.set_xticks([x - 0.5 for x in range(1, len(months))], minor=True)
    d.set_yticks([y - 0.5 for y in range(1, len(cohorts))], minor=True)
    d.grid(which="minor", color=t["bg"], lw=1.2); d.tick_params(which="minor", length=0)
    d.set_xlabel("Months since first purchase"); d.set_ylabel("Cohort (month of first purchase)")
    panel(fig, d, "d", "Monthly repeat-purchase rate by cohort (%)")
    return fig


if __name__ == "__main__":
    style(T)
    fig = draw(T)
    fig.savefig(Path(__file__).parent / "figure1.png", dpi=300)
