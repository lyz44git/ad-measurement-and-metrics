"""Follow-up 4 of study 02f: the corrected ranker with its ratio taken where it is applied (design/followup_plan_4.md).

Usage: python code/run_followup4.py <derived_dir/criteo_attr.parquet> [out_dir]
Refits the third design's labels-seen, delayed-feedback and reference networks with its seeds. About 12 minutes.
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
import followup3_core as f3  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SEED, CUTOFFS, W, DRAWS, MIN_CONV, BOOT_SEED = 20261128, tuple(range(22, 31)), 14, 200, 200, 20261129
NETS = ["labels_seen", "delay", "reference"]
FORECASTS = NETS + ["corrected_test_day", "corrected_previous_day", "pooled_test_day"]


def log(msg, t0=[time.time()]):
    print(f"[{time.time() - t0[0]:6.0f}s] {msg}", flush=True)


def main(src, out):
    out = Path(out)
    d = pd.read_parquet(src, columns=["timestamp", "uid", "campaign", "conversion", "conversion_timestamp", "click",
                                      "time_since_last_click"])
    d = v2.prepare(d)
    camp_idx, camp_values = pd.factorize(d.campaign, sort=True)
    ts, conv = d.timestamp.to_numpy(np.float64), d.conversion.to_numpy()
    cts = d.conversion_timestamp.to_numpy(np.float64)
    y14 = v2.window_label(ts, conv, cts, W); uid = d.uid.to_numpy()
    camp = torch.from_numpy(camp_idx.astype(np.int64)); num_raw = d[v2.NUM].to_numpy(np.float32)
    del d
    K = len(camp_values)
    pred = {k: [] for k in FORECASTS}; Y, U, C = [], [], []
    for T in CUTOFFS:
        tr = (ts >= v2.WINDOW * dc.DAY) & (ts < T * dc.DAY); te = (ts >= T * dc.DAY) & (ts < (T + 1) * dc.DAY)
        seen, delay, elapsed = v2.labels_at_cutoff(ts, conv, cts, T, W)
        mu, sd = num_raw[tr].mean(0), num_raw[tr].std(0) + 1e-6

        def tensors(mask):
            idx = torch.from_numpy(np.flatnonzero(mask))
            return {"camp": camp[idx], "num": torch.from_numpy((num_raw[mask] - mu) / sd)}
        X_tr, X_te = tensors(tr), tensors(te)
        base = max(float(seen[tr].mean()), 1e-3)
        jobs = {"labels_seen": ("label", {"label": torch.from_numpy(seen[tr])}),
                "delay": ("delay", {"label": torch.from_numpy(seen[tr]), "delay": torch.from_numpy(delay[tr]),
                                    "elapsed": torch.from_numpy(elapsed[tr])}),
                "reference": ("label", {"label": torch.from_numpy(y14[tr])})}
        prev = (ts >= (T - 1) * dc.DAY) & (ts < T * dc.DAY)
        X_prev = tensors(prev)
        on_prev = {}
        for name, (kind, target) in jobs.items():
            net = v2.fit(K, kind, X_tr, target, base, SEED + T, window=W)
            pred[name].append(v2.predict(net, X_te)[0])
            if name != "reference":
                on_prev[name] = v2.predict(net, X_prev)[0]
        ps, pd_, ct = pred["labels_seen"][-1], pred["delay"][-1], camp_idx[te]
        k = f3.campaign_ratio(ct, pd_, ps, K)                       # every test campaign has impressions on day T
        k_prev = f3.campaign_ratio(camp_idx[prev], on_prev["delay"], on_prev["labels_seen"], K)
        pred["corrected_test_day"].append(f3.corrected(ps, ct, k))
        pred["corrected_previous_day"].append(f3.corrected(ps, ct, k_prev))
        pred["pooled_test_day"].append(f3.corrected(ps, ct, np.full(K, pd_.sum() / ps.sum())))
        Y.append(y14[te].astype(np.float64)); U.append(uid[te]); C.append(camp_idx[te])
        yt = Y[-1]
        log(f"cutoff {T}: " + json.dumps({n: round(float(pred[n][-1].sum() / yt.sum()), 3) for n in FORECASTS})
            + f"; test-day k_c p10/p50/p90 {np.round(np.quantile(k[np.bincount(ct, minlength=K) > 0], [.1, .5, .9]), 3).tolist()}"
            + f"; previous-day k_c p10/p50/p90 {np.round(np.quantile(k_prev[np.bincount(ct, minlength=K) > 0], [.1, .5, .9]), 3).tolist()}")

    y = np.concatenate(Y); cc = np.concatenate(C); users = pd.factorize(np.concatenate(U))[0]; n_users = int(users.max()) + 1
    P = {k: np.concatenate(v) for k, v in pred.items()}
    keep = np.bincount(cc, y, K) >= MIN_CONV
    rank = {k: dc.Ranker(P[k], y) for k in FORECASTS}
    ll = {k: dc.log_loss_rows(P[k], y) for k in FORECASTS}
    point = {k: dc.metrics(P[k], y, ranker=rank[k]) | {"campaign_error": f3.campaign_error(P[k], y, cc, keep, K)} for k in FORECASTS}
    draws = {k: [] for k in FORECASTS}
    for w in dc.user_weights(users, n_users, DRAWS, BOOT_SEED):
        for k in FORECASTS:
            draws[k].append({"log_loss": float((w @ ll[k]) / w.sum()), "campaign_error": f3.campaign_error(P[k], y, cc, keep, K, w),
                             "calibration_ratio": float((w @ P[k]) / (w @ y))})

    def ci(x):
        return [float(np.quantile(x, 0.025)), float(np.quantile(x, 0.975))]

    def diff(a, b, m):
        return {"estimate": point[a][m] - point[b][m], "ci95": ci([da[m] - db[m] for da, db in zip(draws[a], draws[b])])}
    err = {k: f3.per_campaign_error(P[k], y, cc, keep, K) for k in FORECASTS}
    R = {"campaigns_scored": int(keep.sum()), "share_of_test_conversions": float(y[keep[cc]].sum() / y.sum()),
         "test_impressions": int(len(y)), "test_conversions": int(y.sum()),
         "forecasts": {k: {m: {"estimate": point[k][m]} | ({"ci95": ci([x[m] for x in draws[k]])} if m in draws[k][0] else {})
                           for m in point[k]} for k in FORECASTS},
         "differences": {f"log_loss_{a}_minus_{b}": diff(a, b, "log_loss")
                         for a in ("corrected_test_day", "corrected_previous_day", "pooled_test_day", "delay")
                         for b in ("labels_seen", "delay", "reference") if a != b}
                        | {f"campaign_error_{a}_minus_labels_seen": diff(a, "labels_seen", "campaign_error")
                           for a in ("delay", "corrected_test_day", "corrected_previous_day", "pooled_test_day")},
         "share_of_campaigns_smaller_error_than_labels_seen": {k: float(np.mean(err[k][keep] < err["labels_seen"][keep])) for k in FORECASTS if k != "labels_seen"},
         "campaign_error_quantiles": {k: [float(q) for q in np.nanquantile(err[k][keep], [0.25, 0.5, 0.75, 0.9])] for k in FORECASTS}}
    R["decision"] = {
        "corrected_ranker_improves_fit": {"met": bool(R["differences"]["log_loss_corrected_test_day_minus_labels_seen"]["ci95"][1] < 0),
                                          "rule": "pooled log loss of the corrected ranker with the test-day ratio below the labels-seen network's (95% interval of the difference below zero)"}}
    R["seconds"] = round(time.time() - log.__defaults__[0][0])
    (out / "followup4.json").write_text(json.dumps(R, indent=1))
    log(json.dumps({k: {m: round(point[k][m], 5) for m in ("calibration_ratio", "log_loss", "roc_auc", "campaign_error")} for k in FORECASTS}))
    log("decision " + json.dumps({k: v["met"] for k, v in R["decision"].items()}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ROOT / "out")
