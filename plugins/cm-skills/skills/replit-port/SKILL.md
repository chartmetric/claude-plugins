---
name: replit-port
description: Port a Chartmetric data-science notebook into a Replit app — scaffold the server that holds the ClickHouse secrets, write the house-style PROMPT.md for Replit's agent, build the parity fixture that proves the app reproduces the notebook, and carry the notebook's caveats onto the screen. Use when turning a DS notebook, score, or model into a Replit dashboard/explorer, writing or updating a Replit build prompt, exporting a static data pack for Replit, or wiring a Replit app to ClickHouse.
---

# Replit Port

Turn a finished DS notebook into an internal Replit app **without the app and the
notebook drifting apart**. The notebook stays the source of truth; the app is a
viewer over it, and it proves that claim on every load.

This skill encodes what the fan-intensity, international-score, demographic-geo and
three-pillar-audience ports converged on over four rounds of hand-iteration.

## When to use this

- A notebook has produced a score, a model output or a write-back table, and it now
  needs a UI a PM can click through.
- Writing a Replit build prompt, or an **update** prompt for an app that already exists.
- Wiring a Replit app to ClickHouse, or exporting a static pack for one.
- The app's numbers stopped matching the notebook's.

## The four non-negotiables

Every port re-does these by hand. Do them from the start instead.

1. **Secrets and SQL live on the server.** The browser never sees a credential and
   never names a table. Replit Secrets are spelled `CLICKHOUSE_HOST` / `_PORT` /
   `_USER` / `_PASSWORD` (and `CLICKHOUSE_VERT_*` for the vert warehouse) — never the
   `CH_*` spelling the notebook container uses. Missing secret = loud failure at boot,
   never a hardcoded fallback. Queries are parameterised, never interpolated, and the
   account is SELECT-only. → `reference/serving.md`
2. **Pull once, cache, serve from cache.** No database round trip per keystroke, per
   slider frame, or per render. Boot-time bulk pull into memory or a local store, an
   explicit "Refresh data" admin action, and per-artist responses cached for minutes.
   Anything the browser can compute in under ~5 ms must not become a fetch.
   → `reference/serving.md`
3. **A parity check, visible in the UI.** The app recomputes a fixture of notebook-
   computed values on load and shows a green/red badge with the point count. If it goes
   red, every number on screen is suspect and the UI must say so. This is the only
   thing standing between a port and silent divergence. → `reference/parity.md`
4. **Explainability is the feature, not the polish.** Every number has a tooltip,
   every tooltip's copy lives in one glossary module, and the notebook's limitations
   render *on the page* — not behind a link, not paraphrased, not trimmed.
   → `reference/explainability.md`

## First moves

1. **Read the notebook, not just its output table.** You need: the exact recompute
   math the app will re-run, the write-back table and its `model_version` / `timestp`
   discipline, and — most importantly — every caveat the notebook's §7 sanity section
   turned up. Those caveats are the app's copy.
2. **Decide the data path.** Direct ClickHouse is the default (see below). Take the
   static pack only for a specific reason — the app must run credential-less, the
   snapshot must be frozen for a demo, or the grant doesn't exist yet.
3. **Check the grant before promising the direct path.** The shared `external_devin`
   account **cannot read `chartmetric_test`**, which is where most DS write-back lands.
   `SELECT currentUser()` and one real `SELECT` against the actual table, from the
   account the app will use, before writing a line of prompt. → `reference/serving.md`
4. **Copy `assets/PROMPT_TEMPLATE.md`** and fill it in. It is the house structure; the
   section order and the voice both matter, because Replit's agent follows a prompt
   far more literally than a person does.
5. **Scaffold the server from `assets/server/`** — a zero-dependency Node server with
   the credential chain, the HTTPS ClickHouse client, boot-time secret validation and
   the cache already wired. It runs on a bare Replit Node template with no install step.

## Data path: direct is the default

ClickHouse Cloud is internet-facing. Every Chartmetric service carries `0.0.0.0/0` in
its IP access list, and rw-standard and ro-standard additionally carry an explicit
Replit egress address. A Replit app talking to ClickHouse over HTTPS:8443 is
established practice here — do not tell anyone it "can't reach" the database.

| | Direct | Static pack |
|---|---|---|
| Data | live | a snapshot, refreshed by re-running the exporter |
| Needs at runtime | secrets + a SELECT grant | nothing |
| Take it when | the app should show current data | credential-less demo, frozen snapshot, or the grant is missing |

The real constraints are credentials (server-side only) and **grants**, not reachability.

## What a finished port contains

```
PROMPT.md                 the build prompt for Replit's agent — the main artifact
README.md                 how to run it, how to refresh it, what it is honestly
server/
  index.js                boot-time secret check, endpoints, cache
  clickhouse.js           HTTPS client, parameterised queries, warehouse registry
  queries.js              every SQL string, server-side only
src/glossary.ts           every tooltip, caveat, limitation and next-step string
data/parity.json          notebook-computed values the app asserts against on load
scripts/export_pack.py    the exporter (static path, or to build the parity fixture)
.replit  package.json     so Run works on a bare template
```

For a compute-heavy app, add the ported math as its own module (`src/scoring.js`) with
the parity check wired into its load. Keep it JavaScript and keep it out of the
framework — it is the one file that must not be rewritten by an agent later.

## Stack for the generated prompt

React + TypeScript + Vite + Tailwind, shadcn/ui (Radix) for the tooltip and hover-card
layer, so the app can later fold into Flow. Flow design tokens:

```
primary #00B88A teal   accent #eacd3e gold
dark  bg #14161a  panels #1b1e23  lines #2e333a
light bg #f6f7f8  panels #ffffff
body Inter        headings Playfair Display
```

Light mode is the default; dark mode must be genuinely good, not an afterthought.

**No charting or mapping library** unless the app truly needs one — stacked bars and
progress rows are divs, and a map is canvas. Plotly, d3, Leaflet and MapLibre are each
larger than a typical data pack. Virtualize any table over a few hundred rows.

## Iterating on an app that already exists

Write an **update prompt**, not a new build prompt. It names what changed in the data
contract, adds the new features, and — critically — lists what must **not** be touched:
the scoring math, the weight sliders, the validation views. See `reference/workflow.md`
for the update-prompt shape and `reference/explainability.md` for how to add a caveat
without rewriting the glossary.

## Reference files (load as needed)

- `reference/workflow.md` — end-to-end sequence, the interview, update prompts, verification.
- `reference/serving.md` — secrets, warehouses, the HTTPS interface, SQL rules, caching, grants.
- `reference/parity.md` — building the fixture, wiring the badge, what to do when it goes red.
- `reference/explainability.md` — glossary module, tooltip rules, the caveat taxonomy.
- `reference/static-pack.md` — pack layout, sharding, `Float32Array` payloads, the exporter.

## Assets and scripts

- `assets/PROMPT_TEMPLATE.md` — the house prompt skeleton, section by section.
- `assets/server/` — zero-dependency Node server, ClickHouse client, `.replit`, `package.json`.
- `assets/glossary.ts` — the glossary module shape, with the caveat taxonomy stubbed.
- `scripts/export_pack.py` — stdlib-only exporter: credential chain, HTTPS queries,
  manifest/shard writer, parity fixture writer, and the refuse-to-write guard.

## Related skills

- **`ds-notebook`** is upstream of this one. The notebook it produces is what gets
  ported; its §1 config and §7 validation are this skill's two main inputs.
- **`cm-ai:replit-env`** is a different job: reaching an *existing* Replit workspace
  (cm-workspace, the kevin repl) over SSH. It does not overlap with porting a notebook.

## Chartmetric specifics

- Credentials for **building** the pack come from `~/code/chartmetric/devin-secrets.env`,
  which is **shell-escaped and must be `source`d** — parsing it as a dotenv silently
  yields a wrong password and a `Code: 516` that reads like a permissions problem.
- `external_devin` is **HTTPS-only** (8443); the native protocol on 9440 rejects it with
  the same Code 516. Personal accounts work on both.
- `cm_artist` is a ReplacingMergeTree with un-merged duplicate ids — always
  `argMax(name, modified_at)` + `GROUP BY`. Do **not** read `cm_artist.image_url`; it is
  populated for 0.03% of rows. Images come from
  `chartmetric_analytics_flattened.f_artist_image`.
- Databases are read-only. The app never writes.
