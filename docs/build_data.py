"""Collect the numbers shown on the interactive page (docs/index.html) from the committed result files.

Usage: python docs/build_data.py   (writes docs/data.js)

Every value on the page comes from this file; nothing is typed by hand into the page.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
G1, G2, G3 = "01_with_an_experiment/", "02_without_an_experiment/", "03_planning_a_test/"
Z_POWER = 1.959964 + 0.841621


def load(rel):
    return json.loads((ROOT / rel).read_text())


def rows(rel):
    with open(ROOT / rel) as f:
        return list(csv.DictReader(f))


def r(x, k=4):
    return round(float(x), k)


def experiment():
    inc = load(G1 + "01a_ad_incrementality/out/criteo/a_incrementality.json")
    at = load(G2 + "02a_attribution_metric_validation/out/attribution_vs_experiment.json")
    out = {"users": inc["n"]}
    for key in ("visit", "conversion"):
        itt = inc[key]["itt"]
        out[key] = {
            "control_rate": r(itt["control_mean"], 6), "ad_rate": r(itt["control_mean"] + itt["est"], 6),
            "relative_lift": r(itt["relative_lift"]), "credited": int(round(at[key]["attributed"])),
            "caused": int(round(at[key]["incremental"])), "caused_ci": int(round(1.96 * itt["se"] * at["n_treated"])),
            "ratio": r(at[key]["attributed_over_incremental"])}
    return out


def segments():
    p = load(G1 + "01b_bayesian_segment_effects/out/part2_segments.json")
    p.update(load(G1 + "01b_bayesian_segment_effects/out/part2_segments_rerun.json"))
    out = []
    for k in sorted(p, key=int):
        s = p[k]["seg"]
        out.append({"sample": int(k) + 1, "rmse": {m: r(100 * p[k]["rmse"][m]) for m in ("nopool", "bayes", "cpool")},
                    "bench": [r(100 * v, 3) for v in s["bench"]], "nopool": [r(100 * v, 3) for v in s["nopool"]],
                    "bayes": [r(100 * v, 3) for v in s["bayes"]]})
    return out


def credit():
    m = load(G2 + "02b_multi_touch_attribution/out/mta.json")
    rules = {k: {b: r(100 * v, 2) for b, v in m["credit_by_recency_bucket"][k].items()} for k in ("cr_last", "cr_decay", "cr_linear", "cr_first")}
    bd = load(G2 + "02d_attribution_and_bidding/out/bidding.json")["budgets"]
    budgets = {k: {"overlap": r(100 * bd[k]["spend_overlap"], 3),
                   "loss": {rule: [r(100 * v, 3) for v in bd[k]["cross_rule_loss"][rule]] for rule in ("cr_last", "cr_decay")}}
               for k in ("0.25", "0.5", "0.75")}
    return {"rules": rules, "budgets": budgets, "paths": m["paths"], "multi_touch_conversions": m["multi_touch_test_conversions"],
            "zero_credit_last_touch": r(100 * m["share_touches_zero_credit_last_touch"], 1)}


def mmm():
    S = G2 + "02c_marketing_mix_modeling/out/"
    det = [x for x in rows(S + "detectability.csv") if x["sim"] == "brand_shapes"]
    idx = {(x["org"], x["channel"]): float(x["index"]) for x in det if x["freq"] == "D"}
    rec = [x for x in rows(S + "mmm_pooled_recovery_daily.csv") if x["sim"] == "brand_shapes" and x["single_converged"] == "True"]
    pts = [{"index": r(idx[(x["org"], x["channel"])], 3), "error": r(100 * abs(float(x["single"]) - float(x["true"])) / float(x["true"]), 2),
            "channel": x["channel"]} for x in rec]
    t1 = load(S + "detectability.json")["tests"]["T1"]
    share = {}
    for f in ("W", "D"):
        v = [float(x["index"]) for x in det if x["freq"] == f]
        share[f] = {"share": r(100 * sum(u >= 2 for u in v) / len(v), 1), "n": len(v)}
    return {"points": pts, "median_below": r(100 * t1["index_below_2"]["median_err"], 1), "median_above": r(100 * t1["index_2_or_more"]["median_err"], 1),
            "share": share}


def sizing():
    eff = load(G1 + "01c_sql_metric_readout/out/readout.json")["effects"]
    n = lambda p0, l: Z_POWER ** 2 * (p0 * (1 - p0) + p0 * (1 + l) * (1 - p0 * (1 + l))) / (p0 * l) ** 2
    lifts = [5, 10, 25, 50]
    users = {k: [int(round(n(eff[k]["control_rate"], l / 100))) for l in lifts] for k in ("visit", "conversion")}
    cov = load(G3 + "03a_lift_study_sizing/out/covariate_adjustment.json")["required_n_one_point_lift"]
    tab = rows(G3 + "03b_geo_experiment_design/out/design_summary.csv")
    est = {"CR: year-over-year difference": "yoy", "CR: ANCOVA (CUPED)": "adjusted", "MP: pair ANCOVA": "pairs",
           "CR: volume-weighted ANCOVA": "vw"}
    grid = {v: {} for v in est.values()}
    for x in tab:
        if x["estimator"] in est and x["mde_80_pct"]:
            grid[est[x["estimator"]]][f'{x["metros"]}|{x["test_months"]}'] = r(x["mde_80_pct"], 1)
    return {"lifts": lifts, "users": users, "control": {k: r(eff[k]["control_rate"], 6) for k in ("visit", "conversion")},
            "one_point": {k: int(round(v)) for k, v in cov.items()}, "geo": grid, "metros": [20, 50, 100, 150], "months": [1, 2, 3]}


def customers():
    s = load("04_customer_metrics_retention/out/12_ltv_segments.json")
    b = s["burnin3_contamination"]; c = s["cohorts_new_accounts"]
    cohorts = [{"month": m, "size": c["size"][m], "rates": [None if c["repeat_rate"][m].get(str(k)) is None else r(100 * c["repeat_rate"][m][str(k)], 2)
                                                          for k in range(1, 12)]} for m in c["repeat_rate"]]
    return {"labeled_new": b["apparent_new"], "bought_before": b["bought_in_prior_12m"], "cohorts": cohorts}


def study01():
    inc = load(G1 + "01a_ad_incrementality/out/criteo/a_incrementality.json")
    tg = load(G1 + "01a_ad_incrementality/out/criteo/c_targeting.json")
    eff = {k: {"itt": [r(100 * inc[k]["itt"]["est"]), r(196 * inc[k]["itt"]["se"])],
               "adj": [r(100 * inc[k]["aipw_linear"]["est"]), r(196 * inc[k]["aipw_linear"]["se"])]} for k in ("visit", "conversion")}
    dec = [{"d": x["decile"], "pred": r(100 * x["predicted"], 3), "real": r(100 * x["realized"], 3), "ci": r(196 * x["se"], 3)} for x in tg["calibration_selected"]]
    names = {"response": "Response model", "t_learner": "T-learner (selected)", "x_learner": "X-learner", "dr_learner": "DR-learner",
             "causal_forest": "Causal forest", "random": "Random order"}
    qini = [{"model": k, "label": names[k], "qini": r(1e4 * v["qini"], 3), "lo": r(1e4 * v["qini_ci"][0], 3), "hi": r(1e4 * v["qini_ci"][1], 3),
             "top20": r(100 * v["share_incremental_top20"], 1)} for k, v in tg["test"].items() if k in names]
    ro = load(G1 + "01c_sql_metric_readout/out/readout.json")
    checks = [{"name": k.split("_", 1)[1].replace("_", " "), "value": v} for k, v in ro["checks"].items()]
    rec = [{"metric": x["metric"], "kind": x["kind"], "sql": x["sql"], "python": x["python"], "diff": x["abs_diff"], "agree": x["agree"]} for x in ro["reconciliation"]]
    pr = load(G1 + "01d_private_segment_effects/out/a_private_summary.json")
    al = load(G1 + "01d_private_segment_effects/out/c_allocation.json")
    eps = [{"eps": k, "nopool": r(100 * v["rmse_nopool"], 3), "ml": r(100 * v["rmse_ml"], 3), "better": v.get("ml_better_reps")} for k, v in pr["by_eps"].items()]
    alloc = {k: {"share": {m: r(100 * v, 2) for m, v in al[k]["mean_share"].items()}, "random": r(100 * al[k]["random"], 1),
                 "ml_gt_response": al[k]["ml_gt_response"], "nopool_gt_response": al[k]["nopool_gt_response"], "ml_ge_nopool": al[k]["ml_ge_nopool"]}
             for k in ("10", "20", "30")}
    return {"effects": eff, "deciles": dec, "overall": r(100 * tg["test_overall_itt"]["est"], 3), "qini": qini,
            "checks": checks, "rows": ro["checks"]["c1_rows"], "reconciliation": rec,
            "eps": eps, "baseline": r(100 * pr["nonprivate_nopool_rmse"], 3), "alloc": alloc}


def study02():
    at = load(G2 + "02a_attribution_metric_validation/out/attribution_vs_experiment.json")["per_exposed_user_visit_effect"]
    inc = load(G1 + "01a_ad_incrementality/out/criteo/a_incrementality.json")
    # point estimates rounded once to one decimal, as displayed (25.549 must not become 25.55 and then 25.6)
    est = [{"label": "Experiment, unadjusted", "group": "exp", "v": r(100 * inc["cace_visit_unadjusted"]["est"], 1), "ci": r(196 * inc["cace_visit_unadjusted"]["se"], 2)},
           {"label": "Experiment, adjusted", "group": "exp", "v": r(100 * inc["cace_visit_adjusted"]["est"], 1), "ci": r(196 * inc["cace_visit_adjusted"]["se"], 2)},
           {"label": "Exposed vs. unexposed", "group": "obs", "v": r(100 * at["naive"], 1), "ci": r(196 * at["naive_se"], 2)},
           {"label": "Regression adjustment", "group": "obs", "v": r(100 * at["ols_adjusted"], 1), "ci": r(196 * at["ols_se"], 2)},
           {"label": "Double machine learning", "group": "obs", "v": r(100 * at["dml"], 1), "ci": r(196 * at["dml_se"], 2)}]
    m = load(G2 + "02b_multi_touch_attribution/out/mta.json")
    clicked = {k: r(100 * m["credit_on_clicked_touches"][k], 2) for k in ("cr_last", "cr_decay", "cr_linear", "cr_first")}
    S = G2 + "02c_marketing_mix_modeling/out/"
    rec, hold = {}, {}
    for f, suf in (("W", ""), ("D", "_daily")):
        rows_ = [x for x in rows(S + f"mmm_recovery{suf}.csv") if x["converged"] == "True"]
        sm = load(S + f"mmm_summary{suf}.json")
        rec[f] = {"points": [{"true": r(x["true"], 3), "est": r(x["est"], 3), "lo": r(x["lo"], 3), "hi": r(x["hi"], 3)} for x in rows_],
                  "spearman": r(sm["recovery"]["spearman"], 2), "coverage": r(100 * sm["recovery"]["coverage90"], 0), "median_err": r(100 * sm["recovery"]["median_abs_rel_err"], 0)}
        hold[f] = {"wmape": {k: r(100 * v, 1) for k, v in sm["wmape_median"].items()}, "diff": r(sm["diff_mean"], 3), "diff_ci": [r(v, 3) for v in sm["diff_ci"]],
                   "brands": int(sm["converged"]), "better": int(sm["mmm_better_than_b0"])}
    bd = load(G2 + "02d_attribution_and_bidding/out/bidding.json")["budgets"]
    comp = {k: {rule: {c: r(100 * v, 2) for c, v in bd[k]["composition"][rule].items()} for rule in ("cr_last", "cr_decay")} for k in bd}
    all_spend = {c: r(100 * v, 2) for c, v in load(G2 + "02d_attribution_and_bidding/out/bidding.json")["all_test_spend_composition"].items()}
    return {"exposure": est, "clicked": clicked, "share_clicked": r(100 * m["share_touches_clicked"], 1),
            "multi_touch_share": r(100 * m["share_conv_multi_touch"], 1), "recovery": rec, "holdout": hold, "composition": comp, "all_spend": all_spend}


def study03():
    d = load(G3 + "03a_lift_study_sizing/out/lift_study_sizing.json")
    by = d["by_n"]; ns = sorted(by, key=int)
    power = {"n": [int(n) for n in ns], "studies": d["studies_per_n"],
             **{k: [r(100 * by[n][k], 2) for n in ns] for k in ("power_z", "bayes_detect", "aa_false_positive_z", "aa_false_positive_bayes")}}
    cv = load(G3 + "03a_lift_study_sizing/out/covariate_adjustment.json")["by_n"]; cn = sorted(cv, key=int)
    cov = {"n": [int(n) for n in cn], "mde": {k: [r(100 * cv[n][k]["mde80"], 3) for n in cn] for k in ("D", "L", "M")},
           "ratio": {k: [[r(cv[n][k]["variance_ratio_to_D"], 3)] + [r(v, 3) for v in cv[n][k]["variance_ratio_ci"]] for n in cn] for k in ("L", "M")}}
    tab = rows(G3 + "03b_geo_experiment_design/out/design_summary.csv")
    vw = {f'{x["metros"]}|{x["test_months"]}': [r(100 * float(x["false_positive_rate"]), 2), int(x["draws"])] for x in tab if x["estimator"] == "CR: volume-weighted ANCOVA"}
    ri = {x["metros"]: {"ri": r(100 * float(x["false_positive_rate"]), 2), "ri_draws": int(x["draws"]), "t": r(100 * float(x["false_positive_rate_t_test"]), 2),
                        "mde_ri": r(x["mde_80_pct"], 1), "mde_t": r(x["mde_80_pct_t_test"], 1)}
          for x in rows(G3 + "03b_geo_experiment_design/out/randomization_inference_check.csv") if x["estimator"] == "CR: volume-weighted ANCOVA"}
    byh = rows(G3 + "03c_hierarchical_forecasting/reports/tables/inventory_ets_by_horizon.csv")
    methods = ["base", "bu", "mint_shrink", "ols", "wls_struct", "td"]
    hz = {lv: {m: [r(x["rel_to_no_change"], 4) for x in sorted([y for y in byh if y["level"] == lv and y["method"] == m], key=lambda y: int(y["h"]))] for m in methods}
          for lv in ("US", "division", "state", "metro")}
    head = rows(G3 + "03c_hierarchical_forecasting/reports/tables/inventory_ets_headline.csv")
    gap = {x["level"]: r(100 * float(x["incoherence_mean"]), 2) for x in head if x["method"] == "base" and x["incoherence_mean"] and x["level"] != "metro"}
    nodes = {x["level"]: int(x["n_nodes"]) for x in head if x["method"] == "base"}
    return {"power": power, "cov": cov, "vw_fp": vw, "ri": ri, "horizon": hz, "gap": gap, "nodes": nodes}


def study04():
    s = load("04_customer_metrics_retention/out/12_ltv_segments.json"); e = load("04_customer_metrics_retention/out/14_ltv_extension.json")
    segs = [{"seg": x["segment"], "acc": r(100 * x["share_accounts"], 2), "sales": r(100 * x["share_next6m_sales_existing"], 2), "n": x["n"],
             "mean": r(x["mean_next6m_sales"], 0), "lo": r(x["mean_ci_boot"][0], 0), "hi": r(x["mean_ci_boot"][1], 0)} for x in s["rule_segments"]]
    E2 = e["E2"]
    auc = {"model": [r(E2["auc_model"], 3)] + [r(v, 3) for v in E2["auc_model_ci"]], "recency": [r(E2["auc_recency"], 3)] + [r(v, 3) for v in E2["auc_recency_ci"]],
           "n": E2["n_high_value"], "terciles": [{"t": x["tercile"], "rate": r(100 * x["repurchase_rate"], 1), "lo": r(100 * x["ci"][0], 1), "hi": r(100 * x["ci"][1], 1), "n": x["n"]} for x in E2["by_tercile"]]}
    ev6, ev12 = s["eval"], e["E1"]["eval"]
    rank = {"6": {"label": "6 months from 2011-06-01", "n": s["n_test"], "model": [r(ev6["BGNBD_GG"]["spearman"], 3)] + [r(v, 3) for v in ev6["BGNBD_GG"]["spearman_ci"]],
                  "rule": [r(ev6["P0_last6m"]["spearman"], 3)] + [r(v, 3) for v in ev6["P0_last6m"]["spearman_ci"]]},
            "12": {"label": "12 months from 2010-12-01", "n": e["E1"]["n_accounts"], "model": [r(ev12["bgnbd_gg"]["spearman"], 3)] + [r(v, 3) for v in ev12["bgnbd_gg"]["spearman_ci"]],
                   "rule": [r(ev12["past_sales"]["spearman"], 3)] + [r(v, 3) for v in ev12["past_sales"]["spearman_ci"]]}}
    cal = {k: [[r(x["pred"], 1), r(x["actual"], 1)] for x in s[f"calib_{k}"]] for k in ("BGNBD_GG", "ML_lgbm_tweedie")}
    return {"segments": segs, "auc": auc, "rank": rank, "calibration": cal}


def added_studies():
    """Studies 03d (surrogate outcome), 02f (delayed conversions) and 02e (off-policy evaluation)."""
    sa = load("03_planning_a_test/03d_surrogate_outcome/out/surrogate.json"); fa = load("03_planning_a_test/03d_surrogate_outcome/out/followup.json")
    e = sa["experiment"]["estimates"]
    names = {"direct": ("direct", "Direct"), "visit_x_fixed_rate": ("fixed", "Visit effect × fixed rate"),
             "surrogate_index": ("surrogate", "Surrogate index"), "surrogate_index_both_arms": ("both", "Surrogate index, both arms")}
    unadj = [{"key": names[k][0], "label": names[k][1], "v": r(100 * e[k]["estimate"], 4), "lo": r(100 * e[k]["ci95"][0], 4),
              "hi": r(100 * e[k]["ci95"][1], 4), "share": r(e[k].get("share_of_direct", 1.0), 3)} for k in names]
    A = fa["aipw_estimated_assignment"]
    adj = [{"key": "direct", "label": "Direct", "v": r(100 * A["direct"], 4), "lo": r(100 * (A["direct"] - 1.96 * A["direct_se"]), 4),
            "hi": r(100 * (A["direct"] + 1.96 * A["direct_se"]), 4), "share": 1.0},
           {"key": "surrogate", "label": "Surrogate index", "v": r(100 * A["surrogate_index"], 4), "lo": r(100 * (A["surrogate_index"] - 1.96 * A["surrogate_se"]), 4),
            "hi": r(100 * (A["surrogate_index"] + 1.96 * A["surrogate_se"]), 4), "share": r(A["share_of_direct"], 3)}]
    t = sa["test_size"]
    size = {"n": t["grid_n"], "direct": [r(100 * v, 5) for v in t["rmse_direct"]], "surr": [r(100 * v, 5) for v in t["rmse_surrogate"]],
            "cross": round(t["crossover_n_per_arm"]), "pts": [{"n": int(k), "direct": r(100 * v["direct"], 5), "surr": r(100 * v["surrogate_index"], 5)} for k, v in t["resampling"].items()]}
    db = load("02_without_an_experiment/02f_delayed_conversions/out/delay.json"); f1 = load("02_without_an_experiment/02f_delayed_conversions/out/followup.json")
    f2 = load("02_without_an_experiment/02f_delayed_conversions/out/followup2.json")
    labels = [("naive_lightgbm", "LightGBM, labels seen"), ("naive_network", "Network, labels seen"), ("delay_network", "Delayed feedback, exponential"),
              ("weibull_network", "Delayed feedback, Weibull"), ("delay_sequence_network", "Exponential + GRU over history"), ("oracle_lightgbm", "LightGBM, 30-day labels")]
    cut = {}
    for T, c in db["cutoffs"].items():
        rows_ = []
        for k, lab in labels:
            m = f2["cutoffs"][T]["models_p_times_F30"]["weibull"] if k == "weibull_network" else c["models"][k]
            cr = m["calibration_ratio"]
            rows_.append({"key": k, "label": lab, "v": r(cr["estimate"], 4), "lo": r(cr["ci95"][0], 4), "hi": r(cr["ci95"][1], 4)})
        cut[T] = {"beyond": r(f1["share_of_30_day_conversions_with_delay_longer_than"][T], 4), "rows": rows_}
    oc = load("02_without_an_experiment/02e_off_policy_evaluation/out/ope_v2.json")
    acc = load("02_without_an_experiment/02e_off_policy_evaluation/out/ope_v2_accuracy.json")["settings"]
    pol = {"all": "All users", "response_20": "Response 20%", "uplift_20": "Uplift 20%", "random_20": "Random 20%"}
    est_names = [("naive", "Unweighted comparison"), ("dm", "Direct method"), ("ips_known", "IPS, logged propensity"), ("ips_estimated", "IPS, estimated propensity"),
                 ("snips", "SNIPS, estimated propensity"), ("dr_known", "DR, logged propensity"), ("dr", "DR, estimated propensity")]
    logs = rows("02_without_an_experiment/02e_off_policy_evaluation/out/ope_v2_logs.csv")
    import numpy as np
    est = {}
    for st in ("moderate", "strong"):
        est[st] = {}
        for pk in pol:
            lst = []
            for k, lab in est_names:
                x = np.array([1000 * float(q["estimate"]) for q in logs if q["setting"] == st and q["policy"] == pk and q["estimator"] == k])
                cov = oc["settings"][st]["summary"][pk][k].get("coverage95")
                lst.append({"key": k, "label": lab, "mean": r(float(x.mean()), 3), "p02": r(float(np.quantile(x, 0.025)), 3),
                            "p98": r(float(np.quantile(x, 0.975)), 3), "cov": None if cov is None else r(cov, 3),
                            "mae": r(acc[st][pk][k]["mean_absolute_error"], 3)})
            est[st][pk] = lst
    truth = {pk: {"v": r(oc["truth_log_part"][pk]["aipw_r"], 3), "se": r(oc["truth_log_part"][pk]["aipw_r_se"], 3),
             "u": r(oc["truth_log_part"][pk]["unadjusted"], 3)} for pk in pol}
    rows_n = {st: round(oc["settings"][st]["log_rows_mean"]) for st in ("moderate", "strong")}
    return {"s03d": {"rows": {"unadjusted": unadj, "adjusted": adj}, "size": size}, "s02f": {"cut": cut},
            "s02e": {"policies": pol, "truth": truth, "est": est, "rows": rows_n}}


if __name__ == "__main__":
    data = {"experiment": experiment(), "segments": segments(), "credit": credit(), "mmm": mmm(), "sizing": sizing(), "customers": customers(),
            "s01": study01(), "s02": study02(), "s03": study03(), "s04": study04(), **added_studies()}
    out = Path(__file__).parent / "data.js"
    out.write_text("// Generated by docs/build_data.py from the result files of the repository. Do not edit by hand.\nwindow.DATA = "
                   + json.dumps(data, separators=(",", ":")) + ";\n")
    print("wrote", out.relative_to(ROOT), f"{out.stat().st_size / 1024:.0f} KB")
