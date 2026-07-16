# Validation, sanity & explainability

The point of these is to make the notebook *distrust itself* until proven right.

## 1. Freshness sentinels (highest-value check)

Derived/"analytics" tables freeze silently — the ETL job stops, the table keeps
serving its last snapshot, and every number downstream looks plausible while
being months old. **Always print `max(<date>)` for every source.**

```python
for label, tbl, datecol in SOURCES:            # SOURCES from §1
    mx = query_df(f"SELECT max({datecol}) AS d FROM {tbl}")["d"].iloc[0]
    lag = (pd.Timestamp.today().normalize() - pd.Timestamp(mx)).days
    flag = "  <-- STALE" if lag > STALE_DAYS else ""
    print(f"{label:28s} max={mx}  ({lag}d old){flag}")
```

Real case: an `artist_discovery_*` mirror was **7 months stale** while its raw
input tables were current. The freshness print is what surfaced it. When a
derived table is stale but its inputs are fresh, **recompute from the inputs**.

## 2. Schema verification

Assert every dependency before heavy work:

```python
cols = [r[0] for r in c.execute(
    f"SELECT name FROM system.columns WHERE database='{db}' AND table='{tbl}'")]
for col in needed:
    assert col in cols, f"'{col}' missing on {db}.{tbl} — depends on it"
```

Discover, don't assume, when a table's location varies (query `system.tables`).

## 3. As-of validation of a recompute

When you replace a stored metric with a from-raw recompute, prove the recompute
is faithful by reproducing the stored value **as of the stored table's own
date** (not today — the stored table is frozen). Compute your formula with the
window/anchor shifted to the frozen date and compare:

```python
# stored value (frozen date) vs recompute-as-of(frozen date) should match
```

Real case: a playlist-adoption slope recomputed server-side matched the stored
`slope_90` to ~3 significant figures once computed as-of the frozen date —
confirming the closed-form derivation before trusting today's fresh output.

## 4. Sanity diagnostics for scores

- **Distribution** — histogram + summary; watch for pile-ups at 0/100 or NaNs.
- **Coverage** — fraction of the population with each signal/pillar present. A
  large "missing everything" segment means the score isn't really measuring
  those rows.
- **Expected correlations, with the right sign.** State the hypothesis and test
  it (e.g. a per-fan score should correlate ~0 with audience size).
- **Leak localization** — for a size/peer-neutral score, compute *within-group*
  correlation of each component vs the confounder (e.g. within-bin Spearman vs
  log-size, Fisher-averaged). A component that stays correlated *within* peer
  groups is genuinely re-measuring the confounder — localize which one and fix
  it at the source, don't tune it away.
- **Convergent validity** — if two signals claim to measure the same construct,
  check they actually agree; if they don't, treat them as complementary, not
  redundant (and don't expect one to validate the other).

## 5. Whole-population guardrail

Percentiles, quantile bins, and peer-group medians are defined over the **entire
eligible population at once**. Never compute a normalization on a batch/chunk and
concatenate — batch-relative percentiles corrupt every score. If the data
doesn't fit in memory for a normalization, that's a design problem to solve
(sample the ranks, or push the rank server-side), not something to shard.

## 6. Zero-heavy signal normalization (a conservation law)

For a signal where "zero" is common and participation is correlated with the
confounder (e.g. only bigger artists have any TikTok adoption), you cannot
simultaneously have all three of: (a) zeros mapped to a constant across groups,
(b) flat per-group means, and (c) positives ranked above zeros. Pinning zeros to
an absolute 0 breaks (b) — groups with more participants get higher means, a
between-group ladder that per-group normalization can't remove. **Prefer a plain
within-group percentile rank with average ties:** the zero block lands at the
midpoint of its own mass, every group's mean is 50 by construction, and
positives still outrank zeros. Verify at the *composite* level, not the single
signal — a rank that looks anti-correlated alone can cancel correctly once
combined.

## 7. Determinism

Stable sort keys, pinned windows, `today()`-relative dates documented in §1, no
reliance on row order from the DB. Re-running should reproduce the scores.
