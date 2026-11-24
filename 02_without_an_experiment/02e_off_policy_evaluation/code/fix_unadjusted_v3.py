"""Replace the "unadjusted" column of ope_v3.json's benchmark (design/erratum.md, item 2).

run_ope_v3.py first wrote, as "unadjusted", the difference between rows whose assignment agrees with the policy and
control rows, which is not a policy value for a policy that treats only some users. The unadjusted value of the
earlier designs is IPS with the experiment's constant assignment share (ope_core.truth); this script computes it on
the same pool and writes it in place. No other number changes.

Usage: python code/fix_unadjusted_v3.py <criteo-research-uplift-v2.1.csv.gz> [out_dir]
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import design_calc_v3 as dc  # noqa: E402
import ope_core as oc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main(src, out):
    out = Path(out); f = out / "ope_v3.json"; R = json.loads(f.read_text())
    X, a, y, z, r, acts, thr, pool, trim = dc.setup(src)
    assert int(pool.sum()) == R["pool_rows"]
    a, y = a[pool], y[pool]
    for p in oc.POLICIES:
        R["benchmark"][p]["unadjusted_as_first_written"] = R["benchmark"][p]["unadjusted"]
        R["benchmark"][p]["unadjusted"] = 1000 * oc.truth(y, a, acts[p][pool])[0]
    f.write_text(json.dumps(R, indent=1))
    print({p: round(v["unadjusted"], 3) for p, v in R["benchmark"].items()})


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ROOT / "out")
