"""Follow-up 2 of study 03d: do visits point to the right segments? (design/followup_plan_2.md)

Usage: python code/run_followup2.py <criteo-research-uplift-v2.1.csv.gz> [out_dir]
A few minutes; no model is fitted.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pyarrow.csv as pacsv

ROOT = Path(__file__).resolve().parents[1]
SEED, K, PICK, DRAWS = 20261124, 100, 20, 1000
N_TOTAL = 13_979_592
SIZES = {"1%": 0.01, "2%": 0.02, "5%": 0.05, "10%": 0.10, "20%": 0.20}
SEG_KEYS = ["f0", "f2", "f8", "f10", "f7", "f3"]


def log(msg, t0=[time.time()]):
    print(f"[{time.time() - t0[0]:6.0f}s] {msg}", flush=True)


def segments(cols):
    """ntile(100) over (order by f0, f2, f8, f10, f7, f3, file order) - 1, as in study 01b."""
    n = len(cols[0])
    order = np.lexsort([np.arange(n)] + [c for c in reversed(cols)])
    seg = np.empty(n, np.int16)
    seg[order] = (np.arange(n) * K // n).astype(np.int16)
    return seg


def counts(seg, t, v, c, w=None):
    """Per segment and arm: users, visits, conversions. Arrays [K, 2] (column 1 = ad arm)."""
    w = np.ones(len(seg)) if w is None else w
    key = seg.astype(np.int64) * 2 + t
    n = np.bincount(key, w, 2 * K).reshape(K, 2)
    nv = np.bincount(key, w * v, 2 * K).reshape(K, 2)
    nc = np.bincount(key, w * c, 2 * K).reshape(K, 2)
    return n, nv, nc


def effects(n, nv, nc):
    pv, pc = nv / n, nc / n
    return pv[:, 1] - pv[:, 0], pc[:, 1] - pc[:, 0], pv, pc


def corrected_corr(n, nv, nc):
    dv, dc, pv, pc = effects(n, nv, nc)
    s_vv = (pv * (1 - pv) / n).sum(1); s_cc = (pc * (1 - pc) / n).sum(1); s_vc = (pc * (1 - pv) / n).sum(1)
    C = np.cov(np.vstack([dv, dc]))
    vv, cc, vc = C[0, 0] - s_vv.mean(), C[1, 1] - s_cc.mean(), C[0, 1] - s_vc.mean()
    return {"corrected": float(vc / np.sqrt(vv * cc)) if vv > 0 and cc > 0 else float("nan"),
            "raw": float(np.corrcoef(dv, dc)[0, 1]),
            "signal_share_visit": float(vv / C[0, 0]), "signal_share_conversion": float(cc / C[1, 1])}


def main(src, out):
    out = Path(out)
    tab = pacsv.read_csv(src, convert_options=pacsv.ConvertOptions(
        include_columns=SEG_KEYS + ["treatment", "visit", "conversion"])).to_pandas()
    assert len(tab) == N_TOTAL
    seg = segments([tab[k].to_numpy(np.float64) for k in SEG_KEYS])
    t = tab.treatment.to_numpy(np.int64); v = tab.visit.to_numpy(np.float64); c = tab.conversion.to_numpy(np.float64)
    del tab
    hist = np.random.default_rng(SEED).random(N_TOTAL) < 0.5
    ex = ~hist
    log("segments built")

    # 1. direction on the experiment half
    n, nv, nc = counts(seg[ex], t[ex], v[ex], c[ex])
    dv, dc, pv, pc = effects(n, nv, nc)
    D = corrected_corr(n, nv, nc)
    rng = np.random.default_rng(SEED + 40)
    probs = np.stack([1 - pv, pv - pc, pc], -1)                  # [K, 2, 3]
    boot = []
    for _ in range(DRAWS):
        draw = np.empty_like(probs)
        for a in range(2):
            draw[:, a, :] = rng.multinomial(n[:, a].astype(np.int64), probs[:, a, :])
        bn = draw.sum(-1); bc = draw[..., 2]; bv = draw[..., 1] + bc
        boot.append(corrected_corr(bn, bv, bc)["corrected"])
    boot = np.array(boot)
    D["ci90"] = [float(np.nanquantile(boot, 0.05)), float(np.nanquantile(boot, 0.95))]
    D["draws_undefined"] = int(np.isnan(boot).sum())
    R = {"segments": K, "experiment_half_rows": int(ex.sum()), "direction": D,
         "segment_effects_experiment_half": {"visit_pp": (100 * dv).tolist(), "conversion_pp": (100 * dc).tolist()},
         "overall_conversion_effect_pp": float(100 * (c[ex & (t == 1)].mean() - c[ex & (t == 0)].mean()))}
    log(f"direction: {json.dumps(D)}")

    # 2. choosing segments from small samples of the historical half, scored on the experiment half
    bench = dc
    top_bench = np.sort(bench)[::-1][:PICK].mean()
    R["choice_reference_pp"] = {"random": float(bench.mean() * 100), "best_on_experiment_half": float(100 * top_bench)}
    hidx = np.flatnonzero(hist)
    rng = np.random.default_rng(SEED + 50)
    perm = rng.permutation(hidx)
    R["choice"] = {}
    for name, frac in SIZES.items():
        m = int(round(frac * N_TOTAL))
        res = []
        for k in range(20):
            if name == "2%":
                idx = perm[k * m:(k + 1) * m]
            else:
                idx = rng.choice(hidx, m, replace=False)
            sn, snv, snc = counts(seg[idx], t[idx], v[idx], c[idx])
            sdv, sdc, _, _ = effects(sn, snv, snc)
            by_v = np.argsort(-sdv, kind="stable")[:PICK]; by_c = np.argsort(-sdc, kind="stable")[:PICK]
            res.append({"by_visit": float(100 * bench[by_v].mean()), "by_conversion": float(100 * bench[by_c].mean()),
                        "overlap": int(len(set(by_v) & set(by_c)))})
        bv_ = np.array([r["by_visit"] for r in res]); bc_ = np.array([r["by_conversion"] for r in res])
        R["choice"][name] = {"users": m, "draws": res, "mean_by_visit": float(bv_.mean()), "mean_by_conversion": float(bc_.mean()),
                             "visit_higher_in": int((bv_ > bc_).sum()),
                             "share_of_gain_by_visit": float((bv_.mean() - R["choice_reference_pp"]["random"]) /
                                                             (R["choice_reference_pp"]["best_on_experiment_half"] - R["choice_reference_pp"]["random"])),
                             "share_of_gain_by_conversion": float((bc_.mean() - R["choice_reference_pp"]["random"]) /
                                                                  (R["choice_reference_pp"]["best_on_experiment_half"] - R["choice_reference_pp"]["random"]))}
        log(f"{name}: by visit {bv_.mean():.4f} pp, by conversion {bc_.mean():.4f} pp, visit higher in {(bv_ > bc_).sum()}/20")
    two = R["choice"]["2%"]
    R["decision"] = {
        "1_visits_point_the_same_way": {"met": bool(D["corrected"] >= 0.7 and D["ci90"][0] >= 0.5),
                                        "rule": "noise-corrected correlation >= 0.7 and lower end of its 90% interval >= 0.5"},
        "2_visits_choose_better_in_a_small_test": {"met": bool(two["mean_by_visit"] > two["mean_by_conversion"] and two["visit_higher_in"] >= 15),
                                                   "rule": "2% samples: higher mean conversion effect when chosen by visit effect, and higher in at least 15 of 20"}}
    R["seconds"] = round(time.time() - log.__defaults__[0][0])
    (out / "followup2.json").write_text(json.dumps(R, indent=1))
    log("decision " + json.dumps({k: v["met"] for k, v in R["decision"].items()}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ROOT / "out")
