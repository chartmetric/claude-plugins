---
name: ds-notebook
description: Scaffold, extend, and harden Chartmetric data-science notebooks — standalone Jupyter notebooks that query ClickHouse (preferred) or Snowflake with memory-safe patterns, freshness sentinels, schema verification, server-side eligibility scratch tables, parquet caching, sanity/validation diagnostics, and disabled write-back cells. Use when starting a new DS/analytics/scoring notebook, adding queries to one, choosing ClickHouse vs Snowflake, or debugging data sourcing (stale derived tables, recompute-from-raw, peer-group normalization, OOMing joins).
---

# DS Notebook

Build Chartmetric data-science notebooks that are **standalone, reproducible,
memory-safe, and honest about their data**. This skill encodes the workflow that
the fan-intensity project converged on the hard way.

## When to use this

- Starting a new analytics / scoring / feature-engineering notebook.
- Adding a query or signal to an existing DS notebook.
- Choosing a datastore (ClickHouse vs Snowflake) or a source table.
- A query OOMs, a signal looks size-correlated, or a "fresh" number smells stale.

## First moves

1. **Read `reference/workflow.md`** — the section-by-section anatomy every
   notebook should follow, and why each section exists.
2. **Copy `assets/notebook_template.ipynb`** as the starting point. It already
   contains every section below wired up with the standard helpers. Rename the
   sections to the project's domain; delete what you don't need, but keep §0–§2
   and the write-back cell.
3. Fill in `§1 Schema map & tunables` first — it is the **single source of
   truth** for every table name and knob. Nothing else should hardcode an
   identifier.

## The non-negotiables (golden rules)

These are cheap to follow and expensive to skip. Each maps to a real failure
this workflow has hit.

1. **Config-as-single-source-of-truth.** All DB names, table identifiers, column
   names, windows, and thresholds live in one `§1` cell. Everything downstream
   references it. Re-pointing a table is a one-line edit.
2. **Verify schema before heavy work (`§2`).** Assert every column you depend on
   exists (via `system.columns`) *before* the expensive queries, so you fail
   loudly and early — never a cryptic Code 47/60 mid-scan.
3. **Freshness sentinels (`§2`).** Print `max(date)` for every source table.
   Derived/"analytics" tables go stale silently — a 7-months-frozen mirror looks
   identical to fresh data until you check. See `reference/validation.md`.
4. **Prefer ClickHouse; recompute from raw when freshness matters.** Check if the
   raw tables exist in ClickHouse before reaching for Snowflake, and prefer
   recomputing a metric from fresh raw tables over trusting a stale derived
   table. Validate the recompute *as-of* the old table's date (see
   `reference/validation.md`). Only cross to Snowflake when the data genuinely
   isn't in ClickHouse — see `reference/snowflake.md`.
5. **Memory-safe by construction.** Apply the spill settings, materialize large
   candidate sets as a server-side scratch table (never ship a big `IN (...)`
   literal from Python), and use two-stage / flipped joins on billion-row
   tables. See `reference/clickhouse.md`.
6. **Cache heavy queries locally.** The standard `query_df(..., cache=True)`
   helper writes a parquet keyed by a hash of the SQL, so re-runs are instant.
   See `reference/caching.md`.
7. **Scoring is whole-population.** Percentiles, bins, and peer-group medians are
   computed across all rows at once. **Never** batch/chunk a normalization step —
   batch-relative percentiles silently corrupt every score.
8. **Sanity-check and explain (`§ sanity`).** Distributions, coverage, expected
   correlations, and a "leak localization" pass for scores that should be
   size-neutral. See `reference/validation.md`.
9. **Writes are disabled by default.** The write-back cell ships fully
   commented-out with its DDL + INSERT, so a reviewer must consciously enable it.
10. **Outputs cleared, deterministic.** Commit notebooks with outputs cleared;
    use stable ordering and `today()`-relative windows documented in `§1`.

## Notebook anatomy (what the template gives you)

```
Title + overview (markdown)
## 0 · Imports, config & connectivity   -> helpers: query_df / run_ch / cache, CH_SETTINGS, connectivity test
## 1 · Schema map & tunables            -> DB names, TABLES dict, all knobs (single source of truth)
## 2 · Schema verification & freshness  -> assert columns exist; print max(date) per source (fail loud, fail early)
## 3 · Eligibility (server-side scratch)-> CREATE OR REPLACE scratch table; ELIG = "(SELECT id FROM scratch)"
## 4 · Signals / features               -> one cached query_df per signal
## 5 · Assemble & derive                -> merge onto the population, derive columns
## 6 · Normalize / score                -> whole-population; peer-group patterns
## 7 · Sanity, validation & explain     -> distributions, coverage, correlations, as-of validation, leak localization
## 8 · Write-back (DISABLED)            -> commented-out DDL + INSERT; scratch cleanup
```

## Regenerating a notebook programmatically

For structural changes, keep each cell's source in a file and rebuild the
`.ipynb` deterministically (swap cells, clear outputs, validate JSON + compile
every code cell) with `scripts/build_notebook.py`. This keeps unchanged cells
byte-identical across versions and catches syntax errors before a kernel ever
runs. See the script's header for usage.

## Reference files (load as needed)

- `reference/workflow.md` — full section-by-section anatomy and rationale.
- `reference/clickhouse.md` — connection, memory-safe settings, scratch-table
  pattern, two-stage/flipped joins, cumulative-snapshot (`argMax`) semantics.
- `reference/snowflake.md` — when/how to use Snowflake; ClickHouse-first check.
- `reference/validation.md` — freshness sentinels, schema verification, as-of
  recompute validation, sanity diagnostics, whole-population guardrails.
- `reference/caching.md` — the parquet cache-by-SQL-hash helper and invalidation.

## Chartmetric specifics

- Credentials come from `~/code/chartmetric/devin-secrets.env` (`source` it
  before running). **Databases are read-only — SELECT only.** The one sanctioned
  write is the server-side scratch table in a scratch DB (e.g. `chartmetric_test`).
- ClickHouse connect: `from data_utils.clickhouse_access import clickhouse_connect`.
- Only local sessions can reach the datastores; cloud sessions cannot.
