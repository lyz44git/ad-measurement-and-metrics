"""Run the checks, the SQL readout, the reconciliation with studies 01a and 02a, and the sample-size table.

Usage: python code/run_readout.py <criteo-research-uplift-v2.1.csv.gz> [out_dir]
Studies 01a and 02a must have been run (their result files are read). Writes out/readout.json and three CSV files.
"""
import csv
import json
import sys
import time
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
import readout_core as rc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GROUPS = ROOT.parents[1]
S01A = GROUPS / "01_with_an_experiment" / "01a_ad_incrementality" / "out" / "criteo" / "a_incrementality.json"
S02A = GROUPS / "02_without_an_experiment" / "02a_attribution_metric_validation" / "out" / "attribution_vs_experiment.json"
ROWS = 13_979_592


def write_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main(src, out):
    out = Path(out); out.mkdir(exist_ok=True)
    t0 = time.time()
    con = duckdb.connect()
    con.execute("CREATE TABLE users AS SELECT * FROM read_csv_auto(?)", [str(src)])
    print(f"loaded in {time.time() - t0:.0f} s")
    counts, failed = rc.checks(con, ROWS)
    print("checks:", json.dumps(counts)); print("failed:", failed)
    if failed:
        raise SystemExit(f"data checks failed: {failed}")
    by_arm, eff = rc.readout(con)
    rec = rc.reconcile(by_arm, eff, json.loads(S01A.read_text()), json.loads(S02A.read_text()))
    size = rc.sizing(eff["visit"]["control_rate"], eff["conversion"]["control_rate"])
    res = dict(checks=counts, checks_failed=failed, by_arm=by_arm, effects=eff, reconciliation=rec,
               comparisons=len(rec), disagreements=[r["metric"] for r in rec if not r["agree"]],
               reconciled=all(r["agree"] for r in rec), sizing=size, seconds=round(time.time() - t0, 1))
    (out / "readout.json").write_text(json.dumps(res, indent=1))
    write_csv(out / "readout_by_arm.csv", by_arm)
    write_csv(out / "reconciliation.csv", rec)
    write_csv(out / "sample_size_by_endpoint.csv", size)
    print(json.dumps({k: res[k] for k in ("comparisons", "disagreements", "reconciled", "seconds")}))
    for r in by_arm:
        print(r)
    for r in eff.values():
        print(r)
    for r in size:
        print(r)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ROOT / "out")
