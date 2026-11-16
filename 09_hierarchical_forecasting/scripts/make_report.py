"""Score every saved backtest (tmp/bt_*.npz) and write aggregate tables, headlines.json and one figure.

Every number in reports/memo.md comes from the files this script writes. Tables between
<!-- BEGIN:name --> and <!-- END:name --> markers in the memo are replaced by this script."""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hierfc import metrics as mx  # noqa: E402
from hierfc.paths import ATTRIBUTION, FIGURES, REPO, TABLES, TMP  # noqa: E402

LEVELS = ["US", "division", "state", "metro"]
LABEL = {"base": "base (unreconciled)", "bu": "bottom-up", "td": "top-down", "ols": "OLS",
         "wls_struct": "WLS-structural", "mint_shrink": "MinT-shrink", "naive": "no-change",
         "snaive": "seasonal naive"}
BASE_LABEL = {"ets": "AutoETS", "arima": "AutoARIMA"}
RUNS = [("inventory", "ets", "Primary: inventory, AutoETS base"),
        ("inventory", "arima", "R1: inventory, AutoARIMA base"),
        ("new_listings", "ets", "R2: new listings, AutoETS base")]


def load(tag):
    z = np.load(TMP / f"bt_{tag}.npz")
    ch = {int(k): v for k, v in json.loads((TMP / f"bt_{tag}_children.json").read_text()).items()}
    return {k: z[k] for k in z.files}, ch


def score(tag):
    z, children = load(tag)
    fc, act, sc = z["fc"], z["actual"], z["scale"]
    methods = list(z["methods"]); level, is_rem = z["level"], z["is_rem"]
    H = fc.shape[-1]
    head, byh, comp = [], [], []
    for L, lname in enumerate(LEVELS):
        nodes = mx.level_nodes(level, is_rem, L)
        r_naive = mx.level_rmsse(fc[methods.index("naive")], act, sc, nodes)
        for mi, m in enumerate(methods):
            f = fc[mi]
            row = {"level": lname, "n_nodes": len(nodes), "method": m,
                   "rmsse_1_12": mx.level_rmsse(f, act, sc, nodes),
                   "mae_1_12": mx.level_mae(f, act, nodes),
                   "share_negative": float((f[:, nodes] < 0).mean())}
            row["rel_to_no_change"] = row["rmsse_1_12"] / r_naive
            if L < 3:
                c_mean, c_max = mx.coherence(f, act, children, nodes)
                row["incoherence_mean"], row["incoherence_max"] = c_mean, c_max
            head.append(row)
            for h in range(1, H + 1):
                byh.append({"level": lname, "method": m, "h": h,
                            "rmsse": mx.level_rmsse(f, act, sc, nodes, [h]),
                            "rel_to_no_change": mx.level_rmsse(f, act, sc, nodes, [h])
                            / mx.level_rmsse(fc[methods.index("naive")], act, sc, nodes, [h])})
        # pre-specified comparisons (plan §7)
        lv = pd.DataFrame([r for r in head if r["level"] == lname]).set_index("method")
        best = lv.drop(index="naive").rmsse_1_12.idxmin()
        for name, a, b in [("P1", "mint_shrink", "base"), ("P2", "mint_shrink", "bu"), ("P3", best, "naive")]:
            row = {"comparison": name, "level": lname, "A": a, "B": b,
                   "rmsse_A": lv.loc[a, "rmsse_1_12"], "rmsse_B": lv.loc[b, "rmsse_1_12"]}
            for h in (1, 12):
                d = (mx.origin_loss(fc[methods.index(a)], act, sc, nodes, h)
                     - mx.origin_loss(fc[methods.index(b)], act, sc, nodes, h))
                t = mx.dm_hln(d, h)
                row[f"h{h}_mean_d"], row[f"h{h}_hln"], row[f"h{h}_p"] = t["mean_d"], t["stat"], t["p"]
                row[f"h{h}_A_wins_of_{len(d)}"] = int((d < 0).sum())
            sig_better = any(row[f"h{h}_p"] < 0.05 and row[f"h{h}_mean_d"] < 0 for h in (1, 12))
            sig_worse = any(row[f"h{h}_p"] < 0.05 and row[f"h{h}_mean_d"] > 0 for h in (1, 12))
            if row["rmsse_A"] < row["rmsse_B"] and sig_better:
                row["verdict"] = "A better"
            elif row["rmsse_A"] > row["rmsse_B"] and sig_worse:
                row["verdict"] = "A worse"
            else:
                row["verdict"] = "no clear difference"
            # added after the plan (memo, Deviations D1): the plan's rule did not cover a cell that is significantly
            # better at one horizon and significantly worse at the other; such cells are flagged, verdict unchanged
            if sig_better and sig_worse:
                row["verdict"] += " (mixed: significantly worse at one of h=1/h=12)"
            row["direction"] = " / ".join(
                "identical" if row[f"h{h}_mean_d"] == 0 else
                ("better" if row[f"h{h}_mean_d"] < 0 else "worse") + ("*" if row[f"h{h}_p"] < 0.05 else "")
                for h in (1, 12))
            comp.append(row)
    # the Remainder leaf (non-metro areas + non-member metros), scored on its own
    rem = int(np.where(is_rem & (level == 3))[0][0])
    r_naive = mx.level_rmsse(fc[methods.index("naive")], act, sc, [rem])
    remainder = [{"method": m, "rmsse_1_12": mx.level_rmsse(fc[i], act, sc, [rem]),
                  "rel_to_no_change": mx.level_rmsse(fc[i], act, sc, [rem]) / r_naive}
                 for i, m in enumerate(methods)]
    return pd.DataFrame(head), pd.DataFrame(byh), pd.DataFrame(comp), pd.DataFrame(remainder)


def fmt_headline(df):
    out = ["| Level (nodes) | Method | RMSSE h1–12 | vs no-change | MAE h1–12 (listings) | Mean incoherence | Negative fcst |",
           "|---|---|---:|---:|---:|---:|---:|"]
    for _, r in df.iterrows():
        inc = "—" if pd.isna(r.get("incoherence_mean")) else (
            "0" if r.incoherence_max < 1e-9 else f"{100 * r.incoherence_mean:.2f}%")
        out.append(f"| {r.level} ({r.n_nodes}) | {LABEL[r.method]} | {r.rmsse_1_12:.3f} | {r.rel_to_no_change:.3f} | "
                   f"{r.mae_1_12:,.1f} | {inc} | {100 * r.share_negative:.2f}% |")
    return "\n".join(out)


def fmt_compact(df):
    """Level x method matrix of RMSSE (relative to no-change in brackets)."""
    order = ["base", "bu", "td", "ols", "wls_struct", "mint_shrink", "snaive", "naive"]
    out = ["| Level | " + " | ".join(LABEL[m] for m in order) + " |", "|---|" + "---:|" * len(order)]
    for lname in LEVELS:
        d = df[df.level == lname].set_index("method")
        best = d.drop(index="naive").rmsse_1_12.idxmin()
        cells = []
        for m in order:
            c = f"{d.loc[m, 'rmsse_1_12']:.3f} ({d.loc[m, 'rel_to_no_change']:.2f})"
            cells.append(f"**{c}**" if m == best else c)
        out.append(f"| {lname} ({int(d.n_nodes.iloc[0])}) | " + " | ".join(cells) + " |")
    return "\n".join(out)


def _wp(r, h):
    if r[f"h{h}_mean_d"] == 0:
        return "identical forecasts"
    return f"{r[f'h{h}_A_wins_of_24']}/24, {r[f'h{h}_p']:.3f}"


def fmt_cross(rows):
    """Across the three specifications: base, bottom-up and MinT-shrink, and which method was best per level."""
    out = ["| Specification | Level | Best non-baseline method | Base RMSSE | Bottom-up / base | MinT-shrink / base | MinT-shrink vs base | Best overall incl. seasonal naive |",
           "|---|---|---|---:|---:|---:|---:|---|"]
    for r in rows:
        out.append(f"| {r['spec']} | {r['level']} | {LABEL[r['best_model']]} | {r['base']:.3f} | {r['bu_over_base']:.3f} | "
                   f"{r['mint_over_base']:.3f} | {100 * (r['mint_over_base'] - 1):+.1f}% | {LABEL[r['best_any']]} |")
    bu = np.array([r["bu_over_base"] for r in rows]); mt = np.array([r["mint_over_base"] for r in rows])
    out += ["", f"Across {len(rows)} specification x level cells: bottom-up RMSSE <= base in {int((bu <= 1 + 1e-12).sum())}, "
                f"worst bottom-up / base {bu.max():.3f}; MinT-shrink RMSSE < base in {int((mt < 1).sum())}, "
                f"> base in {int((mt > 1).sum())}; MinT-shrink was the best non-baseline method in "
                f"{sum(r['best_model'] == 'mint_shrink' for r in rows)}, bottom-up in "
                f"{sum(r['best_model'] == 'bu' for r in rows)}."]
    return "\n".join(out)


def cross_rows(spec, head):
    rows = []
    for lname in LEVELS:
        d = head[head.level == lname].set_index("method").rmsse_1_12
        rows.append({"spec": spec, "level": lname, "base": d["base"],
                     "bu_over_base": d["bu"] / d["base"], "mint_over_base": d["mint_shrink"] / d["base"],
                     "best_model": d.drop(index=["naive", "snaive"]).idxmin(),
                     "best_any": d.drop(index="naive").idxmin()})
    return rows


def fmt_comp(df):
    out = ["| Test | Level | A vs B | RMSSE A / B | h=1: A wins, p | h=12: A wins, p | A at h=1 / h=12 | Verdict (plan §7) |",
           "|---|---|---|---:|---:|---:|---|---|"]
    for _, r in df.iterrows():
        out.append(f"| {r.comparison} | {r.level} | {LABEL[r.A]} vs {LABEL[r.B]} | {r.rmsse_A:.3f} / {r.rmsse_B:.3f} | "
                   f"{_wp(r, 1)} | {_wp(r, 12)} | "
                   f"{r.direction} | {r.verdict} |")
    return "\n".join(out)


def fmt_horizon(byh, methods=("base", "bu", "mint_shrink", "snaive"), hs=(1, 3, 6, 12)):
    out = ["| Level | Method | " + " | ".join(f"h={h}" for h in hs) + " |", "|---|---|" + "---:|" * len(hs)]
    for lname in LEVELS:
        for m in methods:
            d = byh[(byh.level == lname) & (byh.method == m)].set_index("h")
            out.append(f"| {lname} | {LABEL[m]} | " + " | ".join(f"{d.loc[h, 'rel_to_no_change']:.2f}" for h in hs) + " |")
    out.append("")
    for m in methods[:3]:
        a = byh[(byh.method == m) & (byh.h <= 6)].rel_to_no_change
        b = byh[(byh.method == m) & (byh.h == 12)].rel_to_no_change
        out.append(f"- {LABEL[m]}, all four levels: h = 1–6 range {a.min():.2f}–{a.max():.2f} of no-change; "
                   f"h = 12 range {b.min():.2f}–{b.max():.2f}.")
    return "\n".join(out)


def fmt_facts(s):
    """Data facts quoted in the memo's prose, formatted once here."""
    cw, br = s["crosswalk"], s["coverage_break_flags_first_training_window"]
    lo, hi = s["remainder_share_of_us_full_data"]
    rows = [("Zillow metros in file", f"{s['n_metros_in_file']}"),
            ("member metros (complete 2018-03 to first origin - 1)", f"{s['n_members']}"),
            ("nodes / leaves", f"{s['n_nodes']} / {s['n_leaves']}"),
            ("nodes per level (excl. Remainder)", ", ".join(f"{k} {v}" for k, v in s["nodes_per_level"].items())),
            ("Remainder share of US, full data", f"{100 * lo:.1f}%–{100 * hi:.1f}%"),
            ("member cells carried forward, full data", f"{s['cells_carried_forward_full_data']}"),
            ("training months per origin", f"{s['train_months_range'][0]}–{s['train_months_range'][1]}"),
            ("MinT shrinkage lambda range", f"{s['shrinkage_lambda_range'][0]:.2f}–{s['shrinkage_lambda_range'][1]:.2f}"),
            ("members matched to a 2023 CBSA", f"{cw['matched']} of {cw['members']} ({cw['matched_metro']} metropolitan, "
                                                f"{cw['matched_micro']} micropolitan)"),
            ("matched members whose state = CBSA title's first state", f"{cw['state_agrees_with_cbsa_first_state']}"),
            ("coverage-break flags (first training window, not masked)",
             f"{br['level_shifts']} level shifts, {br['spikes']} spikes, {br['members_flagged']} members"),
            ("backtest runtime", f"{s['runtime_secs'] / 60:.1f} min")]
    return "\n".join(["| Fact | Value |", "|---|---|"] + [f"| {k} | {v} |" for k, v in rows])


def fmt_remainder(rem):
    out = ["| Method | RMSSE h1–12 | vs no-change |", "|---|---:|---:|"]
    out += [f"| {LABEL[r.method]} | {r.rmsse_1_12:.3f} | {r.rel_to_no_change:.3f} |" for _, r in rem.iterrows()]
    return "\n".join(out)


def figure(byh, path, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    series = [("base", "#2a78d6"), ("bu", "#eb6834"), ("mint_shrink", "#1baf7a")]   # seasonal naive: tables only
    fig, axes = plt.subplots(1, 4, figsize=(13, 4.0), sharey=True, facecolor="#fcfcfb")
    for ax, lname in zip(axes, LEVELS):
        ax.set_facecolor("#fcfcfb")
        ax.axhline(1, color="#8a8984", lw=1.2, ls=(0, (4, 3)))
        for m, col in series:
            d = byh[(byh.level == lname) & (byh.method == m)].sort_values("h")
            ax.plot(d.h, d.rel_to_no_change, color=col, lw=2, label=LABEL[m])
        ax.set_title(lname, fontsize=11, color="#0b0b0b", loc="left")
        ax.set_xticks([1, 3, 6, 9, 12]); ax.set_xlabel("horizon (months)", fontsize=9, color="#52514e")
        ax.tick_params(colors="#52514e", labelsize=8.5)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color("#c8c7c1")
        ax.grid(axis="y", color="#e6e5e0", lw=0.8)
    axes[0].set_ylabel("RMSSE relative to no-change", fontsize=9, color="#52514e")
    axes[0].text(4.2, 1.02, "no-change = 1", fontsize=8, color="#52514e", va="bottom")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper left", bbox_to_anchor=(0.005, 0.925), ncol=3, frameon=False, fontsize=9)
    fig.suptitle(title, x=0.01, y=0.985, ha="left", fontsize=12, color="#0b0b0b")
    fig.text(0.01, 0.01, f"{ATTRIBUTION}. Below 1 = better than no-change. 24 monthly origins, 2023-11 to 2025-10.",
             fontsize=8, color="#52514e")
    fig.tight_layout(rect=(0, 0.04, 1, 0.86))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    TABLES.mkdir(parents=True, exist_ok=True); FIGURES.mkdir(parents=True, exist_ok=True)
    blocks, headlines, cross = {}, {}, []
    for target, base, title in RUNS:
        tag = f"{target}_{base}"
        if not (TMP / f"bt_{tag}.npz").exists():
            print(f"skip {tag}: no backtest output"); continue
        head, byh, comp, rem = score(tag)
        head.to_csv(TABLES / f"{tag}_headline.csv", index=False)
        byh.to_csv(TABLES / f"{tag}_by_horizon.csv", index=False)
        comp.to_csv(TABLES / f"{tag}_comparisons.csv", index=False)
        rem.to_csv(TABLES / f"{tag}_remainder.csv", index=False)
        cross += cross_rows(title.split(":")[0], head)
        blocks[f"compact_{tag}"] = fmt_compact(head)
        blocks[f"headline_{tag}"] = fmt_headline(head)
        blocks[f"comparisons_{tag}"] = fmt_comp(comp)
        blocks[f"horizon_{tag}"] = fmt_horizon(byh)
        blocks[f"remainder_{tag}"] = fmt_remainder(rem)
        summ = json.loads((TABLES / f"data_summary_{tag}.json").read_text())
        blocks[f"facts_{tag}"] = fmt_facts(summ)
        headlines[tag] = {"title": title, "data": summ,
                          "headline": head.round(6).to_dict("records"),
                          "comparisons": comp.round(6).to_dict("records"),
                          "remainder": rem.round(6).to_dict("records")}
        if tag == "inventory_ets":
            figure(byh, FIGURES / "relative_rmsse_by_horizon_inventory_ets.png",
                   "For-sale inventory: forecast error relative to no-change, by level and horizon (AutoETS base)")
    if cross:
        pd.DataFrame(cross).to_csv(TABLES / "cross_spec_summary.csv", index=False)
        blocks["cross_spec"] = fmt_cross(cross)
        headlines["cross_spec"] = pd.DataFrame(cross).round(6).to_dict("records")
    xc = TABLES / "xcheck_nixtla_real_inventory_ets.json"
    if xc.exists():
        x = json.loads(xc.read_text())
        rows = [f"| {LABEL[k]} | {v['max_abs_diff_listings']:.1e} | {v['max_rel_diff']:.1e} |" for k, v in x["methods"].items()]
        blocks["xcheck_nixtla"] = "\n".join(
            [f"Own reconciliation vs hierarchicalforecast 1.5.3 MinTrace, origin {x['origin']}, {x['nodes']} nodes.", "",
             "| Method | Max abs. difference (listings) | Max rel. difference |", "|---|---:|---:|"] + rows)
        headlines["xcheck_nixtla"] = x
    (REPO / "reports" / "headlines.json").write_text(json.dumps(headlines, indent=2))
    md = ["# Results tables (generated by scripts/make_report.py; do not edit by hand)", ""]
    for k, v in blocks.items():
        md += [f"## {k}", "", v, ""]
    (REPO / "reports" / "results_tables.md").write_text("\n".join(md))
    memo = REPO / "reports" / "memo.md"
    if memo.exists():
        txt = memo.read_text()
        for k, v in blocks.items():
            txt = re.sub(rf"(<!-- BEGIN:{k} -->\n).*?(<!-- END:{k} -->)", lambda m: m.group(1) + v + "\n" + m.group(2),
                         txt, flags=re.S)
        left = sorted(set(re.findall(r"<!-- BEGIN:(\w+) -->\n<!-- END:", txt)))
        if left:
            raise SystemExit(f"memo blocks with no generated table: {left}")
        memo.write_text(txt)
    print("wrote", ", ".join(blocks))


if __name__ == "__main__":
    main()
