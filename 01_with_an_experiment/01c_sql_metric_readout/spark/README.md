# 01c on Spark: the same queries, the same numbers

> **Takeaway.** The four SQL files of study 01c run unchanged on Spark 4.3 and give the same 55 cells as DuckDB, with
> a largest relative difference of zero, on all 13,979,592 rows. The readout by arm also matches the committed
> [`out/readout.json`](../out/readout.json).

## Question

The readout of study 01c was written in SQL and run on DuckDB on one machine. A team running the experiment would
query a warehouse table with a distributed engine instead. Do the same queries, unchanged, give the same numbers there?

## Method

1. **Table.** The released file is read by Spark, each column cast to its type (features as doubles, flags as
   integers) and written to Parquet in 32 parts, the layout of a warehouse table. Both engines then read that table.
2. **Queries.** [`checks.sql`](../sql/checks.sql), [`duplicates.sql`](../sql/duplicates.sql),
   [`readout_by_arm.sql`](../sql/readout_by_arm.sql) and [`readout_effects.sql`](../sql/readout_effects.sql), as
   committed, with only the trailing semicolon removed.
3. **Rule, fixed before the run.** Integer cells must be equal and other cells must agree to a relative difference of
   1e-12, since sums may be added in a different order.

Spark ran locally on 16 cores (Java 21).

## Results

Source: [`out/spark_parity.json`](out/spark_parity.json).

| Query | Rows | Cells | Largest relative difference | Seconds, Spark / DuckDB |
|---|---|---|---|---|
| Data checks | 1 | 6 | 0 | 1.2 / 0.07 |
| Duplicate rows | 1 | 1 | 0 | 2.4 / 0.20 |
| Readout by arm | 2 | 20 | 0 | 0.4 / 0.02 |
| Effects and attribution diagnostics | 2 | 28 | 0 | 0.9 / 0.02 |

- **The rule was met:** all 55 cells agree exactly.
- Writing the table took 60 seconds, most of it reading the single gzip file, which Spark cannot split.
- On one machine DuckDB is faster. What carries over is that the metric definitions are plain SQL that a
  distributed engine runs without change; the timings say nothing about a cluster.

## Reproduce

```bash
pip install -r spark/requirements-spark.txt        # and a Java 17 or 21 runtime in JAVA_HOME
python spark/run_spark_readout.py /path/to/criteo-research-uplift-v2.1.csv.gz derived spark/out
pytest spark/test_spark_readout.py                 # same cells on a small simulated file; skipped without Spark
```

The repository's test workflow does not install Spark or Java, so the test above is run by hand.
