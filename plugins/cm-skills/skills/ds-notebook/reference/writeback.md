# Write-back — dtypes, NULLs, and idempotent (re-runnable) writes

Persisting scores with `clickhouse_driver` fails in ways that only surface at
insert time. Two classes of bug dominate: **dtype mismatches** (pandas floats vs
CH integer columns) and **duplicate rows on re-run**. Handle both explicitly.

## 1. Type coercion for `con.execute("INSERT ... VALUES", records)`

`clickhouse_driver` packs each Python value into the column's binary type with
`struct.pack`. It does **no** float→int coercion, and it treats `NaN` as a
value, not as SQL `NULL`. A DataFrame straight out of pandas will almost always
violate one of these. Symptoms:

- `TypeMismatchError: Column <x>: required argument is not an integer` — a
  **float is being packed into an integer column**. Classic causes: a count
  built with `.astype(float)` (so `3.0` not `3`), or an integer column that went
  float because a `left` merge introduced `NaN` for unmatched rows.
- Silent wrong data: `NaN` inserted into a `Nullable(Float64)` column stores a
  literal `NaN` float, not `NULL`.

**Fix — coerce to match the DDL exactly, right before the insert:**

```python
import numpy as np

# (a) integer columns: fill the sentinel, then cast. A NaN count from a left
#     merge is a genuine zero (the entity had none of that thing).
for col in INT_COLS:                       # e.g. counts, flags, id
    out[col] = out[col].fillna(0).astype("int64")

# (b) Nullable(Float64) columns: send Python None (-> SQL NULL), never NaN.
#     Build the records, then null out any remaining float NaN. Non-nullable
#     floats must never be NaN by construction, so this only touches genuinely
#     missing values.
records = [{k: (None if isinstance(v, float) and np.isnan(v) else v)
            for k, v in row.items()} for row in out.to_dict("records")]

con.execute(f"INSERT INTO {TABLE} VALUES", records)
```

Notes:
- `np.float64` **is** a subclass of `float`, so `isinstance(v, float)` catches
  numpy NaNs; `np.int64` is not, so ints (which support `__index__`) pass
  through and pack fine into `IntN`.
- On the FIRST successful write, pass `types_check=True` to `execute` — it's slow
  (per-value) but names the exact offending column/value. Drop it for the real
  bulk insert once types are clean.
- `datetime.date` (`pd.Timestamp(...).date()`) packs into a `Date` column; a
  full `Timestamp`/`datetime` goes into `DateTime`. Don't mix them.
- Decimal/object columns from a prior query often arrive as `object` dtype —
  `pd.to_numeric(col, errors="coerce")` them before the cast.

## 2. Idempotent writes — don't accumulate duplicates on re-run

A plain `MergeTree ORDER BY (id, timestp)` **appends**. Re-running the notebook
the same day writes a second full set of rows for that `timestp` — silent
duplication that doubles counts in every downstream read. During tuning you WILL
re-run. Pick one of:

**A. `ReplacingMergeTree` (preferred for a daily scored table).** Dedups rows
with identical `ORDER BY` keys, keeping the highest version.

```sql
CREATE TABLE IF NOT EXISTS db.artist_score (
    cm_artist Int64,
    score     Float64,
    ...,
    timestp   Date,
    _version  DateTime DEFAULT now()   -- tie-breaker: newest write wins
) ENGINE = ReplacingMergeTree(_version)
ORDER BY (cm_artist, timestp)
```

Re-running the same `(cm_artist, timestp)` overwrites on merge. **Caveat:**
dedup happens *asynchronously at merge time*, so reads can still see both rows
until merged — always read with `FINAL` (or `argMax(col, _version)` + `GROUP BY`)
when you need the deduped view, and/or `OPTIMIZE TABLE db.artist_score FINAL` to
force it. See `clickhouse.md` for the read-side dedup patterns.

**B. Delete-then-insert into a plain `MergeTree`.** Simpler to reason about; the
delete is an async mutation, so let it settle before the insert:

```python
run_ch(f"ALTER TABLE {TABLE} DELETE WHERE timestp = today()")   # clears today's rows
# ... then INSERT today's rows ...
```

**C. Idempotent by construction.** `CREATE OR REPLACE TABLE` (whole-table swap)
if you only ever keep the latest run and don't need history.

## 3. Ship it disabled

Keep the write cell fully commented-out with its DDL + INSERT (see
`workflow.md` §8). A reviewer enables it only after the sanity checks pass. Print
a harmless `"write-back disabled"` so the cell runs clean while disabled, and a
`f"wrote {len(records):,} rows"` once enabled.
