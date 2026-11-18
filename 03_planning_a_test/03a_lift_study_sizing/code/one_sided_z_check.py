"""One-sided z-test on the same simulated studies as part 1, added after review.

Re-runs lift_study_sizing.size_studies with its seed (same draws, same results) and also records, for each study, a
one-sided z-test at 5% (difference > 1.645 x SE), so the z-test and the one-sided Bayesian rule can be compared with
the same direction and level. Does not change lift_study_sizing.py or out/lift_study_sizing.json.

Usage: python code/one_sided_z_check.py [path to study 01b's out/part1_overall.json] [out_dir]
Output: out/one_sided_z_check.json
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lift_study_sizing as lss

Z1 = 1.644854
_records = []
_orig = lss.readout


def readout(a, b, n, lift_true, rng, draws=5000):
    pa, pb = a / n, b / n
    se = np.sqrt(pa * (1 - pa) / n + pb * (1 - pb) / n)
    _records.append(float(((pa - pb) > Z1 * np.maximum(se, 1e-12)).mean()))
    return _orig(a, b, n, lift_true, rng, draws)


def main(src, out_dir):
    lss.readout = readout
    v = json.load(open(src))["visit"]
    res = lss.size_studies(v["n1"], round(v["rate1"] * v["n1"]), v["n0"], round(v["rate0"] * v["n0"]))
    for j, n in enumerate(res["by_n"]):   # readout is called twice per size: real lift, then A/A
        res["by_n"][n]["power_z_one_sided"] = _records[2 * j]
        res["by_n"][n]["aa_false_positive_z_one_sided"] = _records[2 * j + 1]
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    json.dump(res, open(Path(out_dir) / "one_sided_z_check.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    default = lss.ROOT.parents[1] / "01_with_an_experiment" / "01b_bayesian_segment_effects" / "out" / "part1_overall.json"
    main(sys.argv[1] if len(sys.argv) > 1 else default, sys.argv[2] if len(sys.argv) > 2 else lss.ROOT / "out")
