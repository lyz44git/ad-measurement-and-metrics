"""Figure 1 of the README: one panel per step of the argument, in reading order, drawn from the result files.

a 01a  what the randomized experiment measured
b 02a  what exposure-based attribution credits on the same experiment
c 02c  when a marketing mix model can measure a channel (simulation on real spend)
d 03a  how large the next user-level test must be
e 04   how the "new customer" count depends on its definition

Usage: python figures/make_figure1.py   (writes figures/figure1.png)
"""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
INK, INK2, AXIS = "#111111", "#5a5a5a", "#333333"
BLUE, RED, GREY, LIGHT = "#0072B2", "#D55E00", "#9a9a9a", "#d9dde1"

S01A = "01_with_an_experiment/01a_ad_incrementality"
S02A = "02_without_an_experiment/02a_attribution_metric_validation"
S02C = "02_without_an_experiment/02c_marketing_mix_modeling"
S03A = "03_planning_a_test/03a_lift_study_sizing"
S04 = "04_customer_metrics_retention"

TOP, BOT, H_TOP, H_BOT = 0.575, 0.125, 0.29, 0.25
PANELS = {"a": [0.105, TOP, 0.36, H_TOP], "b": [0.625, TOP, 0.355, H_TOP],
          "c": [0.145, BOT, 0.18, H_BOT], "d": [0.435, BOT, 0.215, H_BOT], "e": [0.775, BOT, 0.205, H_BOT]}
TITLES = {"a": "Experiment: what the ads caused", "b": "Attribution on the same users",
          "c": "Marketing mix model: when it can measure", "d": "Next test: users needed per arm",
          "e": "Metric definition: who counts as new"}
STUDY = {"a": "01a", "b": "02a", "c": "02c", "d": "03a", "e": "04"}


def style():
    plt.rcParams.update({
        "font.family": ["Arial", "Helvetica Neue", "DejaVu Sans"], "font.size": 7, "axes.labelsize": 7,
        "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "text.color": INK, "axes.labelcolor": INK,
        "axes.edgecolor": AXIS, "xtick.color": AXIS, "ytick.color": AXIS, "axes.linewidth": 0.5,
        "xtick.major.width": 0.5, "ytick.major.width": 0.5, "xtick.major.size": 2.2, "ytick.major.size": 2.2,
        "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": "white",
        "savefig.facecolor": "white"})


def load(rel):
    return json.loads((ROOT / rel).read_text())


def header(fig, ax, k, x_shift=0.0):
    """Panel letter, title and the study it comes from, above the axes."""
    box = ax.get_position()
    x = PANELS[k][0] - 0.095 + x_shift
    fig.text(x, box.y1 + 0.075, k, fontsize=8, fontweight="bold", va="baseline")
    fig.text(x + 0.018, box.y1 + 0.075, TITLES[k], fontsize=7.5, va="baseline")
    fig.text(x + 0.018, box.y1 + 0.045, f"study {STUDY[k]}", fontsize=6.3, color=INK2, va="baseline")


def hbars(ax, labels, values, colors, fmt, xmax):
    y = list(range(len(values)))[::-1]
    ax.barh(y, values, color=colors, height=0.58, lw=0)
    for yy, v in zip(y, values):
        ax.text(v + xmax * 0.015, yy, fmt(v), va="center", fontsize=6.5)
    ax.set_yticks(y, labels); ax.tick_params(axis="y", length=0)
    ax.set_xlim(0, xmax); ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_position(("outward", 3))
    return y


def draw():
    fig = plt.figure(figsize=(7.2, 4.7), dpi=300)
    ax = {k: fig.add_axes(v) for k, v in PANELS.items()}

    # ---- a: the experiment readout, ad arm against control (control = 100), with 95% intervals
    inc = load(f"{S01A}/out/criteo/a_incrementality.json")
    a = ax["a"]
    for i, (name, key) in enumerate((("Conversion rate", "conversion"), ("Visit rate", "visit"))):
        r = inc[key]["itt"]
        c0, est, se = r["control_mean"], r["est"], r["se"]
        idx, half = 100 * (c0 + est) / c0, 100 * 1.96 * se / c0
        a.plot([100, idx], [i, i], color=LIGHT, lw=3.0, solid_capstyle="round", zorder=1)
        a.plot([idx - half, idx + half], [i, i], color=BLUE, lw=0.9, zorder=2)
        a.plot(100, i, marker="o", ms=4.6, mfc="white", mec=GREY, mew=1.0, zorder=3)
        a.plot(idx, i, marker="o", ms=5.2, color=BLUE, zorder=4)
        a.text(99, i + 0.34, f"{name}: {100 * c0:.2f}% → {100 * (c0 + est):.2f}%", fontsize=6.5, va="center")
        a.text(idx + half + 2.5, i, f"+{idx - 100:.0f}%", fontsize=6.8, va="center", fontweight="bold")
    a.set_xlim(95, 178); a.set_ylim(-0.5, 1.75); a.set_yticks([]); a.set_xticks([100, 125, 150, 175])
    a.set_xlabel(f'Ad arm against control (control = 100), {inc["n"] / 1e6:.1f}M randomized users', labelpad=2)
    a.spines["left"].set_visible(False); a.spines["bottom"].set_position(("outward", 3))
    header(fig, a, "a")

    # ---- b: conversions credited by attribution against conversions caused, same experiment
    at = load(f"{S02A}/out/attribution_vs_experiment.json")["conversion"]
    b = ax["b"]
    vals = [at["attributed"], at["incremental"]]
    hbars(b, ["Credited by exposure-\nbased attribution", "Caused by the ads\n(experiment)"], vals, [RED, BLUE],
          lambda v: f"{v:,.0f}", 30000)
    b.text(vals[0] + 4200, 1, f"+{100 * (at['attributed_over_incremental'] - 1):.0f}%", va="center", fontsize=6.8,
           fontweight="bold", color=RED)
    b.set_xticks([0, 10000, 20000, 30000], ["0", "10,000", "20,000", "30,000"])
    b.set_xlabel("Conversions in the ad arm", labelpad=2)
    header(fig, b, "b", x_shift=-0.02)

    # ---- c: recovery error of a per-brand model by signal-to-noise index, held-out daily simulation
    t1 = load(f"{S02C}/out/detectability.json")["tests"]["T1"]
    hi, lo = t1["index_2_or_more"], t1["index_below_2"]
    c = ax["c"]
    hbars(c, [f"Index 2 or more\n({hi['n']} brand-channels)", f"Index below 2\n({lo['n']})"],
          [100 * hi["median_err"], 100 * lo["median_err"]], [BLUE, GREY], lambda v: f"{v:.0f}%", 62)
    share = {}
    with open(ROOT / S02C / "out/detectability.csv") as f:
        for r in csv.DictReader(f):
            if r["sim"] == "brand_shapes":
                share.setdefault(r["freq"], []).append(float(r["index"]) >= 2)
    w, d = (100 * sum(share[k]) / len(share[k]) for k in ("W", "D"))
    c.set_xlabel("Median error of the channel's\nestimated return", labelpad=2)
    c.set_ylim(-0.6, 2.05)
    c.text(62, 1.95, f"Index 2 or more: {w:.0f}% of\nbrand-channels weekly, {d:.0f}% daily", ha="right", va="top",
           fontsize=6.2, color=INK2, linespacing=1.15)
    header(fig, c, "c", x_shift=-0.04)

    # ---- d: users per arm for a one-point lift at 80% power
    req = load(f"{S03A}/out/covariate_adjustment.json")["required_n_one_point_lift"]
    dd = ax["d"]
    vals = [req["D"], req["L"], req["M"]]
    hbars(dd, ["Unadjusted", "12 user features", "Model prediction"], vals, [GREY, BLUE, BLUE],
          lambda v: f"{100 * round(v / 100):,.0f}", 8200)
    dd.text(vals[2] + 1500, 0, f"−{100 * (1 - vals[2] / vals[0]):.0f}%", va="center", fontsize=6.8,
            fontweight="bold", color=BLUE)
    dd.set_xticks([0, 4000, 8000], ["0", "4,000", "8,000"])
    dd.set_xlabel("Users per arm, one-point lift\nin visit rate, 80% power", labelpad=2)
    header(fig, dd, "d")

    # ---- e: accounts a 3-month look-back labels new, split by purchase in the prior 12 months
    burn = load(f"{S04}/out/12_ltv_segments.json")["burnin3_contamination"]
    n, old = burn["apparent_new"], round(burn["apparent_new"] * burn["share"])
    e = ax["e"]
    e.barh([0], [n - old], color=BLUE, height=0.5, lw=0)
    e.barh([0], [old], left=[n - old], color=RED, height=0.5, lw=0)
    e.text((n - old) / 2, 0, f"{n - old}", ha="center", va="center", fontsize=6.5, color="white")
    e.text(n - old + old / 2, 0, f"{old} ({100 * old / n:.0f}%)", ha="center", va="center", fontsize=6.5, color="white")
    e.text(0, 0.52, "no purchase in the prior 12 months", fontsize=6.2, color=BLUE, va="bottom")
    e.text(n, -0.52, "bought in the prior 12 months", fontsize=6.2, color=RED, va="top", ha="right")
    e.set_xlim(0, n * 1.02); e.set_ylim(-1.0, 1.0); e.set_yticks([]); e.set_xticks([0, 500, 1000], ["0", "500", "1,000"])
    e.spines["left"].set_visible(False); e.spines["bottom"].set_position(("outward", 3))
    e.set_xlabel(f'Accounts labeled new under a\n3-month look-back ({n:,})', labelpad=2)
    header(fig, e, "e")
    return fig


if __name__ == "__main__":
    style()
    draw().savefig(Path(__file__).parent / "figure1.png", dpi=300)
