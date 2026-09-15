# Serving — secrets, ClickHouse, caching

## Secret names

Replit Secrets use the `CLICKHOUSE_*` spelling. The `CH_*` spelling belongs to the
`cm-jupyter` container and must never appear in anything destined for Replit.

| Replit Secret | Warehouse | Host |
|---|---|---|
| `CLICKHOUSE_HOST` `CLICKHOUSE_PORT` `CLICKHOUSE_USER` `CLICKHOUSE_PASSWORD` | rw-standard | `grkyl47mbo.us-west-2.aws.clickhouse.cloud` |
| `CLICKHOUSE_VERT_HOST` `CLICKHOUSE_VERT_USER` `CLICKHOUSE_VERT_PASSWORD` | vert | `j1ez4a7j4k.us-west-2.aws.clickhouse.cloud` |

`CLICKHOUSE_PORT` is `8443` (HTTPS interface).

Rules, all of which have been got wrong at least once:

- Read them with `process.env` in **server** code only.
- Do not rename them and do not prefix them so a bundler exposes them to the client.
  A `VITE_`-prefixed credential is a published credential.
- **No hardcoded fallback.** A missing secret fails loudly at boot. A fallback turns a
  configuration error into a wrong-warehouse connection that returns plausible rows.
- A build script that must run both in the notebook container and on Replit should try
  each name in turn (`CH_HOST`, then `CLICKHOUSE_HOST`, then `clickhouse_host`) rather
  than picking one.

### devin-secrets.env is not a dotenv file

`~/code/chartmetric/devin-secrets.env` stores values **unquoted and shell-escaped** — it
is a bash script. `clickhouse_password` contains a `\!` that `source` resolves to a bare
`!`. Anything that parses it as a plain dotenv (`python-dotenv`, `docker --env-file`, a
regex) passes a **wrong password** and gets `Code: 516 Authentication failed`, which
reads like a permissions problem and sends you looking in the wrong place.

Always `source` it. To hand credentials to a container, have bash write the env file
from the sourced variables (`printf 'k=%s\n' "$var" > file`), never by grepping the
original. Never echo the value to stdout.

Note it is mixed-case: lowercase `clickhouse_host` / `_user` / `_password`, but
uppercase `CLICKHOUSE_PORT` and `CLICKHOUSE_VERT_HOST`.

## Reachability and grants

ClickHouse Cloud is **internet-facing**. Every Chartmetric service carries `0.0.0.0/0`
in its `ipAccessList`, and rw-standard and ro-standard additionally carry an explicit
Replit egress address. A Replit app querying ClickHouse directly is established
practice — the constraints are credentials and grants, not network reach.

**The grant is the real blocker.** The shared `external_devin` account holds
`external_devin_access, read` and **cannot read `chartmetric_test`** — the database
where most DS write-back lands. `chartmetric_test` appears in its `SHOW DATABASES`, but
every table read fails (Code 497 on a granted table name, Code 60 otherwise), and it
cannot read `system.grants` to find out why. So either:

- get `GRANT SELECT ON chartmetric_test.<table> TO read`, or
- write the output somewhere already granted, or
- ship the static pack until one of those happens.

`external_devin` is also **HTTPS-only**. The native protocol on 9440 rejects it with the
same Code 516, so `clickhouse_driver.Client` fails while a curl to 8443 with identical
credentials succeeds. Personal accounts work on both. The HTTPS interface is the right
choice for an app regardless.

### The two warehouses cannot be joined

rw-standard and vert are separate ClickHouse Cloud warehouses. **No account has the
`REMOTE`/`SOURCES` grant**, so `remoteSecure()` federation is impossible for everyone.
If an app needs both, open two connections and merge in the server.

`SELECT 1` succeeds on both and cannot tell them apart. To confirm which warehouse you
reached, assert the expected database appears in `SHOW DATABASES`.

## The HTTPS interface

```
POST https://<host>:8443/?default_format=JSONEachRow
     &output_format_json_quote_64bit_integers=0
     &max_execution_time=30
Authorization: Basic base64(user:password)
body: the SQL
```

`output_format_json_quote_64bit_integers=0` makes 64-bit ids arrive as numbers rather
than strings — omit it and every artist id becomes a string halfway through the app.

**Parameterise, never interpolate.** Pass `{pid:UInt64}` in the SQL and `param_pid` in
the query string. The browser asks for an artist id; the server decides the SQL. Never
accept a query, a table name or a column name as a request parameter.

## Query patterns that keep coming back

**Dedupe discipline — get this wrong and every number is wrong.**

| Table shape | Read it as |
|---|---|
| Accumulates one row per entity per day (`timestp`) | `WHERE timestp = (SELECT max(timestp) FROM …)` |
| ReplacingMergeTree with `_loaded_at` / `created_at` | `FINAL`, or `argMax(col, ts) … GROUP BY key` |
| `cm_artist` and friends (un-merged duplicate ids) | `argMax(name, modified_at) … GROUP BY id` |

After caching, assert `COUNT(*) == COUNT(DISTINCT <key>)`. A missing `timestp` filter
once yielded ~3x duplicate rows, and every count and score derived from them was wrong.

`argMax` inside a `GROUP BY` is usually cheaper than `FINAL` for a single-key lookup,
and it is *required* for correctness if a write-back ever ran twice for one
`model_version` — summing undeduped long-format rows doubles every share.

**Pivot long-format tables server-side.** A 55M-row long table with the sorting key
starting at `profile_id` returns one artist in milliseconds if you `sumIf(weight,
demo_col = '…')` per column in the query. Selecting raw rows and pivoting in JS
transfers thousands of rows to do the same thing slower.

**Chunk id lists.** Never ship a 14k-element `IN (...)` literal — it is slow to parse
and a memory risk on the server. Chunk at ~2,000.

**Names and images.** Names from `chartmetric_raw_data.cm_artist` with
`argMax(name, modified_at)`. Images from
`chartmetric_analytics_flattened.f_artist_image` — **not** `cm_artist.image_url`, which
is populated for 0.03% of rows. Fall back to an initials avatar.

## Caching

The rule: **one bulk pull at boot, then serve from memory.** Never per keystroke, never
per slider frame, never per render.

- **The index** (the searchable list of scored entities — typically 14k–530k rows) loads
  once at boot and lives in memory. `/api/search?q=` filters that in-memory list,
  case-insensitive substring, capped at ~50 rows. Refresh it on an interval, not on a
  request.
- **Per-entity documents** are fetched on demand and cached for a few minutes.
- **Large populations** (hundreds of thousands of rows) go to a local store —
  SQLite/Postgres/Parquet — seeded on first run, plus a `data_meta` row holding the pull
  timestamp and the source `timestp`/`model_version`. Add a small "Refresh data from
  ClickHouse" admin button.
- **One model version at a time.** Read `max(model_version)` at boot and pin it for the
  process. A mid-session switch mixes two runs in one view.

### What must never become a fetch

If the browser can compute it in a few milliseconds, it must not round-trip. Scoring one
artist against 3,144 counties is ~88,000 multiply-adds — **1 to 4 ms measured in the
browser**, against 30–100 ms for a round trip plus a server process to keep alive. Do
the recompute client-side, in a Web Worker if the population is large, over typed arrays
rather than arrays of objects. Re-ranking ~500k artists on a slider change should be
under 100 ms; virtualize the table so rendering is not the bottleneck.

## Failure behaviour

- **Fail visibly.** If the query errors, say the data source is unavailable. Never fall
  back to a cached entity and present it as live.
- **Fail at boot on missing configuration**, not on first request.
- **Never fabricate.** A `null` field renders its empty state. No simulated series, no
  placeholder trendline, no invented sample.
