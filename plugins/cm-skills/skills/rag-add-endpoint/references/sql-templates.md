# Schemas & templates

These are reconstructed from the repos (chartmetric-flow `shared/api-registry.ts` and
`scripts/generate-sitemap-sql.ts`, chartmetric_data_script `metadata/sitemap/`, admini-tool
`server/external-db/sitemap.ts`). **Verify column names
against the live schema before running any SQL** — read-only, e.g.:

```bash
source ~/code/chartmetric/devin-secrets.env && \
curl -sS "${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}/?readonly=1" \
  -u "${clickhouse_user}:${clickhouse_password}" \
  --data-binary "DESCRIBE chartmetric_raw_data.sitemap_feature FORMAT PrettyCompact"
```
(Repeat for `sitemap`, `sitemap_feature_apis`, `sitemap_feature_api_parameters`,
`l_sitemap_feature_apis`. All SQL below is written for the **Postgres** source of truth —
schema `chartmetric` — never for ClickHouse.)

## Table columns (as observed)

- **`chartmetric.sitemap`**: `id`, `entity_type`, `page_type`, `page_name`, `url_pattern`, `product_type` (`main`|`flow`|`sports`), `created_at`, `modified_at` — unique on `(url_pattern, product_type)`
- **`chartmetric.sitemap_feature`**: `id`, `feature_name`, `feature_description`, `feature_description_rich`, `html_label` (unique), `sitemap` (FK → sitemap.id), `feature_icon`, `tooltip_text`, `visualization_type`, `image_screenshot`, `created_at`, `modified_at` — there is no `search_text` column
- **`chartmetric.sitemap_feature_apis`**: `id`, `api_method` (enum `chartmetric.api_method`), `endpoint_path`, `service` (`main`|`flow`), `api_description`, `is_internal`, `sample_response`, `updated_by`, `created_at`, `modified_at` — unique on `(service, endpoint_path, api_method)`
- **`chartmetric.sitemap_feature_api_parameters`**: `id`, `sitemap_feature_apis` (FK), `key`, `type`, `required`, `constraints` (jsonb), `in` (enum: `path`|`query`|`body`|`header`) — unique on `(sitemap_feature_apis, key, "in")`; managed by the Swagger DAG for `main`
- **`chartmetric.l_sitemap_feature_apis`**: `id`, `sitemap_feature` (FK), `sitemap_feature_apis` (FK), `is_used_for_artist_ai_insights`, `created_at`, `modified_at` — unique on `(sitemap_feature, sitemap_feature_apis)`

## FLOW track — api-registry.ts entry shapes

`chartmetric-flow/shared/api-registry.ts` (edit these arrays; this is the committed change).
Existing `htmlLabel`s mostly use a `one-` prefix; follow the prefix of neighboring entries.

```ts
// sitemapPages[]  (add only if the feature needs a new page)
{ urlPattern: "/some/route/:id", pageName: "…", entityType: "artist", pageType: "…", productType: "flow" }

// sitemapApis[]  (the endpoint)
{ apiEndpoint: "/api/music/…", apiMethod: "GET", apiDescription: "…", isInternal: true,
  parameters: [ { key: "id", type: "string", required: true, in: "path" } ] }

// sitemapFeatures[]  (the semantic doc — featureDescriptionRich is what gets embedded)
{ htmlLabel: "one-…", featureName: "…", featureDescription: "…",
  featureDescriptionRich: "Specific: what data, which platforms, what a user would ask.",
  searchText: "keywords a user might use",  // registry-only; not written to Chartmetric Postgres
  featureIcon: "BarChart3",
  tooltipText: "…", visualizationType: "table", sitemapUrlPattern: "/some/route/:id" }

// featureApiLinks[]  (feature ↔ endpoint)
{ featureHtmlLabel: "one-…", apiEndpoint: "/api/music/…", apiMethod: "GET", isUsedForArtistAiInsights: 0 }
```

Regenerate the SQL for the PR body (committed artifact is still only `api-registry.ts`).
The output covers the whole registry and ends with DELETEs for `flow`/`sports` rows not in
it, so excerpt only the new statements:
```bash
cd chartmetric-flow && npx tsx scripts/generate-sitemap-sql.ts
```

## MAIN track — reviewable Postgres SQL

For a `main` endpoint already present in `sitemap_feature_apis` (auto-synced from Swagger),
add a feature and link it. Run inside one transaction; apply via admini-tool / DBA.
`main` paths and page patterns use `{param}` placeholders (e.g. `/artist/{id}/albums`,
`/artist/{artist_id}`), not `:param`.

```sql
BEGIN;

-- 1. Page (reuse if one already fits; otherwise create). Grab its id.
--    SELECT id FROM chartmetric.sitemap WHERE url_pattern = '/artist/{artist_id}' AND product_type = 'main';
INSERT INTO chartmetric.sitemap (entity_type, page_name, url_pattern, page_type, product_type)
VALUES ('artist', 'Artist Albums', '/artist/{artist_id}/albums', 'detail', 'main')
ON CONFLICT (url_pattern, product_type) DO NOTHING;

-- 2. Feature (feature_description_rich is embedded — make it specific).
INSERT INTO chartmetric.sitemap_feature
  (feature_name, feature_description, feature_description_rich,
   html_label, sitemap, feature_icon, tooltip_text, visualization_type)
VALUES
  ('Artist Albums',
   'All albums/releases for an artist with release dates and metadata.',
   'Returns the full discography for an artist: album titles, release dates, label, track counts, and cover art. Use when a user asks about an artist''s albums, releases, or discography.',
   'artist-albums',
   (SELECT id FROM chartmetric.sitemap WHERE url_pattern = '/artist/{artist_id}/albums' AND product_type = 'main'),
   'Disc', 'View an artist''s albums and releases', 'table')
RETURNING id;   -- ← new feature id

-- 3. Link feature ↔ endpoint. Resolve the endpoint id first:
--    SELECT id FROM chartmetric.sitemap_feature_apis
--    WHERE service = 'main' AND endpoint_path = '/artist/{id}/albums' AND api_method = 'GET';
INSERT INTO chartmetric.l_sitemap_feature_apis
  (sitemap_feature, sitemap_feature_apis, is_used_for_artist_ai_insights)
VALUES (<new_feature_id>, <endpoint_id>, 0)
ON CONFLICT DO NOTHING;

COMMIT;
```

Notes:
- `endpoint_path` placeholder convention: `main` rows store `{param}` and `flow` rows store
  `:param`. Check an existing row for the exact stored path before matching/inserting.
- If step 3's endpoint lookup returns nothing, the endpoint isn't in Swagger yet → it must be
  documented in the Chartmetric API Swagger first (then the Friday `Sync_Sitemap_Metadata`
  DAG creates the row). That is the "build/document the API first" case.

## Read-side references (for verifying discovery)

- Retrieval query builder: `melodi-worker/utils/clickhouse/sitemap_queries.py`
- MCP retrieval: `chartmetric-mcp/src/tools/search_sitemap.py`
- Vectorizer: `chartmetric_data_script/data_science/llm/rags/sitemap_rag.py`
- Embedding DAG: `chartmetric_data_script/dags_data_science/rags/update_rag_embeddings.py` (Sundays)
- Swagger sync DAG: `chartmetric_data_script/dags/sitemap/sync_sitemap_metadata_from_swagger.py` (Fridays)
- Feature reconcile DAG: `chartmetric_data_script/dags_data_science/reconcile_sitemap_features.py` (Saturdays, dry run)
- PG→CH sync list: `data_infra/constants/sync/pg_to_ch_daily.py`
