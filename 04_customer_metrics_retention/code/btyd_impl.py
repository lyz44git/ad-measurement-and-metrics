# BG/NBD (Fader, Hardie & Lee 2005) and Gamma-Gamma spend model, implemented from the published likelihoods.
import numpy as np
from scipy.special import gammaln, betaln, hyp2f1, logsumexp
from scipy.optimize import minimize
def bgnbd_ll(params, x, tx, T):
    r, alpha, a, b = np.exp(params)
    A = gammaln(r + x) - gammaln(r) + r * np.log(alpha)
    l1 = betaln(a, b + x) - betaln(a, b) - (r + x) * np.log(alpha + T)
    with np.errstate(divide="ignore", invalid="ignore"):
        l2 = np.where(x > 0, betaln(a + 1, b + x - 1) - betaln(a, b) - (r + x) * np.log(alpha + tx), -np.inf)
    return A + logsumexp(np.vstack([l1, l2]), axis=0)
def fit_bgnbd(x, tx, T, starts=((0.0, 0.0, 0.0, 0.0), (-1.0, 1.0, -1.0, 1.0), (0.5, 2.0, 0.5, 0.5))):
    f = lambda p: -bgnbd_ll(p, x, tx, T).sum()
    best = None
    for x0 in starts:   # multiple starts; keep the best log-likelihood
        res = minimize(f, np.array(x0), method="Nelder-Mead", options=dict(maxiter=20000, xatol=1e-8, fatol=1e-8))
        res = minimize(f, res.x, method="L-BFGS-B")
        if best is None or res.fun < best.fun: best = res
    return np.exp(best.x), -best.fun
def bgnbd_expected(params, t, x, tx, T):
    r, alpha, a, b = params
    num = (a + b + x - 1) / (a - 1) * (1 - ((alpha + T) / (alpha + T + t)) ** (r + x) * hyp2f1(r + x, b + x, a + b + x - 1, t / (alpha + T + t)))
    den = 1 + np.where(x > 0, a / (b + x - 1) * ((alpha + T) / (alpha + tx)) ** (r + x), 0.0)
    return num / den
def bgnbd_palive(params, x, tx, T):
    r, alpha, a, b = params
    return 1 / (1 + np.where(x > 0, a / (b + x - 1) * ((alpha + T) / (alpha + tx)) ** (r + x), 0.0))
def gg_ll(params, x, m):
    p, q, g = np.exp(params)
    return (gammaln(p * x + q) - gammaln(p * x) - gammaln(q) + q * np.log(g) + (p * x - 1) * np.log(m) + p * x * np.log(x) - (p * x + q) * np.log(g + x * m))
def fit_gg(x, m, return_ll=False):
    # Spend is rescaled by its median before optimization (an unscaled fit on GBP stopped at a false boundary p->inf, gamma->0);
    # gamma is a scale parameter in spend units, so it is multiplied back afterwards. Several starts; boundary check.
    c = float(np.median(m)); ms = m / c
    f = lambda pr: -gg_ll(pr, x, ms).sum()
    best = None
    for x0 in [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0), (0.5, 1.5, 0.0), (2.0, 0.5, 1.0)]:
        res = minimize(f, np.array(x0), method="Nelder-Mead", options=dict(maxiter=20000))
        res = minimize(f, res.x, method="L-BFGS-B")
        if best is None or res.fun < best.fun: best = res
    p, q, g = np.exp(best.x); g = g * c
    if p > 1e4 or q > 1e4 or q <= 1: raise RuntimeError(f"Gamma-Gamma fit at/near boundary: p={p}, q={q}, gamma={g}")
    ll = float(-best.fun)   # log-lik on the median-scaled spend (differs from the GBP-scale log-lik by a constant)
    return (np.array([p, q, g]), ll) if return_ll else np.array([p, q, g])
def gg_expected(params, x, m):
    p, q, g = params
    pop = p * g / (q - 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        cond = (p * (g + x * m)) / (p * x + q - 1)
    return np.where(x > 0, cond, pop)
def simulate_bgnbd(n, r, alpha, a, b, T_max, rng):
    # each customer: first purchase at 0, observed for T ~ U(T_max/4, T_max)
    lam = rng.gamma(r, 1 / alpha, n); p = rng.beta(a, b, n); T = rng.uniform(T_max / 4, T_max, n)
    x = np.zeros(n); tx = np.zeros(n)
    for i in range(n):
        t = 0.0
        while True:
            t += rng.exponential(1 / lam[i])
            if t > T[i]: break
            x[i] += 1; tx[i] = t
            if rng.random() < p[i]: break   # dropout after a purchase
    return x, tx, T
if __name__ == "__main__":
    import json, sys
    rng = np.random.default_rng(7)
    true = dict(r=0.243, alpha=4.414, a=0.793, b=2.426)   # CDNOW published estimates used only as plausible truth
    x, tx, T = simulate_bgnbd(20000, *true.values(), T_max=78, rng=rng)
    est, ll = fit_bgnbd(x, tx, T)
    # predictive check on simulated holdout: simulate continuation is complex; check parameter recovery only
    # GG recovery
    p, q, g = 6.25, 3.74, 15.44
    nn = 20000; xg = rng.integers(1, 15, nn).astype(float); nu = rng.gamma(q, 1 / g, nn)
    m = np.array([rng.gamma(p * k, 1 / v) / k for k, v in zip(xg, nu)])
    gest = fit_gg(xg, m)
    # GBP-scale check (spend in hundreds): the unscaled optimizer failed on this scale in the first version
    g2 = 15.44 * 30; nu2 = rng.gamma(q, 1 / g2, nn); m2 = np.array([rng.gamma(p * k, 1 / v) / k for k, v in zip(xg, nu2)])
    gest2 = fit_gg(xg, m2)
    out = dict(bgnbd_true=true, bgnbd_est=dict(zip(true.keys(), est.round(3).tolist())), gg_true=dict(p=p, q=q, g=g), gg_est=dict(zip(["p", "q", "g"], gest.round(3).tolist())),
               gg_true_gbp_scale=dict(p=p, q=q, g=g2), gg_est_gbp_scale=dict(zip(["p", "q", "g"], gest2.round(3).tolist())),
               gg_mean_true=p * g / (q - 1), gg_mean_est=float(gest[0] * gest[2] / (gest[1] - 1)), gg_mean_true_gbp=p * g2 / (q - 1), gg_mean_est_gbp=float(gest2[0] * gest2[2] / (gest2[1] - 1)))
    print(json.dumps(out, indent=1)); json.dump(out, open(sys.argv[1], "w"), indent=1)
