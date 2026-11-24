"""Follow-up of study 02f (design/followup_plan.md, hashed in logs/followup_plan_hash.txt).

Usage: python code/run_followup.py <derived_dir/criteo_attr.parquet> [out_dir]
Same data, features and training as code/run_delay.py; the exponential and Weibull delay networks are trained at each
cutoff with the same seed and scored on the same bootstrap draws. About 10 minutes on an Apple M3 Ultra.
"""
import json
import sys
import time
from pathlib import Path

import sklearn.ensemble  # noqa: F401  (OpenMP order, see run_delay.py)
import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import delay_core as dc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SEED, CUTOFFS, TEST_DAYS, DRAWS = 20261126, (14, 21, 28), 3, 200
MODELS = {"exponential": "dfm", "weibull": "weibull"}


def log(msg, t0=[time.time()]):
    print(f"[{time.time() - t0[0]:6.0f}s] {msg}", flush=True)


def main(src, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    d = pd.read_parquet(src, columns=["timestamp", "uid", "campaign", "conversion", "conversion_timestamp", "click",
                                      "time_since_last_click"])
    d = dc.prepare(d)
    camp_idx, camp_values = pd.factorize(d.campaign, sort=True)
    ts, conv, cts = d.timestamp.to_numpy(np.float64), d.conversion.to_numpy(), d.conversion_timestamp.to_numpy(np.float64)
    delay_all = (cts - ts)[conv == 1] / dc.DAY
    R = {"share_of_30_day_conversions_with_delay_longer_than": {str(T): float((delay_all > T).mean()) for T in CUTOFFS},
         "main_run_delay_network_calibration": {T: v["models"]["delay_network"]["calibration_ratio"]["estimate"]
                                                for T, v in json.loads((out / "delay.json").read_text())["cutoffs"].items()},
         "cutoffs": {}}
    log("identification: " + json.dumps({k: round(v, 3) for k, v in R["share_of_30_day_conversions_with_delay_longer_than"].items()}))
    camp_t = torch.from_numpy(camp_idx.astype(np.int64))
    num_raw = d[dc.NUM].to_numpy(np.float32)
    uid = d.uid.to_numpy()

    for T in CUTOFFS:
        tr = ts < T * dc.DAY
        te = (ts >= T * dc.DAY) & (ts < (T + TEST_DAYS) * dc.DAY)
        seen, delay, elapsed = dc.labels_at_cutoff(ts, conv, cts, T)
        mu, sd = num_raw[tr].mean(0), num_raw[tr].std(0) + 1e-6
        num = torch.from_numpy((num_raw - mu) / sd)
        tidx, eidx = torch.from_numpy(np.flatnonzero(tr)), torch.from_numpy(np.flatnonzero(te))
        T_tr = {"camp": camp_t[tidx], "num": num[tidx]}
        T_te = {"camp": camp_t[eidx], "num": num[eidx]}
        target = {"seen": torch.from_numpy(seen[tr]), "delay": torch.from_numpy(delay[tr]), "elapsed": torch.from_numpy(elapsed[tr])}
        y_te = conv[te].astype(np.float64)
        base = float(seen[tr].mean())
        pred, shape = {}, None
        for name, kind in MODELS.items():
            net = dc.Net(len(camp_values), len(dc.NUM), kind, base_rate=max(base, 1e-3))
            dc.fit(net, T_tr, target, seed=SEED, log=log)
            pred[name] = dc.predict(net, T_te)
            if kind == "weibull":
                with torch.no_grad():
                    net.to("cpu").eval()
                    _, (ls, lk) = net(T_te["camp"][:200_000], T_te["num"][:200_000])
                    shape = [float(q) for q in np.quantile(torch.exp(lk).numpy(), [0.1, 0.5, 0.9])]
                    scale = [float(q) for q in np.quantile(torch.exp(ls).numpy(), [0.1, 0.5, 0.9])]
            log(f"  cutoff {T}: {name} fitted, ratio {pred[name].sum() / y_te.sum():.3f}")
        users = pd.factorize(uid[te])[0]; n_users = int(users.max()) + 1
        rank = {k: dc.Ranker(pred[k], y_te) for k in MODELS}
        point = {k: dc.metrics(pred[k], y_te, ranker=rank[k]) for k in MODELS}
        draws = {k: [] for k in MODELS}
        for w in dc.user_weights(users, n_users, DRAWS, SEED + T):
            for k in MODELS:
                draws[k].append(dc.metrics(pred[k], y_te, w, rank[k]))
        res = {k: {m: {"estimate": point[k][m], "ci95": [float(np.quantile([x[m] for x in draws[k]], q)) for q in (0.025, 0.975)]}
                   for m in point[k]} for k in MODELS}
        dev = np.array([abs(a["calibration_ratio"] - 1) - abs(b["calibration_ratio"] - 1) for a, b in zip(draws["weibull"], draws["exponential"])])
        dll = np.array([a["log_loss"] - b["log_loss"] for a, b in zip(draws["weibull"], draws["exponential"])])
        R["cutoffs"][str(T)] = {
            "models": res, "weibull_shape_quantiles": shape, "weibull_scale_days_quantiles": scale,
            "abs_calibration_error_weibull_minus_exponential": {"estimate": abs(point["weibull"]["calibration_ratio"] - 1) - abs(point["exponential"]["calibration_ratio"] - 1),
                                                               "ci95": [float(np.quantile(dev, 0.025)), float(np.quantile(dev, 0.975))]},
            "log_loss_weibull_minus_exponential": {"estimate": point["weibull"]["log_loss"] - point["exponential"]["log_loss"],
                                                   "ci95": [float(np.quantile(dll, 0.025)), float(np.quantile(dll, 0.975))]}}
        (out / "followup.json").write_text(json.dumps(R, indent=1))
    d14 = R["cutoffs"]["14"]["abs_calibration_error_weibull_minus_exponential"]
    R["decision"] = {"met": bool(d14["ci95"][1] < 0), "rule": "at day 14, |ratio - 1| of the Weibull network below the "
                     "exponential network's, 95% interval of the paired difference below zero"}
    R["seconds"] = round(time.time() - log.__defaults__[0][0])
    (out / "followup.json").write_text(json.dumps(R, indent=1))
    log("decision " + json.dumps(R["decision"]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ROOT / "out")
