"""Style shared by every figure of the repository: palette, fonts, and a few helpers.

The figures use standard chart types with descriptive panel titles; explanations go in the notes under each figure.
"""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

ROOT = Path(__file__).resolve().parents[1]
G1, G2, G3 = "01_with_an_experiment/", "02_without_an_experiment/", "03_planning_a_test/"
S01A, S01B, S01C, S01D = G1 + "01a_ad_incrementality", G1 + "01b_bayesian_segment_effects", G1 + "01c_sql_metric_readout", G1 + "01d_private_segment_effects"
S02A, S02B, S02C, S02D = G2 + "02a_attribution_metric_validation", G2 + "02b_multi_touch_attribution", G2 + "02c_marketing_mix_modeling", G2 + "02d_attribution_and_bidding"
S03A, S03B, S03C, S04 = G3 + "03a_lift_study_sizing", G3 + "03b_geo_experiment_design", G3 + "03c_hierarchical_forecasting", "04_customer_metrics_retention"
NAVY, BLUE, LIGHTBLUE, GREY, ORANGE, INK = "#1f3b5c", "#3f78b0", "#a9c4de", "#9aa3ad", "#e07b39", "#222222"
SHADES = ["#1f3b5c", "#3f78b0", "#a9c4de", "#dfe6ee"]
SEQ = LinearSegmentedColormap.from_list("seq", ["#f3f6fa", "#a9c4de", "#3f78b0", "#1f3b5c"])
Z_POWER = 1.959964 + 0.841621


def style():
    plt.rcParams.update({
        "font.family": ["Arial", "Helvetica Neue", "DejaVu Sans"], "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8.5,
        "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7.5, "legend.frameon": False,
        "text.color": INK, "axes.labelcolor": INK, "axes.edgecolor": "#444444", "xtick.color": "#444444", "ytick.color": "#444444",
        "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6, "xtick.major.size": 3, "ytick.major.size": 3,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "axes.grid.axis": "y", "grid.color": "#e6e6e6",
        "grid.linewidth": 0.6, "axes.axisbelow": True, "figure.facecolor": "white", "savefig.facecolor": "white",
        "errorbar.capsize": 2.5, "lines.linewidth": 1.5, "lines.markersize": 4.5})


def load(rel):
    return json.loads((ROOT / rel).read_text())


def rows(rel):
    with open(ROOT / rel) as f:
        return list(csv.DictReader(f))


def panel(ax, letter, title):
    ax.set_title(f"{letter}. {title}", loc="left", pad=7)


def bars(ax, labels, values, err, colors, fmt, pad=0.02):
    x = range(len(values))
    ax.bar(x, values, yerr=err, color=colors, width=0.58, error_kw=dict(lw=0.8, ecolor="#444444"))
    top = max(v + (e if e else 0) for v, e in zip(values, err if err else [0] * len(values)))
    for i, v in enumerate(values):
        ax.text(i, v + (err[i] if err else 0) + pad * top, fmt(v), ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(list(x), labels); ax.set_xlim(-0.6, len(values) - 0.4); ax.set_ylim(0, top * 1.16)
    ax.tick_params(axis="x", length=0)


def bracket(ax, x0, x1, y, text, color=INK):
    """A thin bracket between two bars with the difference written above it."""
    h = 0.025 * ax.get_ylim()[1]
    ax.plot([x0, x0, x1, x1], [y, y + h, y + h, y], color="#444444", lw=0.7, marker="none")
    ax.text((x0 + x1) / 2, y + 1.6 * h, text, ha="center", va="bottom", fontsize=7.5, fontweight="bold", color=color)


def save(fig, rel):
    """Write the figure to a path given from the repository root."""
    for ax in fig.axes:
        if ax.get_label() != "heat":
            for side in ("left", "bottom"):
                ax.spines[side].set_position(("outward", 4))
    fig.savefig(ROOT / rel, dpi=300)
    plt.close(fig)
    print("wrote", rel)
