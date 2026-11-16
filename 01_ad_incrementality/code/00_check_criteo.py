"""Sanity-check the downloaded Criteo uplift dataset (read-only).

Usage: python -I 00_check_criteo.py <path to criteo-research-uplift-v2.1.csv.gz>
Prints: md5, row count, columns, treatment share, visit / conversion rates by arm.
"""
import hashlib
import sys

import duckdb

path = sys.argv[1]

h = hashlib.md5()
with open(path, "rb") as f:
    for chunk in iter(lambda: f.read(1 << 24), b""):
        h.update(chunk)
print("md5:", h.hexdigest())

con = duckdb.connect()
con.execute(f"CREATE VIEW c AS SELECT * FROM read_csv_auto('{path}')")
print("columns:", [r[0] for r in con.execute("DESCRIBE c").fetchall()])
print("rows:", con.execute("SELECT count(*) FROM c").fetchone()[0])
print(
    con.execute(
        """
        SELECT treatment,
               count(*)            AS n,
               avg(visit)          AS visit_rate,
               avg(conversion)     AS conversion_rate,
               avg(exposure)       AS exposure_rate
        FROM c GROUP BY treatment ORDER BY treatment
        """
    ).df()
)
