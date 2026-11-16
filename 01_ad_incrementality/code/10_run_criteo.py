"""Criteo Uplift v2.1: incrementality, CATE learners, held-out targeting test.

Plan: docs/10_plan_criteo_incrementality_uplift.md (hashed in logs/10_plan_hash.txt before this ran).
Usage: python code/10_run_criteo.py [--config code/10_config.json]
Reads data_raw only; writes out/criteo/ and models/.
"""
import argparse, json, time, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
import upliftkit as uk  # noqa: E402


def log(msg, t0=[time.time()]):
    print(f"[{time.time() - t0[0]:7.0f}s] {msg}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "code" / "10_config.json"))
    cfg = json.loads(Path(ap.parse_args().config).read_text())
    out = ROOT / "out" / "criteo"; out.mkdir(parents=True, exist_ok=True)
    (ROOT / "models").mkdir(exist_ok=True)

    dt = {f: "float32" for f in uk.FEATURES} | {c: "int8" for c in ["treatment", "conversion", "visit", "exposure"]}
    df = pd.read_csv(ROOT / cfg["data"], dtype=dt)
    log(f"loaded {len(df):,} rows")
    X = df[uk.FEATURES].to_numpy(np.float32)
    t = df["treatment"].to_numpy(); visit = df["visit"].to_numpy(); conv = df["conversion"].to_numpy()
    expo = df["exposure"].to_numpy(); del df
    n = len(t)

    # ---------------- Stage A
    A = {"n": n, "treated_share": float(t.mean()),
         "exposure_in_control": float(expo[t == 0].mean())}
    X64 = X.astype(np.float64)
    for name, y in (("visit", visit), ("conversion", conv)):
        A[name] = {"itt": uk.itt(y.astype(float), t), "aipw_linear": uk.aipw_linear(y.astype(float), t, X64)}
    A["smd"] = dict(zip(uk.FEATURES, map(float, uk.smd(X64, t))))
    A["cace_visit_unadjusted"] = uk.cace(A["visit"]["itt"]["est"], A["visit"]["itt"]["se"], expo, t)
    A["cace_visit_adjusted"] = uk.cace(A["visit"]["aipw_linear"]["est"], A["visit"]["aipw_linear"]["se"], expo, t)
    del X64

    rng = np.random.default_rng(cfg["seed"])
    u = rng.random(n)
    tr, va, te = u < 0.5, (u >= 0.5) & (u < 0.7), u >= 0.7
    A["split"] = {"train": int(tr.sum()), "validation": int(va.sum()), "test": int(te.sum())}

    from sklearn.metrics import roc_auc_score
    p = uk._clf(cfg["lgbm"]).fit(X[tr], t[tr]).predict_proba(X[va])[:, 1]
    A["assignment_auc_validation"] = float(roc_auc_score(t[va], p))
    (out / "a_incrementality.json").write_text(json.dumps(A, indent=2))
    log(f"stage A done: visit ITT {A['visit']['itt']['est']:.5f}, adjusted {A['visit']['aipw_linear']['est']:.5f}, "
        f"assignment AUC {A['assignment_auc_validation']:.4f}")

    # ---------------- Stage B
    Xtr, ttr, ytr = X[tr], t[tr], visit[tr]
    L = {}
    L["response"] = uk.fit_response(Xtr, ytr, cfg["lgbm"]); log("response fitted")
    L["t_learner"], m1, m0 = uk.fit_t_learner(Xtr, ttr, ytr, cfg["lgbm"], return_models=True); log("T fitted")
    L["x_learner"] = uk.fit_x_learner(Xtr, ttr, ytr, cfg["lgbm"]); log("X fitted")
    L["dr_learner"] = uk.fit_dr_learner(Xtr, ttr, ytr, cfg["lgbm"], seed=cfg["seed"]); log("DR fitted")
    try:
        L["causal_forest"] = uk.fit_causal_forest(Xtr, ttr, ytr, cfg["causal_forest"], seed=cfg["seed"]); log("CF fitted")
    except Exception as e:  # recorded as a deviation, not hidden
        log(f"causal forest failed: {e!r}")
    m1.booster_.save_model(str(ROOT / "models" / "t_learner_m1.txt"))
    m0.booster_.save_model(str(ROOT / "models" / "t_learner_m0.txt"))

    # ---------------- Stage C
    sv = {k: f(X[va]) for k, f in L.items()}
    val = uk.evaluate(sv, t[va], visit[va], B=cfg["bootstrap"], seed=cfg["seed"], baseline="response")
    causal = [k for k in val if k != "response"]
    selected = max(causal, key=lambda k: val[k]["qini"])
    log(f"validation Qini: { {k: round(v['qini'] * 1e4, 3) for k, v in val.items()} } -> selected {selected}")
    st = {k: f(X[te]) for k, f in L.items()}
    test = uk.evaluate(st, t[te], visit[te], B=cfg["bootstrap"], seed=cfg["seed"] + 1, baseline="response")
    rnd = np.random.default_rng(cfg["seed"] + 2).random(int(te.sum()))
    test["random"] = uk.evaluate({"random": rnd}, t[te], visit[te], B=cfg["bootstrap"], seed=cfg["seed"] + 1)["random"]
    cal = uk.calibration(st[selected], t[te], visit[te].astype(float))
    overall = uk.itt(visit[te].astype(float), t[te])
    C = {"selected_on_validation": selected, "validation": val, "test": test,
         "test_overall_itt": overall, "calibration_selected": cal}
    (out / "c_targeting.json").write_text(json.dumps(C, indent=2))
    pd.DataFrame(cal).to_csv(out / "c_calibration_selected.csv", index=False)
    # decile thresholds of the T-learner on validation, for the scoring service
    thr = np.quantile(sv["t_learner"], np.linspace(0.9, 0.1, 9)).tolist()
    (ROOT / "models" / "service_reference.json").write_text(json.dumps(
        {"features": uk.FEATURES, "decile_thresholds_desc": thr, "selected_learner": selected,
         "served_learner": "t_learner", "config_seed": cfg["seed"]}, indent=2))
    np.save(ROOT / "models" / "parity_X.npy", X[te][:2000]); np.save(ROOT / "models" / "parity_score.npy", st["t_learner"][:2000])
    log("stage C done; all outputs written")


if __name__ == "__main__":
    main()
