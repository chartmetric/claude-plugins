---
name: rag-add-endpoint
description: Add an existing Chartmetric API endpoint to the Flow AI / Melodi assistant's RAG knowledge base (the ClickHouse-backed "sitemap"). First checks feasibility — whether a suitable live endpoint already exists, else reports that the API must be built first — then produces the exact Postgres changes and a PR in the correct repo (edit chartmetric-one's api-registry.ts for `flow` endpoints; reviewable SQL + admini-tool for `main` endpoints), plus the re-vectorization/activation steps. Use when someone wants the assistant to be able to call, discover, or "know about" a new endpoint or data capability. Triggers - /rag-add-endpoint, "add an endpoint to the RAG / knowledge base / sitemap", "make Flow AI / Melodi aware of endpoint X", "integrate this API into the assistant".
---

# Add an Endpoint to the Flow AI / Melodi RAG Knowledge Base

## What the "RAG knowledge base" actually is (read this first)

The assistant does **not** have a hardcoded list of endpoints. It discovers them at
query time through a semantic index called the **sitemap**:

```
user question ──embed──▶ cosine-similarity vs vectorized FEATURES
                          │
                          ▼
              top sitemap_feature rows ──join via l_sitemap_feature_apis──▶ endpoints
                          │
                          ▼
        search_sitemap result → get_endpoint_details → call_read_api
```

Storage & flow of truth:

- **Source of truth = Postgres** (`chartmetric.sitemap*` tables).
- Synced **daily → ClickHouse** `chartmetric_raw_data.*` (`data_infra/constants/sync/pg_to_ch_daily.py`).
- Features are embedded into `chartmetric_analytics_flattened.vectorized_sitemap_feature_name_and_rich_description` by the **`Update_RAG_Embeddings` DAG (Sundays 00:00 UTC)**.
- Read by **both** `melodi-worker` and `chartmetric-mcp` (they only read — never PR the endpoint list into them).

The five tables (see `references/sql-templates.md` for columns):

| Table | Role |
|---|---|
| `sitemap` | Pages (entity_type, url_pattern, product_type) |
| `sitemap_feature` | **The semantic doc that gets embedded** (feature_name, feature_description_rich) |
| `sitemap_feature_apis` | The endpoints (api_method, endpoint_path, service, api_description, is_internal) |
| `sitemap_feature_api_parameters` | Endpoint parameters (for get_endpoint_details) |
| `l_sitemap_feature_apis` | Link: feature ↔ endpoint (many-to-many) |

**The rule that governs everything:** `search_sitemap` matches on **features**, then joins
to endpoints. An endpoint row with **no linked feature is invisible to the RAG**, even if it
is in `sitemap_feature_apis`. So "adding an endpoint" almost always means: make sure a
**feature exists with a strong rich description**, and **link it** to the endpoint.

## Two tracks — decided by the endpoint's `service`

| | `flow` service (chartmetric-one) | `main` service (chartmetric-api) |
|---|---|---|
| Endpoint origin | Declared in code: `shared/api-registry.ts` | Auto-ingested from **Swagger** by the `Sync_Sitemap_Metadata` DAG (Fridays 00:00 UTC) |
| How you add | **Edit `api-registry.ts` → PR to chartmetric-one** | Endpoint appears automatically once in Swagger; the **feature + link** is manual |
| Applied to Postgres by | "Sync to RDS" button in chartmetric-one `/admin` → APIs tab | admini-tool ("Sync to RDS") or reviewable SQL |
| Clean code PR exists? | **Yes** (edit api-registry.ts) | **No** — feature/link is pure data; deliver SQL |

Most "Flow AI" requests are `flow` endpoints — the clean path. `main` endpoints are
data-only additions.

## Step 0 — Prerequisites

- Feasibility checks need **read-only DB access**. This works only in a **local session**
  with `~/code/chartmetric/devin-secrets.env`. If the file is missing you are likely in a
  cloud session — tell the user to switch to Local (see the `query-database` skill), or fall
  back to source-only checks (Swagger + api-registry.ts) and clearly label the KB state as
  "unverified".
- **Never write to any database.** This skill only ever emits SQL for a human to run. All
  DB access is `SELECT`/`DESCRIBE` with the read-only guard (`?readonly=1` for ClickHouse).

## Step 1 — Pin down the ask

The user gives you either:

- **A specific endpoint** (`GET /api/music/artist-sparklines`, or `main` `/artist/{id}/albums`) → go straight to Step 2.
- **A capability** ("let the assistant know an artist's playlist adds") → you must first
  *find* an endpoint that already serves it (Step 2 doubles as the search). If none exists,
  that is the "build the API first" answer.

Also capture the intended **feature description** — what the endpoint returns and when the
assistant should reach for it. This becomes the embedded text and directly determines
retrieval quality. If the user didn't give one, draft it and confirm.

## Step 2 — Classify service + feasibility gate

Determine whether a real, live endpoint exists. Requirement #1 of the output is answered here.

1. **Classify service.** `flow` paths are chartmetric-one routes (typically `/api/...`,
   `service: flow`); `main` paths are chartmetric-api routes (`service: main`). If unsure,
   the catalog query below returns the stored `service`.
2. **Check the live catalog** (read-only ClickHouse — the mirror of what the assistant sees):
   ```bash
   source ~/code/chartmetric/devin-secrets.env && \
   curl -sS "${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}/?readonly=1" \
     -u "${clickhouse_user}:${clickhouse_password}" \
     --data-binary "SELECT service, api_method, endpoint_path, is_internal
       FROM chartmetric_raw_data.sitemap_feature_apis
       WHERE endpoint_path ILIKE '%<path-fragment>%' FORMAT PrettyCompact"
   ```
   (If `CLICKHOUSE_HOST` is already a full `https://host:port`, don't append the port.)
3. **Confirm it is a real route** when not already in the catalog:
   - `flow`: is it in `chartmetric-one/shared/api-registry.ts` (`sitemapApis`) or a real
     chartmetric-one server route?
   - `main`: is it documented in the Chartmetric API **Swagger** (the same source the
     `Sync_Sitemap_Metadata` DAG ingests)? A `main` endpoint that isn't in Swagger will
     never reach the sitemap.

**Gate outcomes:**

- **No live endpoint anywhere** → STOP. Report: *"Not possible yet — this needs a new API
  endpoint built first."* Say which service should own it and, for `main`, that it must be
  added to Swagger. Do not fabricate an endpoint.
- **Endpoint exists** → continue.

## Step 3 — Is it already in the RAG?

An endpoint is only discoverable if it is **linked to a feature**. Check:

```bash
source ~/code/chartmetric/devin-secrets.env && \
curl -sS "${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}/?readonly=1" \
  -u "${clickhouse_user}:${clickhouse_password}" \
  --data-binary "SELECT a.endpoint_path, a.service, f.id AS feature_id, f.feature_name
    FROM chartmetric_raw_data.sitemap_feature_apis a
    LEFT JOIN chartmetric_raw_data.l_sitemap_feature_apis l ON l.sitemap_feature_apis = a.id
    LEFT JOIN chartmetric_raw_data.sitemap_feature f ON f.id = l.sitemap_feature
    WHERE a.endpoint_path ILIKE '%<path-fragment>%' FORMAT PrettyCompact"
```

- **Feature already linked** → it is already discoverable. Report that; only proceed if the
  user wants a better/additional feature description.
- **Endpoint row but no linked feature** → you only need to add a **feature + link** (+ revectorize). Skip endpoint creation.
- **Nothing** → add endpoint (flow only) + feature + link.

## Step 4a — FLOW track: edit api-registry.ts, PR to chartmetric-one

This is the clean code path. Edit **`chartmetric-one/shared/api-registry.ts`** (clone it if
absent — `git clone git@github.com:chartmetric/chartmetric-one.git`; never skip silently):

- Add to **`sitemapApis`**: `{ apiEndpoint, apiMethod, apiDescription, isInternal, parameters }`
  (only if the endpoint isn't already there). Path params in the endpoint are auto-derived;
  list query/body params explicitly.
- Add to **`sitemapFeatures`** (if a new feature): a strong `featureName`,
  `featureDescription`, and especially **`featureDescriptionRich`** (this is embedded — make
  it specific: what data, what platforms, what the user would ask). Set `searchText`,
  `sitemapUrlPattern` (must match an existing `sitemapPages` entry — add one if needed),
  `visualizationType`, `featureIcon`, `tooltipText`.
- Add to **`featureApiLinks`**: `{ featureHtmlLabel, apiEndpoint, apiMethod, isUsedForArtistAiInsights }`.

Then generate the SQL for the PR body / response (requirement #3). The committed change is
**only `api-registry.ts`** — the SQL is for review; it is applied by the admin "Sync to RDS"
button, not by merging a `.sql` file (`data/seed-sitemap-features.sql` is deprecated):

```bash
cd chartmetric-one && npx tsx scripts/generate-sitemap-sql.ts   # prints the full SQL transaction
```

If tsx/node isn't available, hand-write the equivalent SQL from `references/sql-templates.md`.

PR (follow the repo's own CLAUDE.md; branch `feat/<short-desc>`), body must include:
the endpoint, the feature + rich description rationale, the generated SQL, and the
activation steps from Step 5. Then tell the user to click **"Sync to RDS"** in
chartmetric-one `/admin` → APIs tab after merge.

## Step 4b — MAIN track: reviewable SQL + admini-tool

`main` endpoints auto-arrive from Swagger, so there is **no code registry to PR**. The
feature + link is pure Postgres data. Produce reviewable SQL (from
`references/sql-templates.md`, columns verified against the live schema — see Rules):

1. Reuse or `INSERT` a `sitemap` page row for where this feature lives.
2. `INSERT` a `sitemap_feature` (with a strong `feature_description_rich`).
3. `INSERT` a `l_sitemap_feature_apis` row linking the new feature to the endpoint's
   `sitemap_feature_apis.id` (look up that id; the endpoint row itself comes from the Friday
   Swagger sync — if it's missing, the endpoint isn't in Swagger yet → back to Step 2's gate).

Deliver the SQL in the response and tell the user to apply it via **admini-tool** (the
Sitemap Features page / "Sync to RDS"), which is the supported human path. Only open a code
PR here if the user also wants a melodi-worker/chartmetric-mcp description override
(`_API_DESCRIPTION_OVERRIDES`) — that's optional polish, not required for discovery.

## Step 5 — Activation timeline (state this every time)

Adding the rows does not make the endpoint discoverable instantly:

1. Apply to **Postgres** (Sync to RDS / run the SQL).
2. **Daily PG→CH sync** mirrors it to ClickHouse (~24h).
3. **`Update_RAG_Embeddings` DAG (Sundays 00:00 UTC)** embeds the new feature.

So the endpoint typically becomes retrievable **after the next Sunday embedding run**. If
sooner is needed, the embedding DAG / `revectorize_sitemap_features.py` can be triggered
manually by the data team — mention this, don't do it yourself.

## Step 6 — Report (the three required outputs)

1. **Feasibility verdict** — possible (endpoint X, service Y) or "build the API first" (+ what's needed).
2. **The PR** — link to the chartmetric-one PR (flow), or state that main is data-only with no code PR.
3. **The DB queries** — the SQL, inline in the response, and the activation timeline.

## Rules

- Read-only DB access only. Emit SQL; never execute a write. Keep the ClickHouse `?readonly=1` guard.
- **Verify column names against the live schema before finalizing SQL** — the templates in
  `references/sql-templates.md` are reconstructed and can drift. Confirm with
  `DESCRIBE chartmetric_raw_data.sitemap_feature` etc. (read-only).
- Never PR the endpoint list into melodi-worker or chartmetric-mcp — they only read the sitemap.
- Never insert directly into ClickHouse — the daily sync overwrites it. Postgres is the source of truth.
- The `featureDescriptionRich` / `feature_description_rich` is the single biggest lever on
  retrieval quality — invest in it, and confirm it with the user.
- If chartmetric-one isn't cloned for the flow track, give the exact `git clone` command; don't skip.
