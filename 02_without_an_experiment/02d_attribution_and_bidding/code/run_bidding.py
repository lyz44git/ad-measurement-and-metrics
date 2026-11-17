"""Fit the two value models and replay the two bidders on the test users (design/analysis_plan.md).

Usage: python code/run_bidding.py <derived_dir/criteo_attr.parquet> [out_dir]
The parquet file is written by study 02b's code/load_attribution.py. About 10 minutes and 20 GB of memory.
"""
import json
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bidding_core as bc  # noqa: E402
from mta import build_paths, decay_rate  # noqa: E402  (study 02b, on the path through bidding_core)

ROOT = Path(__file__).resolve().parents[1]
SEED, BUDGETS, DRAWS = 20261117, (0.25, 0.50, 0.75), 500


def main(src, out):
    out = Path(out); out.mkdir(exist_ok=True)
    t0 = time.time()
    d = pd.read_parquet(src, columns=["timestamp", "uid", "campaign", "conversion", "conversion_timestamp",
                                      "conversion_id", "click", "cost", "time_since_last_click"])
    p = build_paths(d)
    del d
    ctr = p[(p.y == 1) & (~p.test)]
    lam = decay_rate((ctr.conversion_timestamp - ctr.timestamp).clip(lower=0) / 86400.0)
    p = bc.add_credits(p, lam)
    X = bc.features(p)
    tr, te = ~p.test.values, p.test.values
    print(f"paths built in {time.time() - t0:.0f} s; impressions {len(p):,}, train {tr.sum():,}, test {te.sum():,}", flush=True)

    pred = {}
    for r in bc.RULES:
        m = lgb.LGBMRegressor(objective="cross_entropy", n_estimators=300, learning_rate=0.05, num_leaves=63,
                              min_child_samples=200, random_state=SEED, n_jobs=24, verbose=-1)
        m.fit(X[tr], p.loc[tr, r].values)
        pred[r] = m.predict(X[te])
        print(f"model {r} fitted, {time.time() - t0:.0f} s", flush=True)

    t = p[te]
    cost = t.cost.values.astype(float)
    credit = {r: t[r].values for r in bc.RULES}
    user, uniq = pd.factorize(t.uid.values)
    weights = np.random.default_rng(SEED).poisson(1.0, (DRAWS, len(uniq))).astype(float)
    tslc = t.time_since_last_click.values
    groups = {"within_24h_of_last_click": (tslc >= 0) & (tslc < 86400), "no_earlier_click": tslc < 0,
              "first_logged_impression": X.loc[te, "n_prev"].values == 0}

    res = dict(impressions=int(len(p)), train_impressions=int(tr.sum()), test_impressions=int(te.sum()),
               test_users=int(len(uniq)), decay_per_day=float(lam), half_life_days=float(np.log(2) / lam),
               test_credit={r: float(credit[r].sum()) for r in bc.RULES},
               calibration={r: float(pred[r].sum() / credit[r].sum()) for r in bc.RULES},
               all_test_spend_composition={g: float(cost[m].sum() / cost.sum()) for g, m in groups.items()},
               budgets={})
    for b in BUDGETS:
        bought = {r: bc.buy(pred[r], cost, b) for r in bc.RULES}
        res["budgets"][str(b)] = bc.compare(bought, credit, cost, user, weights, groups)
        print(f"budget {b} done, {time.time() - t0:.0f} s", flush=True)
    res["rule_met"] = bc.decision(res["budgets"]["0.5"])
    res["seconds"] = round(time.time() - t0)
    (out / "bidding.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ROOT / "out")
