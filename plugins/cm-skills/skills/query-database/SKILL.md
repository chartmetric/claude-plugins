---
name: query-database
description: Run READ-ONLY queries against Chartmetric datastores (Postgres/RDS, ClickHouse, Snowflake, Elasticsearch) using credentials from devin-secrets.env. Use when the user asks to query, look up, count, or analyze data in a database. Only works in LOCAL sessions — in cloud sessions, tell the user how to switch.
---

# Query Chartmetric Databases (read-only)

## 0. Environment check — do this FIRST

```bash
test -f ~/code/chartmetric/devin-secrets.env && echo SECRETS_OK || echo NO_SECRETS
```

If `NO_SECRETS`:
- **You are probably in a cloud session** (cloud sessions run on Anthropic's servers and cannot see the user's machine). STOP and tell the user: "Database queries need a local session. Start a new session, click the ☁️ environment pill → **Local** → **Select folder** → `~/code/chartmetric`, then ask me again."
- If the session IS local and the file just doesn't exist, point the user to onboarding to get `devin-secrets.env` into `~/code/chartmetric/`.
- **Never** work around this by asking the user to paste credentials into the chat or into a cloud environment's env vars.

## 1. Load credentials safely

- `source ~/code/chartmetric/devin-secrets.env` **inside the same Bash invocation** that runs the query (shell state doesn't persist between tool calls).
- Variable names differ per datastore. If unsure of exact names, list names only — never values:
  ```bash
  grep -oE '^[A-Za-z_][A-Za-z0-9_]*=' ~/code/chartmetric/devin-secrets.env | sed 's/=$//'
  ```
- Never echo, log, or write credential values anywhere. Refer to them only as `$VAR_NAME`.

## 2. Query per datastore — always with a read-only guard

**Postgres / RDS** (`DB_*` / `RDS_*` vars) — force a read-only transaction at the protocol level:
```bash
source ~/code/chartmetric/devin-secrets.env && \
PGOPTIONS='-c default_transaction_read_only=on' \
psql "host=$DB_HOST port=$DB_PORT dbname=$DB_NAME user=$DB_USER password=$DB_PASSWORD" \
  -c "SELECT ... LIMIT 100;"
```
(Adjust var names to what the file actually contains. If `psql` is missing: `brew install libpq && brew link --force libpq`.)

**ClickHouse** (`CLICKHOUSE_*` / `CH_*` vars) — append `readonly=1` so the server itself rejects writes:
```bash
source ~/code/chartmetric/devin-secrets.env && \
curl -sS "${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}/?readonly=1" \
  -u "${clickhouse_user}:${clickhouse_password}" \
  --data-binary "SELECT ... LIMIT 100 FORMAT PrettyCompact"
```
(If `CLICKHOUSE_HOST` is already a full `https://host:port` URL, don't append the port again.)

**Elasticsearch** (`ELASTIC_*` vars) — GET/`_search` endpoints only:
```bash
source ~/code/chartmetric/devin-secrets.env && \
curl -sS -u "${ELASTIC_USER}:${ELASTIC_PASSWORD}" \
  "${ELASTIC_HOST}/<index>/_search?size=20" -H 'Content-Type: application/json' -d '{"query": ...}'
```
Never call `_delete_by_query`, `_update_by_query`, `_bulk`, or any PUT/POST/DELETE that mutates.

**Snowflake** (`SNOWFLAKE_*` / `SF_*` vars) — use `snowsql` if installed (key-pair auth uses `~/code/chartmetric/chartmetric-infra/local/rsa_key.p8`); if not installed, say so and offer the Postgres/ClickHouse equivalent instead of improvising a connector.

## 3. Rules

- `SELECT` / `SHOW` / `DESCRIBE` / `EXPLAIN` only. Never INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE, and never remove the read-only guards above.
- Default to `LIMIT 100`; raise only if the user asks.
- Before running a query that scans a huge table (no index filter, cross joins), warn about the cost and confirm.
- Present results as a compact table + a one-line takeaway; offer to save large outputs to a file.
