"""Shared style and chart panels for every figure in the repository.

The figures follow the look of the interactive pages (docs/): a navy, blue and grey palette with orange kept for the
difference or threshold being explained, thin grids, direct labels instead of legends where possible, and rounded marks.
Every number is read from the committed result files; nothing is typed in by hand.
"""
import csv
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import patheffects
from matplotlib.patches import FancyBboxPatch

HALO = [patheffects.withStroke(linewidth=3, foreground="white")]

ROOT = Path(__file__).resolve().parents[1]
G1, G2, G3 = "01_with_an_experiment/", "02_without_an_experiment/", "03_planning_a_test/"
S01A, S01B, S01C, S01D = G1 + "01a_ad_incrementality", G1 + "01b_bayesian_segment_effects", G1 + "01c_sql_metric_readout", G1 + "01d_private_segment_effects"
S02A, S02B, S02C, S02D = G2 + "02a_attribution_metric_validation", G2 + "02b_multi_touch_attribution", G2 + "02c_marketing_mix_modeling", G2 + "02d_attribution_and_bidding"
S03A, S03B, S03C, S04 = G3 + "03a_lift_study_sizing", G3 + "03b_geo_experiment_design", G3 + "03c_hierarchical_forecasting", "04_customer_metrics_retention"

INK, INK2, MUTED, GRID = "#1d232b", "#4b5563", "#7b8490", "#e9e6df"
NAVY, BLUE, LIGHT, PALE, GREY, ORANGE, OSOFT = "#1f3b5c", "#3f78b0", "#a9c4de", "#dfe6ee", "#9aa3ad", "#e07b39", "#f6d9c4"
Z_POWER = 1.959964 + 0.841621


def style():
    plt.rcParams.update({
        "font.family": ["Arial", "Helvetica", "DejaVu Sans"], "font.size": 8.5, "axes.titlesize": 9.5,
        "axes.labelsize": 8, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7.5, "legend.frameon": False,
        "text.color": INK, "axes.labelcolor": INK2, "axes.edgecolor": "#b9bec5", "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6, "xtick.major.size": 0, "ytick.major.size": 0,
        "xtick.major.pad": 4, "ytick.major.pad": 4, "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
        "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.7, "axes.axisbelow": True,
        "figure.facecolor": "white", "savefig.facecolor": "white", "lines.solid_capstyle": "round", "lines.dash_capstyle": "round"})


def load(rel):
    return json.loads((ROOT / rel).read_text())


def rows(rel):
    with open(ROOT / rel) as f:
        return list(csv.DictReader(f))


def fmt(v, d=0):
    return f"{v:,.{d}f}"


def panel(ax, letter, title):
    ax.set_title(f"{letter}   {title}", loc="left", fontweight="bold", color=INK, pad=10)


def clean(ax, x=True, y=False):
    """Hide the axis lines that the chart does not need."""
    ax.spines["bottom"].set_visible(x)
    ax.spines["left"].set_visible(y)


def dot(ax, x, y, color=NAVY, s=46, z=4, marker="o"):  # noqa: D103
    ax.scatter([x], [y], s=s, color=color, edgecolor="white", linewidth=1.2, zorder=z, marker=marker)


def pill(ax, x0, x1, y, color, lw=9, z=2, alpha=1.0):
    ax.plot([x0, x1], [y, y], color=color, lw=lw, solid_capstyle="round", zorder=z, alpha=alpha)


def hbars(ax, labels, values, colors, fmtv, vmax=None, lw=12, note=None, label_w=None):
    """Rounded horizontal bars with the value written at the end of each bar."""
    n = len(values); vmax = vmax or max(values) * 1.22
    for i, (lab, v, c) in enumerate(zip(labels, values, colors)):
        y = n - 1 - i
        ax.barh(y, vmax, height=0.56, color=PALE, alpha=0.55, zorder=1, lw=0)
        ax.barh(y, v, height=0.56, color=c, zorder=2, lw=0)
        t = ax.annotate(fmtv(v), (v, y), xytext=(5, 0), textcoords="offset points", va="center", fontsize=8.5, fontweight="bold", color=INK)
        if note and note[i]:
            ax.annotate(note[i], (v, y), xytext=(5, -10), textcoords="offset points", va="center", fontsize=7.5, color=ORANGE, fontweight="bold")
    ax.set_yticks(range(n), labels[::-1]); ax.set_ylim(-0.7, n - 0.3); ax.set_xlim(0, vmax * 1.12)
    ax.grid(False); clean(ax, x=False); ax.set_xticks([])
    ax.tick_params(axis="y", labelsize=8, labelcolor=INK)


def dotrows(ax, labels, est, lo, hi, colors, fmtv, xlim, band=None, ref=None, ref_label=None, bold=None):
    """Point estimates with intervals, one row each, value written to the right."""
    n = len(labels)
    if band:
        ax.axvspan(band[0], band[1], color=PALE, alpha=0.6, lw=0, zorder=0)
    for i in range(n):
        y = n - 1 - i
        ax.plot([lo[i], hi[i]], [y, y], color=colors[i], lw=2.2, zorder=3, solid_capstyle="round")
        dot(ax, est[i], y, colors[i], s=52)
        ax.text(hi[i] + (xlim[1] - xlim[0]) * 0.02, y, fmtv(est[i]), va="center", fontsize=8.5, fontweight="bold", color=INK)
    if ref is not None:
        ax.axvline(ref, color=ORANGE, lw=1.1, ls=(0, (4, 3)), zorder=1)
        if ref_label:
            ax.text(ref, n - 0.45, ref_label, ha="center", va="bottom", fontsize=7.5, color=ORANGE, fontweight="bold")
    ax.set_yticks(range(n), labels[::-1]); ax.set_ylim(-0.6, n - 0.2); ax.set_xlim(*xlim)
    ax.grid(axis="x", color=GRID); ax.grid(axis="y", visible=False); clean(ax, x=False)
    for t, lab in zip(ax.get_yticklabels(), labels[::-1]):
        t.set_color(INK); t.set_fontsize(8)
        if bold and lab in bold:
            t.set_fontweight("bold")


def rbox(ax, x, y, w, h, color, alpha=1.0, r=0.08, ec="none", lw=0, z=1):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=color, ec=ec, lw=lw, alpha=alpha, zorder=z))


def mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]; b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(u + (v - u) * t):02x}" for u, v in zip(a, b))


def nice_log(ax, axis, ticks, labels=None):
    (ax.set_xticks if axis == "x" else ax.set_yticks)(ticks, labels or [fmt(t, 1 if t < 1 else 0) for t in ticks])
    ax.minorticks_off()


def save(fig, rel):
    fig.savefig(ROOT / rel, dpi=300)
    plt.close(fig)
    print("wrote", rel)


# ------------------------------------------------------------------ data in the units the charts use
def experiment():
    inc = load(f"{S01A}/out/criteo/a_incrementality.json"); at = load(f"{S02A}/out/attribution_vs_experiment.json")
    out = {}
    for k in ("visit", "conversion"):
        r = inc[k]["itt"]
        out[k] = dict(p0=r["control_mean"], p1=r["control_mean"] + r["est"], lift=r["relative_lift"], n0=r["n0"], n1=r["n1"],
                      credited=at[k]["attributed"], caused=at[k]["incremental"], ci=1.96 * r["se"] * at["n_treated"],
                      ratio=at[k]["attributed_over_incremental"], adj=inc[k]["aipw_linear"]["est"], adj_se=inc[k]["aipw_linear"]["se"],
                      itt=r["est"], itt_se=r["se"])
    return out


def segments():
    p = load(f"{S01B}/out/part2_segments.json"); p.update(load(f"{S01B}/out/part2_segments_rerun.json"))
    return [p[k] for k in sorted(p, key=int)]


# ------------------------------------------------------------------ panels
def p_rates(fig, spec, letter, title="Visit and conversion rates by group"):
    """Two dumbbells, control to ad group, on one shared index scale (control = 100) so the two lifts compare by length."""
    E = experiment(); ax = fig.add_subplot(spec); top = 185
    for k, name, y in (("visit", "Visit rate", 3.0), ("conversion", "Conversion rate", 0.0)):
        r = E[k]; i1 = 100 * r["p1"] / r["p0"]
        pill(ax, 0, top, y, PALE, lw=7, z=1, alpha=0.7)
        pill(ax, 100, i1, y, ORANGE, lw=7, z=2, alpha=0.75)
        dot(ax, 100, y, GREY, s=70); dot(ax, i1, y, NAVY, s=80)
        ax.text(97, y + 0.42, f"Control\n{100 * r['p0']:.2f}%", ha="right", va="bottom", fontsize=7.5, color=MUTED, linespacing=1.1)
        ax.text(min(i1 - 5, top - 48), y + 0.42, f"Ad group\n{100 * r['p1']:.2f}%", ha="left", va="bottom", fontsize=7.5, color=NAVY, fontweight="bold", linespacing=1.1)
        ax.text((100 + i1) / 2, y - 0.42, f"+{100 * r['lift']:.0f}% relative", ha="center", va="top", fontsize=9, color=ORANGE, fontweight="bold")
        ax.text(0, y + 1.55, name, fontsize=8.5, fontweight="bold", color=INK, va="bottom")
    ax.set_xlim(0, top * 1.01); ax.set_ylim(-1.15, 4.85); ax.set_yticks([])
    ax.set_xticks([0, 50, 100, 150]); ax.grid(False); clean(ax, x=False)
    ax.set_xlabel("% of control rate", fontsize=7.5, color=MUTED)
    ax.set_title(f"{letter}   {title}", loc="left", fontweight="bold", color=INK, pad=10)
    return [ax]


def p_gap(fig, spec, letter, title="Credited by the count, and caused by the ads"):
    """For conversions and visits: the count against the experiment's estimate, on one shared index scale (caused = 100)."""
    E = experiment(); ax = fig.add_subplot(spec); top = 185
    for k, name, y in (("conversion", "Conversions", 3.0), ("visit", "Visits", 0.0)):
        r = E[k]; ia = 100 * r["credited"] / r["caused"]; e = 100 * r["ci"] / r["caused"]
        pill(ax, 100, ia, y, OSOFT, lw=11, z=1)
        ax.plot([100 - e, 100 + e], [y, y], color=NAVY, lw=1.6, zorder=3)
        for v in (100 - e, 100 + e):
            ax.plot([v, v], [y - 0.2, y + 0.2], color=NAVY, lw=1.4, zorder=3)
        dot(ax, 100, y, NAVY, s=80, z=5); dot(ax, ia, y, ORANGE, s=95, z=5, marker="D")
        ax.text(100, y - 0.45, f"{fmt(r['caused'])}\ncaused", ha="center", va="top", fontsize=7.5, color=NAVY, fontweight="bold", linespacing=1.1)
        ax.text(ia, y - 0.45, f"{fmt(r['credited'])}\ncredited", ha="center", va="top", fontsize=7.5, color=ORANGE, fontweight="bold", linespacing=1.1)
        ax.text((100 + ia) / 2, y + 0.42, f"+{fmt(r['credited'] - r['caused'])}  ({100 * (r['ratio'] - 1):.0f}% more)", ha="center", va="bottom",
                fontsize=8, color=INK, fontweight="bold")
        ax.text(0, y + 1.0, name, fontsize=8.5, fontweight="bold", color=INK, va="bottom")
    ax.set_xlim(0, top * 1.01); ax.set_ylim(-1.75, 4.4); ax.set_yticks([])
    ax.set_xticks([0, 50, 100, 150]); ax.grid(axis="x", color=GRID); ax.set_axisbelow(True); clean(ax, x=False)
    ax.set_xlabel("% of caused", fontsize=7.5, color=MUTED)
    ax.set_title(f"{letter}   {title}", loc="left", fontweight="bold", color=INK, pad=10)
    return [ax]


def p_hundred(ax, letter, key="conversion", title=None):
    """Of every 100 outcomes the count credits to the ads, how many the ads caused."""
    E = experiment(); r = E[key]; n = round(100 * r["caused"] / r["credited"])
    for i in range(100):
        c, rr = i % 10, 9 - i // 10
        rbox(ax, c + 0.08, rr + 0.08, 0.84, 0.84, NAVY if i < n else OSOFT, r=0.16)
    ax.set_xlim(0, 10); ax.set_ylim(-4.9, 10); ax.set_aspect("equal"); ax.axis("off")
    ax.text(0, -0.5, f"■ caused by the ads: {n}", color=NAVY, fontsize=7.5, fontweight="bold", va="top")
    ax.text(0, -1.45, f"■ would have occurred\n   anyway: {100 - n}", color=ORANGE, fontsize=7.5, fontweight="bold", va="top", linespacing=1.1)
    ax.text(0, -3.2, f"{fmt(r['caused'])} ÷ {fmt(r['credited'])} = {100 * r['caused'] / r['credited']:.0f}%; a share of the\ntotal, not a label for each conversion",
            color=MUTED, fontsize=6.3, va="top", linespacing=1.15)
    ax.set_title(f"{letter}   {title or 'Of 100 credited'}", loc="left", fontweight="bold", color=INK, pad=10)


def p_deciles(ax, letter, title="Effect by decile of predicted uplift"):
    tg = load(f"{S01A}/out/criteo/c_targeting.json"); cal = tg["calibration_selected"]
    x = [r["decile"] for r in cal]; y = [100 * r["realized"] for r in cal]; h = [196 * r["se"] for r in cal]
    ax.axhline(0, color="#b9bec5", lw=0.8)
    ax.axhline(100 * tg["test_overall_itt"]["est"], color=GREY, lw=1, ls=(0, (4, 3)))
    ax.text(10.4, 100 * tg["test_overall_itt"]["est"] + 0.25, "average", ha="right", fontsize=7, color=MUTED)
    ax.fill_between(x, [u - v for u, v in zip(y, h)], [u + v for u, v in zip(y, h)], color=NAVY, alpha=0.14, lw=0)
    ax.plot(x, y, color=NAVY, lw=2.2, zorder=3)
    for u, v in zip(x, y):
        dot(ax, u, v, NAVY, s=30)
    ax.plot(x, [100 * r["predicted"] for r in cal], color=ORANGE, lw=1.4, ls=(0, (4, 2)), zorder=2)
    ax.text(1.35, y[0], f"realized {y[0]:.1f}", fontsize=7.5, color=NAVY, fontweight="bold", va="center")
    ax.text(10, 100 * cal[-1]["predicted"] - 0.45, "predicted", fontsize=7.5, color=ORANGE, fontweight="bold", ha="right", va="top")
    ax.set_xticks(x); ax.set_xlim(0.5, 10.6); ax.set_ylim(-1.8, 7.6); ax.set_xlabel("Decile of predicted uplift (1 = highest)")
    ax.set_ylabel("Effect on visit rate (pp)"); clean(ax)
    panel(ax, letter, title)


def p_slope(ax, letter, title="Error of segment estimates, ten 2% samples"):
    S = segments(); a = [100 * s["rmse"]["nopool"] for s in S]; b = [100 * s["rmse"]["bayes"] for s in S]
    for u, v in zip(a, b):
        ax.plot([0, 1], [u, v], color=GREY, lw=1, alpha=0.6, zorder=1)
        ax.scatter([0, 1], [u, v], s=14, color=GREY, zorder=2)
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    ax.plot([0, 1], [ma, mb], color=NAVY, lw=3.2, zorder=3)
    dot(ax, 0, ma, NAVY, s=60); dot(ax, 1, mb, NAVY, s=60)
    ax.text(-0.07, ma, f"{ma:.2f}", ha="right", va="center", fontsize=8.5, fontweight="bold", color=NAVY)
    ax.text(1.07, mb, f"{mb:.2f}", ha="left", va="center", fontsize=8.5, fontweight="bold", color=NAVY)
    ax.text(0.5, 0.56, f"lower in {sum(v < u for u, v in zip(a, b))} of {len(a)} samples", ha="center", fontsize=7.5, color=ORANGE, fontweight="bold")
    ax.set_xticks([0, 1], ["Each segment\nalone", "Multilevel\nmodel"]); ax.set_xlim(-0.4, 1.4); ax.set_ylim(0.5, 1.35)
    ax.set_ylabel("RMSE of 100 segment effects (pp)"); clean(ax, x=False)
    panel(ax, letter, title)


def p_seg_scatter(ax, letter, title="Segment estimates in sample 1"):
    s = segments()[0]["seg"]; b = [100 * v for v in s["bench"]]
    ax.plot([-1, 9], [-1, 9], color=ORANGE, lw=1.1, ls=(0, (4, 3)), zorder=1)
    for u, v in zip(b, s["bayes"]):
        ax.plot([u, u], [u, 100 * v], color=NAVY, lw=0.6, alpha=0.35, zorder=2)
    ax.scatter(b, [100 * v for v in s["nopool"]], s=12, color=GREY, alpha=0.55, lw=0, zorder=2)
    ax.scatter(b, [100 * v for v in s["bayes"]], s=20, color=NAVY, edgecolor="white", lw=0.6, zorder=3)
    ax.text(8.8, 7.0, "estimate = benchmark", ha="right", fontsize=7, color=ORANGE, path_effects=HALO)
    ax.text(-0.8, 10.2, "● multilevel model", color=NAVY, fontsize=7.5, fontweight="bold", va="top")
    ax.text(-0.8, 9.0, "● each segment alone", color=GREY, fontsize=7.5, fontweight="bold", va="top")
    ax.set_xlim(-1, 9); ax.set_ylim(-3, 11); ax.set_xlabel("Benchmark effect, other 98% of users (pp)"); ax.set_ylabel("Estimate (pp)"); clean(ax)
    panel(ax, letter, title)


def p_privacy(ax, letter, title="Error under privacy noise"):
    pr = load(f"{S01D}/out/a_private_summary.json"); eps = ["0.1", "0.5", "1.0", "5.0", "inf"]; x = list(range(5))
    base = 100 * pr["nonprivate_nopool_rmse"]
    ax.axhline(base, color=ORANGE, lw=1.1, ls=(0, (4, 3)), label=f"each segment, no noise ({base:.2f})")
    for key, name, c in (("rmse_nopool", "each segment alone", GREY), ("rmse_ml", "multilevel model", NAVY)):
        y = [100 * pr["by_eps"][e][key] for e in eps]
        ax.plot(x, y, color=c, lw=2.2 if c == NAVY else 1.6, zorder=3, marker="o", ms=5.5, mec="white", mew=1, label=name)
    ml1 = 100 * pr["by_eps"]["1.0"]["rmse_ml"]
    ax.annotate(f"{ml1:.2f}", (2, ml1), xytext=(2, ml1 * 0.72), ha="center", fontsize=8, color=NAVY, fontweight="bold")
    ax.set_yscale("log"); nice_log(ax, "y", [1, 2, 4, 8]); ax.set_ylim(0.75, 24)
    ax.legend(loc="upper right", handlelength=1.6, borderaxespad=0.2, labelcolor=INK2)
    ax.set_xticks(x, ["0.1", "0.5", "1", "5", "none"]); ax.set_xlim(-0.35, 4.35); ax.set_xlabel("Privacy budget ε (smaller = more noise)")
    ax.set_ylabel("RMSE of segment effects (pp)"); clean(ax)
    panel(ax, letter, title)


def p_exposure(ax, letter, title="Effect of exposure on the visit rate"):
    pe = load(f"{S02A}/out/attribution_vs_experiment.json")["per_exposed_user_visit_effect"]; inc = load(f"{S01A}/out/criteo/a_incrementality.json")
    est = [("Experiment, unadjusted", inc["cace_visit_unadjusted"]["est"], inc["cace_visit_unadjusted"]["se"], NAVY),
           ("Experiment, adjusted", inc["cace_visit_adjusted"]["est"], inc["cace_visit_adjusted"]["se"], NAVY),
           ("Exposed vs. unexposed", pe["naive"], pe["naive_se"], ORANGE), ("Regression adjustment", pe["ols_adjusted"], pe["ols_se"], BLUE),
           ("Double machine learning", pe["dml"], pe["dml_se"], BLUE)]
    v = [100 * e[1] for e in est]; h = [196 * e[2] for e in est]
    dotrows(ax, [e[0] for e in est], v, [a - b for a, b in zip(v, h)], [a + b for a, b in zip(v, h)], [e[3] for e in est], lambda u: f"{u:.1f}",
            (15, 43), band=(min(v[:2]), max(v[:2])), bold=["Experiment, unadjusted", "Experiment, adjusted"])
    ax.text((v[0] + v[1]) / 2, 4.75, "experimental range", ha="center", fontsize=7, color=MUTED)
    ax.set_xlabel("Percentage points"); panel(ax, letter, title)


RULES = [("cr_last", "Last touch"), ("cr_decay", "Time decay"), ("cr_linear", "Linear"), ("cr_first", "First touch")]
BUCKETS = [("last", "Last\ntouch"), ("<1d", "<1 day\nbefore"), ("1-7d", "1–7 days\nbefore"), (">7d", ">7 days\nbefore")]


def p_heat(ax, letter, title="Share of credit by rule and timing of the touch"):
    cr = load(f"{S02B}/out/mta.json")["credit_by_recency_bucket"]
    for i, (rk, rn) in enumerate(RULES):
        y = len(RULES) - 1 - i
        for j, (bk, _) in enumerate(BUCKETS):
            v = 100 * cr[rk][bk]; c = mix("#f4f1ea", NAVY, 0.06 + 0.94 * v / 100)
            rbox(ax, j + 0.05, y + 0.06, 0.9, 0.88, c, r=0.1)
            ax.text(j + 0.5, y + 0.5, f"{v:.0f}%", ha="center", va="center", fontsize=8.5, fontweight="bold", color="white" if v >= 45 else INK)
    ax.set_xlim(0, 4); ax.set_ylim(0, 4)
    ax.set_xticks([j + 0.5 for j in range(4)], [b[1] for b in BUCKETS]); ax.xaxis.tick_top(); ax.tick_params(axis="x", labelsize=6.8, labelcolor=INK2)
    ax.set_yticks([len(RULES) - 1 - i + 0.5 for i in range(4)], [r[1] for r in RULES]); ax.tick_params(axis="y", labelsize=8, labelcolor=INK)
    ax.grid(False); clean(ax, x=False)
    ax.set_title(f"{letter}   {title}", loc="left", fontweight="bold", color=INK, pad=26)


def p_clicked(ax, letter, title="Share of credit on clicked touches"):
    m = load(f"{S02B}/out/mta.json"); sc = 100 * m["share_touches_clicked"]
    v = [100 * m["credit_on_clicked_touches"][k] for k, _ in RULES]
    for i, u in enumerate(v):
        y = len(v) - 1 - i
        ax.plot([sc, u], [y, y], color=NAVY, lw=2, alpha=0.4)
        dot(ax, u, y, NAVY, s=55); ax.text(u + 0.9, y, f"{u:.0f}%", va="center", fontsize=8.5, fontweight="bold")
    ax.axvline(sc, color=ORANGE, lw=1.1, ls=(0, (4, 3)))
    ax.text(sc, len(v) - 0.35, f"share of touches clicked {sc:.0f}%", ha="center", fontsize=7.5, color=ORANGE, fontweight="bold")
    ax.set_yticks(range(len(v)), [r[1] for r in RULES][::-1]); ax.set_ylim(-0.6, len(v) - 0.1); ax.set_xlim(44, 72)
    ax.set_xticks([45, 50, 55, 60, 65, 70], [f"{t}%" for t in (45, 50, 55, 60, 65, 70)]); ax.grid(axis="x", color=GRID); ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", labelcolor=INK, labelsize=8); clean(ax, x=False)
    panel(ax, letter, title)


def p_bidding(ax, letter, title="Two bidders, one trained on each rule"):
    bd = load(f"{S02D}/out/bidding.json")["budgets"]; ks = ["0.25", "0.5", "0.75"]
    for rule, c, off, name in (("cr_last", GREY, -0.12, "scored by last-touch credit"), ("cr_decay", NAVY, 0.12, "scored by time-decay credit")):
        for q, k in enumerate(ks):
            m, lo, hi = [100 * u for u in bd[k]["cross_rule_loss"][rule]]
            ax.plot([q + off, q + off], [lo, hi], color=c, lw=2.2)
            ax.scatter([q + off], [m], s=46, color=c, edgecolor="white", linewidth=1.2, zorder=4, label=name if q == 0 else None)
            ax.annotate(f"{m:.1f}", (q + off, m), xytext=(7 if off > 0 else -7, 0), textcoords="offset points", ha="left" if off > 0 else "right",
                        va="center", fontsize=7, color=c, fontweight="bold")
    ax.axhline(5, color=ORANGE, lw=1.1, ls=(0, (4, 3))); ax.text(2.45, 5.25, "pre-specified 5%", ha="right", fontsize=7.2, color=ORANGE, fontweight="bold")
    ax.axhline(0, color="#b9bec5", lw=0.8)
    ax.legend(loc="upper left", bbox_to_anchor=(-0.02, 1.0), handletextpad=0.2, labelcolor=INK2, fontsize=6.8)
    ax.set_xticks(range(3), [f"{int(100 * float(k))}%\n{100 * bd[k]['spend_overlap']:.1f}%" for k in ks]); ax.tick_params(axis="x", labelsize=7, labelcolor=INK2)
    ax.text(-0.75, -2.55, "budget\nsame spend", fontsize=6.5, color=MUTED, ha="right", va="center", linespacing=1.35)
    ax.set_xlim(-0.5, 2.5); ax.set_ylim(-1.5, 8.2); ax.set_ylabel("Credit lost (%)"); clean(ax)
    panel(ax, letter, title)


def mmm_points():
    rr = [r for r in rows(f"{S02C}/out/detectability.csv") if r["sim"] == "brand_shapes"]
    idx = {(r["org"], r["channel"]): float(r["index"]) for r in rr if r["freq"] == "D"}
    rec = [r for r in rows(f"{S02C}/out/mmm_pooled_recovery_daily.csv") if r["sim"] == "brand_shapes" and r["single_converged"] == "True"]
    return rr, [(max(idx[(r["org"], r["channel"])], 0.04), 100 * abs(float(r["single"]) - float(r["true"])) / float(r["true"])) for r in rec]


def p_mmm_scatter(ax, letter, title="Recovery error and the signal-to-noise index"):
    rr, pts = mmm_points(); t1 = load(f"{S02C}/out/detectability.json")["tests"]["T1"]
    ax.axvspan(2, 60, color=PALE, alpha=0.55, lw=0, zorder=0)
    ax.axvline(2, color=ORANGE, lw=1.2, ls=(0, (4, 3)))
    for lo_, hi_, m, c in ((0.03, 2, 100 * t1["index_below_2"]["median_err"], GREY), (2, 60, 100 * t1["index_2_or_more"]["median_err"], NAVY)):
        ax.plot([lo_ * 1.15, hi_ / 1.15], [m, m], color=c, lw=1.4, ls=(0, (5, 3)), zorder=2)
        ax.text(lo_ * 1.3 if c == GREY else hi_ / 1.3, m * 1.35, f"median error {m:.0f}%", ha="left" if c == GREY else "right", fontsize=7.5, color=c, fontweight="bold", path_effects=HALO, zorder=5)
    ax.scatter([u for u, v in pts if u < 2], [v for u, v in pts if u < 2], s=26, color=GREY, edgecolor="white", lw=0.7, zorder=3)
    ax.scatter([u for u, v in pts if u >= 2], [v for u, v in pts if u >= 2], s=30, color=NAVY, edgecolor="white", lw=0.7, zorder=3)
    ax.text(2.2, 2400, "index = 2", fontsize=7.2, color=ORANGE, fontweight="bold")
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(0.03, 60); ax.set_ylim(0.6, 4000)
    nice_log(ax, "x", [0.1, 1, 2, 10], ["0.1", "1", "2", "10"]); nice_log(ax, "y", [1, 10, 100, 1000])
    ax.set_xlabel("Signal-to-noise index (log scale)"); ax.set_ylabel("Error of estimated ROAS (%)"); clean(ax)
    panel(ax, letter, title)


def p_mmm_share(ax, letter, title="Brand-channels with an index of 2 or more"):
    rr, _ = mmm_points(); vals = []
    for f in ("W", "D"):
        v = [float(r["index"]) for r in rr if r["freq"] == f]; vals.append((100 * sum(u >= 2 for u in v) / len(v), len(v)))
    hbars(ax, [f"Weekly data\n({vals[0][1]} brand-channels)", f"Daily data\n({vals[1][1]})"], [vals[0][0], vals[1][0]], [GREY, NAVY], lambda u: f"{u:.0f}%", vmax=100, lw=16)
    panel(ax, letter, title)


def p_users_lift(ax, letter, lift=0.10, title=None):
    eff = load(f"{S01C}/out/readout.json")["effects"]
    n = lambda p0, l: Z_POWER ** 2 * (p0 * (1 - p0) + p0 * (1 + l) * (1 - p0 * (1 + l))) / (p0 * l) ** 2
    v, c = n(eff["visit"]["control_rate"], lift), n(eff["conversion"]["control_rate"], lift)
    hbars(ax, ["Visits", "Conversions"], [v, c], [GREY, NAVY], lambda u: fmt(u) if u == v else f"{fmt(u)}\n(×{c / v:.1f})", vmax=c)
    panel(ax, letter, title or f"Users per arm to detect a {100 * lift:.0f}% lift")


def p_cov_users(ax, letter, title="Users per arm for a one-point lift in visits"):
    cov = load(f"{S03A}/out/covariate_adjustment.json")["required_n_one_point_lift"]
    hbars(ax, ["Unadjusted", "Adjusted,\n12 features", "Adjusted, model\nprediction"], [cov["D"], cov["L"], cov["M"]], [GREY, BLUE, NAVY],
          lambda u: fmt(u) + ("" if u == cov["D"] else f"  ({100 * (u / cov['D'] - 1):.1f}%)"), vmax=cov["D"] * 1.0)
    panel(ax, letter, title)


def geo_grid():
    est = {"CR: ANCOVA (CUPED)": "adjusted", "CR: year-over-year difference": "yoy", "MP: pair ANCOVA": "pairs", "CR: volume-weighted ANCOVA": "vw"}
    g = {v: {} for v in est.values()}
    for r in rows(f"{S03B}/out/design_summary.csv"):
        if r["estimator"] in est and r["mde_80_pct"]:
            g[est[r["estimator"]]][(int(r["metros"]), int(r["test_months"]))] = float(r["mde_80_pct"])
    return g


def p_geo_grid(ax, letter, key="adjusted", title="Smallest detectable effect, regression-adjusted"):
    g = geo_grid()[key]; ms, ts = [20, 50, 100, 150], [1, 2, 3]; lo, hi = math.log(min(g.values())), math.log(max(g.values()))
    for i, m in enumerate(ms):
        for j, t in enumerate(ts):
            v = g[(m, t)]; s = 1 - (math.log(v) - lo) / (hi - lo); y = len(ts) - 1 - j
            rbox(ax, i + 0.05, y + 0.07, 0.9, 0.86, mix("#eef2f6", NAVY, 0.1 + 0.9 * s), r=0.1,
                 ec=ORANGE if (m, t) == (100, 2) else "none", lw=1.8 if (m, t) == (100, 2) else 0, z=2)
            ax.text(i + 0.5, y + 0.5, f"{v:.1f}%", ha="center", va="center", fontsize=8.5, fontweight="bold", color="white" if s > 0.45 else INK, zorder=3)
    ax.set_xlim(0, 4); ax.set_ylim(0, 3); ax.set_xticks([i + 0.5 for i in range(4)], [str(m) for m in ms]); ax.set_xlabel("Metros in the test")
    ax.set_yticks([len(ts) - 1 - j + 0.5 for j in range(3)], [f"{t} month{'s' if t > 1 else ''}" for t in ts]); ax.tick_params(axis="y", labelcolor=INK, labelsize=8)
    ax.grid(False); clean(ax, x=False)
    panel(ax, letter, title)


def p_forecast_gap(ax, letter, title="Gap between a level and the sum below it"):
    tab = rows(f"{S03C}/reports/tables/inventory_ets_headline.csv")
    inc = {r["level"]: 100 * float(r["incoherence_mean"]) for r in tab if r["method"] == "base" and r["incoherence_mean"]}
    hbars(ax, ["Nation vs. divisions", "Divisions vs. states", "States vs. metros"], [inc["US"], inc["division"], inc["state"]], [ORANGE] * 3,
          lambda u: f"{u:.1f}%", vmax=6.5, lw=14)
    ax.text(0, -0.85, "Before reconciliation; bottom-up makes each gap zero.", fontsize=7, color=MUTED, va="top")
    panel(ax, letter, title)


def p_new_customers(ax, letter, title="Accounts labeled new under a 3-month look-back"):
    seg = load(f"{S04}/out/12_ltv_segments.json"); b = seg["burnin3_contamination"]; n, old = b["apparent_new"], b["bought_in_prior_12m"]
    ax.barh(0, n - old, height=0.5, color=NAVY, lw=0); ax.barh(0, old, left=n - old, height=0.5, color=ORANGE, lw=0)
    ax.plot([n - old, n - old], [-0.25, 0.25], color="white", lw=2)
    ax.text((n - old) / 2, 0, f"{n - old}", color="white", fontsize=10, fontweight="bold", ha="center", va="center")
    ax.text(n - old + old / 2, 0, f"{old}", color="white", fontsize=10, fontweight="bold", ha="center", va="center")
    ax.text(0, 0.42, f"{fmt(n)} accounts labeled new", fontsize=8, fontweight="bold", color=INK, va="bottom")
    ax.text(0, -0.38, f"{100 * (n - old) / n:.1f}% no purchase in the prior 12 months", color=NAVY, fontsize=7.2, fontweight="bold", va="top")
    ax.text(0, -0.72, f"{100 * old / n:.1f}% bought in the prior 12 months", color=ORANGE, fontsize=7.2, fontweight="bold", va="top")
    ax.set_xlim(0, n); ax.set_ylim(-1.35, 1.0); ax.axis("off")
    panel(ax, letter, title)


def p_auc(ax, letter, title="Ranking repeat buyers (AUC)"):
    e2 = load(f"{S04}/out/14_ltv_extension.json")["E2"]
    v = [e2["auc_recency"], e2["auc_model"]]; ci = [e2["auc_recency_ci"], e2["auc_model_ci"]]
    dotrows(ax, ["Recency alone", "Purchase model"], v, [c[0] for c in ci], [c[1] for c in ci], [GREY, NAVY], lambda u: f"{u:.2f}", (0.68, 0.86), bold=["Purchase model"])
    ax.set_xlabel(f"High-value accounts, n = {fmt(e2['n_high_value'])}"); panel(ax, letter, title)


def p_rank(ax, letter, title="Ranking future sales (rank correlation)"):
    s = load(f"{S04}/out/12_ltv_segments.json"); e = load(f"{S04}/out/14_ltv_extension.json")
    e6, e12 = s["eval"], e["E1"]["eval"]
    items = [("6 months · purchase model", e6["BGNBD_GG"], NAVY), ("6 months · past-sales rule", e6["P0_last6m"], GREY),
             ("12 months · purchase model", e12["bgnbd_gg"], NAVY), ("12 months · past-sales rule", e12["past_sales"], GREY)]
    dotrows(ax, [i[0] for i in items], [i[1]["spearman"] for i in items], [i[1]["spearman_ci"][0] for i in items], [i[1]["spearman_ci"][1] for i in items],
            [i[2] for i in items], lambda u: f"{u:.2f}", (0.54, 0.72))
    ax.axhline(1.5, color=GRID, lw=1)
    ax.set_xlabel(f"Holdouts of {fmt(s['n_test'])} and {fmt(e['E1']['n_accounts'])} accounts"); panel(ax, letter, title)
