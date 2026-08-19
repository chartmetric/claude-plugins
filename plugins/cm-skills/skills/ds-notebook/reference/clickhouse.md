# ClickHouse — connection, memory safety, join cookbook

## Which warehouse? (decide before writing a query)

Chartmetric runs **separate ClickHouse Cloud warehouses**. They are distinct
clusters with distinct credentials, and there is **no `REMOTE` grant — you cannot
join across them in one query**. Pick one per notebook; if you need both, land an
intermediate result and join it in pandas.

| Warehouse | Databases | Host env var | Credentials |
|---|---|---|---|
| `rw-standard` | `chartmetric_analytics`, `chartmetric_raw_data`, `chartmetric_sm_raw_data` | `CLICKHOUSE_HOST` / `clickhouse_host` | `CH_USER`/`CH_PASSWORD`, else `clickhouse_user`/`clickhouse_password` |
| `vert` (new verticals) | `new_vertical` — athletes, brands, creators | `CLICKHOUSE_VERT_HOST` / `clickhouse_newverticals_host` | `clickhouse_newverticals_user` / `clickhouse_newverticals_password` |

`data_utils.clickhouse_access.clickhouse_connect()` **hardcodes the rw-standard
host**, so calling it bare silently targets the music warehouse — a notebook
pointed at `new_vertical` that way fails with "table does not exist" or, worse,
finds a same-named table with different contents. It does accept overrides
(`clickhouse_connect(host=..., username=..., password=...)` — note `username`,
not `user`), but it gives you no control over the port. Prefer the registry below:
it makes the target warehouse a named, printed, one-line change.

## Connection & helpers (standalone, inline in §0)

```python
import os
from clickhouse_driver import Client

# ── warehouse registry: the ONE place a warehouse is named ───────────────────
# Each entry lists candidate env-var names in priority order; the resolver tries
# each verbatim, upper- and lower-cased, because devin-secrets.env mixes
# conventions (CH_USER vs clickhouse_newverticals_user).
CH_WAREHOUSES = {
    "rw-standard": {
        "host": ("CLICKHOUSE_HOST", "clickhouse_host"),
        "user": ("CH_USER", "clickhouse_user"),
        "password": ("CH_PASSWORD", "clickhouse_password"),
    },
    "vert": {
        "host": ("CLICKHOUSE_VERT_HOST", "clickhouse_newverticals_host"),
        "user": ("clickhouse_newverticals_user",),
        "password": ("clickhouse_newverticals_password",),
    },
}
WAREHOUSE = "rw-standard"   # <-- the only place to change the target
CH_NATIVE_PORT = 9440       # clickhouse_driver native TLS (HTTPS would be 8443)

def _env(names):
    for name in names:
        for cand in (name, name.upper(), name.lower()):
            val = os.environ.get(cand)
            if val:
                return val
    raise KeyError(f"none of {names} in the environment — "
                   "`source ~/code/chartmetric/devin-secrets.env` first")

def ch_config(warehouse=None):
    spec = CH_WAREHOUSES[warehouse or WAREHOUSE]
    host = _env(spec["host"]).split("://")[-1].split("/")[0].split(":")[0]  # tolerate a full URL
    return {"warehouse": warehouse or WAREHOUSE, "host": host,
            "user": _env(spec["user"]), "password": _env(spec["password"]),
            "port": CH_NATIVE_PORT}

def ch_client(warehouse=None):
    cfg = ch_config(warehouse)
    return Client(host=cfg["host"], user=cfg["user"], password=cfg["password"],
                  port=cfg["port"], secure=True, send_receive_timeout=3300)

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

def query_df(sql: str, warehouse=None) -> "pd.DataFrame":
    con = ch_client(warehouse)
    try:
        rows, col_types = con.execute(sql, with_column_types=True, settings=CH_SETTINGS)
    finally:
        con.disconnect()
    cols = [name.split('.')[-1] for name, _ in col_types]  # strip analyzer table-qualifier prefixes
    return pd.DataFrame(rows, columns=cols)

def run_ch(sql: str, warehouse=None) -> None:              # DDL / no result set
    con = ch_client(warehouse)
    try:
        con.execute(sql, settings=CH_SETTINGS)
    finally:
        con.disconnect()

_cfg = ch_config()      # print what you actually connected to — a mis-pointed
print(f"warehouse: {_cfg['warehouse']}  host: {_cfg['host']}  user: {_cfg['user']}")
query_df("SELECT 1 AS ok")                                 # …notebook fails here, not 10 cells later
```

Wrap `query_df` with the parquet cache in `caching.md` for heavy queries — and
include the warehouse name in the cache key, or two warehouses will collide on
identical SQL.

**Ad-hoc probing outside the notebook** (e.g. schema/freshness checks): the
ClickHouse HTTPS endpoint works with `curl` — `https://<host>:$CLICKHOUSE_PORT/`
(port is typically 8443 = TLS) with the matching warehouse's user/password from
`devin-secrets.env`. Pass the spill settings as URL params. Note the ad-hoc user
may have narrower grants than the notebook's (e.g. no access to the scratch DB) —
on the vert warehouse the read path is read-only, so verify a `CREATE` grant
before designing around a scratch table.

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
