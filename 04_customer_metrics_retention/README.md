# 04 · Customer metric definitions and retention on retail transactions

**[Explore this study interactively →](https://lyz44git.github.io/ad-measurement-and-metrics/04.html#s04)**

> **Takeaway.** The "new customer" count depends on its definition: of 1,036 accounts that bought in March–May 2011
> and not in December 2010–February 2011, 640 (62%) had bought in December 2009–November 2010, so cohorts here use a
> 12-month look-back. Among 1,442 high-value accounts, a purchase-model score ranked who bought again within six months
> better than recency alone (AUC 0.79 against 0.75). For ranking sales over the next 12 months, a past-sales rule did
> better than the purchase model.

## Questions

1. Does the "new customer" metric count returning buyers as new?
2. Which high-value customers are least likely to buy again?
3. Does a purchase model rank future customer value better than a simple past-sales rule?

## Data

UCI Machine Learning Repository, Online Retail II (id 502, CC BY 4.0): transactions of a UK online gift retailer with
many wholesale accounts, 2009-12-01 to 2011-12-09. Of 1,067,371 raw lines, 794,163 lines and 5,875 accounts remain
after removing exact duplicates, lines without a customer ID, non-merchandise codes and non-positive prices
([`out/10_ltv_audit.json`](out/10_ltv_audit.json)); each analysis below uses its own window and subset of these
accounts. Sales are gross and exclude credit-note invoices. The data contain no marketing treatment, so all
results are predictive or descriptive.

Download `online_retail_II.xlsx` from the UCI repository into `data_raw/` (git-ignored).

## Method

1. **Cleaning and audit** (`10_ltv_load.py`): duplicates, missing IDs and non-merchandise codes counted and removed;
   credit notes kept with a cancellation flag and excluded from sales. Every count is written to the audit file.
2. **Metric definitions** (`12_ltv_segments.py`, `14_ltv_extension.py`): the new-customer definition is tested for
   contamination by returning buyers under different look-back windows; cohorts and segments are then defined once
   and rebuilt in SQL to confirm that both implementations give the same tables.
3. **Retention risk and early value** (`14_ltv_extension.py`): a ranking of high-value accounts by expected
   purchases, and first-month value of new accounts, both evaluated on later months.
4. **Purchase and spend models** (`btyd_impl.py`, checked by `11_btyd.py`): BG/NBD for purchase frequency (a
   stochastic model: Poisson purchases while a customer is active, with a chance of dropping out after each one) and
   Gamma-Gamma for spend per purchase, implemented from the published likelihoods and checked by parameter recovery
   on simulated data. Compared out of time with a last-6-months sales rule and a LightGBM model.

Step 14 was run under [`design/analysis_plan.md`](design/analysis_plan.md), written after steps 10–12 had been run
and fixed before step 14 ran (SHA-256 in
`logs/plan_hash.txt`); deviations are in [`design/deviations.md`](design/deviations.md). Step 15 (`15_same_anchor_checks.py`) was added
after review and is not in the plan.

## Results

Sources: [`out/12_ltv_segments.json`](out/12_ltv_segments.json),
[`out/14_ltv_extension.json`](out/14_ltv_extension.json).

### Metric definitions

**New-customer definition.** Of 1,036 accounts new under a 3-month look-back in March–May 2011, 640 (62%) had bought
in December 2009–November 2010. At a fixed anchor (buyers in each month from 2010-12 to 2011-11), 2,620 of
the 4,449 account-months new under a 3-month look-back (59%) had bought in the previous 12 months
([`out/15_same_anchor_checks.json`](out/15_same_anchor_checks.json)). Cohorts here use a 12-month look-back:

```sql
-- an account is new in a month if it bought in that month and on no day of the previous 12 months
SELECT a.cid, a.mon FROM m a
WHERE NOT EXISTS (SELECT 1 FROM days d
                  WHERE d.cid = a.cid AND d.day < a.mon AND d.day >= a.mon - INTERVAL 12 MONTH)
```

**SQL reconciliation.** The segment table and the cohort repeat-rate matrix, rebuilt in DuckDB SQL
([`out/14_sql_queries.sql`](out/14_sql_queries.sql)), reproduce the 36 segment values to numerical precision and the 56 cohort repeat rates to the stored four
decimal places. Both implementations
use rank-based terciles with boundary accounts in the upper group (deviation 1).

[![Share of each month's new customers who buy again in each later month, by month of first purchase](out/fig/fig6_cohort_retention.png)](https://lyz44git.github.io/ad-measurement-and-metrics/04.html#s04)

### Retention and early value

**Retention risk.** Among the 1,442 accounts in the top third of sales in the 12 months before 2011-06-01 (84% of
those sales), the purchase model ranks buyers in 2011-06 to 2011-11 better than recency alone:

| Ranking | AUC for a repeat purchase within 6 months (95% CI) |
|---|---|
| Purchase-model expected purchases | 0.790 (0.759 to 0.820) |
| Recency alone | 0.752 (0.714 to 0.787) |
| Difference | +0.038 (0.003 to 0.071) |

Repurchase rate by score tercile, lowest to highest: 65.5%, 88.8%, 96.3%.

**Early value of new accounts.** Among 708 new accounts (cohorts 2010-12 to 2011-05), the top quartile by first-month
sales produced 58.9% of sales in months 1–5 (95% CI 47.9% to 68.4%); 59.9% of them bought again, against 35.0% in the
bottom quartile.

**High-value segment.** Accounts that bought in the last 60 days and were in the top third of 6-month sales made up
26.5% (719) of the 2,716 accounts active in the 6 months before 2011-06-01 and produced 72.5% of their next-six-month sales; 91.7% bought again.

**Clustering check.** K-means on recency, frequency, spend and return behavior, with the number of clusters chosen by
bootstrap out-of-bag stability, selects two clusters (adjusted Rand index 0.92 on average, 10th percentile 0.89). Its
high-value cluster is 36.8% of the same 2,716 accounts, against 26.5% for the rule, and produced 76.5% of
next-six-month sales ([`out/12_ltv_segments.json`](out/12_ltv_segments.json)).

[![Nine customer groups by value and time since last purchase: share of customers against share of sales in the next six months, and average sales per customer with 95% intervals](out/fig/fig5_segments.png)](https://lyz44git.github.io/ad-measurement-and-metrics/04.html#s04)

### Purchase model against a simple rule

| Holdout | Spearman, purchase model | Spearman, past-sales rule | Top-decile share of actual sales, model / rule |
|---|---|---|---|
| 6 months from 2011-06-01 (2,716 accounts active in the prior 6 months; rule: last 6 months' sales) | 0.650 | 0.587 | 59.1% / 59.2% |
| 12 months from 2010-12-01 (4,239 accounts with any earlier purchase; rule: last 12 months' sales) | 0.584 | 0.621 | 60.8% / 60.2% |

The model ranks better on the 6-month holdout. **On the 12-month holdout the pre-specified rule was not met**: the
past-sales rule ranks better (Spearman difference −0.037, 95% CI −0.056 to −0.020). A LightGBM model on a fixed
6-month look-back did not differ from the rule on any metric. The two holdouts differ in start date, accounts and
rule, so the contrast is not a horizon effect. At the 2010-12-01 cutoff, on the same 4,239 accounts, the past-sales
rule also ranked better over 6 months (Spearman difference −0.023, 95% CI −0.040 to −0.006;
[`out/15_same_anchor_checks.json`](out/15_same_anchor_checks.json)).

## Reproduce

Each script takes its paths as arguments:

```bash
python code/10_ltv_load.py data_raw/online_retail_II.xlsx derived out
python code/11_btyd.py out/11_btyd_recovery.json
python code/12_ltv_segments.py derived out code
python code/14_ltv_extension.py derived out code
python code/15_same_anchor_checks.py derived out code   # a few seconds
python ../figures/make_study_figures.py   # redraws the figures from out/
```

`tests/` checks the purchase and spend models on simulated customers and runs the published SQL against an
independent pandas implementation on synthetic purchases.

## Scope

- Not lifetime value in the strict sense: no margin, discounting or acquisition cost, and horizons of 6 and 12 months.
- No causal effect of any acquisition or retention action is estimated.
- At the 2010-12-01 cutoff the purchase model does not beat a past-sales rule at 6 or 12 months.
