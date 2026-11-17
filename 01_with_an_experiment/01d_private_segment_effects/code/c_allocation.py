"""Part C: spend allocation across segments by estimated incremental lift against response rate.

Usage: python code/c_allocation.py <criteo_compact.parquet> [out_dir] [out_dir of study 01b]
Reads the stored segment estimates of study 01b (part2_segments.json and its rerun file).
"""
import json
import sys
from pathlib import Path

import duckdb
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from private_core import share_captured  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RULES = ("multilevel", "nopool", "response", "oracle")


def main(src, out, seg_out):
    p2 = json.load(open(Path(seg_out) / "part2_segments.json"))
    p2.update(json.load(open(Path(seg_out) / "part2_segments_rerun.json")))
    ctrl = duckdb.sql(f"select rep, seg, avg(visit) r from '{src}' where treatment=0 and rep<10 group by all").df()
    res = {}
    for B in (10, 20, 30):
        sh = {k: [] for k in RULES}
        for r in map(str, range(10)):
            g = p2[r]["seg"]; bench = np.array(g["bench"])
            resp = np.zeros(100); c = ctrl[ctrl.rep == int(r)]; resp[c.seg.to_numpy()] = c.r.to_numpy()
            for k, x in (("multilevel", np.array(g["bayes"])), ("nopool", np.array(g["nopool"])), ("response", resp),
                         ("oracle", bench)):
                sh[k].append(share_captured(x, bench, B))
        a = {k: np.array(v) for k, v in sh.items()}
        res[B] = {"mean_share": {k: float(v.mean()) for k, v in a.items()}, "random": B / 100,
                  "ml_ge_nopool": int((a["multilevel"] >= a["nopool"]).sum()),
                  "ml_gt_response": int((a["multilevel"] > a["response"]).sum()),
                  "nopool_gt_response": int((a["nopool"] > a["response"]).sum())}
    res["rule_met"] = all(res[B]["ml_gt_response"] >= 8 for B in (10, 20, 30))
    Path(out).mkdir(exist_ok=True)
    json.dump(res, open(Path(out) / "c_allocation.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ROOT / "out",
         sys.argv[3] if len(sys.argv) > 3 else ROOT.parent / "01b_bayesian_segment_effects" / "out")
