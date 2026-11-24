# How the results compare with published research

Each result of this repository is set here against what published research has found: where it agrees, where it
differs, and what could explain the difference. The repository's results come from a handful of public datasets, so
where they differ from a large published study, the published study is the stronger evidence.

The common thread, in marketing and in finance, is that the effect of advertising is real and that the raw comparison
overstates it until the comparison is made by an experiment or another design that removes selection.

## 1. Observational estimates against experiments

[Lewis, Rao, and Reiley (2011)](https://doi.org/10.1145/1963405.1963431) name the problem "activity bias": users who see an ad are more active online to begin
with, so comparing exposed with unexposed users overstates the effect of the ad. The naive comparison in study
[02a](02_without_an_experiment/02a_attribution_metric_validation) shows the same thing (38.0 points against 21.5 to 28.7 from the experiment).

[Gordon et al. (2019)](https://doi.org/10.1287/mksc.2018.1135) compare observational methods with 15 randomized experiments at
Facebook and find that the methods often fail to reproduce the experimental effects, even after conditioning on
extensive demographic and behavioral variables. [Gordon, Moakler, and Zettelmeyer (2023)](https://doi.org/10.1287/mksc.2022.1413) repeat the exercise on 663
experiments with more than 5,000 features each: double machine learning does better than propensity-score matching,
and neither performs well.

In study [02a](02_without_an_experiment/02a_attribution_metric_validation) the adjusted estimates (24.6 to 25.5) fall between the two experimental ones. The comparison is
descriptive: the adjusted estimates are associations within the ad arm, while the experimental ones are complier
effects under instrumental-variable assumptions, and the range between them is not a bound. This is one experiment and
one outcome, so it is not a counterexample. A possible reason is that the 12 released features capture
much of what decided exposure in these data; a single experiment cannot test that. The reading consistent with the
literature is that adjustment worked here and cannot be assumed to work elsewhere.

## 2. How large a test must be

[Lewis and Rao (2015)](https://doi.org/10.1093/qje/qjv023) analyze 25 large advertising experiments run with major U.S. retailers and brokerages and
conclude that informative experiments can require more than 10 million person-weeks, because the effect of
advertising is small next to the variation in what people buy. The same arithmetic appears in study [01c](01_with_an_experiment/01c_sql_metric_readout): a
conversion test needs about 20 times the users of a visit test, 849,000 per group against 41,000 for a 10% lift.

[Deng et al. (2013)](https://doi.org/10.1145/2433396.2433413) introduced the use of pre-experiment data to reduce the variance of an experiment's
readout. The adjustment in study [03a](03_planning_a_test/03a_lift_study_sizing) follows that idea and removes about 31% of the variance, which lowers the
sample for a one-point lift in visits from about 6,500 to about 4,400 per group. It helps and does not close the gap
that Lewis and Rao describe.

[Feit and Berman (2019)](https://doi.org/10.1287/mksc.2019.1194) show that when a test is sized to maximize profit and not to reach a fixed statistical power,
the best sample is substantially smaller than the one a hypothesis test calls for. The sizes in studies
[03a](03_planning_a_test/03a_lift_study_sizing), [01c](01_with_an_experiment/01c_sql_metric_readout) and [03b](03_planning_a_test/03b_geo_experiment_design) are of the hypothesis-test kind; for a firm that only needs to choose the better of two
options, the profit-maximizing size may be smaller, depending on margins, prior uncertainty about the effect and the
population the decision is rolled out to.

## 3. Who to target

[Blake, Nosko, and Tadelis (2015)](https://doi.org/10.3982/ECTA12423) find at eBay that non-brand search ads moved new and infrequent users and not the
frequent buyers who account for most spending, so the users most likely to buy were the wrong ones to target. In
study [01a](01_with_an_experiment/01a_ad_incrementality) the reverse holds: the users most likely to visit are also the ones the ads move most, and a
response model targets as well as an uplift model (each puts about 75% of incremental visits in its top fifth).

[Fernández-Loría and Provost (2022)](https://jmlr.org/papers/v23/19-480.html) give the condition that reconciles the two results: predicting the outcome can be
better for targeting than estimating the effect when outcomes are informative about effects, because the effect
estimate carries the sampling error of two predictions. [Simester, Timoshenko, and Zoumpoulis (2020)](https://doi.org/10.1287/mnsc.2019.3308) add that the more
elaborate targeting methods win when the training data are ideal and lose that advantage when the data have the
flaws that are usual in practice. Whether uplift modeling pays is therefore a property of the setting and has to be
checked in each one, which is what the pre-specified comparison in study [01a](01_with_an_experiment/01a_ad_incrementality) does.

## 4. Marketing mix models and the returns to advertising

[Chan and Perry (2017)](https://research.google/pubs/challenges-and-opportunities-in-media-mix-modeling/) group the obstacles to marketing mix modeling into data limitations, selection bias and model
choice, and note that its estimates are correlational. The simulations in study [02c](02_without_an_experiment/02c_marketing_mix_modeling) isolate the first obstacle
and put a number on it: with weekly data, 19% of brand-channel pairs have enough independent variation in spend for
the channel's return to be measured. Spend in the simulations does not respond to demand, so
selection bias is absent there; in real data it can change the apparent signal in either direction.

[Shapiro, Hitsch, and Tuchman (2021)](https://doi.org/10.3982/ECTA17674) estimate the effect of television advertising for 288 consumer brands and find
elasticities substantially smaller than earlier work, with a negative return at the margin for more than 80% of
brands. In the experiment used here, by contrast, the ads raised the conversion rate by 59%. The two are different
media, products and designs, and different quantities: a relative conversion lift is not a return on spend, and this
repository has no spend or margin data to compute one. Together they say that the effect of advertising varies widely
from one setting to another, which is the case for measuring it in each.

## 5. Attribution and bidding

[Diemert et al. (2017)](https://doi.org/10.1145/3124749.3124752), who released the data used in studies [02b](02_without_an_experiment/02b_multi_touch_attribution) and [02d](02_without_an_experiment/02d_attribution_and_bidding),
report that a bidder that accounts for attribution is more efficient, and that it differs from the baseline mainly in
how it bids right after a click. The replay in study [02d](02_without_an_experiment/02d_attribution_and_bidding) finds the same direction: the time-decay bidder puts
20% of its spend on impressions within a day of a click, against 25% for the last-touch bidder. The effect on what is
bought and on the credit captured is small (at most 2.2% at half the logged budget). The two are not directly
comparable: theirs is a production bidder evaluated by a utility metric and by online tests, this one a six-feature
value model replayed at logged prices. Neither credit rule is validated against an experiment in these data.

## 6. Customer models and customer counts

[Fader, Hardie, and Lee (2005)](https://doi.org/10.1287/mksc.1040.0098) introduced the BG/NBD model used in study [04](04_customer_metrics_retention). [Wübben and von Wangenheim (2008)](https://doi.org/10.1509/jmkg.72.3.082)
find that simple managerial heuristics do at least as well as such models in the tasks managers care about, except
for forecasting the total purchases of a customer base. Study [04](04_customer_metrics_retention) is in line with this: the model ranks
six-month repeat buyers among high-value accounts better than recency alone (AUC 0.79 against 0.75), and a past-sales
rule ranks 12-month sales better than the model.

[McCarthy and Fader (2018)](https://doi.org/10.1177/0022243718802843) value publicly traded retailers from their customer data. When customer counts feed a
valuation in this way, the definition of a new customer is not a reporting detail: in study [04](04_customer_metrics_retention) a three-month
look-back labels 1,036 accounts that bought in March–May 2011 new, of which 640 had bought in December 2009–November
2010.

## 7. The same lesson in finance

The finance literature asks whether advertising moves investors as well as customers, and it shows the same
correction. [Lou (2014)](https://doi.org/10.1093/rfs/hhu019) finds, in annual data, that higher advertising spending comes with more retail buying and
higher stock returns in the same year and lower returns afterward, and that advertising rises before insider sales.
[Focke, Ruenzi, and Ungeheuer (2020)](https://doi.org/10.1093/rfs/hhz142) use daily advertising data and find that advertising raises investor attention but
has little effect on trading and no significant effect on short-term returns; they attribute the earlier positive
relation between advertising and returns to reverse causality. [Liaukonytė and Žaldokas (2022)](https://doi.org/10.1287/mnsc.2021.4003) identify the effect
from time zones, which expose viewers to the same national advertising at different times, and find that a television
advertisement raises searches for the advertiser's financial filings by 3% within 15 minutes.

The pattern matches the one here. Advertising has an effect, the raw association overstates it, and the size of the
effect is known only once the design removes selection.

## 8. Privacy and forecast reconciliation

The privacy study [01d](01_with_an_experiment/01d_private_segment_effects) uses the Laplace mechanism of [Dwork et al. (2006)](https://doi.org/10.1007/11681878_14). What privacy
costs advertisers has been measured at scale by [Wernerfelt et al. (2025)](https://doi.org/10.1287/mksc.2023.0274), in an experiment
with more than 70,000 advertisers: removing data from outside the platform raised the median cost per incremental
customer by 31%, from $38.16 to $49.93. Study [01d](01_with_an_experiment/01d_private_segment_effects) addresses a narrower question, how much accuracy a readout loses when its counts are
noised, and finds that a model which knows the noise scale recovers much of it.

[Wickramasuriya, Athanasopoulos, and Hyndman (2019)](https://doi.org/10.1080/01621459.2018.1448825) derive the reconciliation of hierarchical forecasts that minimizes
the variance of the reconciled errors, given the covariance of the base forecast errors. With 873 series and an
estimated covariance, its gain in study [03c](03_planning_a_test/03c_hierarchical_forecasting) held with one base model and not with another, and bottom-up
reconciliation was the safe default.

## 9. Proxy outcomes, delayed labels and logged policies

[Athey, Chetty, Imbens, and Kang (2026)](https://doi.org/10.3386/w26463) combine short-run outcomes into a surrogate
index that predicts the long-run outcome, and show on a job-training experiment that six quarters of employment
data would have given the long-run effect with 35% smaller standard errors. The index is valid when the treatment
affects the long-run outcome only through the surrogates. Study [03d](03_planning_a_test/03d_surrogate_outcome)
is a case where the index falls short and the experiment shows it: the visit-based index is 42% of the directly
measured effect on conversions. The study does not identify by which path the ads raised conversions. A weaker use
survives: across 100 segments the visit and conversion effects are correlated at 0.95 after removing sampling noise,
and in a test too small to read conversions by segment, choosing segments by their visit effect does better than
choosing by conversions. A proxy that fails as a surrogate for the size of an effect can still rank where it is.

[Chapelle (2014)](https://doi.org/10.1145/2623330.2623634) models the delay between a display-ad click and the
conversion as exponential and fits it jointly with the conversion probability, so that recent clicks whose
conversions have not arrived are not counted as failures. Study [02f](02_without_an_experiment/02f_delayed_conversions)
fits the same likelihood in PyTorch on Criteo's attribution log, at the impression rather than the click level.
[Yoshikawa and Imai (2018)](https://arxiv.org/abs/1802.00255) replace the exponential delay with a non-parametric
one, which is the form of study 02f's final design: under daily retraining on a 14-day label it moves the forecast
from 11.5% too few conversions to 1.8% too many, but does not lower the log loss. An earlier cold-start design of the
study showed the limit of any parametric tail: with two weeks of data, delays longer than two weeks have to be
assumed.

[Dudík, Langford, and Li (2011)](https://arxiv.org/abs/1103.4601) show that the doubly robust estimator of a policy's
value is accurate when either the model of rewards or the model of the logging policy is good.
[Gentzel, Pruthi, and Jensen (2021)](https://proceedings.mlr.press/v139/gentzel21a.html) build observational data
sets with an experimental benchmark by sampling from randomized experiments, the construction of study
[02e](02_without_an_experiment/02e_off_policy_evaluation). There, on logs of about 1.6 million rows, one log's
inverse propensity weighting with the recorded propensity is off by 3% to 4% of the benchmark and the doubly robust
estimator with an estimated propensity by 2.5% to 2.7%; under a stronger bias the doubly robust estimator stays within
6% while inverse weighting with the estimated propensity falls about a third short, as the theorem leads one to
expect. With logs of about 108,000 rows, an earlier design, one log was off by 22% or more: the size of the log
decides whether a single estimate is usable. The practical counterpart is to record the probability of each decision
when it is made, and to log enough of them. The same study shows a
condition of the construction that is easy to miss: the experiment's assignment share must be known for every
row, and in a pooled release it may vary with the features.

## 10. Where the field is going

[Gordon, Moakler, and Zettelmeyer (2026)](https://www.nber.org/papers/w35044) use 2,226 experiment–conversion-event pairs from 839 experiments at Meta to predict the incremental effect of
campaigns that have no experiment, from campaign-level measures that include last-click conversion counts. Their
model explains 88% of the out-of-sample variation in incremental conversions per dollar, against 19% for last-click
attribution alone. This is the constructive answer to the gap this repository starts from: attribution counts are
informative once they are calibrated against experiments, and studies [02a](02_without_an_experiment/02a_attribution_metric_validation) and [01c](01_with_an_experiment/01c_sql_metric_readout) are a one-experiment
version of that calibration.

## References

- Athey, Susan, Raj Chetty, Guido W. Imbens, and Hyunseung Kang. 2026. "The Surrogate Index: Combining Short-Term Proxies to Estimate Long-Term Treatment Effects More Rapidly and Precisely." *Review of Economic Studies* 93 (4): 2284–2312. Working paper version: https://doi.org/10.3386/w26463.
- Blake, Thomas, Chris Nosko, and Steven Tadelis. 2015. "Consumer Heterogeneity and Paid Search Effectiveness: A Large-Scale Field Experiment." *Econometrica* 83 (1): 155–74. https://doi.org/10.3982/ECTA12423.
- Chan, David, and Mike Perry. 2017. "Challenges and Opportunities in Media Mix Modeling." Technical report. Google. https://research.google/pubs/challenges-and-opportunities-in-media-mix-modeling/.
- Chapelle, Olivier. 2014. "Modeling Delayed Feedback in Display Advertising." In *Proceedings of the 20th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*, 1097–1105. New York: ACM. https://doi.org/10.1145/2623330.2623634.
- Deng, Alex, Ya Xu, Ron Kohavi, and Toby Walker. 2013. "Improving the Sensitivity of Online Controlled Experiments by Utilizing Pre-experiment Data." In *Proceedings of the Sixth ACM International Conference on Web Search and Data Mining*, 123–32. New York: ACM. https://doi.org/10.1145/2433396.2433413.
- Diemert, Eustache, Artem Betlei, Christophe Renaudin, and Massih-Reza Amini. 2018. "A Large Scale Benchmark for Uplift Modeling." Paper presented at the AdKDD and TargetAd Workshop, KDD 2018, London, August 20. https://ailab.criteo.com/criteo-uplift-prediction-dataset/.
- Diemert, Eustache, Julien Meynet, Pierre Galland, and Damien Lefortier. 2017. "Attribution Modeling Increases Efficiency of Bidding in Display Advertising." In *Proceedings of the ADKDD’17*, 1–6. New York: ACM. https://doi.org/10.1145/3124749.3124752.
- Dudík, Miroslav, John Langford, and Lihong Li. 2011. "Doubly Robust Policy Evaluation and Learning." In *Proceedings of the 28th International Conference on Machine Learning*, 1097–1104. https://arxiv.org/abs/1103.4601.
- Dwork, Cynthia, Frank McSherry, Kobbi Nissim, and Adam Smith. 2006. "Calibrating Noise to Sensitivity in Private Data Analysis." In *Theory of Cryptography: Third Theory of Cryptography Conference, TCC 2006*, edited by Shai Halevi and Tal Rabin, 265–84. Lecture Notes in Computer Science 3876. Berlin: Springer. https://doi.org/10.1007/11681878_14.
- Fader, Peter S., Bruce G. S. Hardie, and Ka Lok Lee. 2005. "‘Counting Your Customers’ the Easy Way: An Alternative to the Pareto/NBD Model." *Marketing Science* 24 (2): 275–84. https://doi.org/10.1287/mksc.1040.0098.
- Feit, Elea McDonnell, and Ron Berman. 2019. "Test & Roll: Profit-Maximizing A/B Tests." *Marketing Science* 38 (6): 1038–58. https://doi.org/10.1287/mksc.2019.1194.
- Fernández-Loría, Carlos, and Foster Provost. 2022. "Causal Classification: Treatment Effect Estimation vs. Outcome Prediction." *Journal of Machine Learning Research* 23 (59): 1–35. https://jmlr.org/papers/v23/19-480.html.
- Focke, Florens, Stefan Ruenzi, and Michael Ungeheuer. 2020. "Advertising, Attention, and Financial Markets." *Review of Financial Studies* 33 (10): 4676–4720. https://doi.org/10.1093/rfs/hhz142.
- Gentzel, Amanda M., Purva Pruthi, and David Jensen. 2021. "How and Why to Use Experimental Data to Evaluate Methods for Observational Causal Inference." In *Proceedings of the 38th International Conference on Machine Learning*, PMLR 139: 3660–71. https://proceedings.mlr.press/v139/gentzel21a.html.
- Gordon, Brett R., Robert Moakler, and Florian Zettelmeyer. 2023. "Close Enough? A Large-Scale Exploration of Non-experimental Approaches to Advertising Measurement." *Marketing Science* 42 (4): 768–93. https://doi.org/10.1287/mksc.2022.1413.
- Gordon, Brett R., Robert Moakler, and Florian Zettelmeyer. 2026. "Predicted Incrementality by Experimentation (PIE) for Ad Measurement." NBER Working Paper 35044. Cambridge, MA: National Bureau of Economic Research. https://www.nber.org/papers/w35044.
- Gordon, Brett R., Florian Zettelmeyer, Neha Bhargava, and Dan Chapsky. 2019. "A Comparison of Approaches to Advertising Measurement: Evidence from Big Field Experiments at Facebook." *Marketing Science* 38 (2): 193–225. https://doi.org/10.1287/mksc.2018.1135.
- Lewis, Randall A., and Justin M. Rao. 2015. "The Unfavorable Economics of Measuring the Returns to Advertising." *Quarterly Journal of Economics* 130 (4): 1941–73. https://doi.org/10.1093/qje/qjv023.
- Lewis, Randall A., Justin M. Rao, and David H. Reiley. 2011. "Here, There, and Everywhere: Correlated Online Behaviors Can Lead to Overestimates of the Effects of Advertising." In *Proceedings of the 20th International Conference on World Wide Web*, 157–66. New York: ACM. https://doi.org/10.1145/1963405.1963431.
- Liaukonytė, Jūra, and Alminas Žaldokas. 2022. "Background Noise? TV Advertising Affects Real-Time Investor Behavior." *Management Science* 68 (4): 2465–84. https://doi.org/10.1287/mnsc.2021.4003.
- Lou, Dong. 2014. "Attracting Investor Attention through Advertising." *Review of Financial Studies* 27 (6): 1797–1829. https://doi.org/10.1093/rfs/hhu019.
- McCarthy, Daniel M., and Peter S. Fader. 2018. "Customer-Based Corporate Valuation for Publicly Traded Noncontractual Firms." *Journal of Marketing Research* 55 (5): 617–35. https://doi.org/10.1177/0022243718802843.
- Shapiro, Bradley T., Günter J. Hitsch, and Anna E. Tuchman. 2021. "TV Advertising Effectiveness and Profitability: Generalizable Results from 288 Brands." *Econometrica* 89 (4): 1855–79. https://doi.org/10.3982/ECTA17674.
- Simester, Duncan, Artem Timoshenko, and Spyros I. Zoumpoulis. 2020. "Targeting Prospective Customers: Robustness of Machine-Learning Methods to Typical Data Challenges." *Management Science* 66 (6): 2495–2522. https://doi.org/10.1287/mnsc.2019.3308.
- Wernerfelt, Nils, Anna Tuchman, Bradley T. Shapiro, and Robert Moakler. 2025. "Estimating the Value of Offsite Tracking Data to Advertisers: Evidence from Meta." *Marketing Science* 44 (2): 268–86. https://doi.org/10.1287/mksc.2023.0274.
- Wickramasuriya, Shanika L., George Athanasopoulos, and Rob J. Hyndman. 2019. "Optimal Forecast Reconciliation for Hierarchical and Grouped Time Series through Trace Minimization." *Journal of the American Statistical Association* 114 (526): 804–19. https://doi.org/10.1080/01621459.2018.1448825.
- Wübben, Markus, and Florian von Wangenheim. 2008. "Instant Customer Base Analysis: Managerial Heuristics Often ‘Get It Right.’" *Journal of Marketing* 72 (3): 82–93. https://doi.org/10.1509/jmkg.72.3.082.
- Yoshikawa, Yuya, and Yusaku Imai. 2018. "A Nonparametric Delayed Feedback Model for Conversion Rate Prediction." arXiv preprint 1802.00255. https://arxiv.org/abs/1802.00255.
