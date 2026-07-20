# ClickHouse — connection, memory safety, join cookbook

## Connection & helpers (standalone, inline in §0)

```python
from data_utils.clickhouse_access import clickhouse_connect  # returns a clickhouse_driver Client

# Memory-safety settings applied to EVERY query:
#  - analyzer on (multi-CTE / nested-IN queries need it; matches the sync jobs)
#  - external GROUP BY / sort: spill to disk instead of hard-OOMing
#  - join_algorithm auto: falls back to partial-merge join under memory pressure
#  - modest thread count: lower peak memory on billion-row scans
CH_SETTINGS = {
    "allow_experimental_analyzer": 1,
    "memory_usage_overcommit_max_wait_microseconds": 60_000_000,
    "max_bytes_before_external_group_by": 4_000_000_000,
    "max_bytes_before_external_sort":     4_000_000_000,
    "join_algorithm": "auto",
    "max_threads": 8,
}

def query_df(sql: str) -> "pd.DataFrame":
    con = clickhouse_connect()
    try:
        rows, col_types = con.execute(sql, with_column_types=True, settings=CH_SETTINGS)
    finally:
        con.disconnect()
    cols = [name.split('.')[-1] for name, _ in col_types]  # strip analyzer table-qualifier prefixes
    return pd.DataFrame(rows, columns=cols)

def run_ch(sql: str) -> None:                              # DDL / no result set
    con = clickhouse_connect()
    try:
        con.execute(sql, settings=CH_SETTINGS)
    finally:
        con.disconnect()
```

Wrap `query_df` with the parquet cache in `caching.md` for heavy queries.

**Ad-hoc probing outside the notebook** (e.g. schema/freshness checks): the
ClickHouse HTTPS endpoint works with `curl` — `https://$clickhouse_host:$CLICKHOUSE_PORT/`
(port is typically 8443 = TLS) with `clickhouse_user`/`clickhouse_password` from
`devin-secrets.env`. Pass the spill settings as URL params. Note the ad-hoc user
may have narrower grants than the notebook's `clickhouse_connect()` (e.g. no
access to the scratch DB).

## Server-side eligibility scratch table (the anti-OOM pattern)

Do **not** compute a candidate id list in Python and inline it as
`... IN (id1, id2, ..., id950000)` — a multi-MB literal repeated per query OOMs
the server. Instead:

```python
run_ch(f"""
CREATE OR REPLACE TABLE {SCRATCH}
ENGINE = MergeTree ORDER BY id AS
SELECT id, ... FROM {TABLES['...']} WHERE <gates>
  AND id IN (SELECT ... FROM {TABLES['...']} WHERE <more gates>)
""")
ELIG = f"(SELECT id FROM {SCRATCH})"     # every heavy query filters: WHERE x IN {ELIG}
```

`SCRATCH` lives in a writable scratch DB (e.g. `chartmetric_test`). It is the one
sanctioned write in an otherwise read-only notebook. On a replicated single-shard
cluster plain `IN` is correct; on a Distributed/sharded table you would need
`GLOBAL IN`.

## Memory-safe joins on billion-row tables

When a join OOMs, the cause is almost always **hashing the huge side**. Fixes:

1. **Two-stage / narrow-first.** Resolve a small candidate set first (e.g. the
   relevant track ids for eligible artists), materialize/CTE it, then scan the
   giant fact table filtered to that set. Bound the map by catalog size, not by
   fact-table volume.
2. **Flip the join so the small side is hashed.** ClickHouse builds the hash
   table from the **right** table. `FROM huge_table h INNER JOIN small_set s ON …`
   streams `huge_table` (low memory) and hashes `small_set`. If you write it the
   other way, you hash the huge table → OOM.
3. **Avoid double-scanning a CTE.** Referencing a CTE twice (e.g. once in a
   `WHERE x IN (SELECT … FROM cte)` and once in a join) can recompute a huge scan.
   Reference each heavy CTE once.
4. **Prefer `uniq()` (HLL) over `uniqExact()`** for count-distinct at scale, and
   `quantile()` over `quantileExact()` — the approximate variants keep memory flat.
5. **Dedup with `GROUP BY`, not `SELECT DISTINCT`.** `DISTINCT` runs as
   `DistinctTransform` — an **in-memory-only** hash set that does NOT spill, so a
   large distinct set OOMs even with the external-group-by setting on.
   `SELECT a, b FROM … GROUP BY a, b` returns the same rows but runs as an
   aggregation that honors `max_bytes_before_external_group_by` and spills to
   disk. Symptom: an OOM whose stack trace names `DistinctTransform` (often when
   a window/scan was just widened). Same idea for `LIMIT BY` and set-building.
6. Keep the spill settings on; if still strained, lower `max_threads` (fewer
   concurrent hash tables → lower peak) or materialize an intermediate as a
   scratch table.

## Snapshot semantics (get these wrong and every number is wrong)

- **Cumulative running-total tables** (e.g. `youtube_stat`): per-entity current
  value is `argMax(metric, timestp)`, **never** `SUM`.
- **ReplacingMergeTree / SharedReplacingMergeTree**: rows with the same
  `ORDER BY` key are deduped **asynchronously at merge time**, so a plain
  `SELECT` can still return duplicates until a merge runs. To read the deduped
  view, use one of:
  - `SELECT ... FROM t FINAL` — collapses on read (simplest; some overhead).
  - `argMax(col, version) ... GROUP BY key` — pick the newest row per key
    explicitly (works with any recency column); also the pattern for reading a
    time-series stat table as "latest per entity".
  - `OPTIMIZE TABLE t FINAL` — force the merge now (heavy; one-off cleanup only).
  Writing your OWN scored table? `ReplacingMergeTree(version)` makes re-runs
  idempotent (re-inserting a key overwrites) — see `writeback.md`.
- **`argMaxIf` returns 0 (not NULL)** when no rows match the condition — guard
  with an explicit `> 0` check, especially where 0 is also a no-data sentinel.
- **Weight time series on the observation date**, not an ETL `last_updated`
  refresh timestamp.
- Type-mismatched join keys (Int32 vs Int64/UInt32) may need explicit
  `toInt64(...)` on both sides.
