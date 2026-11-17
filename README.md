# Ad measurement and metrics

[![tests](https://github.com/lyz44git/ad-measurement-and-metrics/actions/workflows/tests.yml/badge.svg)](https://github.com/lyz44git/ad-measurement-and-metrics/actions/workflows/tests.yml)

When can an advertising metric support a decision about what the ads did? The studies below take four questions in
turn, on public advertising and e-commerce data: what a randomized experiment says the ads caused (section 1), when
the metrics used without an experiment can be trusted (section 2), how large the next test must be (section 3), and
whether the customer counts that results are reported in are defined correctly (section 4). Studies 01a, 01b, 02a and
03a all use the same randomized experiment; the other studies each use their own public dataset.

<img src="figures/figure1.png" alt="Five panels in reading order: ad arm against control for visit and conversion rates; conversions credited by attribution against conversions caused; median recovery error of a marketing mix model by signal-to-noise index; users per arm needed for a one-point lift with and without adjustment; accounts labeled new under a 3-month look-back, split by purchase in the prior year." width="100%">

**Figure 1 | The argument of the repository, one panel per step, in reading order.** **a**, Visit and conversion rates in the ad arm relative to control (control = 100) for all 14.0M randomized users, with 95% intervals (study 01a). The effect is of assignment to the ad arm: 3.6% of the ad arm saw an ad, and the released data are a non-uniform subsample of several tests. **b**, Conversions in the ad arm credited by exposure-based attribution, against conversions caused by the ads according to the unadjusted experimental estimate (study 02a); for visits the gap is 44%. **c**, Median absolute relative error of a per-brand marketing mix model's channel return in a held-out daily simulation on real spend, for brand-channels with a signal-to-noise index of 2 or more and below 2 (study 02c, test T1); the index is computed before fitting. **d**, Users per arm needed to detect a one-point lift in visit rate at 80% power, unadjusted, adjusted for 12 user features, and adjusted for a model prediction built from them (study 03a). **e**, Accounts a 3-month look-back would label as new customers, split by whether they had bought in the prior 12 months (study 04). Drawn by [`figures/make_figure1.py`](figures/make_figure1.py) from the result files in each study folder.

### 1. With an experiment: what did the ads cause, and for whom?

| Study | Question | Key result |
|---|---|---|
| [`01a_ad_incrementality`](01_with_an_experiment/01a_ad_incrementality) | How many site visits did the ads cause, as opposed to visits that would have happened anyway? | In Criteo's 14.0M-user randomized experiment, assignment to the ad arm raised the visit rate from 3.82% to 4.85% (+1.03 points; +0.77 after regression adjustment) and the conversion rate from 0.19% to 0.31%. A pre-specified uplift model did not rank users for targeting better than a plain response model. |
| [`01b_bayesian_segment_effects`](01_with_an_experiment/01b_bayesian_segment_effects) | Can segment-level ad effects be read from a 2% sample? | A Bayesian multilevel model cut the error of 100 segment estimates by 27% against separate per-segment estimates (0.79 against 1.08 points), in 10 of 10 samples. |

### 2. Without an experiment: when can the usual metrics be trusted?

Studies 02a and 02c check a metric used in place of an experiment against a benchmark: the experiment of study 01a, or
a simulation with known returns. Study 02b shows how much the credit given to each touch depends on the rule chosen;
it has no benchmark.

| Study | Question | Key result |
|---|---|---|
| [`02a_attribution_metric_validation`](02_without_an_experiment/02a_attribution_metric_validation) | Can an exposure-based attribution metric be trusted as a measure of ad impact? | It credited 23,031 conversions where the experiment puts those caused by the ads at 13,687 (68% more; 44% more for visits). Without an experiment, covariate adjustment moved the per-exposed-user effect from a naive 38.0 points to 24.6-25.5, between the two experimental estimates (21.5 regression-adjusted, 28.7 unadjusted). |
| [`02b_multi_touch_attribution`](02_without_an_experiment/02b_multi_touch_attribution) | When a user sees several ads before converting, how much does the credit rule change which touch gets credit? | On 6.1M display-ad user paths, 65% of converting paths had several touches and last touch gave no credit to 82% of the touches in them; a time-decay rule fitted to observed delays (half-life 7.9 days) left 39% of the credit on the last touch. |
| [`02c_marketing_mix_modeling`](02_without_an_experiment/02c_marketing_mix_modeling) | Can a marketing mix model recover each channel's return from a brand's own spend and revenue, and can one tell in advance when it will? | In simulations on the real spend of 31 to 34 e-commerce brands, recovery depended on a signal-to-noise index computed before fitting: in a pre-specified held-out test, the median error of a channel's estimated return was 19% for brand-channels with an index of 2 or more (rank correlation 0.80 with the truth) and 50% for the rest. Only 19% of brand-channels reach that level on weekly data, against 55% on daily data. Pooling the brands in one model did not help, and media terms did not reliably improve holdout forecasts. |

### 3. Planning a test: how large must it be?

Section 2 finds that attribution counts overstate what the ads caused and that a marketing mix model can measure only
some channels. Where a budget decision needs incremental evidence that these metrics cannot give, the next step is an
experiment. These two studies size it: by user (03a) and, where a change can only be randomized by market, by market
(03b). In both, adjusting for what is known
before the test is the main way to make it smaller.

| Study | Question | Key result |
|---|---|---|
| [`03a_lift_study_sizing`](03_planning_a_test/03a_lift_study_sizing) | How many users per arm does a lift study need, and how much does covariate adjustment save? | For a one-point lift in site visits on a 3.8% base rate, an unadjusted readout needs about 6,500 users per arm for 80% power. Adjusting for 12 pre-treatment user features cuts this to about 4,700, and adjusting for a model prediction built from them to about 4,400, with false-positive rates near 5%. |
| [`03b_geo_experiment_design`](03_planning_a_test/03b_geo_experiment_design) | If a change can only be randomized by market, how large a test is needed, and does the usual t-test keep its 5% false-positive rate? | Across 5,000 placebo tests per design on 151 U.S. metros, adjusting for pre-period volume lowered the smallest detectable change in a two-month, 100-metro test from 9.5% to 6.7%. For the volume-weighted estimate the t-test rejected a true null 5.7-9.1% of the time; randomization inference kept it between 4.2% and 5.8%. |

### 4. Customer metrics: are they defined correctly?

An experiment's result is only as good as the metric it is read on. Ad results are often reported as customers
acquired and retained; this study checks how those counts are defined, on a retailer's transactions (no ads in the
data).

| Study | Question | Key result |
|---|---|---|
| [`04_customer_metrics_retention`](04_customer_metrics_retention) | Does the "new customer" metric count returning buyers as new, and which high-value customers are least likely to return? | A 3-month look-back would have labeled 1,036 accounts new, 640 (62%) of which had bought in the prior 12 months. Among high-value accounts, a purchase-model score ranked six-month repeat buyers with AUC 0.79 against 0.75 for recency alone; for 12-month sales a simple past-sales rule ranked better. |

Where a conclusion depends on a decision rule, the analysis plan was fixed before the run and its SHA-256 is recorded
in the study's `logs/` folder. Follow-up analyses added after a first result have their own plan and are labeled as
follow-ups. Results that did not support the more complex method are reported alongside the rest.

## Data sources and terms

Data are not included in this repository. The randomized experiment used in studies 01a, 01b, 02a and 03a was designed,
run and released by Criteo. Study 02b uses Criteo's attribution dataset, study 03b a public Zillow Research
file, study 04 the UCI Online Retail II data, and study 02c a public marketing mix dataset released by Conjura.

| Data | Used in | Terms |
|---|---|---|
| Criteo Uplift Prediction Dataset v2.1 (Diemert, Betlei, Renaudin and Amini 2018, AdKDD) | 01a, 01b, 02a, 03a | Research, non-commercial use. The data pool several tests with non-uniform subsampling, so absolute lifts are not population effects. |
| Zillow Research, metro newly pending listings | 03b | Data Provided by Zillow Group. Only derived simulation results are stored here. |
| UCI Machine Learning Repository, Online Retail II (id 502) | 04 | CC BY 4.0. |
| Criteo Attribution Modeling for Bidding Dataset (Diemert, Meynet, Galland and Lefortier 2017, AdKDD) | 02b | CC BY-NC-SA 4.0. The derived results in `02_without_an_experiment/02b_multi_touch_attribution/out/` are shared under the same license. |
| Conjura, Multi-Region Marketing Mix Modelling (MMM) Dataset for Several eCommerce Brands (Figshare 25314841) | 02c | CC BY 4.0. |

**Use.** This is a non-commercial research project. The data and all derived outputs in this repository are used
for research only.

## Repository layout

One folder per question, with the studies inside it:

```
01_with_an_experiment/
├── 01a_ad_incrementality/
└── 01b_bayesian_segment_effects/
02_without_an_experiment/
├── 02a_attribution_metric_validation/
├── 02b_multi_touch_attribution/
└── 02c_marketing_mix_modeling/
03_planning_a_test/
├── 03a_lift_study_sizing/
└── 03b_geo_experiment_design/
04_customer_metrics_retention/     one study
figures/                           Figure 1 and the scripts that draw the figures
```

Study folders share this structure (not every study needs every folder):

```
study_name/
├── README.md     question, method, findings, limitations, how to run
├── code/         scripts, numbered in run order
├── docs/ or design/   analysis plan written before the run, and any deviations from it
├── out/          result tables (JSON / CSV) and figures
├── logs/         run logs and the SHA-256 of the plan, recorded before the run
└── tests/        checks on simulated data (in `code/tests/` for study 01a)
```

Data go in a git-ignored `data_raw/` folder inside each study; see each README for the download link.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Tested with Python 3.13 on macOS. Studies 01a and 02a load the full Criteo file and need about 16 GB of memory.
Studies 01b and 02c also need NumPyro and JAX: `pip install -r 02_without_an_experiment/02c_marketing_mix_modeling/requirements-mmm.txt`.

## Tests

```bash
pytest -q
```

The tests run on simulated data, so they need none of the datasets. They check that the estimators recover a known
effect and do not detect one that is absent, that false-positive rates stay near 5% under a true null, that adjusting
for a predictive covariate lowers the variance of a readout by the expected amount, that the purchase and spend models
recover known parameters, that the published SQL agrees with an independent pandas implementation, that each
attribution rule gives a conversion exactly one unit of credit, and that the adstock and saturation transforms behave
as specified. They run on every push (see the badge above).

## License

Code is released under the MIT License (see `LICENSE`). The datasets keep their own terms, listed above; the derived
results of study 02b follow CC BY-NC-SA 4.0.

## Notes

Developed with an AI-assisted coding workflow. The research questions, analysis plans and interpretation of results
were led by the author. All results are reproducible from the scripts and public data referenced in each study.
