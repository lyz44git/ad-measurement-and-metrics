"""Local FastAPI scoring service for the uplift model. Run: uvicorn upliftkit.service:app --port 8770

POST /score  {"records": [{"f0": ..., ..., "f11": ...}], "target_top_deciles": 2}
returns the predicted visit uplift, its validation decile (1 = highest) and a target flag.
Offline prototype: no authentication, no deployment.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import lightgbm as lgb
from fastapi import FastAPI
from pydantic import BaseModel, Field, ConfigDict

MODELS = Path(__file__).resolve().parents[2] / "models"
FEATURES = [f"f{i}" for i in range(12)]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")
    f0: float; f1: float; f2: float; f3: float; f4: float; f5: float
    f6: float; f7: float; f8: float; f9: float; f10: float; f11: float


class ScoreRequest(BaseModel):
    records: list[Record] = Field(min_length=1, max_length=10000)
    target_top_deciles: int = Field(default=2, ge=1, le=10)


class Scorer:
    def __init__(self, models: Path = MODELS):
        self.m1 = lgb.Booster(model_file=str(models / "t_learner_m1.txt"))
        self.m0 = lgb.Booster(model_file=str(models / "t_learner_m0.txt"))
        self.ref = json.loads((models / "service_reference.json").read_text())
        self.thr = np.array(self.ref["decile_thresholds_desc"])

    def score(self, X: np.ndarray):
        u = self.m1.predict(X) - self.m0.predict(X)
        decile = 1 + (u[:, None] < self.thr[None, :]).sum(1)
        return u, decile


app = FastAPI(title="upliftkit scoring (offline prototype)")
_scorer: Scorer | None = None


def scorer() -> Scorer:
    global _scorer
    if _scorer is None:
        _scorer = Scorer()
    return _scorer


@app.get("/health")
def health():
    s = scorer()
    return {"status": "ok", "served_learner": s.ref["served_learner"], "features": FEATURES}


@app.post("/score")
def score(req: ScoreRequest):
    X = np.array([[getattr(r, f) for f in FEATURES] for r in req.records], dtype=np.float64)
    u, d = scorer().score(X)
    return {"n": len(u), "uplift": u.tolist(), "decile": d.tolist(),
            "target": (d <= req.target_top_deciles).tolist()}
