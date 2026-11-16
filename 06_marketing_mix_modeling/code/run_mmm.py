"""Per-brand Bayesian marketing mix models (Part A of design/analysis_plan.md).

Usage: python code/run_mmm.py <conjura_mmm_data.csv> <out_dir> [W|D] [processes]
W (default) is the planned weekly model; D is the daily rerun (design/deviations.md, item 1). Needs NumPyro and JAX
(see requirements-mmm.txt). The daily run takes about 3 minutes with 14 processes.

For each eligible brand: the model with media terms and the same model without them, both forecast on a holdout;
channel ROAS, a 10% reallocation between channels (model-implied, not validated) and, for 20 brands, a parameter-
recovery check that refits the model on real spend with simulated revenue.
"""
import os
import sys
import json
import time
import warnings

os.environ.setdefault("XLA_FLAGS", "--xla_cpu_multi_thread_eigen=false intra_op_parallelism_threads=1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mmm_core import settings, load_brands, design, geometric_adstock, hill, simulate_revenue  # noqa: E402


def fit_brand(args):
    org, g, media, seed, y_override, freq = args
    import jax, jax.numpy as jnp, numpyro, numpyro.distributions as dist
    from numpyro.infer import MCMC, NUTS
    from numpyro.diagnostics import summary
    numpyro.set_host_device_count(1)
    s = settings(freq); H, L, YEAR = s["H"], s["L"], s["YEAR"]
    n = len(g); ntr = n - H
    y_raw = g.rev.values.astype(float) if y_override is None else y_override
    ymean = y_raw[:ntr].mean()
    y = y_raw / ymean
    X = design(n, freq, g.week.dt.weekday.values)
    S = np.column_stack([g.google.values, g.meta.values]).astype(float)
    smax = S[:ntr].max(axis=0); smax[smax == 0] = 1.0
    Sx = S / smax

    def media_term(Sx_, a, h, k, beta):
        tot = 0.0; parts = []
        for c in range(2):
            parts.append(beta[c] * hill(geometric_adstock(Sx_[:, c], a[c], L, xp=jnp), h[c], k[c]))
            tot = tot + parts[-1]
        return tot, parts

    def model(Xtr, Str, ytr=None):
        b0 = numpyro.sample("b0", dist.Normal(1.0, 1.0))
        b = numpyro.sample("b", dist.Normal(0.0, 0.5).expand([Xtr.shape[1]]).to_event(1))
        mu = b0 + Xtr @ b
        if media:
            a = numpyro.sample("a", dist.Beta(2.0, 2.0).expand([2]).to_event(1))
            h = numpyro.sample("h", dist.Beta(2.0, 2.0).expand([2]).to_event(1))
            k = numpyro.sample("k", dist.LogNormal(0.0, 0.3).expand([2]).to_event(1))
            beta = numpyro.sample("beta", dist.HalfNormal(1.0).expand([2]).to_event(1))
            mu = mu + media_term(Str, a, h, k, beta)[0]
        sigma = numpyro.sample("sigma", dist.HalfNormal(0.5))
        numpyro.sample("y", dist.Normal(mu, sigma), obs=ytr)

    mcmc = MCMC(NUTS(model, target_accept_prob=0.9), num_warmup=500, num_samples=500, num_chains=2,
                chain_method="sequential", progress_bar=False)
    mcmc.run(jax.random.PRNGKey(seed), jnp.asarray(X[:ntr]), jnp.asarray(Sx[:ntr]), jnp.asarray(y[:ntr]))
    p = {k_: np.asarray(v) for k_, v in mcmc.get_samples().items()}
    rhat = max(float(np.nanmax(v["r_hat"])) for v in summary(mcmc.get_samples(group_by_chain=True)).values())
    nd = len(p["b0"])
    Sj = jnp.asarray(Sx)
    mu_all = np.zeros((nd, n)); contrib = np.zeros((nd, 2, n))
    for i in range(nd):
        base = p["b0"][i] + X @ p["b"][i]
        if media:
            tot, parts = media_term(Sj, p["a"][i], p["h"][i], p["k"][i], p["beta"][i])
            contrib[i, 0] = np.asarray(parts[0]); contrib[i, 1] = np.asarray(parts[1])
            base = base + np.asarray(tot)
        mu_all[i] = base
    yhat = mu_all.mean(axis=0)
    res = dict(org=org, n=n, ntr=ntr, rhat=rhat, ymean=float(ymean),
               wmape=float(np.abs(y[ntr:] - yhat[ntr:]).sum() / y[ntr:].sum()),
               resid_sd=float(np.std(y[:ntr] - yhat[:ntr])))
    res["wmape_naive"] = float(np.abs(y[ntr:] - y[ntr - YEAR:n - YEAR]).sum() / y[ntr:].sum())   # seasonal naive
    if media:
        spend_tr = S[:ntr].sum(axis=0)
        rev_c = contrib[:, :, :ntr].sum(axis=2) * ymean            # draws x channel
        roas = rev_c / np.where(spend_tr > 0, spend_tr, np.nan)
        res["roas_med"] = np.nanmedian(roas, axis=0).tolist()
        res["roas_lo"] = np.nanquantile(roas, 0.05, axis=0).tolist(); res["roas_hi"] = np.nanquantile(roas, 0.95, axis=0).tolist()
        res["share_media"] = (rev_c / (y[:ntr].sum() * ymean)).mean(axis=0).tolist()
        res["spend"] = spend_tr.tolist(); res["rev_tr"] = float(y[:ntr].sum() * ymean)
        res["blended_roas"] = float(res["rev_tr"] / spend_tr.sum())
        res["adstock_med"] = np.median(p["a"], axis=0).tolist()
        # marginal return: +10% spend on one channel over the training periods, per unit of added spend
        mroas = np.zeros((nd, 2)); realloc = np.zeros(nd)
        Sup = [Sx.copy(), Sx.copy()]; Sup[0][:, 0] *= 1.1; Sup[1][:, 1] *= 1.1
        for i in range(nd):
            base_tot = np.asarray(media_term(Sj, p["a"][i], p["h"][i], p["k"][i], p["beta"][i])[0])[:ntr].sum()
            for c in range(2):
                up = np.asarray(media_term(jnp.asarray(Sup[c]), p["a"][i], p["h"][i], p["k"][i], p["beta"][i])[0])[:ntr].sum()
                mroas[i, c] = (up - base_tot) * ymean / (0.1 * spend_tr[c])
        res["mroas_med"] = np.median(mroas, axis=0).tolist()
        hi = int(np.argmax(np.median(mroas, axis=0))); lo = 1 - hi
        move = 0.1 * spend_tr[lo]                                    # move 10% of the lower-return channel's spend
        Sre = Sx.copy(); Sre[:, lo] *= 0.9; Sre[:, hi] *= 1 + move / spend_tr[hi]
        for i in range(nd):
            base_tot = np.asarray(media_term(Sj, p["a"][i], p["h"][i], p["k"][i], p["beta"][i])[0])[:ntr].sum()
            new_tot = np.asarray(media_term(jnp.asarray(Sre), p["a"][i], p["h"][i], p["k"][i], p["beta"][i])[0])[:ntr].sum()
            realloc[i] = (new_tot - base_tot) * ymean / res["rev_tr"]
        res["realloc_to"] = ["google", "meta"][hi]
        res["realloc_med"] = float(np.median(realloc)); res["realloc_lo"] = float(np.quantile(realloc, 0.05))
        res["realloc_hi"] = float(np.quantile(realloc, 0.95))
    else:
        res["base_fit"] = yhat.tolist()
    return res


def main(raw, out, freq="W", nproc=14):
    from multiprocessing import get_context
    from scipy.stats import spearmanr
    t0 = time.time()
    suf = settings(freq)["SUF"]
    brands, n_all = load_brands(raw, freq)
    orgs = sorted(brands)
    print("brands in file", n_all, "eligible", len(orgs), flush=True)
    with get_context("spawn").Pool(nproc) as pool:
        mm = pool.map(fit_brand, [(o, brands[o], True, 11, None, freq) for o in orgs], chunksize=1)
        b0 = pool.map(fit_brand, [(o, brands[o], False, 12, None, freq) for o in orgs], chunksize=1)
        rng = np.random.default_rng(7)
        pick = list(rng.choice(len(orgs), size=min(20, len(orgs)), replace=False))
        sims = [simulate_revenue(brands[orgs[i]], b0[i]["base_fit"], b0[i]["ymean"], b0[i]["resid_sd"], rng, freq)
                for i in pick]
        rec = pool.map(fit_brand, [(orgs[i], brands[orgs[i]], True, 13, sims[j][0], freq) for j, i in enumerate(pick)],
                       chunksize=1)
    rows = []
    for a, b in zip(mm, b0):
        rows.append(dict(org=a["org"], weeks=a["n"], rhat_mmm=a["rhat"], rhat_b0=b["rhat"], wmape_mmm=a["wmape"],
                         wmape_b0=b["wmape"], wmape_naive=a["wmape_naive"],
                         roas_google=a["roas_med"][0], roas_google_lo=a["roas_lo"][0], roas_google_hi=a["roas_hi"][0],
                         roas_meta=a["roas_med"][1], roas_meta_lo=a["roas_lo"][1], roas_meta_hi=a["roas_hi"][1],
                         share_google=a["share_media"][0], share_meta=a["share_media"][1], blended_roas=a["blended_roas"],
                         mroas_google=a["mroas_med"][0], mroas_meta=a["mroas_med"][1],
                         adstock_google=a["adstock_med"][0], adstock_meta=a["adstock_med"][1],
                         realloc_to=a["realloc_to"], realloc_med=a["realloc_med"], realloc_lo=a["realloc_lo"],
                         realloc_hi=a["realloc_hi"], spend_google=a["spend"][0], spend_meta=a["spend"][1],
                         rev_tr=a["rev_tr"]))
    os.makedirs(out, exist_ok=True)
    df = pd.DataFrame(rows); df.to_csv(os.path.join(out, f"mmm_brands{suf}.csv"), index=False)
    conv = df[(df.rhat_mmm < 1.05) & (df.rhat_b0 < 1.05)]
    diff = (conv.wmape_mmm - conv.wmape_b0).values
    rb = np.random.default_rng(1); bs = [rb.choice(diff, len(diff)).mean() for _ in range(2000)]
    lo, hi = np.quantile(bs, [0.025, 0.975])
    true = np.array([s_[1] for s_ in sims]).ravel(); est = np.array([r["roas_med"] for r in rec]).ravel()
    elo = np.array([r["roas_lo"] for r in rec]).ravel(); ehi = np.array([r["roas_hi"] for r in rec]).ravel()
    okrec = np.repeat([r["rhat"] < 1.05 for r in rec], 2)
    summ = dict(freq=freq, brands_in_file=int(n_all), eligible=int(len(df)), converged=int(len(conv)),
                weeks_median=float(df.weeks.median()), weeks_total=int(df.weeks.sum()),
                wmape_mean=dict(mmm=float(conv.wmape_mmm.mean()), b0=float(conv.wmape_b0.mean()), naive=float(conv.wmape_naive.mean())),
                wmape_median=dict(mmm=float(conv.wmape_mmm.median()), b0=float(conv.wmape_b0.median()), naive=float(conv.wmape_naive.median())),
                mmm_better_than_b0=int((diff < 0).sum()), mmm_better_than_naive=int((conv.wmape_mmm < conv.wmape_naive).sum()),
                diff_mean=float(diff.mean()), diff_ci=[float(lo), float(hi)],
                rule_met=bool((diff < 0).mean() > 0.5 and hi < 0),
                roas_median=dict(google=float(conv.roas_google.median()), meta=float(conv.roas_meta.median()),
                                 blended=float(conv.blended_roas.median())),
                roas_iqr=dict(google=conv.roas_google.quantile([.25, .75]).tolist(), meta=conv.roas_meta.quantile([.25, .75]).tolist()),
                media_share_median=dict(google=float(conv.share_google.median()), meta=float(conv.share_meta.median()),
                                        total=float((conv.share_google + conv.share_meta).median())),
                brands_google_mroas_higher=int((conv.mroas_google > conv.mroas_meta).sum()),
                realloc_median=float(conv.realloc_med.median()), realloc_brands_ci_above_0=int((conv.realloc_lo > 0).sum()),
                adstock_median=dict(google=float(conv.adstock_google.median()), meta=float(conv.adstock_meta.median())),
                total_spend=float(conv.spend_google.sum() + conv.spend_meta.sum()),
                recovery=dict(n_brands=len(rec), n_converged=int(sum(r["rhat"] < 1.05 for r in rec)),
                              spearman=float(spearmanr(true[okrec], est[okrec])[0]),
                              coverage90=float(((true >= elo) & (true <= ehi))[okrec].mean()),
                              median_abs_rel_err=float(np.median(np.abs(est[okrec] - true[okrec]) / true[okrec]))),
                seconds=round(time.time() - t0))
    json.dump(summ, open(os.path.join(out, f"mmm_summary{suf}.json"), "w"), indent=1)
    pd.DataFrame(dict(true=true, est=est, lo=elo, hi=ehi, converged=okrec)).to_csv(
        os.path.join(out, f"mmm_recovery{suf}.csv"), index=False)
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[2] if len(a) > 2 else "W", int(a[3]) if len(a) > 3 else 14)
