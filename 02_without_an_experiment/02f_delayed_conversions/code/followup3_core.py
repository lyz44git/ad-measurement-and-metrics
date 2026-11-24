"""Campaign calibration and the corrected ranker of follow-up 3 (design/followup_plan_3.md); no file paths."""
import numpy as np


def campaign_ratio(train_camp, p_delay, p_seen, n_campaigns):
    """k_c = mean delay-network p / mean labels-seen prediction over a campaign's training impressions; campaigns
    without training impressions get the pooled ratio."""
    a = np.bincount(train_camp, p_delay, n_campaigns); b = np.bincount(train_camp, p_seen, n_campaigns)
    k = np.full(n_campaigns, p_delay.sum() / p_seen.sum())
    ok = b > 0
    k[ok] = a[ok] / b[ok]
    return k


def corrected(p_seen, camp, k):
    return np.minimum(k[camp] * p_seen, 0.99)


def campaign_error(p, y, camp, keep, n_campaigns, w=None):
    """Conversion-weighted mean of |predicted / actual - 1| over the campaigns in `keep` (boolean per campaign)."""
    w = np.ones(len(y)) if w is None else w
    P = np.bincount(camp, w * p, n_campaigns); Y = np.bincount(camp, w * y, n_campaigns)
    m = keep & (Y > 0)
    return float((Y[m] * np.abs(P[m] / Y[m] - 1)).sum() / Y[m].sum())


def per_campaign_error(p, y, camp, keep, n_campaigns):
    P = np.bincount(camp, p, n_campaigns); Y = np.bincount(camp, y, n_campaigns)
    e = np.full(n_campaigns, np.nan); m = keep & (Y > 0)
    e[m] = np.abs(P[m] / Y[m] - 1)
    return e
