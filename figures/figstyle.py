"""Style and helpers shared by every figure of the repository.

Rules the figures follow: the panel title states the finding; every mark is labelled where it sits, with no legend to decode;
a quantity is shown in one unit; and colours keep one meaning throughout: navy for what the experiment measured or the better
method, blue for a second method, grey for a baseline or an unadjusted estimate, orange only for what is overstated, overcounted
or miscounted. Type and line weights follow journal conventions (sans-serif, thin axes, no gridlines, bold lowercase panel letters).
"""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import textwrap
from matplotlib import patheffects as pe
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


AX = "#333333"


def style():
    """Nature/Science conventions: 7 pt sans-serif, 0.5 pt axes, outward ticks, no gridlines, no boxes, bold lowercase panel letters."""
    plt.rcParams.update({
        "font.family": ["Arial", "Helvetica", "DejaVu Sans"], "font.size": 7, "axes.labelsize": 7, "axes.titlesize": 7.5,
        "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "legend.fontsize": 6.5, "legend.frameon": False, "legend.handlelength": 1.4,
        "legend.handletextpad": 0.5, "legend.labelspacing": 0.35, "legend.borderaxespad": 0.2,
        "text.color": INK, "axes.labelcolor": INK, "axes.edgecolor": AX, "xtick.color": AX, "ytick.color": AX,
        "axes.linewidth": 0.5, "xtick.major.width": 0.5, "ytick.major.width": 0.5, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
        "xtick.major.pad": 2.5, "ytick.major.pad": 2.5, "axes.labelpad": 3,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False, "grid.color": "#e9e9e9", "grid.linewidth": 0.5, "axes.axisbelow": True,
        "figure.facecolor": "white", "savefig.facecolor": "white", "errorbar.capsize": 0, "lines.linewidth": 1.1, "lines.markersize": 3.6,
        "lines.markeredgecolor": "white", "lines.markeredgewidth": 0.5, "pdf.fonttype": 42, "svg.fonttype": "none"})


def load(rel):
    return json.loads((ROOT / rel).read_text())


def rows(rel):
    with open(ROOT / rel) as f:
        return list(csv.DictReader(f))


PALE, DGREY, MID, BAND_G = "#dfe6ee", "#6e7781", "#555555", "#d9dde2"
HALO = [pe.withStroke(linewidth=2.2, foreground="white")]
W = 7.09   # figure width in inches (180 mm)


def setup():
    style()
    plt.rcParams.update({"font.size": 7.5, "axes.labelsize": 7.5, "xtick.labelsize": 7, "ytick.labelsize": 7, "lines.linewidth": 1.4, "lines.markersize": 4.5})


def head(ax, letter, text, width=34, dx=0.0):
    """Finding as a two-line bold title at a fixed height above the axes; the letter sits at its left."""
    lines = textwrap.wrap(text, width)
    while len(lines) > 2:
        width += 2; lines = textwrap.wrap(text, width)
    h = ax.get_position().height * ax.figure.get_figheight(); w = ax.get_position().width * ax.figure.get_figwidth()
    y = 1 + 0.36 / h
    ax.text(dx / w, y, "\n".join(lines), transform=ax.transAxes, fontsize=8, fontweight="bold", va="top", ha="left", linespacing=1.2)
    ax.text(dx / w - 0.17 / w, y + 0.01 / h, letter, transform=ax.transAxes, fontsize=10, fontweight="bold", va="top", ha="left")


def smooth_xy(x, y, logx=False, logy=False, n=120):
    """Points of a smooth curve through the measured points. The interpolation is monotone between neighbours (PCHIP), so the
    curve passes through every point and never overshoots; it is computed on the scale the axis uses. Falls back to straight
    segments if SciPy is not installed."""
    import math
    x, y = [float(u) for u in x], [float(v) for v in y]
    try:
        from scipy.interpolate import PchipInterpolator
    except ImportError:
        return x, y
    fx = (lambda u: math.log(u)) if logx else (lambda u: u); fy = (lambda u: math.log(u)) if logy else (lambda u: u)
    tx = [fx(u) for u in x]; f = PchipInterpolator(tx, [fy(v) for v in y])
    gx = [tx[0] + (tx[-1] - tx[0]) * i / (n - 1) for i in range(n)]
    return [math.exp(u) if logx else u for u in gx], [math.exp(v) if logy else float(v) for v in f(gx)]


def curve(ax, x, y, color, logx=False, logy=False, ms=4.5, marker=True, **kw):
    """A smooth curve through the measured points, with a dot on each measured point."""
    sx, sy = smooth_xy(x, y, logx, logy)
    ax.plot(sx, sy, color=color, marker="none", solid_capstyle="round", **kw)
    if marker:
        ax.plot(list(x), list(y), "o", color=color, ms=ms, zorder=3)


def band(ax, x, y1, y2, logx=False, logy=False, **kw):
    """Shaded area between two smooth curves through the same x positions."""
    sx, s1 = smooth_xy(x, y1, logx, logy); _, s2 = smooth_xy(x, y2, logx, logy)
    ax.fill_between(sx, s1, s2, lw=0, **kw)


def bare(ax):
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks([]); ax.set_yticks([])


def out(fig, rel, offset=True):
    """Write the figure to a path given from the repository root."""
    if offset:
        for ax in fig.axes:
            for side in ("left", "bottom"):
                ax.spines[side].set_position(("outward", 3))
    fig.savefig(ROOT / rel, dpi=300); plt.close(fig); print("wrote", rel)
