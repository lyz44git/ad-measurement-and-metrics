"""Part 2: segment effects from 2% replicates; no pooling vs complete pooling vs multilevel binomial (NUTS).

Usage: python code/03_segments_bayes.py <derived_dir> <out_dir> [warmup draws [replicates]]   (plan: 1000 1000)
Passing a comma-separated list of replicates writes part2_segments_rerun.json instead (design/deviations.md, item 1).
"""
from pathlib import Path
import sys, json, time, duckdb, numpy as np
import numpyro; numpyro.set_host_device_count(4)
import jax, jax.numpy as jnp, numpyro.distributions as dist
from numpyro.infer import MCMC, NUTS
from numpyro.diagnostics import summary
F, OUT = Path(sys.argv[1]) / "criteo_compact.parquet", Path(sys.argv[2])
WARM, DRAWS = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (1000, 1000)
ONLY = [int(x) for x in sys.argv[5].split(",")] if len(sys.argv) > 5 else list(range(10))
S = 100
cells = duckdb.sql(f"select rep, seg, treatment, count(*) n, sum(visit) y from '{F}' group by all").df()
tot = cells.groupby(["seg", "treatment"])[["n", "y"]].sum()

def arr(df):
    n = np.zeros((S, 2)); y = np.zeros((S, 2))
    for r in df.itertuples(): n[r.seg, r.treatment] += r.n; y[r.seg, r.treatment] += r.y
    return n, y

def model(n, y):
    mu_a = numpyro.sample("mu_a", dist.Normal(-3, 1.5)); mu_b = numpyro.sample("mu_b", dist.Normal(0, 1))
    sa = numpyro.sample("sigma_a", dist.HalfNormal(1)); sb = numpyro.sample("sigma_b", dist.HalfNormal(0.5))
    with numpyro.plate("s", S):
        za = numpyro.sample("z_a", dist.Normal(0, 1)); zb = numpyro.sample("z_b", dist.Normal(0, 1))
    a = mu_a + sa * za; b = mu_b + sb * zb
    numpyro.deterministic("eff", jax.nn.sigmoid(a + b) - jax.nn.sigmoid(a))
    numpyro.sample("y0", dist.Binomial(n[:, 0], logits=a), obs=y[:, 0])
    numpyro.sample("y1", dist.Binomial(n[:, 1], logits=a + b), obs=y[:, 1])

out = {}
for r in ONLY:
    t0 = time.time()
    n, y = arr(cells[cells.rep == r])
    nb, yb = arr(cells[cells.rep != r])
    bench = yb[:, 1] / nb[:, 1] - yb[:, 0] / nb[:, 0]
    p = y / n; nopool = p[:, 1] - p[:, 0]
    se = np.sqrt(p[:, 0] * (1 - p[:, 0]) / n[:, 0] + p[:, 1] * (1 - p[:, 1]) / n[:, 1])
    P = y.sum(0) / n.sum(0); cpool = np.full(S, P[1] - P[0])
    mc = MCMC(NUTS(model, target_accept_prob=0.9), num_warmup=WARM, num_samples=DRAWS, num_chains=4, progress_bar=False)
    mc.run(jax.random.PRNGKey(20261115 + r), jnp.array(n), jnp.array(y))
    smp = mc.get_samples(group_by_chain=True)
    sm = summary({k: smp[k] for k in ["mu_a", "mu_b", "sigma_a", "sigma_b", "eff"]})
    rhat = max(float(np.max(v["r_hat"])) for v in sm.values()); ess = min(float(np.min(v["n_eff"])) for v in sm.values())
    e = np.asarray(smp["eff"]).reshape(-1, S); bayes = e.mean(0); lo, hi = np.quantile(e, [.05, .95], axis=0)
    rmse = lambda x: float(np.sqrt(np.mean((x - bench) ** 2))); mae = lambda x: float(np.mean(np.abs(x - bench)))
    top = lambda x: float(bench[np.argsort(-x)[:20]].mean())
    out[r] = {"n_users": int(n.sum()), "n_control": int(n[:, 0].sum()),
              "rmse": {"nopool": rmse(nopool), "cpool": rmse(cpool), "bayes": rmse(bayes)},
              "mae": {"nopool": mae(nopool), "cpool": mae(cpool), "bayes": mae(bayes)},
              "top20_bench_mean": {"nopool": top(nopool), "bayes": top(bayes), "oracle": top(bench), "all": float(bench.mean())},
              "coverage90": {"nopool": float(np.mean(np.abs(nopool - bench) <= 1.645 * se)), "bayes": float(np.mean((bench >= lo) & (bench <= hi)))},
              "rhat_max": rhat, "ess_min": ess, "sigma_b_mean": float(np.mean(smp["sigma_b"])),
              "warmup": WARM, "draws": DRAWS, "sec": round(time.time() - t0, 1),
              "seg": {"bench": bench.tolist(), "nopool": nopool.tolist(), "bayes": bayes.tolist(), "lo": lo.tolist(), "hi": hi.tolist(),
                      "np_lo": (nopool - 1.645 * se).tolist(), "np_hi": (nopool + 1.645 * se).tolist()}}
    o = out[r]; print(r, o["rmse"], o["top20_bench_mean"], "rhat", round(rhat, 4), "ess", round(ess), o["sec"], flush=True)
tag = "" if len(sys.argv) <= 5 else "_rerun"
json.dump(out, open(OUT / f"part2_segments{tag}.json", "w"))
