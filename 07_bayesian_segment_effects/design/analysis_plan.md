# Pre-specified analysis plan: Bayesian analysis of the Criteo Uplift v2.1 experiment

Written 2026-11-15, before any outcome in this project was computed. The SHA-256 of this file is recorded in
`logs/plan_hash.txt` before the run. Deviations go in `design/deviations.md`.

Data: public Criteo Uplift v2.1 (Diemert et al. 2018), 13,979,592 users, a randomized advertising experiment that
Criteo ran and released. Read from a local `data_raw/` folder (read only).
The dataset pools tests with non-uniform subsampling, so absolute lift is not a population effect; the analysis
compares methods.

Covariates were inspected before this plan (cardinality and quantiles of f0-f11 only; no outcome was looked at).
Most features have one dominant value, so segments are defined by rank, not by value bins.

## Part 1. Overall effect, Bayesian vs frequentist (full data)
- Outcomes: visit, conversion. Arms: treatment (85%) vs control.
- Model: independent Beta(1, 1) priors on each arm's rate; conjugate Beta posteriors; 200,000 Monte Carlo draws.
- Report: posterior mean and 95% equal-tailed credible interval of the absolute lift (p1 - p0) and relative lift
  (p1 / p0 - 1); P(lift > 0). Compare with the frequentist difference in means and its 95% CI.

## Part 2. Segment effects from a small sample: does partial pooling help?
- Segments: 100 equal-size segments, `ntile(100)` over users ordered by (f0, f2, f8, f10, f7, f3, row number).
- Replicates: each user gets u ~ Uniform(0, 1) from seed 20261115; replicate r (r = 0..9) is the users with
  floor(50 u) = r, i.e. ten disjoint 2% samples.
- Benchmark for replicate r: segment ITT on visit (difference in means) computed on all users outside replicate r.
- Estimators on replicate r, outcome visit:
  1. No pooling: per-segment difference in means.
  2. Complete pooling: the replicate's overall difference in means, assigned to every segment.
  3. Bayesian multilevel binomial model:
     y[s,a] ~ Binomial(n[s,a], logistic(alpha[s] + beta[s] * a)), a = 1 for treatment;
     alpha[s] = mu_a + sigma_a * z_a[s], beta[s] = mu_b + sigma_b * z_b[s], z ~ N(0, 1) (non-centered);
     mu_a ~ N(-3, 1.5), mu_b ~ N(0, 1), sigma_a ~ HalfNormal(1), sigma_b ~ HalfNormal(0.5).
     NUTS (NumPyro), 4 chains, 1,000 warm-up, 1,000 draws each, target_accept 0.9.
     Segment effect = posterior mean of logistic(alpha + beta) - logistic(alpha); 90% credible interval.
- Primary metric: root-mean-square error of the 100 segment effects against the benchmark, per replicate.
- Decision rule: the multilevel model "helps" if its RMSE is below no pooling in at least 8 of 10 replicates and
  the mean paired RMSE difference across replicates has a 95% t-interval below zero.
- Secondary:
  - MAE; RMSE vs complete pooling.
  - Targeting: each method picks the 20 segments with the highest estimated effect; report the mean benchmark
    effect of the picked segments (complete pooling has no ranking and is excluded).
  - Coverage of the benchmark by the 90% interval (no pooling: normal interval from the binomial SE). The
    benchmark has its own sampling error, so coverage is approximate.
- Convergence: max R-hat < 1.01 and min bulk ESS > 400 over mu, sigma and the segment effects. If a replicate fails,
  rerun it with 3,000 / 3,000 draws and log the deviation.

## Part 3. Automated report
A script reads only the output JSON files and regenerates a self-contained HTML dashboard: KPI tiles for Part 1,
a per-replicate table and a segment chart (benchmark vs each method, selectable by replicate). No numbers are typed
into the report by hand.
