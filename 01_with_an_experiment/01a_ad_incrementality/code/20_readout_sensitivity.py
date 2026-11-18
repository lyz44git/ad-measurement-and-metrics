"""Sensitivity of two readout numbers to choices made in the main run. Uses committed result files only.

1. Estimator for the conversion count. The headline (study 02a) multiplies the unadjusted difference in conversion
   rates by the 11,882,655 records in the ad arm. Here the same product is formed with the regression-adjusted (AIPW)
   difference of the main run, and both are set against the 23,031 conversions credited by the exposure count.
   Intervals are given for the counts only (difference +/- 1.96 SE, times the fixed arm size). No interval is given
   for the ratio of credited to estimated conversions: that needs the joint uncertainty of numerator and
   denominator.
2. Standard error of the effect per exposed user. The main run divides the standard error of the effect of
   assignment by the exposure share, which treats the share as known. Here a delta-method standard error that also
   counts the sampling error of the share, and its covariance with the ad-arm outcome rate, is computed from the
   aggregate counts of study 01c (records independent; no user identifier).

Inputs : out/criteo/a_incrementality.json (this study),
         ../../02_without_an_experiment/02a_attribution_metric_validation/out/attribution_vs_experiment.json,
         ../01c_sql_metric_readout/out/readout.json
Output : out/criteo/readout_sensitivity.json (new file; no existing output is changed)
Usage  : python code/20_readout_sensitivity.py      (from the study folder; runs in under a second)
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
A = HERE / "out/criteo/a_incrementality.json"
B = HERE.parents[1] / "02_without_an_experiment/02a_attribution_metric_validation/out/attribution_vs_experiment.json"
C = HERE.parent / "01c_sql_metric_readout/out/readout.json"
OUT = HERE / "out/criteo/readout_sensitivity.json"
Z = 1.959963984540054


def count_row(est, se, n1, credited):
    inc = est * n1
    return {"difference": est, "se": se, "estimated_additional": inc,
            "ci95": [(est - Z * se) * n1, (est + Z * se) * n1],
            "credited": credited, "credited_over_estimated": credited / inc,
            "excess": credited - inc, "excess_over_estimated": (credited - inc) / inc,
            "excess_over_credited": (credited - inc) / credited}


def cace_delta(arm0, arm1, outcome, itt, itt_se):
    """Delta-method SE of itt / pi, pi = exposure share of the ad arm, with Cov(ad-arm outcome rate, pi)."""
    n1 = arm1["users"]
    pi = arm1["exposed_users"] / n1
    p_y = arm1[outcome + "s"] / n1
    p_yd = arm1[outcome + "s_of_exposed_users"] / n1
    var_pi = pi * (1 - pi) / n1
    cov = (p_yd - p_y * pi) / n1                       # Cov(ad-arm outcome rate, pi); control arm has no exposure
    est = itt / pi
    var = itt_se ** 2 / pi ** 2 + itt ** 2 * var_pi / pi ** 4 - 2 * itt * cov / pi ** 3
    return {"est": est, "se_fixed_share": itt_se / pi, "se_delta": math.sqrt(var), "exposure_share": pi}


def main():
    a = json.loads(A.read_text()); b = json.loads(B.read_text()); c = json.loads(C.read_text())
    n1 = a["conversion"]["itt"]["n1"]
    credited = b["conversion"]["attributed"]
    arm = {r["arm"]: r for r in c["by_arm"]}
    res = {
        "conversion_count": {
            "unadjusted": count_row(a["conversion"]["itt"]["est"], a["conversion"]["itt"]["se"], n1, credited),
            "regression_adjusted": count_row(a["conversion"]["aipw_linear"]["est"], a["conversion"]["aipw_linear"]["se"],
                                             n1, credited),
        },
        "effect_per_exposed_user": {
            "visit_unadjusted": cace_delta(arm[0], arm[1], "visit", a["visit"]["itt"]["est"], a["visit"]["itt"]["se"]),
            "conversion_unadjusted": cace_delta(arm[0], arm[1], "conversion", a["conversion"]["itt"]["est"],
                                                a["conversion"]["itt"]["se"]),
        },
        "notes": "Counts: difference x 11,882,655 ad-arm records; 95% interval = (difference +/- 1.96 SE) x records. "
                 "No interval for ratios. Delta-method SE assumes independent records.",
    }
    OUT.write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
