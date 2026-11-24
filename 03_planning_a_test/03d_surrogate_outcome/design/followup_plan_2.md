# Follow-up plan 2: do visits point to the right segments?

Written after the main run and the first follow-up were seen (`out/surrogate.json`, `out/followup.json`) and
before anything below was computed.

## Question

The main run found that the effect on visits cannot stand in for the **size** of the effect on conversions: a
visit-based estimate is 42% of the direct one. A team often needs less than the size. It needs to know **where** the
effect is larger, for instance which segments to target, and a small test has too few conversions to tell. Across
segments, does the effect on visits rise and fall with the effect on conversions, and in a small test does choosing
segments by their visit effect pick segments with a larger conversion effect than choosing them by their conversion
effect?

Known before this plan: study 01b found that in 2% samples a multilevel model of the **visit** effect picks 20
segments whose benchmark visit lift is 3.78 points against a best possible 4.03. No conversion effect by segment
has been computed in this repository.

## Data and segments

The split of the main run (seed 20261124): the historical half and the experiment half. **Segments:** the 100
segments of study 01b, equal-size groups by rank on f0, f2, f8, f10, f7 and f3 with the file order breaking ties,
computed on all 13,979,592 rows.

## 1. Direction (experiment half)

For each segment g: the visit effect Δv_g and the conversion effect Δc_g (difference between arms). Across the 100
segments, their correlation corrected for sampling noise: the covariance across segments minus the mean sampling
covariance within segments, over the square root of the product of the variances, each corrected the same way.
Within an arm a conversion implies a visit, so the sampling covariance of the two differences is
Σ_arm p_c (1 − p_v) / n. 90% interval from 1,000 parametric draws of each segment's and arm's counts (no visit;
visit without conversion; conversion), with the correction recomputed in each draw.

## 2. Choosing segments in a small test

From the historical half, 20 disjoint samples of 279,592 users (2% of the experiment, the sample size of study
01b). In each sample, the 20 segments with the largest visit effect and, separately, the 20 with the largest
conversion effect are chosen. Each choice is scored by the mean conversion effect of its 20 segments on the
**experiment half**, which shares no user with the sample. Also reported: random choice (the overall conversion
effect), the 20 segments that are best on the experiment half (an upper reference, biased upward because the same
data choose and score), and the same comparison for samples of 1%, 5%, 10% and 20% of the experiment (20 draws each,
independent across draws).

## Decision rules

1. **Visits point the same way:** the noise-corrected correlation is at least 0.7 and the lower end of its 90%
   interval at least 0.5.
2. **Visits choose better in a small test:** over the 20 samples of 2%, segments chosen by visit effect have a higher
   mean conversion effect on the experiment half than segments chosen by conversion effect, and they are higher in
   at least 15 of the 20 samples.

## What this cannot show

The segments are defined by six anonymized features; a correlation across these segments need not hold across other
groupings. The equivalence rule of the main run is unchanged: visits still understate the size of the effect.
