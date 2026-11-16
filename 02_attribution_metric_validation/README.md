# 02. Validating an attribution metric against an experiment

**Question.** An exposure-based attribution metric credits the ad with every visit or conversion by a user who saw
it. How far is that from what the ad actually caused, and can statistical adjustment close the gap when no experiment
is available?

**Data.** The same Criteo experiment as project 01 (13,979,592 users). Pass the path to the `.csv.gz` file as the
first argument, or place it as described in `../01_ad_incrementality/README.md`.

**What I did.** The analysis was specified before the run as a descriptive comparison with no decision rule:
- Attributed outcomes: visits and conversions among exposed users in the ad arm.
- Incremental outcomes: the intent-to-treat effect times the number of users in the ad arm.
- Per-exposed-user effect on visits three ways: naive exposed-minus-unexposed difference; OLS with covariates;
  cross-fitted double machine learning on 2,000,000 users. Benchmark: the experimental effect on exposed users.

**What I found** (`out/attribution_vs_experiment.json`).

| | Exposure-attributed | Incremental (experiment) | Overstatement |
|---|---|---|---|
| Visits | 177,510 | 122,895 | 44% |
| Conversions | 23,031 | 13,687 | 68% |

Per-exposed-user effect on visits: naive 38.0 points; OLS-adjusted 25.5; double machine learning 24.6. The
experimental figure is 28.7 unadjusted and 21.5 regression-adjusted, so both adjusted observational estimates fall
inside the experimental range and the naive one does not.

**Run.**
```bash
python code/attribution_vs_experiment.py /path/to/criteo-research-uplift-v2.1.csv.gz
```

**Does not show.** Multi-touch or cross-channel attribution: the data have one exposure flag per user and no touch
paths. The experimental benchmark assumes assignment affects visits only through exposure.
