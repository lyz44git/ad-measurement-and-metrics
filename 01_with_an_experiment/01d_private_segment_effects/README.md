# 01d · Segment effects from privacy-protected counts

**[Explore this study interactively →](https://lyz44git.github.io/ad-measurement-and-metrics/01.html#s01d)**

> **Takeaway.** *Noisy count estimation.* When only noisy segment counts may be released, a multilevel model that
> knows the noise scale beat per-segment estimates on the same noisy counts in at least 9 of 10 samples at every
> epsilon. At epsilon = 1 its error is 1.06 points, against 1.08 for per-segment estimates and 0.95 for the same
> model on unprotected counts.
>
> *Reach allocation using the original segment estimates.* Ranking segments by estimated lift beat ranking by response
> rate when 10% or 20% of users can be reached, but not at 30%, so the pre-specified rule was not met.

## Questions

1. If the counts behind a segment-level lift readout are released with differential-privacy noise, how much accuracy
   is left, and does a model that accounts for the noise recover some of it?
2. Which ranking captures more incremental visits when only a fixed share of users can be reached: estimated lift or
   response rate?

## Data

The Criteo experiment used in [study 01a](../01a_ad_incrementality), with the 100 segments, the ten 2% samples and
the benchmark of [study 01b](../01b_bayesian_segment_effects): the benchmark for a sample is the segment effect on the
other 98% of users. The noise is simulated on counts derived from the public experiment, with segment membership held
fixed. Pass the path to the `criteo_compact.parquet` file written by study 01b's `code/01_build.py`.

## Method

The analysis plan, [`design/analysis_plan.md`](design/analysis_plan.md), was hashed before any outcome of this study was
computed; the overall effect and the noise-free segment errors of study 01b were already known. The SHA-256 in
`logs/plan_hash.txt` is that of the original file; the published copy differs in three places, where a local directory path and the names of two local project folders were replaced. The plan has four
parts: Parts A and C are reported here, Part B is [study 02a](../../02_without_an_experiment/02a_attribution_metric_validation)
and Part D is part 1 of [study 03a](../../03_planning_a_test/03a_lift_study_sizing). Deviations are in
[`design/deviations.md`](design/deviations.md).

**Part A, privacy.**

1. **Release.** For each sample, the visit count and the user count of every segment-by-arm cell get independent
   Laplace noise of scale 2 / epsilon. For fixed segment membership, adding or removing one record changes at most two
   counts by 1 each, so this single release is epsilon-differentially private at the record level. The guarantee does
   not cover how the segments were built. Epsilon is 0.1, 0.5, 1 or 5; three noise draws per sample and epsilon.
2. **Estimators,** both from the noisy counts only: the difference of noisy rates in each segment (no pooling), and a
   multilevel normal model whose sampling variance adds the variance of the noise (NumPyro, NUTS, 4 chains of 500
   warm-up and 500 draws).
3. **Decision rule.** The multilevel model helps under privacy noise if, at every epsilon and without noise, its
   RMSE against the benchmark is below no pooling in at least 8 of 10 samples.

**Part C, allocation.** No privacy noise: for each sample, segments are ranked by the multilevel estimate of study
01b, by the no-pooling estimate, by the control-arm visit rate (response) and, as an after-the-fact reference, by the
benchmark itself. The top segments covering 10%, 20% or 30% of users are reached; the value is the share of all
benchmark incremental visits they hold. Decision rule: ranking by lift beats ranking by response if the multilevel
ranking captures more in at least 8 of 10 samples at every reach level.

## Results

Sources: [`out/a_private_summary.json`](out/a_private_summary.json), [`out/c_allocation.json`](out/c_allocation.json).

**Part A.** RMSE of 100 segment effects against the benchmark, in percentage points, mean of 10 samples:

| Epsilon | No pooling | Noise-aware multilevel | Multilevel better in |
|---|---|---|---|
| 0.1 | 6.95 | 2.03 | 10 of 10 |
| 0.5 | 1.77 | 1.35 | 10 of 10 |
| 1 | 1.27 | 1.06 | 10 of 10 |
| 5 | 1.09 | 0.96 | 9 of 10 |
| no noise | 1.08 | 0.95 | 9 of 10 |

**Part C.** Share of benchmark incremental visits captured, mean of 10 samples:

| Reach (share of users) | Multilevel lift ranking | No-pooling lift ranking | Response-rate ranking | Best ranking on the benchmark | Random | Multilevel above response in |
|---|---|---|---|---|---|---|
| 10% | 56.6% | 56.0% | 33.5% | 60.2% | 10% | 10 of 10 |
| 20% | 79.1% | 76.9% | 67.1% | 84.3% | 20% | 10 of 10 |
| 30% | 87.6% | 83.5% | 86.5% | 90.6% | 30% | 4 of 10 |

[![Error of segment estimates by privacy budget for separate and pooled estimates; and the share of extra visits captured when users are chosen by pooled estimates, by separate estimates, by how often they visit anyway, or at random, using rankings without privacy noise](out/fig_privacy_and_allocation.png)](https://lyz44git.github.io/ad-measurement-and-metrics/01.html#s01d)

Panel a: log scale; "no noise" is epsilon = ∞. Panel b uses the noise-free estimates.

- **The pre-specified rule of Part A was met.** The gain from the model grows as the privacy budget shrinks: at
  epsilon = 0.1 no pooling is off by 6.95 points and the multilevel model by 2.03.
- At epsilon = 1 the noise adds 0.11 points to the error of the multilevel model (1.06 against 0.95 without noise).
- **The pre-specified rule of Part C was not met.** At 30% reach, lift ranking won in 4 of 10 samples although its
  mean share was higher (87.6% against 86.5%); the rule required 8 at every reach level. It won in 10 of 10 at 10%
  and 20%.
- 10 of 130 fits had a largest R-hat between 1.01 and 1.019; as the plan says they are listed and were not
  rerun. The published code was reorganized into functions; a rerun reproduces every number of the original run
  ([`logs/rerun_check.txt`](logs/rerun_check.txt)).

## Reproduce

```bash
pip install -r ../../02_without_an_experiment/02c_marketing_mix_modeling/requirements-mmm.txt   # NumPyro and JAX
python code/a_private_aggregates.py ../01b_bayesian_segment_effects/derived/criteo_compact.parquet out   # about 3 minutes
python code/c_allocation.py ../01b_bayesian_segment_effects/derived/criteo_compact.parquet out   # uses the noise-free segment fits of 01b
```

`tests/` checks the noise scale of the release, the variance formula against the simulated spread of the estimate,
that a smaller privacy budget gives a larger error, and the allocation share; it needs only the root
`requirements.txt`.

## Scope

- One release per sample. Repeated releases of the same data would spend more privacy budget; composition is not
  studied here.
- The Laplace mechanism on counts is a textbook mechanism, not a production privacy system.
- The normal model used here is less accurate without noise (0.95) than the binomial model of study 01b (0.79);
  it is used because its variance can absorb the noise.
- Part C limits the share of users reached; no price or auction data enter it, so it is not bidding. Bidding on
  logged prices is in [study 02d](../../02_without_an_experiment/02d_attribution_and_bidding).
