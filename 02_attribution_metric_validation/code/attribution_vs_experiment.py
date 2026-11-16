"""Exposure-attributed outcomes vs experimental incrementality on the Criteo Uplift v2.1 experiment.

Usage: python code/attribution_vs_experiment.py [path to criteo-research-uplift-v2.1.csv.gz]
Reads the regression-adjusted benchmark from study 01's output; writes out/attribution_vs_experiment.json.
"""
import sys, json
from pathlib import Path
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier as HGB
from sklearn.model_selection import KFold

ROOT = Path(__file__).resolve().parents[1]
STUDY01 = ROOT.parent / "01_ad_incrementality"
SEED = 20261115


def attribution_summary(n0, n1, exposed1, y0, y1, attributed):
    """Compare outcomes credited to the ad (outcomes of exposed users) with the experiment's incremental outcomes.

    n0, n1: users in the control and ad arms; exposed1: exposed users in the ad arm; y0, y1: outcome totals by arm;
    attributed: outcome total among exposed users in the ad arm.
    """
    itt = y1 / n1 - y0 / n0
    incremental = itt * n1
    return {"itt": itt, "incremental": incremental, "attributed": int(attributed),
            "share_of_attributed_incremental": incremental / attributed,
            "attributed_over_incremental": attributed / incremental, "cace": itt / (exposed1 / n1),
            "treated_total": int(y1), "share_of_treated_outcomes_attributed": attributed / y1}


def naive_difference(Y, D):
    """Exposed-minus-unexposed difference in mean outcome, with an unequal-variance standard error."""
    est = Y[D == 1].mean() - Y[D == 0].mean()
    se = np.sqrt(Y[D == 1].var() / (D == 1).sum() + Y[D == 0].var() / (D == 0).sum())
    return float(est), float(se)


def ols_adjusted(Y, D, X):
    """Coefficient on D from OLS of Y on D and standardized covariates, with an HC1 standard error."""
    Z = np.column_stack([np.ones(len(D)), D, (X - X.mean(0)) / X.std(0)])
    XtX = Z.T @ Z; beta = np.linalg.solve(XtX, Z.T @ Y); u = Y - Z @ beta
    meat = (Z * (u ** 2)[:, None]).T @ Z; inv = np.linalg.inv(XtX)
    V = inv @ meat @ inv * len(D) / (len(D) - Z.shape[1])
    return float(beta[1]), float(np.sqrt(V[1, 1]))


def dml_plr(Y, D, X, seed=SEED, max_iter=200):
    """Cross-fitted partially linear (double machine learning) estimate of the effect of D on Y.

    Two folds; gradient-boosted classifiers for E[D | X] and E[Y | X]; residual-on-residual regression.
    """
    rD = np.zeros(len(D)); rY = np.zeros(len(D))
    for tr, te in KFold(2, shuffle=True, random_state=seed).split(X):
        rD[te] = D[te] - HGB(max_iter=max_iter, learning_rate=0.1, random_state=0).fit(X[tr], D[tr]).predict_proba(X[te])[:, 1]
        rY[te] = Y[te] - HGB(max_iter=max_iter, learning_rate=0.1, random_state=0).fit(X[tr], Y[tr]).predict_proba(X[te])[:, 1]
    est = float((rD * rY).sum() / (rD ** 2).sum()); psi = rD * (rY - est * rD)
    se = float(np.sqrt((psi ** 2).mean() / (rD ** 2).mean() ** 2 / len(D)))
    return est, se


def main(src):
    import duckdb
    con = duckdb.connect()
    con.execute(f"create table t as select * from read_csv_auto('{src}')")
    a = con.execute("select treatment, count(*) n, sum(exposure) e, sum(visit) v, sum(conversion) c, sum(visit*exposure) ve, "
                    "sum(conversion*exposure) ce from t group by 1 order by 1").fetchall()
    (_, n0, e0, v0, c0, _, _), (_, n1, e1, v1, c1, ve1, ce1) = a
    res = {"n_control": n0, "n_treated": n1, "exposed_treated": int(e1), "exposure_share": e1 / n1, "exposed_control": int(e0)}
    res["visit"] = attribution_summary(n0, n1, e1, v0, v1, ve1)
    res["conversion"] = attribution_summary(n0, n1, e1, c0, c1, ce1)

    # per-exposed-user effect on visit among users in the ad arm
    d = con.execute("select exposure, visit, f0,f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11 from t where treatment=1").fetchnumpy()
    D = d["exposure"].astype(np.float64); Y = d["visit"].astype(np.float64)
    X = np.column_stack([d[f"f{i}"] for i in range(12)]).astype(np.float64)
    naive, se_naive = naive_difference(Y, D)
    ols, se_ols = ols_adjusted(Y, D, X)
    idx = np.random.default_rng(SEED).choice(len(D), 2_000_000, replace=False)
    dml, se_dml = dml_plr(Y[idx], D[idx], X[idx].astype(np.float32))
    cace = res["visit"]["cace"]
    cace_adj = json.loads((STUDY01 / "out" / "criteo" / "a_incrementality.json").read_text())["cace_visit_adjusted"]["est"]
    res["per_exposed_user_visit_effect"] = {
        "naive": naive, "naive_se": se_naive, "ols_adjusted": ols, "ols_se": se_ols,
        "dml": dml, "dml_se": se_dml, "dml_n": len(idx), "cace_unadjusted": cace, "cace_adjusted_study_01": cace_adj,
        "ratio_to_cace": {"naive": naive / cace, "ols": ols / cace, "dml": dml / cace},
        "visit_rate_exposed": float(Y[D == 1].mean()), "visit_rate_unexposed_treated": float(Y[D == 0].mean())}
    json.dump(res, open(ROOT / "out" / "attribution_vs_experiment.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    default = STUDY01 / "data_raw" / "criteo_uplift_v2.1" / "criteo-research-uplift-v2.1.csv.gz"
    main(sys.argv[1] if len(sys.argv) > 1 else str(default))
