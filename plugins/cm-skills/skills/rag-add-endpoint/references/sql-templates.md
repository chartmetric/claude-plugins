# Schemas & templates

These are reconstructed from the repos (chartmetric-one `shared/api-registry.ts`,
chartmetric-one `data/seed-sitemap-features.sql`, chartmetric_data_script
`metadata/sitemap/`, admini-tool `server/external-db/sitemap.ts`). **Verify column names
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

- **`chartmetric.sitemap`**: `id`, `entity_type`, `page_name`, `url_pattern`, `page_type`, `product_type`, `modified_at`
- **`chartmetric.sitemap_feature`**: `id`, `search_text`, `feature_name`, `feature_description`, `feature_description_rich`, `html_label`, `sitemap` (FK → sitemap.id), `feature_icon`, `tooltip_text`, `visualization_type`, `modified_at`
- **`chartmetric.sitemap_feature_apis`**: `id`, `api_method` (enum `chartmetric.api_method`), `endpoint_path`, `service` (`main`|`flow`), `api_description`, `is_internal`, `sample_response`
- **`chartmetric.sitemap_feature_api_parameters`**: FK to `sitemap_feature_apis`, `name`, `in` (`path`|`query`|`body`|`header`), `required`, `type` — managed by the Swagger DAG for `main`; verify columns before touching
- **`chartmetric.l_sitemap_feature_apis`**: `sitemap_feature` (FK), `sitemap_feature_apis` (FK), `is_used_for_artist_ai_insights`

## FLOW track — api-registry.ts entry shapes

`chartmetric-one/shared/api-registry.ts` (edit these arrays; this is the committed change):

```ts
// sitemapPages[]  (add only if the feature needs a new page)
{ urlPattern: "/some/route/:id", pageName: "…", entityType: "artist", pageType: "…", productType: "one" }

// sitemapApis[]  (the endpoint)
{ apiEndpoint: "/api/music/…", apiMethod: "GET", apiDescription: "…", isInternal: true,
  parameters: [ { key: "id", type: "string", required: true, in: "path" } ] }

// sitemapFeatures[]  (the semantic doc — featureDescriptionRich is what gets embedded)
{ htmlLabel: "one-…", featureName: "…", featureDescription: "…",
  featureDescriptionRich: "Specific: what data, which platforms, what a user would ask.",
  searchText: "keywords a user might use", featureIcon: "BarChart3",
  tooltipText: "…", visualizationType: "table", sitemapUrlPattern: "/some/route/:id" }

// featureApiLinks[]  (feature ↔ endpoint)
{ featureHtmlLabel: "one-…", apiEndpoint: "/api/music/…", apiMethod: "GET", isUsedForArtistAiInsights: 0 }
```

Regenerate the SQL for the PR body (committed artifact is still only `api-registry.ts`):
```bash
cd chartmetric-one && npx tsx scripts/generate-sitemap-sql.ts
```

## MAIN track — reviewable Postgres SQL

For a `main` endpoint already present in `sitemap_feature_apis` (auto-synced from Swagger),
add a feature and link it. Run inside one transaction; apply via admini-tool / DBA.

```sql
BEGIN;

-- 1. Page (reuse if one already fits; otherwise create). Grab its id.
--    SELECT id FROM chartmetric.sitemap WHERE url_pattern = '/artist/:id' AND product_type = 'main';
INSERT INTO chartmetric.sitemap (entity_type, page_name, url_pattern, page_type, product_type)
VALUES ('artist', 'Artist Albums', '/artist/:id/albums', 'detail', 'main')
ON CONFLICT DO NOTHING;

-- 2. Feature (feature_description_rich is embedded — make it specific).
INSERT INTO chartmetric.sitemap_feature
  (search_text, feature_name, feature_description, feature_description_rich,
   html_label, sitemap, feature_icon, tooltip_text, visualization_type)
VALUES
  ('artist albums discography releases',
   'Artist Albums',
   'All albums/releases for an artist with release dates and metadata.',
   'Returns the full discography for an artist: album titles, release dates, label, track counts, and cover art. Use when a user asks about an artist''s albums, releases, or discography.',
   'artist-albums',
   (SELECT id FROM chartmetric.sitemap WHERE url_pattern = '/artist/:id/albums' AND product_type = 'main'),
   'Disc', 'View an artist''s albums and releases', 'table')
RETURNING id;   -- ← new feature id

-- 3. Link feature ↔ endpoint. Resolve the endpoint id first:
--    SELECT id FROM chartmetric.sitemap_feature_apis
--    WHERE service = 'main' AND endpoint_path = '/artist/:id/albums' AND api_method = 'GET';
INSERT INTO chartmetric.l_sitemap_feature_apis
  (sitemap_feature, sitemap_feature_apis, is_used_for_artist_ai_insights)
VALUES (<new_feature_id>, <endpoint_id>, 0)
ON CONFLICT DO NOTHING;

COMMIT;
```

Notes:
- `endpoint_path` placeholder convention: `main` uses `{id}` in some readers but the catalog
  stores service-specific forms — check an existing row for the exact stored format before
  matching/inserting.
- If step 3's endpoint lookup returns nothing, the endpoint isn't in Swagger yet → it must be
  documented in the Chartmetric API Swagger first (then the Friday `Sync_Sitemap_Metadata`
  DAG creates the row). That is the "build/document the API first" case.

## Read-side references (for verifying discovery)

- Retrieval query builder: `melodi-worker/utils/clickhouse/sitemap_queries.py`
- Vectorizer: `melodi-worker/scripts/embedding/revectorize_sitemap_features.py`
- Embedding DAG: `chartmetric_data_script/dags_data_science/rags/update_rag_embeddings.py` (Sundays)
- Swagger sync DAG: `chartmetric_data_script/dags/sitemap/sync_sitemap_metadata_from_swagger.py` (Fridays)
- PG→CH sync list: `data_infra/constants/sync/pg_to_ch_daily.py`
