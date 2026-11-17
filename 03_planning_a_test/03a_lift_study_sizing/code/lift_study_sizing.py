"""Power and false-positive rates of lift studies at survey-scale sample sizes, by resampling a completed experiment.

Usage: python code/lift_study_sizing.py [path to study 01b's out/part1_overall.json] [out_dir]
Needs only the arm sizes and visit counts of the Criteo experiment, which study 01b writes to part1_overall.json.
Site visit is the binary response; there are no survey data.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SIZES = (1000, 2500, 5000, 10000, 20000)
Z = 1.959964


def readout(a, b, n, lift_true, rng, draws=5000):
    """Frequentist and Bayesian readouts of many two-arm studies with n users per arm.

    a, b: successes in the exposed and control arm of each study. Returns the share of studies in which the z-test
    rejects at 5%, the share whose 95% interval covers lift_true, the share with posterior P(lift > 0) > 0.95 under
    Beta(1, 1) priors, and the share with a significant positive difference.
    """
    pa, pb = a / n, b / n
    diff = pa - pb
    se = np.sqrt(pa * (1 - pa) / n + pb * (1 - pb) / n)
    rej = np.abs(diff) > Z * np.maximum(se, 1e-12)
    cover = np.abs(diff - lift_true) <= Z * se
    post = (rng.beta(1 + a[:, None], 1 + n - a[:, None], (len(a), draws))
            > rng.beta(1 + b[:, None], 1 + n - b[:, None], (len(a), draws))).mean(1)
    return float(rej.mean()), float(cover.mean()), float((post > 0.95).mean()), float(((diff > 0) & rej).mean())


def size_studies(n1, k1, n0, k0, sizes=SIZES, studies=2000, seed=20261115):
    """Resample `studies` lift studies per size from an experiment with k1 of n1 exposed-arm and k0 of n0 control-arm
    users responding. Drawing n users without replacement from an arm gives a hypergeometric number of responders.
    A/A studies draw both arms from the control arm."""
    rng = np.random.default_rng(seed)
    truth = k1 / n1 - k0 / n0
    out = {"truth_lift": truth, "rate_control": k0 / n0, "rate_treated": k1 / n1, "studies_per_n": studies, "by_n": {}}
    for n in sizes:
        a = rng.hypergeometric(k1, n1 - k1, n, studies); b = rng.hypergeometric(k0, n0 - k0, n, studies)
        power, cover, bdet, pos = readout(a, b, n, truth, rng)
        a0 = rng.hypergeometric(k0, n0 - k0, n, studies); b0 = rng.hypergeometric(k0, n0 - k0, n, studies)
        fp, _, bfp, _ = readout(a0, b0, n, 0.0, rng)
        out["by_n"][n] = {"power_z": power, "power_z_positive": pos, "coverage95": cover, "bayes_detect": bdet,
                          "aa_false_positive_z": fp, "aa_false_positive_bayes": bfp}
    ok = [n for n, v in out["by_n"].items() if v["power_z"] >= 0.8]
    out["smallest_n_power80"] = min(ok) if ok else None
    return out


def main(src, out_dir):
    v = json.load(open(src))["visit"]
    res = size_studies(v["n1"], round(v["rate1"] * v["n1"]), v["n0"], round(v["rate0"] * v["n0"]))
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    json.dump(res, open(Path(out_dir) / "lift_study_sizing.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    default = ROOT.parents[1] / "01_with_an_experiment" / "01b_bayesian_segment_effects" / "out" / "part1_overall.json"
    main(sys.argv[1] if len(sys.argv) > 1 else default, sys.argv[2] if len(sys.argv) > 2 else ROOT / "out")
