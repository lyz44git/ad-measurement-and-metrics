"""One-origin cross-check of own reconciliation vs Nixtla on the real 873-node hierarchy (inventory, AutoETS)."""
import sys, warnings, json
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hierfc import backtest, data, models, reconcile as rc
from hierfc.paths import TABLES
from hierarchicalforecast.methods import MinTrace
if __name__ == "__main__":
    warnings.simplefilter("ignore")
    src = data.load_source("inventory"); _, hier = backtest.setup(src)
    a = backtest.FIRST_ORIGIN
    months, L, Y, _, _ = backtest.origin_inputs(src, hier, a)
    y_hat, fitted = models.base_forecasts(Y, months, 12, "ets", n_jobs=8)
    S = hier.S; out = {}
    mine = {"ols": rc.g_mint(S, rc.w_ols(S)), "wls_struct": rc.g_mint(S, rc.w_wls_struct(S)),
            "mint_shrink": rc.g_mint(S, rc.shrink_cov((Y - fitted).T)[0])}
    for k, G in mine.items():
        P, _ = MinTrace(method=k)._get_PW_matrices(S=S, y_hat=y_hat, y_insample=Y, y_hat_insample=fitted)
        a1, a2 = S @ G @ y_hat, S @ P @ y_hat
        out[k] = {"max_rel_diff": float(np.max(np.abs(a1 - a2) / np.abs(a2).clip(1))), "max_abs_diff_listings": float(np.max(np.abs(a1 - a2)))}
    out = {"origin": data.ym_str(a), "nodes": int(hier.n), "methods": out}
    (TABLES / "xcheck_nixtla_real_inventory_ets.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
