# Local caching — parquet, keyed by SQL hash

Heavy queries should run once. Cache their results to disk keyed by a hash of the
exact SQL, so re-executing the notebook (or re-running a cell) is instant and you
iterate on the pandas/analysis layer without re-hitting the warehouse.

## Drop-in helper (inline in §0)

```python
import hashlib, os
import pandas as pd

CACHE_DIR     = "./_dscache"          # per-notebook working dir; add to .gitignore
CACHE_VERSION = "v1"                  # bump to invalidate everything at once
os.makedirs(CACHE_DIR, exist_ok=True)

def _cache_path(sql: str) -> str:
    key = hashlib.sha1((CACHE_VERSION + sql).encode()).hexdigest()[:16]
    return os.path.join(CACHE_DIR, f"{key}.parquet")

def query_df(sql: str, cache: bool = True) -> pd.DataFrame:
    """Run SQL on ClickHouse; cache the result as parquet keyed by hash(sql).
    Pass cache=False for cheap/volatile queries or to force a refresh."""
    if cache:
        path = _cache_path(sql)
        if os.path.exists(path):
            return pd.read_parquet(path)
    con = clickhouse_connect()
    try:
        rows, col_types = con.execute(sql, with_column_types=True, settings=CH_SETTINGS)
    finally:
        con.disconnect()
    df = pd.DataFrame(rows, columns=[n.split('.')[-1] for n, _ in col_types])
    if cache:
        df.to_parquet(_cache_path(sql))
    return df
```

## Rules of thumb

- **Cache the expensive scans** (the per-signal `§4` queries), not `SELECT 1` or
  sub-second lookups.
- **The cache key is the exact SQL string.** Any change (even whitespace or a
  changed threshold interpolated into an f-string) is a new key → automatic
  refresh. That's the point: edit the query, get fresh data; re-run unchanged,
  get the cache.
- **Invalidate** by deleting `./_dscache`, bumping `CACHE_VERSION`, or passing
  `cache=False`.
- **Never commit the cache.** Add `_dscache/` to `.gitignore`.
- **Freshness interacts with caching.** A cached result can hide that the source
  advanced. Keep the `§2` freshness sentinels on `cache=False` so they always
  read live, and clear the cache when you intend a fresh full run.
- Parquet preserves dtypes better than CSV and is fast; it needs `pyarrow`
  (already present in the DS env).
