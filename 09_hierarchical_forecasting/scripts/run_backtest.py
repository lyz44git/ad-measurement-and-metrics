"""Run one backtest specification and save its forecasts to tmp/ (derived from Zillow data: never committed).

usage: python scripts/run_backtest.py --target inventory --base ets
Refuses to run if docs/pre_analysis_plan.md no longer matches its recorded SHA-256."""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hierfc import backtest, data, quality  # noqa: E402
from hierfc.paths import PAP, PAP_HASH, TABLES, TMP, VINTAGE  # noqa: E402


def check_pap() -> str:
    want = PAP_HASH.read_text().split()[0]
    got = hashlib.sha256(PAP.read_bytes()).hexdigest()
    if want != got:
        sys.exit(f"pre-analysis plan changed after it was hashed ({got} != {want}); log a deviation instead")
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["inventory", "new_listings"], required=True)
    ap.add_argument("--base", choices=["ets", "arima"], default="ets")
    ap.add_argument("--jobs", type=int, default=8)
    args = ap.parse_args()
    pap = check_pap()
    TMP.mkdir(exist_ok=True); TABLES.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    warnings.simplefilter("ignore")
    res = backtest.run(args.target, args.base, n_jobs=args.jobs)
    hier = res["hier"]
    tag = f"{args.target}_{args.base}"
    np.savez_compressed(TMP / f"bt_{tag}.npz", fc=res["fc"], actual=res["actual"], scale=res["scale"],
                        level=hier.level, is_rem=hier.is_rem, nodes=np.array(hier.nodes),
                        methods=np.array(res["methods"]), origins=np.array(res["origins"]))
    (TMP / f"bt_{tag}_children.json").write_text(json.dumps({str(k): [int(x) for x in v]
                                                              for k, v in hier.children.items()}))
    res["diag"].to_csv(TMP / f"bt_{tag}_diag.csv", index=False)

    # aggregate-only description of the data (counts and shares; no series values)
    src = data.load_source(args.target)
    _, L0, _, _, _ = backtest.origin_inputs(src, hier, backtest.FIRST_ORIGIN)
    summary = {
        "target": args.target, "base": args.base, "vintage": VINTAGE, "pap_sha256": pap,
        "data_window": [data.ym_str(data.START), data.ym_str(backtest.LAST_ORIGIN - 1 + backtest.H)],
        "n_origins": len(res["origins"]), "first_origin": res["origins"][0], "last_origin": res["origins"][-1],
        "n_metros_in_file": int(src[src.region != data.US].region.nunique()),
        "n_members": int(len(res["members"])), "n_nodes": int(hier.n), "n_leaves": int(hier.m),
        "nodes_per_level": {lv: int(((hier.level == i) & ~hier.is_rem).sum())
                            for i, lv in enumerate(["US", "division", "state", "metro"])},
        "cells_carried_forward_full_data": int(res["n_filled_full"]),
        "remainder_share_of_us_full_data": [float(res["rem_share_full"].min()), float(res["rem_share_full"].max())],
        "shrinkage_lambda_range": [float(res["diag"]["lambda"].min()), float(res["diag"]["lambda"].max())],
        "train_months_range": [int(res["diag"]["T"].min()), int(res["diag"]["T"].max())],
        "coverage_break_flags_first_training_window": quality.flag_breaks(L0[:-1]),
        "crosswalk": quality.crosswalk_summary(res["members"]),
        "runtime_secs": round(time.time() - t0, 1),
    }
    (TABLES / f"data_summary_{tag}.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
