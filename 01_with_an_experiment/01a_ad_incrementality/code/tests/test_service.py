"""Service checks. Skipped until code/10_run_criteo.py has written models/."""
import sys, time, json
from pathlib import Path
import numpy as np
import pytest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))
pytestmark = pytest.mark.skipif(not (ROOT / "models" / "service_reference.json").exists(), reason="models not built")


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from upliftkit.service import app
    return TestClient(app)


def recs(X):
    return [{f"f{i}": float(v) for i, v in enumerate(r)} for r in X]


def test_health(client):
    r = client.get("/health").json()
    assert r["status"] == "ok" and len(r["features"]) == 12


def test_api_matches_batch_scores(client):
    X = np.load(ROOT / "models" / "parity_X.npy"); ref = np.load(ROOT / "models" / "parity_score.npy")
    r = client.post("/score", json={"records": recs(X)}).json()
    assert r["n"] == len(X) and np.max(np.abs(np.array(r["uplift"]) - ref)) < 1e-9


def test_deciles_and_target_flag(client):
    X = np.load(ROOT / "models" / "parity_X.npy")
    r = client.post("/score", json={"records": recs(X), "target_top_deciles": 3}).json()
    d = np.array(r["decile"])
    assert d.min() >= 1 and d.max() <= 10 and (np.array(r["target"]) == (d <= 3)).all()
    u = np.array(r["uplift"])
    assert u[d == d.min()].min() >= u[d == d.max()].max()   # deciles are ordered by score


@pytest.mark.parametrize("bad", [
    {"records": []},
    {"records": [{"f0": 1.0}]},
    {"records": [{**{f"f{i}": 0.0 for i in range(12)}, "extra": 1}]},
    {"records": [{f"f{i}": 0.0 for i in range(12)}], "target_top_deciles": 11},
])
def test_schema_rejects_bad_input(client, bad):
    assert client.post("/score", json=bad).status_code == 422


def test_latency_benchmark(client):
    X = np.load(ROOT / "models" / "parity_X.npy")[:1000]; body = {"records": recs(X)}
    ts = []
    for _ in range(10):
        t0 = time.perf_counter(); client.post("/score", json=body); ts.append(time.perf_counter() - t0)
    (ROOT / "out" / "criteo" / "d_service_latency.json").write_text(json.dumps(
        {"batch_1000_ms_median": float(np.median(ts) * 1e3), "runs": 10}))
    assert np.median(ts) < 2.0
