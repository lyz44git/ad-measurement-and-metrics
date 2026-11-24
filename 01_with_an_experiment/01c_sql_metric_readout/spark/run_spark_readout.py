"""Run the four SQL files of study 01c unchanged on Spark and compare every cell with DuckDB.

Usage: python spark/run_spark_readout.py <criteo-research-uplift-v2.1.csv.gz> [derived_dir] [out_dir]
Needs Java 17 or 21 (JAVA_HOME) and `pip install -r spark/requirements-spark.txt`.

Rule, fixed before the run: integer cells must be equal and floating-point cells must agree to a relative
difference of 1e-12 (sums can be added in a different order). The file is first written to Parquet in 32 parts,
the layout of a table in a warehouse, and the queries read that table.
"""
import json
import re
import sys
import time
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SQL = ["checks", "duplicates", "readout_by_arm", "readout_effects"]
FLAGS = ["treatment", "conversion", "visit", "exposure"]
REL_TOL = 1e-12


def read_sql(name):
    text = (ROOT / "sql" / f"{name}.sql").read_text()
    return re.sub(r";\s*$", "", text.strip())


def spark_session(cores=16, memory="24g"):
    from pyspark.sql import SparkSession
    return (SparkSession.builder.master(f"local[{cores}]").appName("criteo-readout")
            .config("spark.driver.memory", memory).config("spark.ui.enabled", "false")
            .config("spark.sql.shuffle.partitions", "64").getOrCreate())


def to_parquet(spark, src, dst, parts=32):
    from pyspark.sql import functions as F
    df = spark.read.option("header", True).csv(str(src))
    df = df.select(*[F.col(f"f{i}").cast("double") for i in range(12)], *[F.col(c).cast("bigint") for c in FLAGS])
    df.repartition(parts).write.mode("overwrite").parquet(str(dst))


def compare(a, b):
    """Cell-by-cell comparison of two lists of row dicts with the same keys and order."""
    cells, worst, bad = 0, 0.0, []
    for i, (ra, rb) in enumerate(zip(a, b)):
        for k in ra:
            va, vb = ra[k], rb[k]
            cells += 1
            if isinstance(va, str) or isinstance(vb, str):
                ok = va == vb
            elif float(va).is_integer() and float(vb).is_integer() and abs(va) < 2 ** 53:
                ok = int(va) == int(vb)
            else:
                rel = abs(va - vb) / max(abs(va), abs(vb), 1e-300)
                worst = max(worst, rel); ok = rel <= REL_TOL
            if not ok:
                bad.append({"row": i, "column": k, "spark": va, "duckdb": vb})
    return {"rows": len(a), "rows_other": len(b), "cells": cells, "max_relative_difference": worst, "disagreements": bad}


def main(src, derived, out):
    derived, out = Path(derived), Path(out)
    derived.mkdir(parents=True, exist_ok=True); out.mkdir(parents=True, exist_ok=True)
    pq = derived / "criteo_users_parquet"
    spark = spark_session()
    t0 = time.time(); to_parquet(spark, src, pq); t_write = time.time() - t0
    spark.read.parquet(str(pq)).createOrReplaceTempView("users")
    con = duckdb.connect()
    con.execute(f"CREATE VIEW users AS SELECT * FROM read_parquet('{pq}/*.parquet')")
    res = {"spark_version": spark.version, "java": spark.sparkContext._jvm.System.getProperty("java.version"),
           "cores": 16, "parquet_parts": len(list(pq.glob("*.parquet"))), "seconds_csv_to_parquet": round(t_write, 1),
           "rule": f"integers equal; other numbers within a relative difference of {REL_TOL:g}", "queries": {}}
    for name in SQL:
        q = read_sql(name)
        t1 = time.time(); s_rows = [r.asDict() for r in spark.sql(q).collect()]; ts = time.time() - t1
        t2 = time.time(); d_df = con.execute(q).fetchdf(); td = time.time() - t2
        d_rows = d_df.to_dict("records")
        c = compare(s_rows, d_rows)
        c |= {"seconds_spark": round(ts, 2), "seconds_duckdb": round(td, 2)}
        res["queries"][name] = c
        print(name, json.dumps({k: c[k] for k in ("rows", "cells", "max_relative_difference")}), len(c["disagreements"]), flush=True)
    committed = json.loads((ROOT / "out" / "readout.json").read_text())
    s_arm = [r.asDict() for r in spark.sql(read_sql("readout_by_arm")).collect()]
    res["matches_committed_readout_by_arm"] = compare(s_arm, committed["by_arm"])["disagreements"] == []
    res["cells"] = sum(v["cells"] for v in res["queries"].values())
    res["agree"] = all(not v["disagreements"] and v["rows"] == v["rows_other"] for v in res["queries"].values())
    res["rows_in_table"] = spark.sql("SELECT COUNT(*) AS n FROM users").collect()[0]["n"]
    (out / "spark_parity.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps({k: res[k] for k in ("spark_version", "java", "cells", "agree", "matches_committed_readout_by_arm",
                                          "seconds_csv_to_parquet")}))
    spark.stop()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ROOT / "derived", sys.argv[3] if len(sys.argv) > 3 else ROOT / "spark" / "out")
