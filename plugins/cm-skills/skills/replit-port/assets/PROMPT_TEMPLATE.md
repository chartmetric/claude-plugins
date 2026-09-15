<!--
  HOUSE TEMPLATE for a Replit build prompt. Fill in every <angle-bracket> placeholder
  and DELETE every HTML comment before handing it over — the comments are instructions
  to you, not to the agent.

  Section order matters. The agent reads this literally and top-down: it must know what
  not to reinvent before it knows what to build.

  Delete sections that genuinely don't apply. Do NOT delete:
    - "Things that are deliberate"      (the agent will "fix" them)
    - "Explainability"                  (the reason the app is trusted)
    - "Sanity checks to run yourself"   (the highest-value section in the file)
-->

# Replit build prompt — <App Name>

<!-- One of these two openers. The first is much stronger when you have a demo. -->
Paste everything below the line into Replit's AI agent after uploading this folder.
A **working demo already runs** (`node server.js`), so the agent's job is to
productionise it, not to invent the model. Read `README.md` first if you want to see it
running before changing anything.

<!-- Without a demo: -->
> Paste this into Replit Agent as the project brief. Attach `<notebook>.ipynb` as
> context — it is the source of truth for the scoring algorithm; this document tells
> the app what to DO, where the data comes from, and the exact recompute math.

---

## What you are building

<!-- Two or three sentences. Lead with the question the app answers, in plain English. -->
<One-sentence statement of the question the app answers.> <Who picks what; what gets
drawn; what gets explained.>

An internal, non-customer-facing web app for Chartmetric PMs and data scientists.
It should look and feel like a polished mock-up of a real product feature — clean, fast
and trustworthy — not a rough prototype. Audience: internal PMs (no ML background) and
data scientists. **Every number must be explainable in plain language.**

**The one idea the whole UI must convey:** <the single thing that, if a user misreads
it, makes the app actively harmful — e.g. "the score is relative to similarly-sized
peers, not absolute; a tier-1 artist scoring 100 and a tier-4 artist scoring 100 are
not comparable">. If a user can misread <the main view> as <the wrong reading>, the UI
has failed.

<!-- That last sentence is not decoration. It is what forces a hard UI constraint
     later (a mandatory tier selector, a scope badge, a taxonomy label). -->

## Do not reimplement these

<!-- Only if you are shipping code alongside the prompt. This table is the single most
     effective thing in the file. One row per file, one reason each. -->

The model, the data and the maths are **already implemented and verified** in this repo.

| File | What it is | Rule |
|---|---|---|
| `src/scoring.js` | All scoring maths, ported from the notebook and checked against it to <tol> | **Use as-is.** Import it. |
| `src/glossary.ts` | Every tooltip, limitation and next-step string | **Use as-is.** Extend, never duplicate. |
| `server/` | Secrets, ClickHouse client, every SQL string | **Use as-is.** Never move a query to the client. |
| `data/*` | The static data pack | **Do not edit by hand.** Regenerate with `scripts/export_pack.py`. |
| `app.js` | The vanilla demo wiring | **Replace this.** It is the reference for behaviour. |

Add TypeScript declarations for the `src/*.js` modules rather than converting them —
converting risks silent numeric changes. A `src/scoring.d.ts` is fine.

## Hard constraints

- **The app does not query the database per request.** <One-time bulk pull at boot /
  per-entity fetch cached for N minutes>, served from cache thereafter. Never per
  keystroke, never per slider frame.
- **Read-only, SELECT-only.** Credentials come from Replit Secrets
  (`CLICKHOUSE_HOST`, `CLICKHOUSE_PORT`, `CLICKHOUSE_USER`, `CLICKHOUSE_PASSWORD`),
  are used **only in server code**, are never renamed or prefixed so a bundler exposes
  them to the client, and have **no hardcoded fallback** — a missing secret fails
  loudly at boot. Never accept a query, table or column as a request parameter: the
  browser asks for an id, the server decides the SQL. Never write to the database.
- **Recompute is client-side and instant.** Changing a weight must re-rank all
  ~<N> rows in <100 ms — Web Worker, typed arrays, virtualized table.
- **<The invariant that silently breaks the model.>** e.g. "Percentile ranks are
  computed WITHIN listener tier, never globally. This is the single easiest thing to
  get wrong and it silently breaks the score."
- **No invented data or rules.** Use only the fields and formula below. If a field is
  missing, degrade gracefully — render the empty state, never a fabricated value.

## Data contract

<!-- DIRECT path. For the static-pack path, replace this section with the pack layout
     and loading rules from reference/static-pack.md. -->

```
browser  →  Replit server (holds the credentials)  →  ClickHouse Cloud over HTTPS
```

| Replit Secret | Warehouse | Serves |
|---|---|---|
| `CLICKHOUSE_HOST` `CLICKHOUSE_USER` `CLICKHOUSE_PASSWORD` `CLICKHOUSE_PORT` | rw-standard, `grkyl47mbo.us-west-2.aws.clickhouse.cloud:8443` | <what> |
| `CLICKHOUSE_VERT_HOST` `CLICKHOUSE_VERT_USER` `CLICKHOUSE_VERT_PASSWORD` | vert, `j1ez4a7j4k.us-west-2.aws.clickhouse.cloud:8443` | <what> |

The two warehouses **cannot be joined** — no account has the `REMOTE` grant. Open two
connections and merge in the server.

Query over the HTTPS interface: `POST https://<host>:8443/?default_format=JSONEachRow`
with HTTP basic auth and the SQL as the body. Add
`output_format_json_quote_64bit_integers=0` so 64-bit ids arrive as numbers, and set
`max_execution_time=30`. **Parameterise, never interpolate** (`{id:UInt64}` passed as
`param_id`).

<!-- CRITICAL dedupe line, if the table needs one. Put it in bold, near the top. -->
**CRITICAL — <dedupe discipline>.** `<table>` <accumulates one row per entity per day /
is a ReplacingMergeTree>. Always read `<WHERE timestp = (SELECT max(timestp) …) /
FINAL / argMax(…) GROUP BY …>`. Without it you get ~<N>x duplicate rows and every count
and score is wrong. After caching, verify `COUNT(*) == COUNT(DISTINCT <key>)`.

### Tables and columns

| column | type | meaning |
|---|---|---|
| <col> | <type> | <what it means, in plain language, with units> |

<!-- Spell out NULL semantics. This is the most common silent error in these apps. -->
**NULL semantics matter.** `<col>` and `<col>` are nullable: NULL means *unknown*, and
the recompute must substitute <a neutral 0.5 percentile>, **not** zero. Every other
column is zero-filled, where zero is a genuine observation ("<did not chart anywhere>").

### Endpoints

```
GET /api/search?q=      filters the in-memory index, case-insensitive substring, ≤50 rows
GET /api/<entity>/:id   assembles the document below; cached in memory for N minutes
POST /api/refresh       admin: re-runs the bulk pull, overwrites the cache
```

Names come from `chartmetric_raw_data.cm_artist` with `argMax(name, modified_at)` (it
has un-merged duplicate ids). Images come from
`chartmetric_analytics_flattened.f_artist_image` — **not** `cm_artist.image_url`, which
is populated for 0.03% of rows. Fall back to an initials avatar.

## The recompute — implement exactly

<!-- Pseudocode, not prose. Copy the structure from the notebook cell. Annotate the
     lines that are easy to get wrong. -->

```
<pseudocode>
```

<Reproducing the stored `<score>` at default weights is the app's correctness test —
**assert it matches to within rounding on load**, and show a small green/red indicator.
If it doesn't match, the recompute is wrong.>

`src/scoring.js` runs a parity check against `data/parity.json` on load. **Keep that
check and keep it visible in the UI.** If it ever goes red, the app and the notebook
have diverged and every number on screen is suspect.

## Screens and behaviour

<!-- One numbered heading per screen. Behaviour, not layout advice — the agent is good
     at layout and bad at guessing rules. -->

### 1. <Leaderboard / picker>
- Sortable, **virtualized** table, default sorted by `<col>`.
- <The mandatory control that prevents the misreading named at the top.>
- Columns: <list>, each linking to `https://app.chartmetric.com/artist/{cm_artist}`.
- **Every score cell has a tooltip** explaining what it means and the raw values behind
  it. Hover `<col>` → "<worked example in plain language>".
- **Low-confidence rows are visually de-emphasised** and filtered out by default, with a
  toggle. <N of M (X%)> are `<flag>`; showing them unmarked would make the board look
  broken.
- Row click → drill-down.

### 2. <Weight panel / controls>
- <Sliders>, auto-normalized, running sum shown, "Reset to defaults".
- **Named presets**: save / load / rename / delete, persisted locally.
- Every control gets a tooltip from the glossary. A control that does not apply in the
  current mode is **visibly disabled**, never silently ignored.

### 3. <Comparison / validation mode>
- Two weightings side by side; combined table with each entity's rank in both and
  `rank_delta`, sorted by `|rank_delta|`; Spearman between the two rankings.
- **Validation readout** — the properties a PM can break:
  - **Size-neutrality**: <correlation> should sit near **<x>**. Flag red above ~<y> — it
    means the weighting made the score track popularity rather than <the real thing>.
  - **Coverage neutrality**: median score by data-completeness group, currently
    <a / b / c>. A widening gap means the weighting rewards *having data*.
  - **Predictive check**: <the notebook's external target>, currently <value> overall.
  - Histogram of the score, and median by peer group (want flat).

### 4. <Drill-down>
This is where the explainability lives. It must answer "why this number?" in one screen.
- Header: <identity, size, links>.
- **Composition**: a stacked bar of each weighted contribution, so the user sees exactly
  which signals produced the number.
- **Each axis** with its percentile and the raw value in plain language.
- **<The model's most distinctive idea>, visualised.** <How.>
- **Detail table** with plain-language labels; NULL-valued inputs greyed as "no data —
  scored neutral", explicitly distinguished from zero.
- A one-line auto-generated "why this score" sentence.

### 5. Glossary
Always reachable via "?" in the nav. Plain-language definitions with a one-line
"why it matters" each: <list every term>. Lead with <the one idea>.

## Explainability is the point — make it heavy

1. **Every number on screen has a tooltip**, with copy from `src/glossary.ts`. Do not
   write copy inline; if something is missing, add it to the glossary.
2. **Formulas render in monospace** inside the tooltip where the glossary entry has one.
3. **Raw vs normalized must be unmistakable.** <Which column is the headline that
   reconciles with app.chartmetric.com, and which is the scored variant.>
4. **Per-entity honesty badge.** Show which <dimensions/pillars> actually scored this
   entity, and <which taxonomy or label frame is in play>. Where <a dimension> is
   genuinely absent, mark it in a warning colour next to the results, not buried.
5. **<Scope badge>.** <The thing most likely to be misread — e.g. "the demographics
   describe the artist's whole worldwide audience, not their American one".> Say so on
   screen.
6. **A limitations section** built from `LIMITATIONS` and `NEXT_STEPS` in the glossary,
   collapsible but **present on the page** — not a separate route, not behind a link.
   Render every entry. Do not paraphrase or trim them.
7. **A provenance footer**: <vintage, counts, constants, generation date>. All of it
   from `data/manifest.json`; none of it hardcoded.
8. **The parity badge**, with its point count.

<!-- Taxonomy rule — include verbatim whenever more than one classification scheme is
     on screen. -->
**Taxonomies differ and must be labelled.** <Scheme A> uses <classes>; <scheme B> uses
<classes>. Never render them in one shared legend or imply the categories line up. Show
each block's own taxonomy label.

**Always show the sample size next to an observation** — "<n> <units> from <m> <units>".
A share computed from 32 observations carries roughly ±9 percentage points of sampling
noise, so a card that hides n invites over-reading. Below <threshold>, render the
observation greyed with "sample too small to estimate from".

## Stack

- **React + TypeScript + Vite**, **Tailwind CSS**, **shadcn/ui** (Radix), with
  `@radix-ui/react-tooltip` and `@radix-ui/react-hover-card` for the explainability layer.
- **No charting library** — the visuals are stacked bars and progress rows, which are
  divs. **No mapping library** — the map is canvas. Plotly, d3, Leaflet and MapLibre are
  each larger than the entire data pack.
- No state library. Component state plus a single context is plenty.

### Design tokens (from Flow)

```
primary   #00B88A  teal
accent    #eacd3e  gold
dark bg   #14161a   panels #1b1e23   lines #2e333a
light bg  #f6f7f8   panels #ffffff
body font Inter          headings Playfair Display
```

**Light mode is the default.** Dark mode must still be genuinely good, not an
afterthought; check <the legend and the ramp> in both.

## Performance rules

- <Scoring one entity is ~N ms for all M rows.> **Never** put the recompute behind a
  network call.
- Load the pack once. `.f32` files are `Float32Array`s fetched via `arrayBuffer()`; do
  not convert them to JSON or to arrays of objects.
- Rebuild <expensive geometry> only on resize; <recolouring> is cheap and can run on
  every slider frame.
- Serve `data/*` with gzip.
- Virtualize any table over a few hundred rows.

## Things that are deliberate — do not "fix" them

<!-- Keep this section. Without it the agent will "correct" the model. -->

- **<Composite scores look small.>** <Why — the geometric mean compresses; a
  single-dimension lift of 4.6 at weight 0.20 becomes 1.36.> This is correct. Surface
  the per-dimension columns rather than rescaling.
- **<Values clipped at the baseline.>** That is the definition, not a bug.
- **<Two modes genuinely disagree.>** <Worked example.> Both are shipped on purpose.
- **<A label that suppresses near-neutral dimensions.>** <Why suppression is correct.>

## Definition of done

- [ ] Parity badge green on load, showing the checked-point count.
- [ ] <Every control> works, and the view redraws live while dragging a slider.
- [ ] Every number has a tooltip; every glossary entry is reachable from the UI.
- [ ] <Entities missing a dimension> are visibly flagged.
- [ ] The full limitations list and next steps render on the page.
- [ ] Provenance footer shows real values from the manifest.
- [ ] Missing secrets fail loudly at boot; no credential appears in the client bundle.
- [ ] Works at 1280px and at 390px wide.
- [ ] No console errors; no dependency added for mapping or charting.

## Sanity checks to run yourself before saying it works

<!-- The highest-value section in the file. Use the notebook's own validated examples.
     If the notebook has no spot checks, go find some before writing this prompt. -->

| Input | Expect |
|---|---|
| <entity> | <the specific, checkable result> |
| <entity> | <result> |
| <any entity, second mode> | Different and less extreme than <first mode>, not a rescaled copy |

If <a result looks degenerate>, check the honesty badge before assuming the app is
broken — it usually means <a dimension is missing or the scope is mismatched>, and both
are real properties of the data.

## Explicit non-goals

- Not customer-facing (internal mock-up).
- No live/per-request database access; no writes to the database.
- Do not re-implement the heavy signal computation — the notebook already did it. The
  app only recomputes <the weighted combination and the ranking> from cached values.
