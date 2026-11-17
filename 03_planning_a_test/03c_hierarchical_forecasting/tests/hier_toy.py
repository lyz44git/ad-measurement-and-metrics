"""Synthetic hierarchy shared by the tests."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hierfc import data  # noqa: E402

TOY_METROS = [("1", "Alpha, CA", "CA"), ("2", "Beta, CA", "CA"), ("3", "Gamma, OR", "OR"),
              ("4", "Delta, TX", "TX"), ("5", "Eps, TX", "TX"), ("6", "Zeta, OK", "OK"),
              ("7", "Eta, NY", "NY"), ("8", "Theta, NY", "NY"),
              ("9", "Late, NY", "NY")]          # starts late: never a member
N_MONTHS = 60                                   # 2018-03 .. 2023-02
TOY_ORIGINS = [data.ym(2021, 6), data.ym(2021, 7), data.ym(2021, 8)]


def make_toy_src(seed=0, gap_region="2", gap_month=data.ym(2021, 9)):
    """Synthetic source table shaped like data.load_source(): seasonal positive counts, a US row equal to the metros
    plus a positive remainder, one member with a single missing month after the first origin, one late starter."""
    rng = np.random.default_rng(seed)
    months = np.arange(data.START, data.START + N_MONTHS)
    rows, total = [], np.zeros(N_MONTHS)
    for k, (rid, name, st) in enumerate(TOY_METROS):
        base = 200 + 150 * k
        v = base * (1 + 0.2 * np.sin(2 * np.pi * (months % 12) / 12)) * np.exp(np.cumsum(rng.normal(0, 0.03, N_MONTHS)))
        v = np.round(v)
        total += v
        for mth, val in zip(months, v):
            if rid == "9" and mth < data.ym(2022, 1):
                continue
            if rid == gap_region and mth == gap_month:
                continue
            rows.append((rid, name, st, mth, val))
    us = np.round(total * 1.15)
    rows += [(data.US, "United States", "", mth, val) for mth, val in zip(months, us)]
    df = pd.DataFrame(rows, columns=["region", "name", "state", "valid_month", "value"])
    df["known_month"] = df.valid_month + 1
    return df[["region", "name", "state", "valid_month", "known_month", "value"]]


def cheap_base(Y, h):
    """Deterministic stand-in for a base model: drift forecast with one-step fitted values."""
    drift = (Y[:, -1] - Y[:, -13]) / 12
    y_hat = Y[:, -1:] + drift[:, None] * np.arange(1, h + 1)
    fitted = np.hstack([Y[:, :1], Y[:, :-1]])
    return y_hat, fitted
