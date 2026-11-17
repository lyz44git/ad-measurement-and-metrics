"""Value labels, bid-time features, budgeted purchase sets and their comparison (design/analysis_plan.md)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "02b_multi_touch_attribution" / "code"))
from mta import rule_credits  # noqa: E402  (credit rules of study 02b)

RULES = ("cr_last", "cr_decay")
FEATURES = ["campaign", "tslc", "n_prev", "clicks_prev", "gap_prev", "hour"]


def add_credits(p, lam):
    """Last-touch and time-decay credit of every impression; 0 for impressions of users who do not convert."""
    c = rule_credits(p[p.y == 1], lam)
    p = p.copy()
    for r in RULES:
        p[r] = 0.0
        p.loc[c.index, r] = c[r]
    return p


def features(p):
    """Features known before an impression is bought. p: one row per impression, sorted by uid and timestamp."""
    g = p.groupby("uid", sort=False)
    return pd.DataFrame({
        "campaign": p.campaign.astype("category"),
        "tslc": p.time_since_last_click.where(p.time_since_last_click >= 0).astype(float),
        "n_prev": g.cumcount().astype(float),
        "clicks_prev": (g.click.cumsum() - p.click).astype(float),
        "gap_prev": (p.timestamp - g.timestamp.shift(1)).astype(float),
        "hour": ((p.timestamp % 86400) // 3600).astype(float)}, index=p.index)[FEATURES]


def buy(score, cost, share):
    """Impressions bought in decreasing order of score per unit cost until spend reaches `share` of total cost."""
    order = np.argsort(-(score / cost), kind="stable")
    k = np.searchsorted(np.cumsum(cost[order]), share * cost.sum(), side="right")
    bought = np.zeros(len(cost), dtype=bool)
    bought[order[:k]] = True
    return bought


def by_user(values, user, n_users):
    return np.bincount(user, weights=values, minlength=n_users)


def ratio_ci(num, den, weights):
    """Point estimate and 95% percentile interval of sum(num) / sum(den) under user bootstrap weights."""
    est = num.sum() / den.sum()
    b = (weights @ num) / (weights @ den)
    lo, hi = np.quantile(b, [0.025, 0.975])
    return float(est), float(lo), float(hi)


def compare(bought, credit, cost, user, weights, groups):
    """Metrics of the plan for one budget.

    bought, credit: dicts keyed by rule (the bidder trained on that rule; the credit under that rule).
    groups: dict of boolean arrays for the composition of spend. weights: draws x users bootstrap weights.
    """
    n = weights.shape[1]
    out = {"captured": {}, "cross_rule_loss": {}, "spend_share": {}, "composition": {}}
    tot = {r: by_user(credit[r], user, n) for r in RULES}
    cap = {(k, r): by_user(credit[r] * bought[k], user, n) for k in RULES for r in RULES}
    for k in RULES:
        out["spend_share"][k] = float(cost[bought[k]].sum() / cost.sum())
        out["captured"][k] = {r: ratio_ci(cap[(k, r)], tot[r], weights) for r in RULES}
        spend = cost[bought[k]].sum()
        out["composition"][k] = {g: float(cost[bought[k] & m].sum() / spend) for g, m in groups.items()}
    for r in RULES:
        other = [k for k in RULES if k != r][0]
        est, lo, hi = ratio_ci(cap[(other, r)], cap[(r, r)], weights)
        out["cross_rule_loss"][r] = (1 - est, 1 - hi, 1 - lo)
    both = bought[RULES[0]] & bought[RULES[1]]
    budget = np.mean([cost[bought[k]].sum() for k in RULES])
    out["spend_overlap"] = float(cost[both].sum() / budget)
    out["impressions_bought"] = {k: int(bought[k].sum()) for k in RULES}
    return out


def decision(res50, threshold=0.05):
    """Plan: loss of at least 5% under both rules at the 50% budget, lower end of both intervals above 0."""
    return bool(all(res50["cross_rule_loss"][r][0] >= threshold and res50["cross_rule_loss"][r][1] > 0 for r in RULES))
