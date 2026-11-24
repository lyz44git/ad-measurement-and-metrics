"""Features, labels at a cutoff, delayed-feedback networks and metrics (design/analysis_plan.md).

Kept free of file paths for testing. Times are in seconds in the data and in days inside the models.
"""
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

DAY = 86400.0
HIST = 20
NUM = ["log_since_click", "no_click_before", "log_since_prev", "first_impression", "log_n_prev",
       "log_n_prev_clicks", "hour_sin", "hour_cos"]


# ----------------------------------------------------------------------------- data

def prepare(d):
    """Sort by user and time and add the bid-time features. d: DataFrame with timestamp, uid, campaign, click,
    time_since_last_click, conversion, conversion_timestamp. Returns the sorted frame with the new columns."""
    d = d.sort_values(["uid", "timestamp"], kind="stable").reset_index(drop=True)
    uid, ts = d.uid.to_numpy(), d.timestamp.to_numpy()
    first = np.r_[True, uid[1:] != uid[:-1]]
    grp_start = np.maximum.accumulate(np.where(first, np.arange(len(d)), 0))
    n_prev = np.arange(len(d)) - grp_start
    clk = d.click.to_numpy().astype(np.int64)
    cum = np.cumsum(clk) - clk                       # clicks before this row, all users
    n_prev_clicks = cum - cum[grp_start]
    gap = np.where(first, -1, ts - np.r_[ts[0], ts[:-1]])
    tslc = d.time_since_last_click.to_numpy()
    hour = (ts // 3600) % 24
    d["n_prev"], d["n_prev_clicks"], d["since_prev"] = n_prev, n_prev_clicks, gap
    d["log_since_click"] = np.where(tslc >= 0, np.log1p(np.maximum(tslc, 0)), 0.0)
    d["no_click_before"] = (tslc < 0).astype(float)
    d["log_since_prev"] = np.where(gap >= 0, np.log1p(np.maximum(gap, 0)), 0.0)
    d["first_impression"] = first.astype(float)
    d["log_n_prev"], d["log_n_prev_clicks"] = np.log1p(n_prev), np.log1p(n_prev_clicks)
    d["hour_sin"], d["hour_cos"] = np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24)
    return d


def history(d, campaign_idx, k=HIST):
    """The user's previous k impressions for every row, oldest first, left-padded.

    Returns campaign index + 1 (0 = padding), log1p(seconds before the current impression) and click, each [n, k].
    """
    uid, ts, clk = d.uid.to_numpy(), d.timestamp.to_numpy(), d.click.to_numpy().astype(np.int8)
    n = len(d)
    camp = np.zeros((n, k), np.int32); lag = np.zeros((n, k), np.float32); hc = np.zeros((n, k), np.int8)
    rows = np.arange(n)
    for j in range(1, k + 1):
        src = rows - j
        ok = src >= 0
        ok[ok] &= uid[src[ok]] == uid[ok]
        col = k - j                                   # most recent previous impression in the last column
        s = src[ok]
        camp[ok, col] = campaign_idx[s] + 1
        lag[ok, col] = np.log1p(np.maximum(ts[ok] - ts[s], 0))
        hc[ok, col] = clk[s]
    return camp, lag, hc


def labels_at_cutoff(ts, conv, conv_ts, cutoff_day):
    """Label seen at the cutoff, delay of a seen conversion and elapsed time, in days."""
    T = cutoff_day * DAY
    seen = (conv == 1) & (conv_ts < T)
    delay = np.where(seen, (conv_ts - ts) / DAY, 0.0)
    elapsed = (T - ts) / DAY
    return seen.astype(np.float32), np.maximum(delay, 1e-6).astype(np.float32), elapsed.astype(np.float32)


# ----------------------------------------------------------------------------- models

class Body(nn.Module):
    """Campaign embedding + numeric features -> two hidden layers of 64; optional GRU over the history."""

    def __init__(self, n_campaigns, n_num, seq=False, emb=16, hidden=64, gru=32):
        super().__init__()
        self.emb = nn.Embedding(n_campaigns + 1, emb)
        self.seq = seq
        extra = 0
        if seq:
            self.hemb = nn.Embedding(n_campaigns + 1, emb, padding_idx=0)
            self.gru = nn.GRU(emb + 3, gru, batch_first=True)
            extra = gru
        self.mlp = nn.Sequential(nn.Linear(emb + n_num + extra, hidden), nn.ReLU(), nn.Linear(hidden, hidden), nn.ReLU())

    def forward(self, camp, num, hcamp=None, hlag=None, hclk=None):
        z = [self.emb(camp), num]
        if self.seq:
            present = (hcamp > 0).float().unsqueeze(-1)
            steps = torch.cat([self.hemb(hcamp), hlag.unsqueeze(-1) / 10.0, hclk.float().unsqueeze(-1), present], -1)
            _, h = self.gru(steps)
            z.append(h[-1])
        return self.mlp(torch.cat(z, -1))


class Net(nn.Module):
    """kind = 'naive' (one logit), 'dfm' (logit of p and log of an exponential delay rate) or 'weibull' (logit of p,
    log of a Weibull delay scale and log of its shape; follow-up, design/followup_plan.md)."""

    def __init__(self, n_campaigns, n_num, kind, seq=False, base_rate=0.05, base_delay_days=7.0):
        super().__init__()
        self.kind = kind
        self.body = Body(n_campaigns, n_num, seq)
        self.p = nn.Linear(64, 1)
        nn.init.constant_(self.p.bias, float(np.log(base_rate / (1 - base_rate))))
        if kind == "dfm":
            self.rate = nn.Linear(64, 1)
            nn.init.constant_(self.rate.bias, float(np.log(1 / base_delay_days)))
        if kind == "weibull":
            self.scale, self.shape = nn.Linear(64, 1), nn.Linear(64, 1)
            nn.init.constant_(self.scale.bias, float(np.log(5.0)))
            nn.init.constant_(self.shape.bias, float(np.log(0.6)))

    def forward(self, *x):
        h = self.body(*x)
        s = self.p(h).squeeze(-1)
        if self.kind == "dfm":
            return s, self.rate(h).squeeze(-1)
        if self.kind == "weibull":
            return s, (self.scale(h).squeeze(-1), self.shape(h).squeeze(-1))
        return s, None


def dfm_nll(s, log_rate, seen, delay, elapsed):
    """Negative log-likelihood of the delayed-feedback model (Chapelle 2014), mean over rows.

    Seen conversion: log p + log rate - rate * delay. Otherwise: log(1 - p + p * exp(-rate * elapsed)).
    """
    rate = torch.exp(log_rate)
    log_p, log_1mp = F.logsigmoid(s), F.logsigmoid(-s)
    ll_seen = log_p + log_rate - rate * delay
    ll_not = torch.logaddexp(log_1mp, log_p - rate * elapsed)
    return -(seen * ll_seen + (1 - seen) * ll_not).mean()


def weibull_nll(s, log_scale, log_shape, seen, delay, elapsed):
    """As dfm_nll with a Weibull delay: density (k/l)(d/l)^(k-1) exp(-(d/l)^k), survival exp(-(e/l)^k)."""
    k = torch.exp(log_shape)
    log_p, log_1mp = F.logsigmoid(s), F.logsigmoid(-s)
    zd = torch.log(delay) - log_scale
    ll_seen = log_p + log_shape - log_scale + (k - 1) * zd - torch.exp(k * zd)
    ze = torch.log(torch.clamp(elapsed, min=1e-6)) - log_scale
    ll_not = torch.logaddexp(log_1mp, log_p - torch.exp(k * ze))
    return -(seen * ll_seen + (1 - seen) * ll_not).mean()


def device():
    return torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")


def _batches(n, bs, rng):
    perm = rng.permutation(n)
    for i in range(0, n, bs):
        yield perm[i:i + bs]


def fit(model, tensors, target, epochs=3, bs=8192, lr=1e-3, seed=0, dev=None, log=None):
    """tensors: dict of CPU tensors of inputs (camp, num and, for the sequence model, hcamp, hlag, hclk);
    target: dict with seen and, for the delayed-feedback model, delay and elapsed."""
    dev = dev or device()
    torch.manual_seed(seed)
    model.to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    rng = np.random.default_rng(seed)
    keys = ["camp", "num"] + (["hcamp", "hlag", "hclk"] if model.body.seq else [])
    n = len(target["seen"])
    for ep in range(epochs):
        tot, cnt = 0.0, 0
        for b in _batches(n, bs, rng):
            bi = torch.from_numpy(b)
            x = [tensors[k][bi].to(dev) for k in keys]
            s, lr_ = model(*x)
            seen = target["seen"][bi].to(dev)
            if model.kind == "dfm":
                loss = dfm_nll(s, lr_, seen, target["delay"][bi].to(dev), target["elapsed"][bi].to(dev))
            elif model.kind == "weibull":
                loss = weibull_nll(s, lr_[0], lr_[1], seen, target["delay"][bi].to(dev), target["elapsed"][bi].to(dev))
            else:
                loss = F.binary_cross_entropy_with_logits(s, seen)
            opt.zero_grad(); loss.backward(); opt.step()
            tot += float(loss.detach()) * len(b); cnt += len(b)
        if log:
            log(f"  epoch {ep + 1}: loss {tot / cnt:.5f}")
    return model


@torch.no_grad()
def predict(model, tensors, bs=65536, dev=None):
    dev = dev or device()
    model.to(dev).eval()
    keys = ["camp", "num"] + (["hcamp", "hlag", "hclk"] if model.body.seq else [])
    n = len(tensors["camp"]); out = []
    for i in range(0, n, bs):
        x = [tensors[k][i:i + bs].to(dev) for k in keys]
        s, _ = model(*x)
        out.append(torch.sigmoid(s).float().cpu().numpy())
    model.train()
    return np.concatenate(out).astype(np.float64)


# ----------------------------------------------------------------------------- metrics

def log_loss_rows(p, y):
    p = np.clip(p, 1e-7, 1 - 1e-7)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


class Ranker:
    """Weighted ROC AUC and average precision from score groups computed once (ties share a group)."""

    def __init__(self, score, y):
        uniq, inv = np.unique(score, return_inverse=True)
        self.inv, self.g, self.y = inv, len(uniq), y.astype(bool)

    def _counts(self, w):
        pos = np.bincount(self.inv[self.y], w[self.y], self.g)
        neg = np.bincount(self.inv[~self.y], w[~self.y], self.g)
        return pos, neg

    def auc(self, w):
        pos, neg = self._counts(w)
        below = np.cumsum(neg) - neg
        return float((pos * (below + 0.5 * neg)).sum() / (pos.sum() * neg.sum()))

    def ap(self, w):
        pos, neg = self._counts(w)
        pos, neg = pos[::-1], neg[::-1]               # descending score
        tp, fp = np.cumsum(pos), np.cumsum(neg)
        prec = tp / np.maximum(tp + fp, 1e-12)
        return float((pos * prec).sum() / pos.sum())


def metrics(p, y, w=None, ranker=None):
    w = np.ones(len(y)) if w is None else w
    ll = log_loss_rows(p, y)
    r = ranker or Ranker(p, y)
    return {"calibration_ratio": float((w @ p) / (w @ y)), "log_loss": float((w @ ll) / w.sum()),
            "roc_auc": r.auc(w), "pr_auc": r.ap(w)}


def user_weights(user_codes, n_users, draws, seed):
    rng = np.random.default_rng(seed)
    for _ in range(draws):
        yield rng.poisson(1.0, n_users).astype(np.float64)[user_codes]


@torch.no_grad()
def predict_parts(model, tensors, horizon=30.0, bs=65536, dev=None):
    """For a delayed-feedback network: p(x), F_x(horizon) and the prediction for a horizon-day label, p * F.

    Second follow-up of study 02f (design/followup_plan_2.md)."""
    dev = dev or device()
    model.to(dev).eval()
    keys = ["camp", "num"] + (["hcamp", "hlag", "hclk"] if model.body.seq else [])
    n = len(tensors["camp"]); P, Fh = [], []
    for i in range(0, n, bs):
        x = [tensors[k][i:i + bs].to(dev) for k in keys]
        s, par = model(*x)
        if model.kind == "dfm":
            F_ = 1 - torch.exp(-torch.exp(par) * horizon)
        elif model.kind == "weibull":
            F_ = 1 - torch.exp(-torch.exp(torch.exp(par[1]) * (np.log(horizon) - par[0])))
        else:
            raise ValueError("only delayed-feedback networks have a delay distribution")
        P.append(torch.sigmoid(s).float().cpu().numpy()); Fh.append(F_.float().cpu().numpy())
    model.train()
    p, f = np.concatenate(P).astype(np.float64), np.concatenate(Fh).astype(np.float64)
    return p, f, p * f


@torch.no_grad()
def training_loss(model, tensors, target, bs=65536, dev=None):
    """Mean training loss of a delayed-feedback network on the given rows."""
    dev = dev or device()
    model.to(dev).eval()
    n, tot = len(target["seen"]), 0.0
    for i in range(0, n, bs):
        sl = slice(i, i + bs)
        s, par = model(tensors["camp"][sl].to(dev), tensors["num"][sl].to(dev))
        args = (target["seen"][sl].to(dev), target["delay"][sl].to(dev), target["elapsed"][sl].to(dev))
        loss = dfm_nll(s, par, *args) if model.kind == "dfm" else weibull_nll(s, par[0], par[1], *args)
        tot += float(loss) * len(target["seen"][sl])
    model.train()
    return tot / n
