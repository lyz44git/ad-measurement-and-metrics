# Analysis plan — customer value over 12 months, retention risk, acquisition and SQL reconciliation

Written 2026-11-15 before running `code/14_ltv_extension.py`. SHA-256 of this file is saved to `logs/plan_hash.txt`
before the run. Data: UCI Online Retail II (id 502, CC BY 4.0), a real UK online gift retailer with many wholesale
accounts, 2009-12-01 to 2011-12-09, cleaned by `code/10_ltv_load.py` (794,163 lines, 5,875 accounts). Sales are gross
(no margin), from non-credit-note invoices. Everything here is predictive or descriptive; there is no marketing
treatment in the data, so nothing estimates the effect of an acquisition or retention campaign.

## E1. Twelve-month holdout of the customer-value model
- Cutoff 2010-12-01. Population: every account with at least one purchase day before the cutoff.
- Target: sales in [2010-12-01, 2011-12-01).
- Models: (a) past sales before the cutoff (12 months of history); (b) BG/NBD x Gamma-Gamma fitted only on purchases
  before the cutoff, prediction = expected purchase days over 365/7 weeks x expected spend per purchase day.
- Primary metric: Spearman rank correlation between prediction and actual. Secondary: AUC for any purchase in the
  window, share of actual sales held by the predicted top decile (random tie-breaks, 20 draws), predicted/actual total.
- Uncertainty: customer bootstrap, 500 draws, models held fixed; paired difference (b) - (a).
- Decision rule: prefer (b) if the paired 95% interval of the Spearman difference lies above 0.

## E2. Retention risk among high-value accounts
- Cutoff 2011-06-01. Population: accounts with a purchase in the prior 12 months, top third by sales in that window.
- Outcome: any purchase in [2011-06-01, 2011-12-01).
- Scores: (a) days since last purchase (recency only); (b) BG/NBD expected purchase days in the next 26 weeks, model
  fitted on all purchases before the cutoff.
- Report: AUC of each score with bootstrap intervals, the paired difference, and the repurchase rate by tercile of (b).
- No decision rule; descriptive.

## E3. Early value of newly acquired accounts
- New accounts: first purchase in a month with no purchase in the previous 12 months, cohorts 2010-12 to 2011-05
  (each observed for five further complete months).
- Split accounts into quartiles of first-month sales (pooled over cohorts).
- Report: share of months 1-5 sales from the top quartile, and the share of accounts that buy again in months 1-5 by
  quartile, with bootstrap intervals. Descriptive.

## E4. SQL reconciliation
- Rebuild in DuckDB SQL, from the cleaned line file: (i) the account-level recency / frequency / sales table at the
  2011-06-01 cutoff with the recency x value rule segments and their next-6-month sales; (ii) the new-account cohort
  sizes and monthly repeat rates.
- Compare with the pandas results in `out/12_ltv_segments.json`; report the largest absolute difference.

## Not covered
Margin, discounting, acquisition cost, marketing channels, media spend, randomized treatments, user logs.
