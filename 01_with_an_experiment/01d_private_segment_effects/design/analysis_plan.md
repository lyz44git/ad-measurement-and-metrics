# Pre-specified analysis plan: four advertising-measurement tests on Criteo Uplift v2.1

Written 2026-11-15 before any outcome of Parts A-D was computed. SHA-256 recorded in `logs/plan_hash.txt` before the
run. Deviations go in `design/deviations.md`.

Data: public Criteo Uplift v2.1 (13,979,592 users; treatment, exposure, visit, conversion, f0-f11), from an
advertising experiment Criteo randomized and completed. Read only from
a local `data_raw/` folder. Segments and replicates are reused unchanged from
the segment study (01b) (100 rank-based segments; ten disjoint 2% replicates; benchmark = segment
ITT on visit among all users outside the replicate).

Already known before this plan (from earlier projects): overall ITT on visit +1.034 pp; exposure share among treated
3.60%; CACE 28.7 pp unadjusted and 21.5 pp adjusted; non-private segment RMSE 1.085 pp (no pooling) and 0.788 pp
(multilevel binomial). Not yet computed: anything with noise added, the exposed-vs-unexposed comparisons, the
allocation shares, and the survey-scale resampling.

The dataset is subsampled non-uniformly, so absolute lifts are not population effects; the tests compare methods.
None of these tests uses auction, cost, survey or cross-channel data, and none will be described as if it did.

## Part A. Differentially private aggregates: how much accuracy survives?
- Release per replicate: for each segment x arm cell the counts (n, y). One user changes n by 1 and y by at most 1 in
  one cell, so L1 sensitivity is 2. Mechanism: independent Laplace noise with scale 2/epsilon on every count
  (epsilon-differential privacy for the release). epsilon in {0.1, 0.5, 1, 5} plus no noise ("inf").
- Three independent noise draws per replicate and epsilon (seed 20261115 + 1000*replicate + 10*epsilon index + draw).
- Estimators computed from the noisy counts only (noisy n clipped below at 1):
  1. No pooling: difference of noisy rates.
  2. Noise-aware multilevel normal model: d[s] ~ N(theta[s], v[s]), theta[s] = mu + tau * z[s], z ~ N(0,1),
     mu ~ N(0, 0.05), tau ~ HalfNormal(0.05), where v[s] sums, over the two arms, p(1-p)/n + 2*(2/epsilon)^2/n^2
     with p the arm's pooled noisy rate and n the cell's noisy count. NUTS (NumPyro), 4 chains, 500 warm-up, 500 draws.
     Estimate = posterior mean of theta.
- Metric: RMSE of the 100 segment effects against the non-private benchmark, averaged over the three draws.
- Decision rule: the multilevel model "helps under privacy noise" if, at every epsilon (including inf), its RMSE is
  below no pooling in at least 8 of 10 replicates.
- Secondary: mean RMSE by epsilon for both estimators; the smallest epsilon at which the private multilevel RMSE is
  no higher than the non-private no-pooling RMSE; max R-hat (target < 1.01; fits above it are listed, not rerun).

## Part B. Attribution vs incrementality
Full data, treated arm unless stated. "Exposure-attributed" means crediting an outcome to the ad whenever the user was
exposed (the logic of last-touch attribution with one channel).
- Attributed visits and conversions: outcomes among exposed treated users.
- Incremental visits and conversions: ITT x number of treated users.
- Report the share of attributed outcomes that is incremental, and the attributed-to-incremental ratio.
- Per-exposed-user effect on visit, three ways:
  1. Naive: exposed minus unexposed visit rate among treated users.
  2. Covariate-adjusted observational: OLS of visit on exposure and f0-f11 among treated users (HC1 SE).
  3. Cross-fitted partially linear (double machine learning) estimate with gradient-boosted nuisance models
     (scikit-learn HistGradientBoosting, 2 folds) on a random 2,000,000 treated users (seed 20261115).
  Benchmark: the experimental CACE (ITT / exposure share; valid if assignment moves visits only through exposure).
- Report each estimate's ratio to the unadjusted CACE. No decision rule; this part is descriptive.

## Part C. Spend allocation across segments from a small experiment
- For each replicate, rank the 100 segments by: (1) multilevel estimate (stored fits from the segment study), (2) no-pooling
  estimate, (3) control-arm visit rate in the replicate ("response" ranking), (4) the benchmark itself (oracle).
- Budget B in {10%, 20%, 30%} of users = top B segments. Value = share of total benchmark incremental visits
  (sum of benchmark segment effects, equal-size segments) captured by the chosen segments. Random allocation = B.
- Report mean share over 10 replicates per rule and budget, and in how many replicates the multilevel ranking
  captures at least as much as no pooling and as the response ranking.
- Decision rule: "incrementality-ranked allocation beats response-ranked allocation" if the multilevel ranking
  captures more than the response ranking in at least 8 of 10 replicates at every budget.

## Part D. Survey-scale lift studies (the sample sizes of brand-lift surveys)
This is a design exercise with site visit as the binary response. It uses no survey or brand data.
- For n per arm in {1,000, 2,500, 5,000, 10,000, 20,000}: draw 2,000 studies, each n treated and n control users
  sampled without replacement from the full data (seed 20261115).
- Frequentist: two-sided z-test at 5%; power = rejection share; coverage of the 95% CI for the full-data lift.
- Bayesian: Beta(1,1) priors; "detect" if P(lift > 0) > 0.95 (5,000 posterior draws per study).
- A/A check: 2,000 studies per n with both arms drawn from control users; false-positive rate of each rule.
- Report power, coverage and A/A rates by n, and the smallest n in the grid with at least 80% power.
