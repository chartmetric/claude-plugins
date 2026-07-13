---
name: clickhouse-benchmark
description: Benchmark and compare ClickHouse queries using server-side system.query_log stats. Use when the user wants to measure query performance, compare old vs new query versions, or analyze duration/memory/bytes-read for a ClickHouse query. Produces P50/P90/P99 latency plus read_rows, read_bytes, memory_usage, and peak_memory_usage aggregated from system.query_log — no external tools required, just curl + ClickHouse.
---

# ClickHouse Query Benchmark

Benchmarks ClickHouse queries by running them N times with tagged `query_id`s, then aggregating stats from `system.query_log` server-side. More accurate than `time curl` because it uses ClickHouse's own internal measurements (CPU time, peak memory, actual bytes read after pruning).

## When to use

- User asks to benchmark a ClickHouse query
- User wants to compare performance of two query versions (e.g. "is the new query faster?")
- User mentions `X-ClickHouse-Summary`, `clickhouse-benchmark`, or wall-clock timing for ClickHouse
- User asks about query performance analysis, p50/p90/p99 latency, memory usage, or rows read

## Prerequisites

The following env vars must be set (the user already has these in their shell):

- `CLICKHOUSE_HOST`
- `CLICKHOUSE_PORT`
- `clickhouse_user`
- `clickhouse_password`

If any are missing, ask the user to export them or confirm they're in the shell env.

## How to run (step-by-step)

The script takes query **files**, not inline SQL. Before running the
benchmark, write the SQL to temp files.

### Step 1 — Write queries to temp files

Use the Write tool (or `cat <<'EOF'` in Bash) to save each query.
**Always append `FORMAT Null`** so output is discarded and you measure
pure execution cost, not data transfer.

If the user gives you the SQL inline, in a file, or references a query in
the codebase, extract it and write it to `/tmp/bench_<label>.sql`.

### Step 2 — Run the benchmark

**Single query:**
```bash
"${CLAUDE_PLUGIN_ROOT}/skills/clickhouse-benchmark/benchmark.sh" <label> /tmp/bench_<label>.sql [runs]
```

**Compare two queries side-by-side:**
```bash
"${CLAUDE_PLUGIN_ROOT}/skills/clickhouse-benchmark/benchmark.sh" compare \
  old /tmp/bench_old.sql \
  new /tmp/bench_new.sql \
  5
```

Default is 5 runs if omitted. Labels must be short `[a-zA-Z0-9_]` identifiers.

### Step 3 — Report results

Summarize the side-by-side table to the user, calling out:
- Duration improvement (avg_ms, p50, p90)
- Rows/bytes read reduction
- Memory reduction
- Any outlier runs that suggest cold-cache effects

## What it reports

- **Per-run table**: duration_ms, read_rows, read_bytes, memory_usage, peak_memory_usage, cpu_ms, result_rows
- **Aggregate**: min/p50/p90/p99/max/avg duration, avg rows/bytes read, avg/max memory
- **Side-by-side (compare mode)**: one row per label with avg_ms, p50, p90, avg_read_rows, avg_read_bytes, avg_mem

All numbers come from `system.query_log` — ClickHouse's own accounting.

## Raw SQL (if the user wants to run by hand)

If the user wants the queries without the script, this is the essence:

```sql
-- After running each query N times with query_ids like 'bench_old_1', 'bench_old_2', ...
SYSTEM FLUSH LOGS;

SELECT
  count() AS runs,
  round(min(query_duration_ms)) AS min_ms,
  round(quantile(0.5)(query_duration_ms)) AS p50_ms,
  round(quantile(0.9)(query_duration_ms)) AS p90_ms,
  round(quantile(0.99)(query_duration_ms)) AS p99_ms,
  round(max(query_duration_ms)) AS max_ms,
  round(avg(query_duration_ms)) AS avg_ms,
  formatReadableQuantity(round(avg(read_rows))) AS avg_read_rows,
  formatReadableSize(round(avg(read_bytes))) AS avg_read_bytes,
  formatReadableSize(round(avg(memory_usage))) AS avg_mem,
  formatReadableSize(round(max(peak_memory_usage))) AS max_peak_mem
FROM system.query_log
WHERE query_id LIKE 'bench_old_%'
  AND type = 'QueryFinish';
```

Tag runs from any client with `?query_id=bench_old_1` in the URL.
