"""Checks of the features, the labels at a cutoff, the delayed-feedback loss and the metrics on small simulated data."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import average_precision_score, roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
import delay_core as dc

CPU = torch.device("cpu")


def toy_log():
    return pd.DataFrame(dict(
        uid=[2, 1, 1, 2, 1], timestamp=[50, 10, 30, 70, 100], campaign=[3, 1, 2, 3, 1], click=[1, 1, 0, 0, 1],
        time_since_last_click=[-1, -1, 20, 20, 70], conversion=[0, 1, 1, 0, 0], conversion_timestamp=[-1, 200, 200, -1, -1]))


def test_features_and_history_use_only_earlier_impressions():
    d = dc.prepare(toy_log())
    assert d.uid.tolist() == [1, 1, 1, 2, 2] and d.timestamp.tolist() == [10, 30, 100, 50, 70]
    assert d.n_prev.tolist() == [0, 1, 2, 0, 1]
    assert d.n_prev_clicks.tolist() == [0, 1, 1, 0, 1]
    assert d.since_prev.tolist() == [-1, 20, 70, -1, 20]
    camp, lag, clk = dc.history(d, d.campaign.to_numpy(), k=3)
    assert camp[2].tolist() == [0, 2, 3] and clk[2].tolist() == [0, 1, 0]      # user 1, third impression
    assert np.isclose(lag[2, 2], np.log1p(70)) and np.isclose(lag[2, 1], np.log1p(90))
    assert camp[3].tolist() == [0, 0, 0] and camp[4].tolist() == [0, 0, 4]      # user 2 has no earlier row of user 1


def test_labels_at_the_cutoff_hide_later_conversions():
    ts = np.array([0.0, 0.0, 5 * dc.DAY]); conv = np.array([1, 1, 0]); cts = np.array([2 * dc.DAY, 12 * dc.DAY, -1])
    seen, delay, elapsed = dc.labels_at_cutoff(ts, conv, cts, cutoff_day=10)
    assert seen.tolist() == [1, 0, 0] and np.isclose(delay[0], 2) and np.allclose(elapsed, [10, 10, 5])


def test_dfm_loss_matches_the_formula():
    s = torch.tensor([0.3, -1.0]); lr = torch.tensor([np.log(0.2), np.log(0.5)], dtype=torch.float32)
    seen, delay, el = torch.tensor([1.0, 0.0]), torch.tensor([3.0, 0.0]), torch.tensor([4.0, 2.0])
    p = torch.sigmoid(s); r = torch.exp(lr)
    want = -(torch.log(p[0] * r[0] * torch.exp(-r[0] * 3)) + torch.log(1 - p[1] + p[1] * torch.exp(-r[1] * 2))) / 2
    assert torch.isclose(dc.dfm_nll(s, lr, seen, delay, el), want)


def simulated(n=60_000, seed=0, cutoff=10.0):
    """Two campaigns with conversion rates 0.10 and 0.30, exponential delays with mean 4 days, impressions spread
    over the 10 days before the cutoff. Returns inputs, labels seen at the cutoff and the true probabilities."""
    rng = np.random.default_rng(seed)
    camp = rng.integers(0, 2, n)
    p = np.where(camp == 1, 0.30, 0.10)
    conv = rng.random(n) < p
    ts = rng.uniform(0, cutoff, n)
    d = rng.exponential(4.0, n)
    seen = conv & (ts + d < cutoff)
    t = {"camp": torch.from_numpy(camp.astype(np.int64)), "num": torch.zeros(n, 2)}
    target = {"seen": torch.from_numpy(seen.astype(np.float32)), "delay": torch.from_numpy(np.where(seen, d, 1e-6).astype(np.float32)),
              "elapsed": torch.from_numpy((cutoff - ts).astype(np.float32))}
    return t, target, p


def test_delay_model_corrects_the_bias_that_the_naive_model_has():
    t, target, p = simulated()
    naive = dc.fit(dc.Net(2, 2, "naive"), t, target, epochs=4, bs=1024, lr=3e-3, dev=CPU)
    dfm = dc.fit(dc.Net(2, 2, "dfm", base_rate=0.2, base_delay_days=4.0), t, target, epochs=4, bs=1024, lr=3e-3, dev=CPU)
    pn, pd_ = dc.predict(naive, t, dev=CPU), dc.predict(dfm, t, dev=CPU)
    assert pn.sum() / p.sum() < 0.75
    assert abs(pd_.sum() / p.sum() - 1) < 0.08


def test_sequence_network_runs_on_padded_histories():
    n = 64
    t = {"camp": torch.zeros(n, dtype=torch.long), "num": torch.zeros(n, 3), "hcamp": torch.zeros(n, 5, dtype=torch.long),
         "hlag": torch.zeros(n, 5), "hclk": torch.zeros(n, 5, dtype=torch.int8)}
    t["hcamp"][:10, -1] = 1
    m = dc.Net(1, 3, "dfm", seq=True)
    out = dc.predict(m, t, dev=CPU)
    assert out.shape == (n,) and np.all((out > 0) & (out < 1))


def test_grouped_auc_and_average_precision_match_sklearn_with_ties_and_weights():
    rng = np.random.default_rng(1)
    s = np.round(rng.random(5000), 2); y = (rng.random(5000) < 0.2 + 0.5 * s).astype(float)
    w = rng.poisson(1.0, 5000).astype(float)
    r = dc.Ranker(s, y)
    assert np.isclose(r.auc(w), roc_auc_score(y, s, sample_weight=w))
    assert np.isclose(r.ap(w), average_precision_score(y, s, sample_weight=w))
    m = dc.metrics(s, y)
    assert np.isclose(m["calibration_ratio"], s.sum() / y.sum())


def test_weibull_loss_matches_the_formula_and_reduces_to_exponential_at_shape_one():
    s = torch.tensor([0.3, -1.0]); seen = torch.tensor([1.0, 0.0])
    delay, el = torch.tensor([3.0, 1e-6]), torch.tensor([4.0, 2.0])
    lam, k = torch.tensor([2.0, 5.0]), torch.tensor([0.7, 0.7])
    p = torch.sigmoid(s)
    f0 = (k[0] / lam[0]) * (delay[0] / lam[0]) ** (k[0] - 1) * torch.exp(-(delay[0] / lam[0]) ** k[0])
    want = -(torch.log(p[0] * f0) + torch.log(1 - p[1] + p[1] * torch.exp(-(el[1] / lam[1]) ** k[1]))) / 2
    assert torch.isclose(dc.weibull_nll(s, torch.log(lam), torch.log(k), seen, delay, el), want, atol=1e-6)
    one = torch.zeros(2)
    assert torch.isclose(dc.weibull_nll(s, torch.log(lam), one, seen, delay, el), dc.dfm_nll(s, -torch.log(lam), seen, delay, el), atol=1e-6)


def test_weibull_model_recovers_a_heavy_tailed_delay_that_the_exponential_underpredicts():
    rng = np.random.default_rng(3); n, cutoff = 80_000, 10.0
    camp = rng.integers(0, 2, n); p = np.where(camp == 1, 0.30, 0.10)
    conv = rng.random(n) < p; ts = rng.uniform(0, cutoff, n)
    d = 4.0 * rng.weibull(0.5, n)                       # many short delays and a long tail
    seen = conv & (ts + d < cutoff)
    t = {"camp": torch.from_numpy(camp.astype(np.int64)), "num": torch.zeros(n, 2)}
    target = {"seen": torch.from_numpy(seen.astype(np.float32)), "delay": torch.from_numpy(np.where(seen, d, 1e-6).astype(np.float32)),
              "elapsed": torch.from_numpy((cutoff - ts).astype(np.float32))}
    w = dc.fit(dc.Net(2, 2, "weibull", base_rate=0.2), t, target, epochs=4, bs=1024, lr=3e-3, dev=CPU)
    e = dc.fit(dc.Net(2, 2, "dfm", base_rate=0.2, base_delay_days=4.0), t, target, epochs=4, bs=1024, lr=3e-3, dev=CPU)
    rw, re_ = dc.predict(w, t, dev=CPU).sum() / p.sum(), dc.predict(e, t, dev=CPU).sum() / p.sum()
    assert abs(rw - 1) < abs(re_ - 1) and abs(rw - 1) < 0.10


def test_horizon_prediction_is_p_times_the_delay_cdf():
    torch.manual_seed(0)
    t = {"camp": torch.zeros(5, dtype=torch.long), "num": torch.zeros(5, 2)}
    e = dc.Net(1, 2, "dfm", base_rate=0.2, base_delay_days=10.0)
    p, f, q = dc.predict_parts(e, t, horizon=30.0, dev=CPU)
    assert np.allclose(q, p * f) and np.all((f > 0) & (f < 1))
    w = dc.Net(1, 2, "weibull", base_rate=0.2)
    p, f, q = dc.predict_parts(w, t, horizon=30.0, dev=CPU)
    with torch.no_grad():
        _, (ls, lk) = w(t["camp"], t["num"])
    want = 1 - np.exp(-(30.0 / np.exp(ls.numpy())) ** np.exp(lk.numpy()))
    assert np.allclose(f, want, atol=1e-5)
