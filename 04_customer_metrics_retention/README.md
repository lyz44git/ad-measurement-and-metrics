# 04. Customer metrics and retention on retail transactions

**Questions.**
1. Is the "new customer" metric counting returning buyers?
2. Which high-value customers are least likely to return?
3. Does a purchase model rank future customer value better than a simple past-sales rule?

**Data.** UCI Machine Learning Repository, Online Retail II (id 502, CC BY 4.0): a UK online gift retailer with many
wholesale accounts, 2009-12-01 to 2011-12-09. 1,067,371 raw lines; 794,163 lines and 5,875 accounts after removing
exact duplicates, lines with no customer ID, non-merchandise codes and non-positive prices (`out/10_ltv_audit.json`).
Sales are gross. There is no marketing treatment in the data, so everything here is predictive or descriptive.

**What I did.** Steps 10-13 build the cleaned table, a BG/NBD purchase model and a Gamma-Gamma spend model written
from the published likelihoods (checked by parameter recovery on simulated data), and segments validated on the next
six months. Step 14 was run under `design/analysis_plan.md`, hashed before the run (`logs/plan_hash.txt`);
deviations are in `design/deviations.md`.

**What I found.**
- **New-customer definition.** With a 3-month look-back, 1,036 accounts would be labelled new, of which 640 (62%) had
  bought in the prior 12 months. Cohorts here use a 12-month look-back instead.
- **SQL reconciliation.** The segment table and the cohort repeat-rate matrix were rebuilt in DuckDB SQL
  (`out/14_sql_queries.sql`) and match the pandas results in all 92 cells.
- **Retention risk.** Among the 1,442 accounts in the top third of 12-month sales (84% of those sales), the purchase
  model's expected purchases ranked repeat buyers with AUC 0.790 against 0.752 for recency alone (difference +0.038,
  95% CI 0.003 to 0.071). Repurchase rate by score tercile: 65.5%, 88.8%, 96.3%.
- **Early value of new accounts.** Among 708 new accounts, the top quartile by first-month sales produced 58.9% of
  sales in months 1-5, and 59.9% of them bought again against 35.0% in the bottom quartile.
- **High-value segment.** Accounts that bought in the last 60 days and were in the top third of 6-month sales were
  26.5% of 2,716 active accounts and produced 72.5% of their next-six-month sales.
- **Customer-value model against a simple rule.** On a 6-month holdout the model ranked accounts better than a
  last-6-months sales rule (Spearman 0.650 against 0.587). **On the 12-month holdout the pre-specified rule was not
  met:** the past-sales rule ranked accounts better (Spearman difference -0.037, 95% CI -0.056 to -0.020), and the
  top-decile share did not differ (60.8% against 60.2%).

**Run.** The scripts take their paths as arguments:
```bash
python code/10_ltv_load.py data_raw/online_retail_II.xlsx derived out
python code/11_btyd.py out/11_btyd_recovery.json
python code/12_ltv_segments.py derived out code
python code/13_ltv_figs.py out
python code/14_ltv_extension.py derived out code
```
`btyd_impl.py` is an importable copy of `11_btyd.py`.

**Does not show.** Lifetime value in the strict sense (no margin, discounting or acquisition cost; horizons of 6 and
12 months), the causal effect of any acquisition or retention action, or a model that beats simple rules at 12 months.
