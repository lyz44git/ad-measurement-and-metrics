# Ad measurement and metrics

Analyses of public advertising and e-commerce data: an experiment readout, validation of an attribution metric,
power analysis for market-level tests, and customer retention metrics.

| Study | Question | Key result |
|---|---|---|
| [`01_ad_incrementality`](01_ad_incrementality) | How many site visits did the ads cause, as opposed to visits that would have happened anyway? | In Criteo's 14.0M-user randomized experiment, ads raised the visit rate from 3.82% to 4.85% (+1.03 points; +0.77 after regression adjustment) and the conversion rate from 0.19% to 0.31%. |
| [`02_attribution_metric_validation`](02_attribution_metric_validation) | Can an exposure-based attribution metric be trusted as a measure of ad impact? | It credited 44% more visits and 68% more conversions than the experiment says were incremental. Covariate adjustment moved the per-exposed-user effect from a naive 38.0 points to 24.6-25.5, inside the experimental range of 21.5-28.7. |
| [`03_geo_experiment_design`](03_geo_experiment_design) | If a change can only be randomized by market, how large a test is needed, and does the usual t-test keep its 5% false-positive rate? | Across 5,000 placebo tests per design on 151 U.S. metros, adjusting for pre-period volume lowered the smallest detectable change in a two-month, 100-metro test from 9.5% to 6.7%. For the volume-weighted estimate the t-test rejected a true null 5.7-9.1% of the time; randomization inference brought it back to about 5%. |
| [`04_customer_metrics_retention`](04_customer_metrics_retention) | Is the "new customer" metric counting returning buyers, and which high-value customers are least likely to return? | A 3-month look-back would have labelled 1,036 accounts new, 62% of which had bought in the prior year. A purchase-model score ranked repeat buyers with AUC 0.79 against 0.75 for recency alone. |

Where a conclusion depends on a decision rule, the analysis plan was fixed before the run and its SHA-256 is recorded
in the study's `logs/` folder. Results that did not support the more complex method are reported alongside the rest.

## Data sources and terms

Data are not included in this repository. The experiment analysed in studies 01 and 02 was designed, run and released
by Criteo; studies 03 and 04 use public Zillow and UCI data.

| Data | Used in | Terms |
|---|---|---|
| Criteo Uplift Prediction Dataset v2.1 (Diemert, Betlei, Renaudin and Amini 2018, AdKDD) | 01, 02 | Research, non-commercial use. The data pool several tests with non-uniform subsampling, so absolute lifts are not population effects. |
| Zillow Research, metro newly pending listings | 03 | Data Provided by Zillow Group. Only derived simulation results are stored here. |
| UCI Machine Learning Repository, Online Retail II (id 502) | 04 | CC BY 4.0. |

## Repository layout

Study folders share this structure (not every study needs every folder):

```
NN_study_name/
├── README.md     question, method, findings, limitations, how to run
├── code/         scripts, numbered in run order
├── docs/ or design/   analysis plan written before the run, and any deviations from it
├── out/          result tables (JSON / CSV) and figures
└── logs/         run logs and the SHA-256 of the plan, recorded before the run
```

Data go in a git-ignored `data_raw/` folder inside each study; see each README for the download link.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Tested with Python 3.13 on macOS. Studies 01 and 02 load the full Criteo file and need about 16 GB of memory.

## Licence

Code is released under the MIT licence (see `LICENSE`). The datasets keep their own terms, listed above.

## Notes

Developed with an AI-assisted coding workflow. The research questions, analysis plans and interpretation of results
were led by the author. All results are reproducible from the scripts and public data referenced in each study.
