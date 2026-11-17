"""Part A: Laplace-noised segment counts; no pooling against a noise-aware multilevel normal model.

Usage: python code/a_private_aggregates.py <criteo_compact.parquet> [out_dir]
The parquet file is written by study 01b's code/01_build.py. About 3 minutes; needs NumPyro and JAX.
"""
import json
import sys
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import numpyro
numpyro.set_host_device_count(4)
import jax
import jax.numpy as jnp
import numpyro.distributions as dist
from numpyro.diagnostics import summary
from numpyro.infer import MCMC, NUTS

sys.path.insert(0, str(Path(__file__).resolve().parent))
from private_core import S, EPS, SEED, cell_arrays, laplace_release, no_pooling, sampling_variance, rmse  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DRAWS = 3


def model(d, v):
    mu = numpyro.sample("mu", dist.Normal(0, 0.05)); tau = numpyro.sample("tau", dist.HalfNormal(0.05))
    with numpyro.plate("s", S):
        z = numpyro.sample("z", dist.Normal(0, 1))
    theta = numpyro.deterministic("theta", mu + tau * z)
    numpyro.sample("d", dist.Normal(theta, jnp.sqrt(v)), obs=d)


def summarize(rows):
    df = pd.DataFrame(rows); df["eps"] = df.eps.astype(str)
    g = df.groupby(["eps", "rep"])[["rmse_nopool", "rmse_ml"]].mean().reset_index()
    out = {"by_eps": {}, "rhat_max": float(df.rhat.max()), "fits": int(len(df)),
           "fits_rhat_above_1.01": int((df.rhat >= 1.01).sum())}
    for e, x in g.groupby("eps"):
        out["by_eps"][e] = {"rmse_nopool": float(x.rmse_nopool.mean()), "rmse_ml": float(x.rmse_ml.mean()),
                            "ml_better_reps": int((x.rmse_ml < x.rmse_nopool).sum())}
    ref = out["by_eps"]["inf"]["rmse_nopool"]
    ok = [e for e in ["0.1", "0.5", "1.0", "5.0"] if out["by_eps"][e]["rmse_ml"] <= ref]
    out["nonprivate_nopool_rmse"] = ref
    out["smallest_eps_ml_le_nonprivate_nopool"] = min(ok, key=float) if ok else None
    out["rule_met"] = all(v["ml_better_reps"] >= 8 for v in out["by_eps"].values())
    return out


def main(src, out):
    out = Path(out); out.mkdir(exist_ok=True)
    cells = duckdb.sql(f"select rep, seg, treatment, count(*) n, sum(visit) y from '{src}' group by all").df()
    mc = MCMC(NUTS(model), num_warmup=500, num_samples=500, num_chains=4, progress_bar=False)
    rows = []; t0 = time.time()
    for r in range(10):
        n, y = cell_arrays(cells[cells.rep == r]); nb, yb = cell_arrays(cells[cells.rep != r])
        bench = yb[:, 1] / nb[:, 1] - yb[:, 0] / nb[:, 0]
        for ei, eps in enumerate(EPS):
            for k in range(DRAWS if eps else 1):
                seed = SEED + 1000 * r + 10 * ei + k
                nn, yy, b = laplace_release(n, y, eps, np.random.default_rng(seed))
                d, v = no_pooling(nn, yy), sampling_variance(nn, yy, b)
                mc.run(jax.random.PRNGKey(seed), jnp.array(d), jnp.array(v))
                smp = mc.get_samples(group_by_chain=True)
                sm = summary({q: smp[q] for q in ["mu", "tau", "theta"]})
                rhat = max(float(np.max(x["r_hat"])) for x in sm.values())
                th = np.asarray(smp["theta"]).reshape(-1, S).mean(0)
                rows.append({"rep": r, "eps": eps if eps else "inf", "draw": k, "rmse_nopool": rmse(d, bench),
                             "rmse_ml": rmse(th, bench), "rhat": rhat, "tau": float(np.mean(smp["tau"]))})
        print(r, round(time.time() - t0), flush=True)
    json.dump(rows, open(out / "a_private_raw.json", "w"))
    res = summarize(rows)
    json.dump(res, open(out / "a_private_summary.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ROOT / "out")
