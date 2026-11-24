"""Third design of study 02f: four networks retrained at 9 daily cutoffs on a 14-day label (design/analysis_plan_v3.md).

Usage: python code/run_delay_v3.py <derived_dir/criteo_attr.parquet> [out_dir]
The parquet file is written by study 02b's code/load_attribution.py.
"""
import json
import sys
import time
from pathlib import Path

import sklearn.ensemble  # noqa: F401  (OpenMP runtime first, as in conftest.py)
import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import delay_core as dc  # noqa: E402
import delay_v2 as v2  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SEED, CUTOFFS, DRAWS, W = 20261128, tuple(range(22, 31)), 200, 14
MODELS = ["labels_seen", "complete_only", "delay", "reference"]


def log(msg, t0=[time.time()]):
    print(f"[{time.time() - t0[0]:6.0f}s] {msg}", flush=True)


def main(src, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    d = pd.read_parquet(src, columns=["timestamp", "uid", "campaign", "conversion", "conversion_timestamp", "click",
                                      "time_since_last_click"])
    d = v2.prepare(d)
    camp_idx, camp_values = pd.factorize(d.campaign, sort=True)
    ts, conv = d.timestamp.to_numpy(np.float64), d.conversion.to_numpy()
    cts = d.conversion_timestamp.to_numpy(np.float64)
    y7 = v2.window_label(ts, conv, cts, W)
    uid = d.uid.to_numpy()
    camp = torch.from_numpy(camp_idx.astype(np.int64))
    num_raw = d[v2.NUM].to_numpy(np.float32)
    del d
    n_camp = len(camp_values)
    R = {"impressions": int(len(ts)), "campaigns": int(n_camp), "window_days": W, "feature_window_days": v2.WINDOW,
         "conversion_share_window": float(y7.mean()), "share_of_conversions_within_window": float(y7.sum() / conv.sum()),
         "device": str(dc.device()), "torch": torch.__version__, "cutoffs": {}}
    log(f"prepared {len(ts):,} impressions, {n_camp} campaigns")

    P = {k: [] for k in MODELS}; Y, U, D = [], [], []
    shares_hat, shares_obs = [], []
    for T in CUTOFFS:
        tr = (ts >= v2.WINDOW * dc.DAY) & (ts < T * dc.DAY)
        te = (ts >= T * dc.DAY) & (ts < (T + 1) * dc.DAY)
        old = tr & (ts < (T - W) * dc.DAY)
        seen, delay, elapsed = v2.labels_at_cutoff(ts, conv, cts, T, W)
        mu, sd = num_raw[tr].mean(0), num_raw[tr].std(0) + 1e-6

        def tensors(mask):
            idx = torch.from_numpy(np.flatnonzero(mask))
            return {"camp": camp[idx], "num": torch.from_numpy((num_raw[mask] - mu) / sd)}
        X_tr, X_old, X_te = tensors(tr), tensors(old), tensors(te)
        base = max(float(seen[tr].mean()), 1e-3)
        info = {"train_impressions": int(tr.sum()), "complete_label_impressions": int(old.sum()),
                "test_impressions": int(te.sum()), "train_share_seen": float(seen[tr].mean()),
                "train_share_window": float(y7[tr].mean()), "test_share_window": float(y7[te].mean()), "models": {}}
        log(f"cutoff {T}: train {tr.sum():,} (seen {info['train_share_seen']:.4f}, complete {info['train_share_window']:.4f}), "
            f"older than the window {old.sum():,}, test {te.sum():,}")
        jobs = {"labels_seen": ("label", X_tr, {"label": torch.from_numpy(seen[tr])}),
                "complete_only": ("label", X_old, {"label": torch.from_numpy(y7[old])}),
                "delay": ("delay", X_tr, {"label": torch.from_numpy(seen[tr]), "delay": torch.from_numpy(delay[tr]),
                                          "elapsed": torch.from_numpy(elapsed[tr])}),
                "reference": ("label", X_tr, {"label": torch.from_numpy(y7[tr])})}
        y_te = y7[te].astype(np.float64)
        for name, (kind, X, target) in jobs.items():
            net = v2.fit(n_camp, kind, X, target, base, SEED + T, window=W)
            p, pi = v2.predict(net, X_te)
            P[name].append(p)
            info["models"][name] = dc.metrics(p, y_te)
            if pi is not None:
                info["delay_shares_estimated"] = [float(x) for x in pi]
                shares_hat.append(pi)
        c = (y_te == 1)
        obs = np.bincount(np.clip(np.floor((cts[te][c] - ts[te][c]) / dc.DAY), 0, W - 1).astype(int),
                          minlength=W) / c.sum()
        info["delay_shares_observed"] = [float(x) for x in obs]; shares_obs.append(obs)
        Y.append(y_te); U.append(uid[te]); D.append(np.full(int(te.sum()), T))
        R["cutoffs"][str(T)] = info
        log("  predicted/actual: " + json.dumps({k: round(info["models"][k]["calibration_ratio"], 3) for k in MODELS}))
        (out / "delay_v3_partial.json").write_text(json.dumps(R, indent=1))

    y = np.concatenate(Y); users = pd.factorize(np.concatenate(U))[0]; n_users = int(users.max()) + 1
    pred = {k: np.concatenate(v) for k, v in P.items()}
    rank = {k: dc.Ranker(pred[k], y) for k in MODELS}
    point = {k: dc.metrics(pred[k], y, ranker=rank[k]) for k in MODELS}
    ll = {k: dc.log_loss_rows(pred[k], y) for k in MODELS}
    draws = {k: [] for k in MODELS}; closed = []
    for w in dc.user_weights(users, n_users, DRAWS, SEED):
        m = {k: {"calibration_ratio": float((w @ pred[k]) / (w @ y)), "log_loss": float((w @ ll[k]) / w.sum()),
                 "roc_auc": rank[k].auc(w)} for k in MODELS}
        for k in MODELS:
            draws[k].append(m[k])
        closed.append((m["labels_seen"]["log_loss"] - m["delay"]["log_loss"]) /
                      (m["labels_seen"]["log_loss"] - m["reference"]["log_loss"]))

    def ci(x):
        return [float(np.quantile(x, 0.025)), float(np.quantile(x, 0.975))]

    def diff(a, b):
        return {"estimate": point[a]["log_loss"] - point[b]["log_loss"],
                "ci95": ci([da["log_loss"] - db["log_loss"] for da, db in zip(draws[a], draws[b])])}
    gap = (point["labels_seen"]["log_loss"] - point["delay"]["log_loss"]) / \
          (point["labels_seen"]["log_loss"] - point["reference"]["log_loss"])
    R["pooled"] = {"test_impressions": int(len(y)), "test_conversions": int(y.sum()),
                   "models": {k: {m: {"estimate": point[k][m], "ci95": ci([x[m] for x in draws[k]])}
                                  for m in ("calibration_ratio", "log_loss", "roc_auc")} for k in MODELS},
                   "log_loss_difference": {"delay_minus_labels_seen": diff("delay", "labels_seen"),
                                           "delay_minus_complete_only": diff("delay", "complete_only"),
                                           "delay_minus_reference": diff("delay", "reference")},
                   "share_of_gap_closed": {"estimate": float(gap), "ci95": ci(closed)},
                   "delay_shares_estimated_mean": [float(x) for x in np.mean(shares_hat, 0)],
                   "delay_shares_observed_mean": [float(x) for x in np.mean(shares_obs, 0)]}
    ratio = point["delay"]["calibration_ratio"]
    half = float(np.mean([abs(x["calibration_ratio"] - 1) <= 0.5 * abs(z["calibration_ratio"] - 1)
                          for x, z in zip(draws["delay"], draws["labels_seen"])]))
    R["pooled"]["share_of_draws_with_half_the_calibration_error"] = half
    rule1 = bool(0.95 <= ratio <= 1.05 and half >= 0.95)
    rule2 = bool(R["pooled"]["log_loss_difference"]["delay_minus_labels_seen"]["ci95"][1] < 0)
    R["decision"] = {"1_level_is_corrected": {"met": rule1, "rule": "pooled predicted over actual within 0.95 to 1.05 and "
                     "absolute calibration error at most half the labels-seen network's in at least 95% of draws"},
                     "2_fit_improves": {"met": rule2, "rule": "log loss below the labels-seen network's (95% interval "
                     "of the difference below zero)"}}
    R["seconds"] = round(time.time() - log.__defaults__[0][0])
    (out / "delay_v3.json").write_text(json.dumps(R, indent=1))
    (out / "delay_v3_partial.json").unlink()
    log("pooled: " + json.dumps({k: round(point[k]["calibration_ratio"], 3) for k in MODELS}) + f" gap closed {gap:.2f}")
    log("decision " + json.dumps({k: v["met"] for k, v in R["decision"].items()}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ROOT / "out")
