# Results: Criteo Uplift v2.1 — incrementality, CATE learners, held-out targeting test (2026-11-12)

Label: **analysis of a public randomized advertising experiment** (Diemert et al. 2018), designed and run by Criteo.
Plan hashed before the run (`logs/10_plan_hash.txt`). Code `code/10_run_criteo.py`, `code/upliftkit/`. Run log
`logs/10_run_criteo.log` (408 s). Outputs `out/criteo/`. Tests `logs/10_pytest.log` (15 passed).
The dataset pools several tests with non-uniform subsampling: absolute lift is not a population effect.

## A. Incrementality (13,979,592 users; 85.0% treated)
| | Unadjusted ITT | Regression-adjusted (AIPW, linear) |
|---|---|---|
| Visit | +1.034 pp (SE 0.015); +27.1% on a 3.82% control rate | +0.773 pp (SE 0.013) |
| Conversion | +0.115 pp (SE 0.003) on 0.194% | +0.100 pp (SE 0.003) |
| Visit CACE (3.60% of treated exposed; none in control) | 28.7 pp (SE 0.41) | 21.5 pp (SE 0.35) |
- Assignment is slightly predictable: held-out AUC 0.509; largest standardized mean difference 0.049. Adjustment
  lowers the visit effect by 25%. Both are reported, as planned; the adjusted figure is the safer one.

## B–C. Targeting (train 6,992,867 / validation 2,794,934 / test 4,191,791; outcome = visit)
Test set, scored once. Qini ×10⁴ per user, 95% Poisson-bootstrap CI.
| Ranking | Qini | CI | Qini − response | CI of difference | Realized uplift, top 10% |
|---|---|---|---|---|---|
| Response model P(visit\|X) | 31.0 | [29.4, 32.7] | — | — | 5.30 pp |
| T-learner (selected on validation) | 29.8 | [28.1, 31.8] | −1.2 | [−3.0, +0.6] | 6.00 pp |
| Causal forest (EconML, 300K subsample) | 29.9 | [28.1, 31.6] | −1.2 | [−3.1, +0.6] | 6.22 pp |
| X-learner | 21.0 | [19.1, 23.2] | −10.0 | [−11.7, −8.2] | 6.30 pp |
| DR-learner | 13.4 | [11.4, 15.8] | −17.7 | [−19.1, −15.8] | 6.01 pp |
| Random | 0.6 | [−0.7, 1.9] | | | 1.13 pp |
- **Heterogeneity is large and detected by every learner.** The top decile's realized uplift is 6.0 pp against 1.05 pp
  overall; the top 20% holds 75% of all incremental visits.
- **Pre-specified decision: uplift targeting does not beat response targeting** on Qini (difference CI includes 0).
  In this experiment users likely to visit anyway are also the users the ad moves most.
- X- and DR-learners rank well at the top but worse over the whole curve; with 15% control and a slightly
  predictable assignment, their imputed and inverse-weighted targets are noisier.
- Calibration of the selected learner (`c_calibration_selected.csv`): deciles 1–9 track realized uplift (decile 1
  predicted 6.6 pp, realized 6.0 pp). Decile 10 is wrong in sign: predicted −0.8 pp, realized +0.7 pp (SE 0.12).
  The model's "ads hurt" segment is not real; no user group should be excluded on its basis.

## D. Packaging
`upliftkit` (estimators, learners, evaluation), `10_config.json`, saved model, local FastAPI `/score` endpoint.
15 pytest checks pass: recovery of a simulated ATE and heterogeneity, no detection under a null, seeded bootstrap,
API schema rejection (4 cases), API-vs-batch parity (< 1e-9 on 2,000 rows), ordered deciles. Median latency
11 ms per 1,000-record batch (in-process test client). Offline only; not deployed.

## Deviations from the plan
None in estimators or decision rule. The top-10% uplift column has no CI (not pre-specified).

## Does and does not show
Shows: analysis of a business randomized experiment at scale with non-compliance; meta-learners and a causal forest
validated on randomized held-out data; an honest negative result on a pre-registered comparison; a tested scoring tool.
Does not show: designing or running an experiment; production deployment; a population-level lift estimate.
