"""Checks of the bid-time features, the budgeted purchase and the comparison metrics on small simulated data."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
import bidding_core as bc
from mta import build_paths


def log(n_users=400, seed=0):
    rng = np.random.default_rng(seed); rows = []
    for u in range(n_users):
        k = rng.integers(1, 6); ts = np.sort(rng.integers(0, 20 * 86400, k))
        conv = rng.random() < 0.3; tc = ts[-1] + 3600 if conv else -1
        last_click = -1
        for t in ts:
            click = int(rng.random() < 0.3)
            rows.append(dict(timestamp=int(t), uid=u, campaign=int(rng.integers(0, 5)), conversion=int(conv),
                             conversion_timestamp=int(tc), conversion_id=u if conv else -1, click=click,
                             cost=float(rng.choice([1e-5, 5e-5, 2e-4])),
                             time_since_last_click=int(t - last_click) if last_click >= 0 else -1))
            if click:
                last_click = t
    return pd.DataFrame(rows)


def test_credits_sum_to_one_per_converting_path_and_are_zero_elsewhere():
    p = bc.add_credits(build_paths(log()), lam=0.1)
    s = p.groupby("uid")[list(bc.RULES)].sum()
    y = p.groupby("uid").y.first()
    assert np.allclose(s[y == 1], 1.0) and np.allclose(s[y == 0], 0.0)
    assert (p.loc[p.y == 1, "cr_last"] == p.loc[p.y == 1, "is_last"]).all()


def test_features_use_only_the_past():
    p = build_paths(log(seed=1))
    X = bc.features(p)
    q = p.copy()
    last = q.groupby("uid").tail(1).index
    q.loc[last, "click"] = 1 - q.loc[last, "click"]           # change what happens at each user's last impression
    assert bc.features(q).equals(X)                           # no feature of any impression changes
    first = p.groupby("uid").head(1).index
    assert (X.loc[first, "n_prev"] == 0).all() and X.loc[first, "gap_prev"].isna().all()
    assert (X.loc[first, "clicks_prev"] == 0).all()


def test_buy_takes_best_value_per_cost_within_budget():
    score = np.array([0.9, 0.5, 0.4, 0.1]); cost = np.array([3.0, 1.0, 1.0, 1.0])
    b = bc.buy(score, cost, 0.5)          # budget 3; value per cost 0.3, 0.5, 0.4, 0.1; item 0 (cost 3) no longer fits
    assert b.tolist() == [False, True, True, False] and cost[b].sum() <= 3.0
    assert bc.buy(score, cost, 1.0).all() and not bc.buy(score, cost, 0.0).any()


def test_compare_on_a_case_with_a_known_answer():
    # four users, one impression each; the two rules put the credit on different impressions
    credit = {"cr_last": np.array([1.0, 1.0, 0.0, 0.0]), "cr_decay": np.array([1.0, 0.0, 1.0, 0.0])}
    bought = {"cr_last": np.array([True, True, False, False]), "cr_decay": np.array([True, False, True, False])}
    cost = np.ones(4); user = np.arange(4); w = np.ones((5, 4))
    r = bc.compare(bought, credit, cost, user, w, {"all": np.ones(4, dtype=bool)})
    assert r["captured"]["cr_last"]["cr_last"][0] == 1.0 and r["captured"]["cr_decay"]["cr_last"][0] == 0.5
    assert r["cross_rule_loss"]["cr_last"][0] == 0.5 and r["cross_rule_loss"]["cr_decay"][0] == 0.5
    assert r["spend_overlap"] == 0.5 and r["spend_share"]["cr_last"] == 0.5
    assert bc.decision(r) and not bc.decision({"cross_rule_loss": {"cr_last": (0.5, 0.2, 0.7), "cr_decay": (0.02, 0.01, 0.03)}})
