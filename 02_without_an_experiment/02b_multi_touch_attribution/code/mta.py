"""Touch-level multi-touch attribution on Criteo display-ad paths (Part B of design/analysis_plan.md).

Usage: python code/mta.py <derived_dir/criteo_attr.parquet> <out_dir>
Writes <out_dir>/mta.json. About 5 minutes and 10 GB of memory on the full file.
"""
import json
import sys
import zlib
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

BUCKETS = ["last", "<1d", "1-7d", ">7d"]
RULES = ["cr_last", "cr_first", "cr_linear", "cr_decay", "cr_dd"]


def build_paths(d):
    """One path per user, one row per touch.

    Converters: all their impressions up to the first conversion, clicked or not (design/deviations.md, item 1).
    Other users: all their impressions. Users are split 70/30 into train and test by a hash of the user id.
    Adds y (path converted), test, n (touches in the path), pos, is_last, bucket (recency relative to the last touch:
    0 last, 1 under a day, 2 one to seven days, 3 over seven days) and feat (clicked x bucket, 8 touch types).
    """
    d = d.sort_values(["uid", "timestamp"], kind="stable").reset_index(drop=True)
    tc = d[d.conversion == 1].groupby("uid").conversion_timestamp.min().rename("tc")
    d = d.join(tc, on="uid")
    conv = d[d.tc.notna() & (d.timestamp <= d.tc)].assign(y=1)
    conv["conversion_timestamp"] = conv.tc
    non = d[d.tc.isna()].assign(y=0)
    p = pd.concat([conv, non], ignore_index=True).sort_values(["uid", "timestamp"], kind="stable").reset_index(drop=True)
    p["test"] = (p.uid.map(lambda u: zlib.crc32(str(u).encode()) % 10) >= 7)
    g = p.groupby("uid", sort=False)
    p["n"] = g.timestamp.transform("size")
    p["t_last"] = g.timestamp.transform("max")
    p["pos"] = g.cumcount()
    p["is_last"] = (p.pos == p.n - 1)
    gap = (p.t_last - p.timestamp) / 86400.0
    p["bucket"] = np.where(p.is_last, 0, np.where(gap < 1, 1, np.where(gap <= 7, 2, 3)))
    p["feat"] = p.click.astype(int) * 4 + p.bucket
    return p


def path_design(p):
    """Path-level design matrix: counts of the 8 touch types and log(1 + touches); one row per user."""
    X = pd.crosstab(p.uid, p.feat).reindex(columns=range(8), fill_value=0)
    meta = p.groupby("uid", sort=False).agg(y=("y", "first"), test=("test", "first"), n=("n", "first")).loc[X.index]
    return X, meta, np.column_stack([X.values, np.log1p(meta.n.values)])


def decay_rate(delay_days):
    """Maximum-likelihood rate of an exponential distribution of touch-to-conversion delays, per day."""
    return 1.0 / np.mean(delay_days)


def rule_credits(c, lam):
    """Last-touch, first-touch, linear and time-decay credit for the touches of converting paths.

    c: touches of converting paths with columns uid, timestamp, conversion_timestamp, n, pos, is_last.
    Each rule's credits sum to 1 within a path.
    """
    c = c.copy()
    c["cr_last"] = c.is_last.astype(float)
    c["cr_first"] = (c.pos == 0).astype(float)
    c["cr_linear"] = 1.0 / c.n
    w = np.exp(-lam * (c.conversion_timestamp - c.timestamp).clip(lower=0) / 86400.0)
    c["cr_decay"] = w / w.groupby(c.uid).transform("sum")
    return c


def removal_credits(c, X, Xa, model):
    """Model-based removal effect of each touch, normalised within a path. Reported but not used for conclusions
    (design/deviations.md, item 2)."""
    coef, b0 = model.coef_[0], model.intercept_[0]
    row = X.index.get_indexer(c.uid)
    lin = b0 + Xa[row] @ coef
    ln_n, ln_n1 = np.log1p(c.n.values), np.log1p(c.n.values - 1)
    lin_minus = lin - coef[c.feat.values] - coef[8] * (ln_n - ln_n1)
    sig = lambda z: 1 / (1 + np.exp(-z))
    rem = np.clip(sig(lin) - sig(lin_minus), 0, None)
    tot = pd.Series(rem, index=c.index).groupby(c.uid).transform("sum")
    return np.where(tot > 0, rem / tot.where(tot > 0, 1.0), 1.0 / c.n)


def main(src, out):
    d = pd.read_parquet(src, columns=["timestamp", "uid", "campaign", "conversion", "conversion_timestamp",
                                      "conversion_id", "click"])
    p = build_paths(d)
    X, meta, Xa = path_design(p)
    tr, te = ~meta.test.values, meta.test.values
    y = meta.y.values

    # path conversion model against a touches-only model, paired user bootstrap on the test users
    full = LogisticRegression(C=10.0, max_iter=2000).fit(Xa[tr], y[tr])
    base = LogisticRegression(C=10.0, max_iter=2000).fit(Xa[tr][:, -1:], y[tr])
    pf, pb = full.predict_proba(Xa[te])[:, 1], base.predict_proba(Xa[te][:, -1:])[:, 1]
    auc_f, auc_b = roc_auc_score(y[te], pf), roc_auc_score(y[te], pb)
    rng = np.random.default_rng(3); yt = y[te]; nte = len(yt); diffs = []
    for _ in range(500):
        i = rng.integers(0, nte, nte)
        if yt[i].min() == yt[i].max():
            continue
        diffs.append(roc_auc_score(yt[i], pf[i]) - roc_auc_score(yt[i], pb[i]))
    auc_ci = np.quantile(diffs, [0.025, 0.975]).tolist()

    # time-decay rate from the training converters' touch-to-conversion delays
    ctr = p[(p.y == 1) & (~p.test)]
    delay_days = (ctr.conversion_timestamp - ctr.timestamp).clip(lower=0) / 86400.0
    lam = decay_rate(delay_days)

    # credits on multi-touch conversions of the test users
    c = rule_credits(p[(p.y == 1) & p.test & (p.n > 1)], lam)
    c["cr_dd"] = removal_credits(c, X, Xa, full)
    nconv = c.uid.nunique()
    res = dict(
        paths=int(len(meta)), paths_train=int(tr.sum()), paths_test=int(te.sum()), conversions=int(y.sum()),
        conv_rate=float(y.mean()), share_conv_multi_touch=float((meta.n[meta.y == 1] > 1).mean()),
        auc=dict(full=float(auc_f), touches_only=float(auc_b), diff=float(auc_f - auc_b), diff_ci=auc_ci),
        data_driven_rule_met=bool(auc_ci[0] > 0),
        decay_per_day=float(lam), half_life_days=float(np.log(2) / lam), mean_delay_days=float(delay_days.mean()),
        multi_touch_test_conversions=int(nconv), touches_in_them=int(len(c)), mean_touches=float(len(c) / nconv),
        share_touches_zero_credit_last_touch=float((c.cr_last == 0).mean()),
        credit_on_last_touch={r: float(c.loc[c.is_last, r].sum() / nconv) for r in RULES},
        credit_on_clicked_touches={r: float(c.loc[c.click == 1, r].sum() / nconv) for r in RULES},
        share_touches_clicked=float(c.click.mean()),
        credit_by_recency_bucket={r: {b: float(c.loc[c.bucket == i, r].sum() / nconv) for i, b in enumerate(BUCKETS)}
                                  for r in RULES},
        coef=dict(zip([f"{a}|{b}" for a in ("unclicked", "clicked") for b in BUCKETS] + ["log1p_touches"],
                      [float(v) for v in full.coef_[0]])),
    )
    # how much credit moves between campaigns (45% of multi-touch test paths span more than one campaign; out/campaign_span.json)
    camp = c.groupby("campaign")[RULES].sum()
    res["campaign_credit_moved_decay_vs_last"] = float((camp.cr_decay - camp.cr_last).abs().sum() / 2 / nconv)
    Path(out).mkdir(parents=True, exist_ok=True)
    json.dump(res, open(Path(out) / "mta.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
