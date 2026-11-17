"""Checks of the lift-study sizing simulation on a made-up experiment (no data needed)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
import lift_study_sizing as ls

N = 2_000_000


def run(k1, sizes=(500, 4000), studies=600):
    return ls.size_studies(N, k1, N, 80_000, sizes=sizes, studies=studies, seed=1)   # control rate 4%


def test_power_rises_with_sample_size_and_intervals_cover():
    r = run(100_000)["by_n"]                                   # true lift 1 point on a 4% base
    assert r[4000]["power_z"] > r[500]["power_z"] + 0.2
    assert r[4000]["bayes_detect"] > r[500]["bayes_detect"]
    for n in r:
        assert 0.92 <= r[n]["coverage95"] <= 0.98


def test_no_true_lift_gives_about_five_percent_rejections():
    r = run(80_000)["by_n"]
    for n in r:
        assert r[n]["power_z"] < 0.09 and r[n]["aa_false_positive_z"] < 0.09 and r[n]["aa_false_positive_bayes"] < 0.09


def test_smallest_size_with_80_percent_power_is_reported():
    r = run(120_000, sizes=(500, 4000, 16000))                 # true lift 2 points
    assert r["smallest_n_power80"] == 4000 and r["by_n"][500]["power_z"] < 0.8
