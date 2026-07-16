# Notebook anatomy — section by section

Every section earns its place by preventing a specific failure. Order matters:
cheap guards run before expensive work.

## Title + overview (markdown)

A plain-language brief a PM could read: what the notebook produces, the key
inputs, and the headline method. If the output is a composite/score, state what
it is and is *not* measuring, and list the components with weights. Keep a short
changelog when iterating (v1 → v2 → …) so a reader knows what changed and why.

## §0 · Imports, config & connectivity

- Imports (numpy, pandas, matplotlib, scipy as needed).
- The datastore helper(s): `query_df` / `run_ch` for ClickHouse, plus the
  memory-safe `CH_SETTINGS` dict, and the parquet cache (see
  `caching.md`, `clickhouse.md`).
- A one-line connectivity smoke test (`query_df("SELECT 1 AS ok")`).

Keep the notebook **standalone**: define the helpers in this cell rather than
importing a project module, so the notebook runs anywhere the driver + creds
exist.

## §1 · Schema map & tunables — the single source of truth

The only cell anyone edits to re-point data or change behavior:

- `DB_*` database names.
- A `TABLES = {...}` dict mapping short logical names → fully-qualified table
  names, **with a one-line schema comment per table** (key columns + types +
  gotchas: cumulative? nullable sentinel? ReplacingMergeTree needs FINAL?).
- All windows, thresholds, weights, and mode toggles, each with a comment on
  units and intent.

If a downstream cell hardcodes a table or column, it belongs here instead.

## §2 · Schema verification & freshness (fail loudly, fail early)

Before any heavy query:

1. **Column asserts** — for each dependency, pull `system.columns` and assert the
   needed columns are present. A missing column fails here with a clear message,
   not 40 minutes into a scan.
2. **Freshness sentinels** — print `max(<date col>)` for every source table.
   This is the highest-value check in the whole notebook. Derived/analytics
   mirrors freeze silently; only a freshness print reveals it. Treat a source
   whose max date is far behind `today()` as broken until proven otherwise.
3. **Runtime discovery** where a table's location/columns vary — discover it
   (query `system.tables`) instead of assuming.

## §3 · Eligibility — materialized server-side

Compute the candidate population **once, server-side**, as a small scratch table
(`CREATE OR REPLACE TABLE scratch ... ENGINE = MergeTree ORDER BY id`). Every
downstream heavy query filters with `id IN (SELECT id FROM scratch)` — a
server-side hash-set test — so no id list ever travels through Python or bloats
SQL text. This is the fix for the classic OOM of shipping a multi-MB `IN (...)`
literal into every query. See `clickhouse.md`.

## §4 · Signals / features

One cached `query_df` per signal. Keep each query focused and documented. Apply
data-quality guards (minimum observations, non-zero denominators) explicitly and
comment why. Missing data is a decision: is a missing value a genuine zero, or
unknown (NaN)? State it per signal.

## §5 · Assemble & derive

Left-merge signals onto the population (`how="left"`), coerce ClickHouse
object-dtype numerics to float once, up front. Derive ratios/rates here with
explicit zero/NaN handling.

## §6 · Normalize / score

If normalizing or ranking: it is **whole-population**. Compute percentiles /
bins / peer medians across all rows at once — never per batch. For size- or
peer-neutral scores, normalize *within peer groups* and document the grouping.
Prefer rank-with-ties over ad-hoc zero-pinning for zero-heavy signals (see the
fan-intensity notes in `validation.md`).

## §7 · Sanity, validation & explainability

Always include (see `validation.md` for specifics):
- Output distribution (histogram) and summary stats.
- Coverage per signal/pillar (what fraction of the population has each).
- Expected correlations (and, for a size-neutral score, a "leak localization"
  pass that shows *which* component carries any residual size correlation).
- An **as-of validation** when you recomputed a metric that also exists as a
  (possibly stale) table: reproduce the old value by computing as-of the old
  date, and confirm they match.

## §8 · Write-back (DISABLED)

Ship the write path fully commented-out: the `CREATE TABLE IF NOT EXISTS` DDL
(explicit column types) and the `INSERT`. A reviewer enables it only after the
sanity checks look right. Include an optional scratch-table cleanup line.
Print a harmless `"write-back disabled"` so the cell runs clean.
