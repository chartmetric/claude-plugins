#!/usr/bin/env bash
# ClickHouse query benchmark via system.query_log
#
# Usage:
#   ./benchmark.sh <label> <query_file> [runs]
#   ./benchmark.sh compare <label_a> <query_file_a> <label_b> <query_file_b> [runs]
#
# Env vars (tries UPPERCASE first, falls back to lowercase):
#   CLICKHOUSE_HOST / clickhouse_host — hostname or full URL (https://host:port)
#   CLICKHOUSE_PORT / clickhouse_port — port (ignored if HOST is a full URL)
#   CLICKHOUSE_USER / clickhouse_user
#   CLICKHOUSE_PASSWORD / clickhouse_password
#
# Tags each run with a unique query_id, flushes system.query_log, then
# aggregates server-side stats (duration, read_rows, read_bytes, memory, CPU).

set -euo pipefail

# --- help ----------------------------------------------------------------
if [[ "${1:-}" == "" || "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  sed -n '2,15p' "$0"
  exit 0
fi

# --- resolve env vars (UPPERCASE preferred, lowercase fallback) ----------
ch_host="${CLICKHOUSE_HOST:-${clickhouse_host:-}}"
ch_port="${CLICKHOUSE_PORT:-${clickhouse_port:-}}"
ch_user="${CLICKHOUSE_USER:-${clickhouse_user:-}}"
ch_pass="${CLICKHOUSE_PASSWORD:-${clickhouse_password:-}}"

[[ -z "$ch_host" ]] && { echo "error: CLICKHOUSE_HOST (or clickhouse_host) must be set" >&2; exit 1; }
[[ -z "$ch_user" ]] && { echo "error: CLICKHOUSE_USER (or clickhouse_user) must be set" >&2; exit 1; }
[[ -z "$ch_pass" ]] && { echo "error: CLICKHOUSE_PASSWORD (or clickhouse_password) must be set" >&2; exit 1; }

# Build base URL — handle both "host" and "https://host:port" formats
if [[ "$ch_host" == https://* ]]; then
  CH_URL="$ch_host"
else
  [[ -z "$ch_port" ]] && { echo "error: CLICKHOUSE_PORT (or clickhouse_port) must be set when HOST is not a full URL" >&2; exit 1; }
  CH_URL="https://${ch_host}:${ch_port}"
fi

AUTH="${ch_user}:${ch_pass}"

ch_exec() {
  # $1 = query string, optional $2 = query_id
  local q="$1"
  local qid="${2:-}"
  local url="$CH_URL"
  [[ -n "$qid" ]] && url="${url}/?query_id=${qid}"
  curl -sS --fail-with-body --user "$AUTH" "$url" --data-binary "$q"
}

ch_exec_file() {
  # $1 = query file, $2 = query_id
  local file="$1"
  local qid="$2"
  curl -sS --fail-with-body --user "$AUTH" \
    "${CH_URL}/?query_id=${qid}" \
    --data-binary @"$file" > /dev/null
}

run_benchmark() {
  local label="$1"
  local query_file="$2"
  local runs="${3:-5}"
  local run_tag
  run_tag="$(date +%s)_$$"

  echo ">> Running '${label}' ${runs} time(s) ..."
  for i in $(seq 1 "$runs"); do
    local qid="bench_${label}_${run_tag}_${i}"
    printf "   run %d/%d  query_id=%s ... " "$i" "$runs" "$qid"
    local t0 t1
    t0=$(date +%s.%N)
    ch_exec_file "$query_file" "$qid"
    t1=$(date +%s.%N)
    printf "%.3fs\n" "$(echo "$t1 - $t0" | bc)"
  done

  # Return the run_tag so caller can look up stats
  echo "$run_tag"
}

print_stats() {
  local label="$1"
  local run_tag="$2"
  local pattern="bench_${label}_${run_tag}_%"

  # Force flush of async query log (may fail without admin privileges — wait instead)
  ch_exec "SYSTEM FLUSH LOGS" > /dev/null 2>&1 || { echo "   (SYSTEM FLUSH LOGS not permitted — waiting 8s for async flush)"; sleep 8; }

  echo
  echo "=== Per-run stats for '${label}' ==="
  ch_exec "
    SELECT
      query_id,
      round(query_duration_ms) AS duration_ms,
      formatReadableQuantity(read_rows) AS read_rows,
      formatReadableSize(read_bytes) AS read_bytes,
      formatReadableSize(memory_usage) AS mem,
      round(ProfileEvents['OSCPUVirtualTimeMicroseconds']/1000) AS cpu_ms,
      result_rows
    FROM system.query_log
    WHERE query_id LIKE '${pattern}'
      AND type = 'QueryFinish'
    ORDER BY event_time_microseconds
    FORMAT PrettyCompactMonoBlock
  "

  echo
  echo "=== Aggregate stats for '${label}' ==="
  ch_exec "
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
      formatReadableSize(round(avg(memory_usage))) AS avg_mem
    FROM system.query_log
    WHERE query_id LIKE '${pattern}'
      AND type = 'QueryFinish'
    FORMAT Vertical
  "
}

cmd="${1:-}"

case "$cmd" in
  compare)
    label_a="$2"; file_a="$3"
    label_b="$4"; file_b="$5"
    runs="${6:-5}"
    tag_a="$(run_benchmark "$label_a" "$file_a" "$runs" | tail -n1)"
    tag_b="$(run_benchmark "$label_b" "$file_b" "$runs" | tail -n1)"
    print_stats "$label_a" "$tag_a"
    print_stats "$label_b" "$tag_b"
    echo
    echo "=== Side-by-side summary ==="
    ch_exec "
      WITH
        '${label_a}' AS la, 'bench_${label_a}_${tag_a}_%' AS pa,
        '${label_b}' AS lb, 'bench_${label_b}_${tag_b}_%' AS pb
      SELECT
        label,
        count() AS runs,
        round(avg(query_duration_ms)) AS avg_ms,
        round(quantile(0.5)(query_duration_ms)) AS p50_ms,
        round(quantile(0.9)(query_duration_ms)) AS p90_ms,
        formatReadableQuantity(round(avg(read_rows))) AS avg_read_rows,
        formatReadableSize(round(avg(read_bytes))) AS avg_read_bytes,
        formatReadableSize(round(avg(memory_usage))) AS avg_mem
      FROM (
        SELECT la AS label, query_duration_ms, read_rows, read_bytes, memory_usage
        FROM system.query_log
        WHERE query_id LIKE pa AND type = 'QueryFinish'
        UNION ALL
        SELECT lb AS label, query_duration_ms, read_rows, read_bytes, memory_usage
        FROM system.query_log
        WHERE query_id LIKE pb AND type = 'QueryFinish'
      )
      GROUP BY label
      ORDER BY label
      FORMAT PrettyCompactMonoBlock
    "
    ;;
  *)
    # Single benchmark: $1=label $2=query_file [$3=runs]
    label="$1"; file="$2"; runs="${3:-5}"
    tag="$(run_benchmark "$label" "$file" "$runs" | tail -n1)"
    print_stats "$label" "$tag"
    ;;
esac
