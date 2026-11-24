"""Accuracy of a single log in the second design, from the saved per-log estimates (design/erratum.md).

analysis_plan_v2.md asks for a mean absolute error below 10% of the benchmark. run_ope_v2.py compared the absolute
value of the mean error with 10%, a different quantity. This script computes both from out/ope_v2_logs.csv and
out/ope_v2.json and applies the rule as it is written. It reads no raw data and fits no model.

Usage: python code/accuracy_from_logs.py out
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ope_core as oc  # noqa: E402

RULES = {"1_known_propensity_ips": "ips_known", "2_dr_estimated_propensity": "dr"}


def main(out_dir):
    out = Path(out_dir); R = json.loads((out / "ope_v2.json").read_text())
    truth = {p: v["aipw_r"] / 1000 for p, v in R["truth_log_part"].items()}
    est = {}
    with open(out / "ope_v2_logs.csv") as f:
        for r in csv.DictReader(f):
            est.setdefault((r["setting"], r["policy"], r["estimator"]), []).append(float(r["estimate"]))
    res = {"benchmark": "AIPW with the estimated assignment probability on the log part (truth_log_part.aipw_r in ope_v2.json)",
           "settings": {}, "decision_as_written": {}}
    for (st, pol, k), x in sorted(est.items()):
        res["settings"].setdefault(st, {}).setdefault(pol, {})[k] = dict(oc.accuracy(x, truth[pol]), logs=len(x))
    for rule, k in RULES.items():
        by = {p: oc.rule_as_written(res["settings"]["moderate"][p][k], R["settings"]["moderate"]["summary"][p][k]["coverage95"])
              for p in oc.POLICIES}
        res["decision_as_written"][rule] = {
            "met": all(by.values()), "by_policy": by,
            "mean_absolute_error": {p: res["settings"]["moderate"][p][k]["mean_absolute_error"] for p in oc.POLICIES},
            "coverage95": {p: R["settings"]["moderate"]["summary"][p][k]["coverage95"] for p in oc.POLICIES},
            "as_computed_by_run_ope_v2": R["decision"][rule]["met"]}
    (out / "ope_v2_accuracy.json").write_text(json.dumps(res, indent=1))
    for rule, d in res["decision_as_written"].items():
        print(rule, "met as written:", d["met"], "| mean absolute error:", {p: round(v, 3) for p, v in d["mean_absolute_error"].items()})


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "out")
