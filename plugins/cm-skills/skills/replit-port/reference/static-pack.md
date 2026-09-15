# The static pack

Take this path when the app must run without credentials, when the snapshot must not
change under a demo, or when the grant the direct path needs does not exist yet.
Otherwise prefer direct ClickHouse — see `reference/serving.md`.

## Two layouts

Pick by how the app reads the data, not by size.

### Sharded JSON — for per-entity documents

When the app shows one entity at a time and each entity is a rich document.

```
data/manifest.json     counts, model_version, shard_size, coverage, notes — read first
data/index.json        one lean row per entity, for the picker
data/shards/<n>.json   { "<id>": <entity document>, ... }
```

Loading rules, which belong verbatim in the prompt:

1. On boot fetch **`manifest.json` and `index.json` only**.
2. On selection fetch `shards/<row.shard>.json`, keep it in a map keyed by shard number,
   read the entity out. Later entities in the same shard need no fetch.
3. **Never fetch all shards** and never build a combined in-memory object of every
   entity. The index is the only thing fully resident.

Index rows stay lean — id, name, a coverage bitmask/flags, and the shard number. Images
live in the document, not the index; the picker shows a placeholder until the shard
loads. Shard size ~250 documents.

### Typed-array matrix — for whole-population maths

When the app scores one entity against every row of a fixed matrix on every interaction.

```
data/areas.f32      3,144 areas × 32 cells, Float32, row-major
data/areas.json     one metadata row per area
data/artists.f32    4,855 artists × the same 32 cells
data/artists.json   id, name, size, a block-presence bitmask
data/manifest.json  cell layout, weights, baseline, provenance
data/parity.json    notebook-computed values asserted on load
```

- Fetch `.f32` with `arrayBuffer()` into a `Float32Array`. **Never** convert to JSON or
  to arrays of objects — that is the entire performance argument.
- Serve `.f32` as `application/octet-stream`.
- **`manifest.json` is the authority on the cell layout.** Nothing hardcodes offsets.
- Ship **raw shares, not precomputed ratios**, when one matrix can then serve several
  scoring modes. Deriving the ratio at load costs under a millisecond.
- Serve `data/*` with gzip.

## Blocks are not dimensions

The trap worth stating loudly in every prompt that has it: when a dimension ships two
label frames (a current taxonomy and a legacy one), the manifest carries **more blocks
than dimensions**. Exactly one frame is present per entity.

Expose `dimNames`, `blockFor()`, `dimsPresent()` and a `byDim` field on result rows, and
tell the agent to use them **rather than indexing the block list positionally** — or the
UI renders two columns for one dimension and mislabels every entity.

This is not hypothetical. A pack once exported only the newer frame, silently stripping
that dimension from 24% of entities. Coverage went from 4,853/4,855 down to 3,697/4,855
and the affected maps degenerated into an unrelated signal. Check coverage per block
against the notebook's own numbers after every export.

## The exporter

`scripts/export_pack.py` — stdlib only, HTTPS, read-only, nothing writes to any
database. Conventions it follows and yours should too:

- **Re-run the notebook's own cells** for config, coercion and scoring rather than
  reimplementing them, so the pack cannot drift from the notebook's definitions. This
  also gives the parity fixture for free.
- **Print the account actually in use** on the first line. The credential chain prefers
  `CH_USER` over the `clickhouse_user` in devin-secrets.env, so the same command picks a
  different account depending on the shell — and only one of them can read
  `chartmetric_test`.
- **Refuse to write a pack that looks healthy and is empty.** If no entity carries the
  thing the pack exists to carry, exit with a message naming the account, the table and
  the version filter. A pack of nulls renders an empty card everywhere and goes
  unnoticed for a week.
- **Chunk id lists** at ~2,000 before they become an `IN` literal.
- **Bounded first pass.** Always support `--limit` so a full export is never the first
  thing you run.
- Write `manifest.json` with counts, coverage per block/pillar, the source version, the
  generation timestamp, and a `notes` array naming what the pack deliberately lacks.

Refresh:

```bash
source ~/code/chartmetric/devin-secrets.env
python3 scripts/export_pack.py --all --limit 500     # bounded first
python3 scripts/export_pack.py --all                 # then the whole thing
cd .. && zip -r <project>-replit.zip replit -x '*.pyc' '*/__pycache__/*'
```

## What a pack must not be used for

State both in the prompt:

- **No catalogue-wide aggregates.** A pack covers the entities one model run scored, not
  a sample designed to be representative. Any leaderboard, average or "entities like
  this" built across it is misleading.
- **No inferred trend.** Two different `as_of` values, or a `generated_at`, are not a
  time series. If there is one snapshot per source, render the "historical data not
  available" empty state and do not simulate a series.

And say plainly in the coverage panel that an absent entity means *not scored by this
run*, not *has no audience*.
