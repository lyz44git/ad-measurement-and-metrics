# 08 · Sizing lift studies at survey-scale sample sizes

> **Takeaway.** To detect a one-point lift on a 4% base rate, a study needs about 10,000 users per arm: power is 19%
> at 1,000 per arm, 73% at 5,000 and 94% at 10,000. False-positive rates stay near 5% at every size, for both the
> z-test and a Bayesian readout.

## Question

Lift studies that survey users, such as brand-lift studies, run on a few thousand respondents per arm. How often
would a study of that size detect a real effect of about one point, and how often would it report one that is not
there?

## Data

Arm sizes and visit counts of the Criteo experiment from [study 07](../07_bayesian_segment_effects)
(`out/part1_overall.json`): visit rate 3.82% in the control arm and 4.85% in the ad arm, a true lift of 1.03 points.
Site visit stands in for the survey response. No survey data are used.

## Method

A design study with no decision rule.

1. For each size (1,000 to 20,000 users per arm), draw 2,000 studies by sampling users without replacement from each
   arm of the experiment.
2. Read each study with a two-sided z-test at 5% and with a Beta-Binomial posterior, calling a detection when
   P(lift > 0) > 0.95.
3. A/A studies draw both arms from the control arm and give the false-positive rate.

## Results

Source: [`out/lift_study_sizing.json`](out/lift_study_sizing.json).

| Users per arm | Power, z-test | Bayesian detection | 95% CI coverage | A/A false positives, z-test / Bayesian |
|---|---|---|---|---|
| 1,000 | 19% | 29% | 95.9% | 5.3% / 4.4% |
| 2,500 | 43% | 56% | 94.5% | 4.8% / 4.4% |
| 5,000 | 73% | 82% | 95.3% | 5.1% / 5.5% |
| 10,000 | 94% | 97% | 94.6% | 5.1% / 4.8% |
| 20,000 | 99.9% | 100% | 95.5% | 5.7% / 4.9% |

The smallest size on this grid with at least 80% power is 10,000 users per arm. The Bayesian rule detects more often
because it is one-sided.

## Reproduce

```bash
python code/lift_study_sizing.py     # a few seconds; reads study 07's part1_overall.json
```

`tests/` checks on a made-up experiment that power rises with sample size, that intervals cover the true lift about
95% of the time, and that rejections stay near 5% when there is no lift.

## Scope

- Design only: no survey was run and no brand outcome (awareness, recall, intent) is measured.
- One base rate and one effect size, taken from this experiment.
