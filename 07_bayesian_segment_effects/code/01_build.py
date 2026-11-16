"""Build the compact analysis file: segment (100 rank-based), replicate id, treatment, visit, conversion.

Usage: python code/01_build.py <criteo-research-uplift-v2.1.csv.gz> <derived_dir>
Plan: design/analysis_plan.md (Part 2 segment and replicate rules).
"""
import sys
from pathlib import Path
import duckdb, numpy as np
SRC, OUT = sys.argv[1], Path(sys.argv[2]) / "criteo_compact.parquet"
OUT.parent.mkdir(parents=True, exist_ok=True)
con = duckdb.connect()
con.execute(f"create table t0 as select f0,f2,f8,f10,f7,f3, treatment::TINYINT treatment, visit::TINYINT visit, conversion::TINYINT conversion from read_csv_auto('{SRC}')")
con.execute("create table t as select rowid as rid, * from t0")  # rowid = file order
n = con.execute("select count(*) from t").fetchall()[0][0]
u = np.random.default_rng(20261115).random(n)
rep = np.floor(50 * u).astype(np.int16)
import pandas as pd
con.register("r", pd.DataFrame({"rid": np.arange(n), "rep": rep}))
con.execute(f"""copy (select ntile(100) over (order by f0,f2,f8,f10,f7,f3,t.rid) - 1 as seg, r.rep, treatment, visit, conversion
  from t join r using (rid)) to '{OUT}' (format parquet)""")
print(n, con.execute(f"select count(distinct seg), min(c), max(c) from (select seg, count(*) c from '{OUT}' group by seg)").fetchall())
