# 06 · Bayesian marketing mix models for 31 e-commerce brands

> **Takeaway.** On weekly data, a two-channel marketing mix model could not recover known channel returns (rank
> correlation 0.01 in a simulation with real spend); on daily data it could, in rank (0.75), with wide intervals. Adding
> media terms did not reliably improve holdout forecasts over trend and seasonality alone. Channel ROAS from these
> models should be calibrated with experiments (studies 01 and 03) before it guides a budget.

## Question

Can a marketing mix model fitted to a brand's own spend and revenue recover how much each channel returns, and does it
forecast revenue better than a model without media?

## Data

Conjura, "Multi-Region Marketing Mix Modelling (MMM) Dataset for Several eCommerce Brands" (Figshare 25314841,
CC BY 4.0): daily spend by channel and purchases for 93 anonymised e-commerce brands. Download `conjura_mmm_data.csv`
into `data_raw/` (git-ignored).

Revenue is purchases at original price minus discounts. Google spend is the sum of the five Google columns and Meta
spend the sum of the three Meta columns; TikTok (3% of rows) is left out. The data have no price, promotion calendar,
offline media or competitor information.

## Method

The analysis plan, [`design/analysis_plan.md`](design/analysis_plan.md) (Part A; Part B is study 05), was fixed before
the run; its SHA-256 is in `logs/plan_hash.txt`. The daily run is a deviation from the weekly plan, made after the
weekly results were seen ([`design/deviations.md`](design/deviations.md)).

1. **Brands.** One series per brand across all territories. A brand is eligible with two years of consecutive data
   (104 weeks, or 728 days for the daily run) and Google and Meta spend above 0 in at least 80% of periods.
2. **Model.** Per brand, Bayesian (NumPyro, NUTS, 2 chains of 500 warm-up and 500 draws): trend, two annual Fourier
   harmonics (plus day of week in the daily run) and, for each channel, a coefficient on a Hill saturation curve of
   geometrically adstocked spend.
3. **Holdout.** The last 13 weeks (91 days for the daily run), scored by weighted absolute percentage error (wMAPE)
   against the same model without media and a seasonal-naive forecast. Decision rule: the media model is preferred if
   it has the lower wMAPE in more than half of the brands and the 95% bootstrap interval of the mean difference is
   below 0.
4. **Parameter recovery.** For 20 brands, real spend with simulated revenue: known channel returns drawn from
   Uniform(0.5, 4), the model refitted, and estimated returns compared with the truth.

## Results

Sources: [`out/mmm_summary.json`](out/mmm_summary.json) (weekly), [`out/mmm_summary_daily.json`](out/mmm_summary_daily.json)
(daily); per-brand tables in `out/mmm_brands*.csv` and recovery draws in `out/mmm_recovery*.csv`.

| | Weekly (plan) | Daily (deviation 1) |
|---|---|---|
| Eligible brands / converged (R-hat < 1.05) | 34 / 30 | 31 / 27 |
| Holdout wMAPE, median: media model / no media / seasonal naive | 0.19 / 0.22 / 0.32 | 0.35 / 0.38 / 0.42 |
| Media model better than no-media model | 19 of 30 | 16 of 27 |
| Mean wMAPE difference, media minus no media (95% CI over brands) | +0.012 (−0.064 to 0.102) | −0.008 (−0.118 to 0.123) |
| Recovery: rank correlation of true and estimated ROAS (converged refits) | 0.01 (18 of 20) | 0.75 (17 of 20) |
| Recovery: coverage of 90% intervals / median absolute relative error | 89% / 35% | 94% / 28% |
| Model ROAS, median across brands: Google / Meta | 4.4 / 3.5 | 3.1 / 2.7 |
| Revenue / total spend, median across converged brands | 5.9 | 6.4 |
| Media share of revenue, median across brands | 61% | 43% |

- **The pre-specified forecasting rule was not met** in either run: the interval of the mean wMAPE difference
  includes 0.
- Weekly brand-level ROAS is not identified (recovery 0.01). Daily data make it recoverable in rank (0.75), with wide
  intervals. Model ROAS is well below revenue per unit of spend, as expected when part of revenue would occur without
  media.
- Moving 10% of spend toward the channel with the higher marginal return has a model-implied median gain of about 1%
  of revenue; its 90% interval is above 0 in 16 of 27 brands in the daily run. This is not validated.

## Reproduce

```bash
pip install -r requirements-mmm.txt
python code/run_mmm.py data_raw/conjura_mmm_data.csv out W 14   # weekly (plan), about 2 minutes on 14 processes
python code/run_mmm.py data_raw/conjura_mmm_data.csv out D 14   # daily, about 2 minutes
```

With the versions in `requirements-mmm.txt`, repeated runs gave identical draws. MCMC draws change with small
floating-point differences, so other versions or machines can give somewhat different numbers (deviation 2).

`tests/` checks the adstock and saturation transforms, the brand eligibility rule and the recovery simulation on
synthetic data; it needs only the root `requirements.txt`.

## Scope

- Observational: spend responds to expected demand, so model ROAS is not a causal estimate, and no experiment
  calibrates it here.
- Two channels; no price, promotion, offline media or competitor data.
- Spend is in each brand's own currency, so totals are not compared across brands.
