"""Delayed conversions: five models retrained at three cutoffs and scored on 30-day labels (design/analysis_plan.md).

Usage: python code/run_delay.py <derived_dir/criteo_attr.parquet> [out_dir]
The parquet file is written by study 02b's code/load_attribution.py. About 40 minutes on an Apple M3 Ultra.
"""
import json
import sys
import time
from pathlib import Path

# Load scikit-learn's OpenMP runtime before LightGBM and PyTorch (as in the repository's conftest.py): otherwise the
# runtimes conflict on macOS and large tensor indexing crashes.
import sklearn.ensemble  # noqa: F401
import lightgbm as lgb
import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import delay_core as dc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SEED, CUTOFFS, TEST_DAYS, DRAWS = 20261126, (14, 21, 28), 3, 200
MODELS = ["naive_lightgbm", "naive_network", "delay_network", "delay_sequence_network", "oracle_lightgbm"]
LGB = dict(objective="binary", n_estimators=300, learning_rate=0.05, num_leaves=63, min_child_samples=200,
           random_state=SEED, n_jobs=32, verbose=-1)
TAB = ["campaign_idx", "since_click", "n_prev", "n_prev_clicks", "since_prev", "hour"]


def log(msg, t0=[time.time()]):
    print(f"[{time.time() - t0[0]:6.0f}s] {msg}", flush=True)


def main(src, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    d = pd.read_parquet(src, columns=["timestamp", "uid", "campaign", "conversion", "conversion_timestamp", "click",
                                      "time_since_last_click"])
    d = dc.prepare(d)
    camp_idx, camp_values = pd.factorize(d.campaign, sort=True)
    d["campaign_idx"] = camp_idx
    d["since_click"] = np.where(d.time_since_last_click >= 0, d.time_since_last_click, np.nan)
    d["since_prev"] = np.where(d.since_prev >= 0, d.since_prev, np.nan)
    d["hour"] = (d.timestamp // 3600) % 24
    hc, hl, hk = dc.history(d, camp_idx)
    ts, conv, cts = d.timestamp.to_numpy(np.float64), d.conversion.to_numpy(), d.conversion_timestamp.to_numpy(np.float64)
    log(f"prepared {len(d):,} impressions, {len(camp_values)} campaigns")

    tensors_all = {"camp": torch.from_numpy(camp_idx.astype(np.int64)), "hcamp": torch.from_numpy(hc.astype(np.int64)),
                   "hlag": torch.from_numpy(hl), "hclk": torch.from_numpy(hk)}
    num_raw = d[dc.NUM].to_numpy(np.float32)
    X_tab = d[TAB]
    R = {"impressions": int(len(d)), "campaigns": int(len(camp_values)), "conversion_share_30d": float(conv.mean()),
         "device": str(dc.device()), "torch": torch.__version__, "cutoffs": {}}

    for T in CUTOFFS:
        tr = ts < T * dc.DAY
        te = (ts >= T * dc.DAY) & (ts < (T + TEST_DAYS) * dc.DAY)
        seen, delay, elapsed = dc.labels_at_cutoff(ts, conv, cts, T)
        mu, sd = num_raw[tr].mean(0), num_raw[tr].std(0) + 1e-6
        num = torch.from_numpy((num_raw - mu) / sd)
        tidx, eidx = torch.from_numpy(np.flatnonzero(tr)), torch.from_numpy(np.flatnonzero(te))
        T_tr = {k: v[tidx] for k, v in tensors_all.items()} | {"num": num[tidx]}
        T_te = {k: v[eidx] for k, v in tensors_all.items()} | {"num": num[eidx]}
        target = {"seen": torch.from_numpy(seen[tr]), "delay": torch.from_numpy(delay[tr]),
                  "elapsed": torch.from_numpy(elapsed[tr])}
        y_te = conv[te].astype(np.float64)
        info = {"train_impressions": int(tr.sum()), "test_impressions": int(te.sum()),
                "train_conversion_share_seen": float(seen[tr].mean()), "train_conversion_share_30d": float(conv[tr].mean()),
                "test_conversion_share_30d": float(y_te.mean())}
        log(f"cutoff {T}: train {tr.sum():,} (seen {info['train_conversion_share_seen']:.4f} vs 30-day "
            f"{info['train_conversion_share_30d']:.4f}), test {te.sum():,}")

        pred = {}
        for name, lab in (("naive_lightgbm", seen[tr]), ("oracle_lightgbm", conv[tr])):
            m = lgb.LGBMClassifier(**LGB).fit(X_tab[tr], lab, categorical_feature=["campaign_idx"])
            pred[name] = m.predict_proba(X_tab[te])[:, 1]
            log(f"  {name} fitted")
        base = float(seen[tr].mean())
        for name, kind, seq in (("naive_network", "naive", False), ("delay_network", "dfm", False),
                                ("delay_sequence_network", "dfm", True)):
            net = dc.Net(len(camp_values), len(dc.NUM), kind, seq=seq, base_rate=max(base, 1e-3))
            dc.fit(net, T_tr, target, seed=SEED, log=log)
            pred[name] = dc.predict(net, T_te)
            log(f"  {name} fitted")

        users, n_users = pd.factorize(d.uid.to_numpy()[te])[0], None
        n_users = int(users.max()) + 1
        rank = {k: dc.Ranker(pred[k], y_te) for k in MODELS}
        point = {k: dc.metrics(pred[k], y_te, ranker=rank[k]) for k in MODELS}
        draws = {k: [] for k in MODELS}
        for w in dc.user_weights(users, n_users, DRAWS, SEED + T):
            for k in MODELS:
                draws[k].append(dc.metrics(pred[k], y_te, w, rank[k]))
        res = {}
        for k in MODELS:
            res[k] = {m: {"estimate": point[k][m],
                          "ci95": [float(np.quantile([x[m] for x in draws[k]], q)) for q in (0.025, 0.975)]}
                      for m in point[k]}

        def diff(a, b):
            x = np.array([da["log_loss"] - db["log_loss"] for da, db in zip(draws[a], draws[b])])
            return {"estimate": point[a]["log_loss"] - point[b]["log_loss"],
                    "ci95": [float(np.quantile(x, 0.025)), float(np.quantile(x, 0.975))]}
        info["models"] = res
        info["log_loss_difference"] = {"delay_network_minus_naive_network": diff("delay_network", "naive_network"),
                                       "sequence_minus_delay_network": diff("delay_sequence_network", "delay_network"),
                                       "delay_network_minus_oracle": diff("delay_network", "oracle_lightgbm"),
                                       "naive_lightgbm_minus_oracle": diff("naive_lightgbm", "oracle_lightgbm")}
        R["cutoffs"][str(T)] = info
        log(f"  calibration: " + json.dumps({k: round(point[k]["calibration_ratio"], 3) for k in MODELS}))
        (out / "delay.json").write_text(json.dumps(R, indent=1))

    c = R["cutoffs"]
    rule1 = all(0.90 <= c[str(T)]["models"]["delay_network"]["calibration_ratio"]["estimate"] <= 1.10 and
                c[str(T)]["log_loss_difference"]["delay_network_minus_naive_network"]["ci95"][1] < 0 for T in CUTOFFS)
    rule2 = all(c[str(T)]["log_loss_difference"]["sequence_minus_delay_network"]["ci95"][1] < 0 for T in CUTOFFS)
    R["decision"] = {"delay_model_corrects_bias": {"met": rule1, "rule": "calibration ratio in [0.90, 1.10] and log loss "
                     "below the naive network's (95% interval of the difference below zero) at all three cutoffs"},
                     "history_adds_to_delay_model": {"met": rule2, "rule": "sequence network log loss below the delay "
                     "network's (95% interval below zero) at all three cutoffs"}}
    R["seconds"] = round(time.time() - log.__defaults__[0][0])
    (out / "delay.json").write_text(json.dumps(R, indent=1))
    log("decision " + json.dumps({k: v["met"] for k, v in R["decision"].items()}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ROOT / "out")
