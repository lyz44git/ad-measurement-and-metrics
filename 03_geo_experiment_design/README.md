# 03. How big must a market-level test be?

**Question.** Suppose a change can only be randomized by market (metro), for example because prices or processes are
set per market. How many metros and months does a test need, which design detects the smallest effect, and does the
usual t-test keep its 5% false-positive rate?

**Data.** Zillow Research public data: newly pending listings, metro, monthly, 2018-01 to 2026-09. Data Provided by
Zillow Group. Download `Metro_new_pending_uc_sfrcondo_month.csv` from zillow.com/research/data. After dropping
incomplete series, small metros and seven metros with coverage breaks (`out/coverage_breaks.csv`), 151 metros remain.

**What I did.** Placebo experiments on historical data. Each draw picks a start month and N metros and assigns half to
treatment, with no true effect, so the rejection rate is the false-positive rate. Adding a known lift to treated
metros gives power; the minimum detectable effect is the smallest lift with 80% power. 5,000 draws per cell for
1-, 2- and 3-month tests with 20 to 150 metros. Designs compared: difference in means, year-over-year difference,
regression adjustment on the same months a year earlier and the last three months (the idea behind CUPED),
a volume-weighted version, and matched pairs. No real experiment was run.

**What I found** (2-month tests; `out/design_summary.csv`, `out/randomization_inference_check.csv`).
- **Adjust for the past instead of comparing growth rates.** At 100 metros, regression adjustment detects a 6.7%
  change against 9.5% for a year-over-year comparison. Comparing raw levels is useless because metros differ in size.
- **Market tests detect only large effects.** 150 metros detect 5.3%; 20 metros detect 16.3%.
- **Matched pairs add nothing once you adjust:** 6.8% at 100 metros against 6.7% without pairs.
- **Longer tests help little:** 1, 2 and 3 months give 7.2%, 6.7% and 6.4% at 100 metros.
- **The total-volume estimate needs a different test.** Weighting metros by volume makes the t-test reject a true null
  5.7% to 9.1% of the time, worst with few metros, because a few large metros dominate. Randomization inference brings
  it back to about 5% (4.2% to 5.8%), at a cost: 8.8% detectable at 100 metros.

![Minimum detectable effect by number of metros](out/fig1_mde_by_metros.png)

**Run.**
```bash
python code/geo_experiment_power.py /path/to/Metro_new_pending_uc_sfrcondo_month.csv   # about 20 seconds
```

**Does not show.** A real experiment, interference between markets, or effects on outcomes other than listing volume.
