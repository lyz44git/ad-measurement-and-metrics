"""Second design of study 02f (design/analysis_plan_v2.md): features over a rolling 7-day window, a 7-day conversion
label, and a delayed-feedback network whose delay distribution is a histogram over the seven days.

Kept free of file paths for testing. Times are in seconds in the data and in days inside the model.
"""
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

import delay_core as dc

DAY = dc.DAY
WINDOW = 7                      # days: feature look-back, conversion window and warm-up
NUM = ["log_since_click", "no_click_before", "log_since_prev", "none_in_window", "log_n_prev", "log_n_prev_clicks",
       "hour_sin", "hour_cos"] + [f"dow_{k}" for k in range(7)]


def prepare(d):
    """Sort by user and time and add features that use only the user's impressions of the previous WINDOW days.

    d: DataFrame with timestamp, uid, campaign, click, time_since_last_click. Counts from the start of the log grow
    with calendar time; counts over a fixed window do not."""
    d = d.sort_values(["uid", "timestamp"], kind="stable").reset_index(drop=True)
    uid, ts = d.uid.to_numpy(), d.timestamp.to_numpy().astype(np.int64)
    n = len(d)
    code = np.cumsum(np.r_[0, uid[1:] != uid[:-1]]).astype(np.int64)
    span = int(ts.max()) + int(WINDOW * DAY) + 2
    key = code * span + ts + int(WINDOW * DAY)          # increasing within and across users
    left = np.searchsorted(key, key - int(WINDOW * DAY), side="left")   # first row of the user inside the window
    rows = np.arange(n)
    n_prev = rows - left
    clk = d.click.to_numpy().astype(np.int64)
    cum = np.r_[0, np.cumsum(clk)]
    n_prev_clicks = cum[rows] - cum[left]
    gap = np.where(n_prev > 0, ts - ts[np.maximum(rows - 1, 0)], -1)
    tslc = d.time_since_last_click.to_numpy()
    tslc = np.where((tslc >= 0) & (tslc <= WINDOW * DAY), tslc, -1)     # a click older than the window counts as none
    hour = (ts // 3600) % 24
    dow = (ts // int(DAY)) % 7
    d["n_prev"], d["n_prev_clicks"] = n_prev, n_prev_clicks
    d["log_since_click"] = np.where(tslc >= 0, np.log1p(np.maximum(tslc, 0)), 0.0)
    d["no_click_before"] = (tslc < 0).astype(float)
    d["log_since_prev"] = np.where(gap >= 0, np.log1p(np.maximum(gap, 0)), 0.0)
    d["none_in_window"] = (n_prev == 0).astype(float)
    d["log_n_prev"], d["log_n_prev_clicks"] = np.log1p(n_prev), np.log1p(n_prev_clicks)
    d["hour_sin"], d["hour_cos"] = np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24)
    for k in range(7):
        d[f"dow_{k}"] = (dow == k).astype(float)
    return d


def window_label(ts, conv, conv_ts, window=WINDOW):
    """1 if a conversion follows the impression within `window` days."""
    return ((conv == 1) & (conv_ts - ts <= window * DAY)).astype(np.float32)


def labels_at_cutoff(ts, conv, conv_ts, cutoff_day, window=WINDOW):
    """Window label as seen at the cutoff, delay of a seen conversion and time watched (capped at the window), in days."""
    T = cutoff_day * DAY
    seen = (window_label(ts, conv, conv_ts, window) == 1) & (conv_ts < T)
    delay = np.where(seen, (conv_ts - ts) / DAY, 0.0)
    elapsed = np.clip((T - ts) / DAY, 0.0, window)
    return seen.astype(np.float32), np.clip(delay, 0.0, window - 1e-4).astype(np.float32), elapsed.astype(np.float32)


class HazardNet(nn.Module):
    """kind = 'label' (one logit, trained on a 0/1 label) or 'delay' (logit of p = P(conversion within WINDOW days)
    and WINDOW logits of the share of those conversions arriving on each day after the impression)."""

    def __init__(self, n_campaigns, n_num, kind, base_rate=0.03, window=WINDOW):
        super().__init__()
        self.kind = kind
        self.body = dc.Body(n_campaigns, n_num, seq=False)
        self.p = nn.Linear(64, 1)
        nn.init.constant_(self.p.bias, float(np.log(base_rate / (1 - base_rate))))
        if kind == "delay":
            self.bins = nn.Linear(64, window)

    def forward(self, camp, num):
        h = self.body(camp, num)
        return self.p(h).squeeze(-1), (self.bins(h) if self.kind == "delay" else None)


def delay_cdf(pi, t):
    """Share of the window's conversions that have arrived t days after the impression, the density being constant
    within each day. pi: [n, WINDOW] shares; t: [n] days in [0, WINDOW]."""
    w = pi.shape[1]
    cum = torch.cat([torch.zeros_like(pi[:, :1]), torch.cumsum(pi, 1)], 1)
    fl = torch.clamp(torch.floor(t), 0, w).long()
    frac = t - fl.float()
    part = pi.gather(1, torch.clamp(fl, max=w - 1).unsqueeze(1)).squeeze(1)
    return cum.gather(1, fl.unsqueeze(1)).squeeze(1) + frac * part * (fl < w)


def hazard_nll(s, bins, seen, delay, elapsed):
    """Negative log-likelihood, mean over rows. Seen conversion on day k: log p + log pi_k. Otherwise:
    log(1 - p * F(elapsed)), which is log(1 - p) once the impression has been watched for the whole window."""
    log_p, log_1mp = F.logsigmoid(s), F.logsigmoid(-s)
    log_pi = F.log_softmax(bins, 1)
    k = torch.clamp(torch.floor(delay), 0, bins.shape[1] - 1).long()
    ll_seen = log_p + log_pi.gather(1, k.unsqueeze(1)).squeeze(1)
    surv = torch.clamp(1 - delay_cdf(torch.exp(log_pi), elapsed), min=0.0)
    ll_not = torch.logaddexp(log_1mp, log_p + torch.log(surv + 1e-12))
    return -(seen * ll_seen + (1 - seen) * ll_not).mean()


def fit(n_campaigns, kind, tensors, target, base_rate, seed, epochs=3, bs=8192, lr=1e-3, dev=None, log=None, window=WINDOW):
    """Seeds PyTorch before the network is built, so the initial weights are reproducible as well as the batches."""
    dev = dev or dc.device()
    torch.manual_seed(seed)
    model = HazardNet(n_campaigns, tensors["num"].shape[1], kind, base_rate, window).to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    rng = np.random.default_rng(seed)
    n = len(target["label"])
    for ep in range(epochs):
        tot, cnt = 0.0, 0
        for b in dc._batches(n, bs, rng):
            bi = torch.from_numpy(b)
            s, bins = model(tensors["camp"][bi].to(dev), tensors["num"][bi].to(dev))
            y = target["label"][bi].to(dev)
            if kind == "delay":
                loss = hazard_nll(s, bins, y, target["delay"][bi].to(dev), target["elapsed"][bi].to(dev))
            else:
                loss = F.binary_cross_entropy_with_logits(s, y)
            opt.zero_grad(); loss.backward(); opt.step()
            tot += float(loss.detach()) * len(b); cnt += len(b)
        if log:
            log(f"    epoch {ep + 1}: loss {tot / cnt:.5f}")
    return model


@torch.no_grad()
def predict(model, tensors, bs=65536, dev=None):
    """P(conversion within WINDOW days) and, for the delay network, the mean share arriving on each day."""
    dev = dev or dc.device()
    model.to(dev).eval()
    n = len(tensors["camp"]); out, pis = [], []
    for i in range(0, n, bs):
        s, bins = model(tensors["camp"][i:i + bs].to(dev), tensors["num"][i:i + bs].to(dev))
        out.append(torch.sigmoid(s).float().cpu().numpy())
        if bins is not None:
            pis.append(torch.softmax(bins, 1).sum(0).float().cpu().numpy())
    p = np.concatenate(out).astype(np.float64)
    return p, (np.sum(pis, 0) / n if pis else None)
