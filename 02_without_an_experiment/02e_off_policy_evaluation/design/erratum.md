# Erratum to the second design: which error the decision rules name

Written on 2026-11-24, after the results of the second design and an outside review. The plans and their hashes are
unchanged.

**What the plan says.** [`analysis_plan_v2.md`](analysis_plan_v2.md), Decision rules: IPS with the logged propensity
(rule 1) and DR with an estimated propensity (rule 2) each have "mean absolute error below 10% of the truth and
coverage of at least 90% for each of the four policies".

**What the code computed.** `run_ope_v2.py` compared the absolute value of the *mean* error over the 200 logs with
10%: the bias of the estimator, the quantity the first plan had named ("mean absolute bias"). The mean absolute
error is the average size of one log's error. An estimator can be right on average and far off in a single log, so
the two are not interchangeable, and the wording of the plan is the one that binds.

**The rules as written.** [`code/accuracy_from_logs.py`](../code/accuracy_from_logs.py) recomputes both quantities
from the saved per-log estimates ([`out/ope_v2_logs.csv`](../out/ope_v2_logs.csv)) and writes
[`out/ope_v2_accuracy.json`](../out/ope_v2_accuracy.json). Moderate setting, 200 logs per policy:

| Policy | IPS, logged propensity: mean error | mean absolute error | DR, estimated propensity: mean error | mean absolute error |
|---|---|---|---|---|
| All users | −0.4% | 22.0% | −4.3% | 22.6% |
| Response model 20% | −0.9% | 24.2% | −5.4% | 25.0% |
| Uplift model 20% | −2.1% | 22.2% | −5.6% | 22.5% |
| Random 20% | +2.9% | 53.2% | 0.0% | 49.7% |

Coverage of the 95% intervals is 94% to 97% for both estimators and meets its condition. The mean absolute error is
above 10% for every policy and both estimators, so **neither rule is met as written**. `out/ope_v2.json` keeps the
field `decision` as the run produced it (both `true`); it records the comparison of the mean error, not the rule of
the plan.

**What stands.** On average over logs both estimators are close to the benchmark (within 3% and 6%) and their
intervals cover it at the stated rate. What does not hold is the accuracy of a single log of about 108,000 rows.

## Item 2, third design: the "unadjusted" column of the benchmark

Written on 2026-11-24 after the third design ran. `run_ope_v3.py` first wrote, as the unadjusted value of each
policy, the difference between rows whose assignment agrees with the policy and control rows. For a policy that
treats only some users that is not a policy value (for the response 20% policy it gave 88 visits per 1,000).
[`code/fix_unadjusted_v3.py`](../code/fix_unadjusted_v3.py) recomputes the column as in the earlier designs, IPS with
the experiment's constant assignment share, and keeps the first value under `unadjusted_as_first_written`. The column
is descriptive; no estimate, error or rule uses it. The line in `run_ope_v3.py` is corrected.
