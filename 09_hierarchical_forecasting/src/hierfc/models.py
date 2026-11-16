"""Base forecasts (statsforecast AutoETS / AutoARIMA, one model per node) and the two naive baselines."""
from __future__ import annotations
import numpy as np
import pandas as pd


def _ds(months: np.ndarray) -> pd.DatetimeIndex:
    return pd.to_datetime([f"{m // 12:04d}-{m % 12 + 1:02d}-01" for m in months])


def base_forecasts(Y: np.ndarray, months: np.ndarray, h: int, kind: str = "ets", n_jobs: int = 1):
    """Y: n x T training values (one row per node). Returns (y_hat n x h, fitted n x T).
    Fitted values are the in-sample one-step predictions used for MinT residuals."""
    from statsforecast import StatsForecast
    from statsforecast.models import AutoARIMA, AutoETS
    n, T = Y.shape
    model = {"ets": AutoETS(season_length=12), "arima": AutoARIMA(season_length=12)}[kind]
    col = type(model).__name__
    ids = np.repeat(np.arange(n), T)
    df = pd.DataFrame({"unique_id": ids, "ds": np.tile(_ds(months), n), "y": Y.ravel()})
    sf = StatsForecast(models=[model], freq="MS", n_jobs=n_jobs)
    fc = sf.forecast(df=df, h=h, fitted=True)
    fv = sf.forecast_fitted_values()
    fc = fc.sort_values(["unique_id", "ds"])
    fv = fv.sort_values(["unique_id", "ds"])
    y_hat = fc[col].to_numpy(float).reshape(n, h)
    fitted = fv[col].to_numpy(float).reshape(n, T)
    if not (np.array_equal(fc.unique_id.to_numpy().reshape(n, h)[:, 0], np.arange(n))
            and np.array_equal(fv.unique_id.to_numpy().reshape(n, T)[:, 0], np.arange(n))):
        raise RuntimeError("statsforecast output order does not match the node order")
    return y_hat, fitted


def naive(Y: np.ndarray, h: int) -> np.ndarray:
    """No change: every horizon gets the last training value."""
    return np.repeat(Y[:, -1:], h, axis=1)


def seasonal_naive(Y: np.ndarray, h: int, season: int = 12) -> np.ndarray:
    """Same month one year earlier (h <= season)."""
    if h > season:
        raise ValueError("h must be <= season")
    T = Y.shape[1]
    return Y[:, T - season: T - season + h]
