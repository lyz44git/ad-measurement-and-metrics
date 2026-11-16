"""Exposure-attributed outcomes vs experimental incrementality on the Criteo Uplift v2.1 experiment.

Usage: python code/attribution_vs_experiment.py [path to criteo-research-uplift-v2.1.csv.gz]
Reads the regression-adjusted benchmark from study 01's output; writes out/attribution_vs_experiment.json.
"""
import sys, json
from pathlib import Path
import duckdb, numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier as HGB
from sklearn.model_selection import KFold
ROOT = Path(__file__).resolve().parents[1]
STUDY01 = ROOT.parent / "01_ad_incrementality"
SRC = sys.argv[1] if len(sys.argv) > 1 else str(STUDY01 / "data_raw" / "criteo_uplift_v2.1" / "criteo-research-uplift-v2.1.csv.gz")
con = duckdb.connect()
con.execute(f"create table t as select * from read_csv_auto('{SRC}')")
a = con.execute("select treatment, count(*) n, sum(exposure) e, sum(visit) v, sum(conversion) c, sum(visit*exposure) ve, sum(conversion*exposure) ce from t group by 1 order by 1").fetchall()
(_, n0, e0, v0, c0, _, _), (_, n1, e1, v1, c1, ve1, ce1) = a
res = {"n_control": n0, "n_treated": n1, "exposed_treated": int(e1), "exposure_share": e1 / n1, "exposed_control": int(e0)}
for name, y1, y0, att in (("visit", v1, v0, ve1), ("conversion", c1, c0, ce1)):
    itt = y1 / n1 - y0 / n0; inc = itt * n1
    res[name] = {"itt": itt, "incremental": inc, "attributed": int(att), "share_of_attributed_incremental": inc / att,
                 "attributed_over_incremental": att / inc, "cace": itt / (e1 / n1),
                 "treated_total": int(y1), "share_of_treated_outcomes_attributed": att / y1}
# per-exposed-user effect on visit among treated users
d = con.execute("select exposure, visit, f0,f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11 from t where treatment=1").fetchnumpy()
D = d["exposure"].astype(np.float64); Y = d["visit"].astype(np.float64)
X = np.column_stack([d[f"f{i}"] for i in range(12)]).astype(np.float64)
naive = Y[D == 1].mean() - Y[D == 0].mean()
se_naive = np.sqrt(Y[D == 1].var() / (D == 1).sum() + Y[D == 0].var() / (D == 0).sum())
Z = np.column_stack([np.ones(len(D)), D, (X - X.mean(0)) / X.std(0)])
XtX = Z.T @ Z; beta = np.linalg.solve(XtX, Z.T @ Y); u = Y - Z @ beta
meat = (Z * (u ** 2)[:, None]).T @ Z; inv = np.linalg.inv(XtX)
V = inv @ meat @ inv * len(D) / (len(D) - Z.shape[1])
ols, se_ols = float(beta[1]), float(np.sqrt(V[1, 1]))
rng = np.random.default_rng(20261115); idx = rng.choice(len(D), 2_000_000, replace=False)
Xs, Ds, Ys = X[idx].astype(np.float32), D[idx], Y[idx]; rD = np.zeros(len(idx)); rY = np.zeros(len(idx))
for tr, te in KFold(2, shuffle=True, random_state=20261115).split(Xs):
    rD[te] = Ds[te] - HGB(max_iter=200, learning_rate=0.1, random_state=0).fit(Xs[tr], Ds[tr]).predict_proba(Xs[te])[:, 1]
    rY[te] = Ys[te] - HGB(max_iter=200, learning_rate=0.1, random_state=0).fit(Xs[tr], Ys[tr]).predict_proba(Xs[te])[:, 1]
dml = float((rD * rY).sum() / (rD ** 2).sum()); psi = rD * (rY - dml * rD)
se_dml = float(np.sqrt((psi ** 2).mean() / (rD ** 2).mean() ** 2 / len(idx)))
cace = res["visit"]["cace"]
cace_adj = json.loads((STUDY01 / "out" / "criteo" / "a_incrementality.json").read_text())["cace_visit_adjusted"]["est"]
res["per_exposed_user_visit_effect"] = {"naive": float(naive), "naive_se": float(se_naive), "ols_adjusted": ols, "ols_se": se_ols,
    "dml": dml, "dml_se": se_dml, "dml_n": len(idx), "cace_unadjusted": cace, "cace_adjusted_study_01": cace_adj,
    "ratio_to_cace": {"naive": float(naive / cace), "ols": ols / cace, "dml": dml / cace},
    "visit_rate_exposed": float(Y[D == 1].mean()), "visit_rate_unexposed_treated": float(Y[D == 0].mean())}
json.dump(res, open(ROOT / "out" / "attribution_vs_experiment.json", "w"), indent=1); print(json.dumps(res, indent=1))
