"""One marketing mix model for all brands, with partial pooling of the media parameters (design/followup_plan.md).

Usage: python code/run_pooled.py <conjura_mmm_data.csv> <out_dir> [W|D] [processes]
Needs NumPyro and JAX (see requirements-mmm.txt).

Fits the pooled model to real revenue and to two simulations with known channel returns, fits the per-brand model of
run_mmm.py to the same simulations, and writes mmm_pooled_summary*.json, mmm_pooled_recovery*.csv and
mmm_pooled_brands*.csv.
"""
import json
import os
import sys
import time
import warnings

warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mmm_core import (settings, load_brands, design, lag_matrix, media_contribution, simulate_revenue,  # noqa: E402
                      simulate_revenue_shapes)
from run_mmm import fit_brand  # noqa: E402

CHANNELS = ("google", "meta")
CHAINS, WARMUP, DRAWS, SEED = 4, 1000, 1000, 21


def prepare(brands, orgs, freq, y_override=None):
    """Arrays for the pooled model, padded to the longest brand: scaled revenue, design, lagged scaled spend."""
    s = settings(freq); H, L = s["H"], s["L"]
    B = len(orgs); T = max(len(brands[o]) for o in orgs)
    P = design(2, freq, np.zeros(2)).shape[1]
    d = dict(y=np.zeros((B, T)), train=np.zeros((B, T), bool), X=np.zeros((B, T, P)), SL=np.zeros((B, T, L, 2)),
             n=np.zeros(B, int), ntr=np.zeros(B, int), ymean=np.zeros(B), spend_tr=np.zeros((B, 2)), L=L, freq=freq,
             orgs=list(orgs))
    for i, o in enumerate(orgs):
        g = brands[o]; n = len(g); ntr = n - H
        y_raw = g.rev.values.astype(float) if y_override is None else np.asarray(y_override[i], dtype=float)
        S = np.column_stack([g.google.values, g.meta.values]).astype(float)
        smax = S[:ntr].max(axis=0); smax[smax == 0] = 1.0
        d["ymean"][i] = y_raw[:ntr].mean()
        d["y"][i, :n] = y_raw / d["ymean"][i]
        d["train"][i, :ntr] = True
        d["X"][i, :n] = design(n, freq, g.week.dt.weekday.values)
        for c in range(2):
            d["SL"][i, :n, :, c] = lag_matrix(S[:, c] / smax[c], L)
        d["n"][i], d["ntr"][i], d["spend_tr"][i] = n, ntr, S[:ntr].sum(axis=0)
    return d


def fit_pooled(args):
    """Fit the pooled model; return per-brand ROAS (median, 90% interval, R-hat), holdout wMAPE and shared parameters."""
    tag, d = args
    import numpyro
    numpyro.set_host_device_count(CHAINS)
    numpyro.enable_x64()
    import jax
    import jax.numpy as jnp
    import numpyro.distributions as dist
    from numpyro.diagnostics import split_gelman_rubin
    from numpyro.infer import MCMC, NUTS

    t0 = time.time()
    B, T, P = d["X"].shape; L = d["L"]
    lag = jnp.arange(L)

    def model(X, SL, y, train):
        b0 = numpyro.sample("b0", dist.Normal(1.0, 1.0).expand([B]).to_event(1))
        b = numpyro.sample("b", dist.Normal(0.0, 0.5).expand([B, P]).to_event(2))
        sigma = numpyro.sample("sigma", dist.HalfNormal(0.5).expand([B]).to_event(1))

        def pooled(name, mu_loc, mu_sd, tau_sd):
            mu = numpyro.sample(f"mu_{name}", dist.Normal(mu_loc, mu_sd).expand([2]).to_event(1))
            tau = numpyro.sample(f"tau_{name}", dist.HalfNormal(tau_sd).expand([2]).to_event(1))
            z = numpyro.sample(f"z_{name}", dist.Normal(0.0, 1.0).expand([B, 2]).to_event(2))
            return mu + tau * z

        a = numpyro.deterministic("a", jax.nn.sigmoid(pooled("a", 0.0, 1.0, 1.0)))
        h = numpyro.deterministic("h", jax.nn.sigmoid(pooled("h", 0.0, 1.0, 1.0)))
        k = numpyro.deterministic("k", jnp.exp(pooled("k", 0.0, 0.3, 0.3)))
        beta = numpyro.deterministic("beta", jnp.exp(pooled("beta", -1.0, 1.0, 1.0)))
        w = a[:, :, None] ** lag
        w = w / w.sum(axis=-1, keepdims=True)                        # brand x channel x lag
        ad = jnp.einsum("btlc,bcl->btc", SL, w)
        pos = ad > 0
        sk = jnp.where(pos, ad, 1.0) ** k[:, None, :]                # guarded: padded and zero-spend periods give 0
        sat = jnp.where(pos, sk / (sk + h[:, None, :] ** k[:, None, :]), 0.0)
        mu = b0[:, None] + jnp.einsum("btp,bp->bt", X, b) + (beta[:, None, :] * sat).sum(axis=-1)
        numpyro.sample("y", dist.Normal(mu, sigma[:, None]).mask(train).to_event(2), obs=y)

    mcmc = MCMC(NUTS(model, target_accept_prob=0.9), num_warmup=WARMUP, num_samples=DRAWS, num_chains=CHAINS,
                chain_method="parallel", progress_bar=False)
    mcmc.run(jax.random.PRNGKey(SEED), jnp.asarray(d["X"]), jnp.asarray(d["SL"]), jnp.asarray(d["y"]),
             jnp.asarray(d["train"]))
    byc = {k_: np.asarray(v) for k_, v in mcmc.get_samples(group_by_chain=True).items()}
    rhat_all = max(float(np.nanmax(split_gelman_rubin(v))) for k_, v in byc.items())
    p = {k_: v.reshape((-1,) + v.shape[2:]) for k_, v in byc.items()}
    nd = p["b0"].shape[0]
    rows = []
    for i, o in enumerate(d["orgs"]):
        n, ntr = d["n"][i], d["ntr"][i]
        contrib = np.stack([media_contribution(d["SL"][i, :n, :, c], p["a"][:, i, c], p["h"][:, i, c], p["k"][:, i, c],
                                               p["beta"][:, i, c]) for c in range(2)], axis=1)   # draws x channel x n
        mu = p["b0"][:, i][:, None] + p["b"][:, i] @ d["X"][i, :n].T + contrib.sum(axis=1)
        yhat = mu.mean(axis=0); y = d["y"][i, :n]
        roas = contrib[:, :, :ntr].sum(axis=2) * d["ymean"][i] / np.where(d["spend_tr"][i] > 0, d["spend_tr"][i], np.nan)
        rhat = [float(split_gelman_rubin(roas[:, c].reshape(CHAINS, nd // CHAINS))) for c in range(2)]
        rows.append(dict(org=o, wmape=float(np.abs(y[ntr:] - yhat[ntr:]).sum() / y[ntr:].sum()),
                         roas_med=np.nanmedian(roas, axis=0).tolist(), roas_lo=np.nanquantile(roas, 0.05, axis=0).tolist(),
                         roas_hi=np.nanquantile(roas, 0.95, axis=0).tolist(), roas_rhat=rhat,
                         share_media=float((contrib[:, :, :ntr].sum(axis=(1, 2)) / y[:ntr].sum()).mean()),
                         adstock_med=np.median(p["a"][:, i], axis=0).tolist()))
    shared = {k_: dict(median=np.median(p[k_], axis=0).tolist(), lo=np.quantile(p[k_], 0.05, axis=0).tolist(),
                       hi=np.quantile(p[k_], 0.95, axis=0).tolist())
              for k_ in p if k_.startswith(("mu_", "tau_"))}
    div = int(np.asarray(mcmc.get_extra_fields()["diverging"]).sum())
    return dict(tag=tag, rows=rows, shared=shared, rhat_max_all=rhat_all, divergences=div, seconds=round(time.time() - t0))


def recovery_table(sim, orgs, truth, pooled, single):
    """One row per brand and channel: true ROAS and both models' estimates, intervals and convergence."""
    out = []
    for i, o in enumerate(orgs):
        for c, ch in enumerate(CHANNELS):
            out.append(dict(sim=sim, org=o, channel=ch, true=truth[i][c],
                            pooled=pooled[i]["roas_med"][c], pooled_lo=pooled[i]["roas_lo"][c],
                            pooled_hi=pooled[i]["roas_hi"][c], pooled_converged=max(pooled[i]["roas_rhat"]) < 1.05,
                            single=single[i]["roas_med"][c], single_lo=single[i]["roas_lo"][c],
                            single_hi=single[i]["roas_hi"][c], single_converged=single[i]["rhat"] < 1.05))
    return pd.DataFrame(out)


def recovery_metrics(t, model):
    """Rank correlation, median absolute relative error and 90% coverage of one model on a recovery table."""
    from scipy.stats import spearmanr
    rel = np.abs(t[model] - t["true"]) / t["true"]
    return dict(n=int(len(t)), spearman=float(spearmanr(t["true"], t[model])[0]), median_abs_rel_err=float(rel.median()),
                mean_abs_rel_err=float(rel.mean()),
                coverage90=float(((t["true"] >= t[f"{model}_lo"]) & (t["true"] <= t[f"{model}_hi"])).mean()))


def recovery_decision(t, boot=2000, seed=1):
    """Follow-up plan rule: lower median error, and brand-bootstrap interval of the mean difference below 0."""
    t = t.assign(d=np.abs(t.pooled - t.true) / t.true - np.abs(t.single - t.true) / t.true)
    by = t.groupby("org").d.mean().values
    rng = np.random.default_rng(seed)
    bs = [rng.choice(by, len(by)).mean() for _ in range(boot)]
    lo, hi = np.quantile(bs, [0.025, 0.975])
    med_p = float((np.abs(t.pooled - t.true) / t.true).median()); med_s = float((np.abs(t.single - t.true) / t.true).median())
    return dict(brands=int(len(by)), diff_mean=float(by.mean()), diff_ci=[float(lo), float(hi)],
                rule_met=bool(med_p < med_s and hi < 0))


def main(raw, out, freq="W", nproc=14):
    from multiprocessing import get_context
    t0 = time.time()
    suf = settings(freq)["SUF"]
    brands, n_all = load_brands(raw, freq)
    orgs = sorted(brands)
    print("brands in file", n_all, "eligible", len(orgs), flush=True)
    ctx = get_context("spawn")
    with ctx.Pool(nproc) as pool:
        b0 = pool.map(fit_brand, [(o, brands[o], False, 12, None, freq) for o in orgs], chunksize=1)
        rng1, rng2 = np.random.default_rng(21), np.random.default_rng(22)
        sim1 = [simulate_revenue_shapes(brands[o], b0[i]["base_fit"], b0[i]["ymean"], b0[i]["resid_sd"], rng1, freq)
                for i, o in enumerate(orgs)]
        sim2 = [simulate_revenue(brands[o], b0[i]["base_fit"], b0[i]["ymean"], b0[i]["resid_sd"], rng2, freq)
                for i, o in enumerate(orgs)]
        single1 = pool.map(fit_brand, [(o, brands[o], True, 13, sim1[i][0], freq) for i, o in enumerate(orgs)], chunksize=1)
        single2 = pool.map(fit_brand, [(o, brands[o], True, 13, sim2[i][0], freq) for i, o in enumerate(orgs)], chunksize=1)
    print("per-brand fits done", round(time.time() - t0), "s", flush=True)
    jobs = [("real", prepare(brands, orgs, freq)),
            ("sim_brand_shapes", prepare(brands, orgs, freq, [s_[0] for s_ in sim1])),
            ("sim_common_shapes", prepare(brands, orgs, freq, [s_[0] for s_ in sim2]))]
    with ctx.Pool(3) as pool:
        real, p1, p2 = pool.map(fit_pooled, jobs, chunksize=1)
    print("pooled fits done", round(time.time() - t0), "s", flush=True)

    os.makedirs(out, exist_ok=True)
    rec = pd.concat([recovery_table("brand_shapes", orgs, [s_[1] for s_ in sim1], p1["rows"], single1),
                     recovery_table("common_shapes", orgs, [s_[1] for s_ in sim2], p2["rows"], single2)])
    rec.to_csv(os.path.join(out, f"mmm_pooled_recovery{suf}.csv"), index=False)
    summ = dict(freq=freq, brands_in_file=int(n_all), eligible=len(orgs), chains=CHAINS, warmup=WARMUP, draws=DRAWS)
    for sim, fit in (("brand_shapes", p1), ("common_shapes", p2)):
        t = rec[rec.sim == sim]; both = t[t.pooled_converged & t.single_converged]
        summ[f"recovery_{sim}"] = dict(
            pooled_brands_converged=int(t.groupby("org").pooled_converged.all().sum()),
            single_brands_converged=int(t.groupby("org").single_converged.all().sum()),
            rhat_max_all=fit["rhat_max_all"], divergences=fit["divergences"], seconds=fit["seconds"],
            both_converged=dict(pooled=recovery_metrics(both, "pooled"), single=recovery_metrics(both, "single"),
                                decision=recovery_decision(both)),
            all_brand_channels=dict(pooled=recovery_metrics(t, "pooled"), single=recovery_metrics(t, "single"),
                                    decision=recovery_decision(t)),
            shared=fit["shared"])
    summ["recovery_rule_met"] = summ["recovery_brand_shapes"]["both_converged"]["decision"]["rule_met"]

    rows = []
    for i, o in enumerate(orgs):
        r = real["rows"][i]
        rows.append(dict(org=o, periods=int(len(brands[o])), wmape_pooled=r["wmape"], wmape_b0=b0[i]["wmape"],
                         wmape_naive=b0[i]["wmape_naive"], rhat_b0=b0[i]["rhat"], roas_rhat=max(r["roas_rhat"]),
                         roas_google=r["roas_med"][0], roas_google_lo=r["roas_lo"][0], roas_google_hi=r["roas_hi"][0],
                         roas_meta=r["roas_med"][1], roas_meta_lo=r["roas_lo"][1], roas_meta_hi=r["roas_hi"][1],
                         share_media=r["share_media"], adstock_google=r["adstock_med"][0], adstock_meta=r["adstock_med"][1]))
    df = pd.DataFrame(rows); df.to_csv(os.path.join(out, f"mmm_pooled_brands{suf}.csv"), index=False)
    conv = df[(df.roas_rhat < 1.05) & (df.rhat_b0 < 1.05)]
    diff = (conv.wmape_pooled - conv.wmape_b0).values
    rb = np.random.default_rng(1); bs = [rb.choice(diff, len(diff)).mean() for _ in range(2000)]
    lo, hi = np.quantile(bs, [0.025, 0.975])
    summ["forecast"] = dict(
        converged=int(len(conv)), rhat_max_all=real["rhat_max_all"], divergences=real["divergences"],
        seconds=real["seconds"],
        wmape_median=dict(pooled=float(conv.wmape_pooled.median()), b0=float(conv.wmape_b0.median()),
                          naive=float(conv.wmape_naive.median())),
        pooled_better_than_b0=int((diff < 0).sum()), diff_mean=float(diff.mean()), diff_ci=[float(lo), float(hi)],
        rule_met=bool((diff < 0).mean() > 0.5 and hi < 0),
        roas_median=dict(google=float(conv.roas_google.median()), meta=float(conv.roas_meta.median())),
        media_share_median=float(conv.share_media.median()), shared=real["shared"])
    summ["seconds"] = round(time.time() - t0)
    json.dump(summ, open(os.path.join(out, f"mmm_pooled_summary{suf}.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in summ.items()}, indent=1))


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[2] if len(a) > 2 else "W", int(a[3]) if len(a) > 3 else 14)
