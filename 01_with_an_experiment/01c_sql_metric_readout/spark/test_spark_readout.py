"""The four SQL files give the same cells on Spark and DuckDB for a small simulated file.

Skipped when PySpark or Java is not installed (the repository's test workflow does not install them).
"""
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("pyspark")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_spark_readout as sr  # noqa: E402


@pytest.fixture(scope="module")
def spark():
    import os
    if not (os.environ.get("JAVA_HOME") or shutil.which("java")):
        pytest.skip("no Java runtime")
    s = sr.spark_session(cores=2, memory="2g")
    yield s
    s.stop()


def test_same_cells_on_spark_and_duckdb(spark, tmp_path):
    import duckdb
    rng = np.random.default_rng(0)
    n = 5000
    d = pd.DataFrame({f"f{i}": np.round(rng.normal(size=n), 1) for i in range(12)})
    d["treatment"] = (rng.random(n) < 0.85).astype(int)
    d["exposure"] = d.treatment * (rng.random(n) < 0.05)
    d["visit"] = (rng.random(n) < 0.04 + 0.2 * d.exposure).astype(int)
    d["conversion"] = d.visit * (rng.random(n) < 0.1)
    d = pd.concat([d, d.iloc[:50]])                         # some duplicate rows for the duplicates check
    src = tmp_path / "users.csv"; d.to_csv(src, index=False)
    pq = tmp_path / "pq"
    sr.to_parquet(spark, src, pq, parts=4)
    spark.read.parquet(str(pq)).createOrReplaceTempView("users")
    con = duckdb.connect(); con.execute(f"CREATE VIEW users AS SELECT * FROM read_parquet('{pq}/*.parquet')")
    for name in sr.SQL:
        q = sr.read_sql(name)
        c = sr.compare([r.asDict() for r in spark.sql(q).collect()], con.execute(q).fetchdf().to_dict("records"))
        assert c["rows"] == c["rows_other"] > 0 and not c["disagreements"], name
