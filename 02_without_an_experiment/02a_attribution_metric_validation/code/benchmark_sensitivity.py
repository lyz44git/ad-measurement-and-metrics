"""Estimated additional outcomes under the unadjusted and the regression-adjusted assignment effect.

Added after the main run. Reads the committed out/attribution_vs_experiment.json and study 01a's
out/criteo/a_incrementality.json; needs no raw data. The primary result stays the unadjusted one. Intervals are 95%
normal intervals for the estimated additional outcomes only; no interval is computed for the ratio to the exposure
count, which would need the joint uncertainty of both terms.

Usage: python code/benchmark_sensitivity.py
Writes out/benchmark_sensitivity.json.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDY01 = ROOT.parents[1] / "01_with_an_experiment" / "01a_ad_incrementality"


def summarize(est, se, n1, attributed):
    inc = est * n1
    return {"additional": inc, "ci95": [(est - 1.96 * se) * n1, (est + 1.96 * se) * n1],
            "attributed": attributed, "attributed_over_additional": attributed / inc}


def main():
    a = json.loads((ROOT / "out" / "attribution_vs_experiment.json").read_text())
    b = json.loads((STUDY01 / "out" / "criteo" / "a_incrementality.json").read_text())
    n1 = a["n_treated"]
    res = {o: {"unadjusted": summarize(b[o]["itt"]["est"], b[o]["itt"]["se"], n1, a[o]["attributed"]),
               "regression_adjusted": summarize(b[o]["aipw_linear"]["est"], b[o]["aipw_linear"]["se"], n1,
                                                a[o]["attributed"])}
           for o in ("visit", "conversion")}
    json.dump(res, open(ROOT / "out" / "benchmark_sensitivity.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
