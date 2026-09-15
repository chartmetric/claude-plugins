# Workflow — notebook to Replit app

## 0 · What you are actually porting

A DS notebook contains four separable things. Only two of them belong in the app.

| In the notebook | Goes in the app? |
|---|---|
| Heavy signal computation (scans, joins, aggregations over millions of rows) | **No.** It already ran. Read its output. |
| The recompute — the weighted combination, the ranking, the lift ratio | **Yes.** This is the product; it must be instant and client-side. |
| The output table / write-back | **Yes**, as the data source. |
| The §7 sanity and validation findings | **Yes**, as UI copy. This is the part people skip. |

If you find yourself re-implementing a scan, stop: you are rebuilding the notebook.
If you find yourself hiding a validation finding, stop: you are building something
that will mislead a PM.

## 1 · Interview before building

Ask only what you cannot read out of the notebook:

- **Who is this for?** Internal PM/DS explorer is the usual answer, and it sets the
  whole register: data-dense, explainable, non-customer-facing, "polished mock-up of a
  real feature" rather than a prototype.
- **What must the user be able to tune?** Weight sliders and a live re-rank are the
  recurring core. If nothing is tunable, the app is a viewer and is much simpler.
- **What is the one idea the UI must convey?** Every one of these models has one, and
  getting it wrong makes the UI actively harmful. For the international score it was
  *the score is relative to same-size peers, not a global ranking*. Write it down; it
  goes near the top of the prompt and it drives at least one hard UI constraint (there,
  a mandatory tier selector).
- **Is the output table stable?** Does it accumulate one row per day (`timestp`), carry
  a `model_version`, or is it a ReplacingMergeTree needing dedupe? Getting this wrong
  triples every count silently.

Read out of the notebook, do not ask: the recompute math, the column list, the
thresholds, the caveats.

## 2 · Verify the data path before writing the prompt

Run these yourself, as the account the app will use, before promising anything:

```bash
source ~/code/chartmetric/devin-secrets.env
# who am I, and can I actually read the table?
```

1. `SELECT currentUser()` — the credential chain prefers `CH_USER` over the
   `clickhouse_user` in devin-secrets.env, so the same command picks a different
   account depending on the shell. Only one of them can read `chartmetric_test`.
2. One real `SELECT ... LIMIT 1` against the actual output table. A `SELECT 1` smoke
   test is a **false positive** — it succeeds on every warehouse and against every
   account, and tells you nothing about grants or about which warehouse you reached.
3. `COUNT(*)` vs `COUNT(DISTINCT <key>)` on the output table. If they differ, find the
   dedupe discipline (`timestp = max(timestp)`, `FINAL`, or `argMax`) and write it into
   the prompt as a **CRITICAL** line. This has broken a port before.
4. If two warehouses are involved, confirm each separately — and remember they cannot
   be joined server-side. No account has the `REMOTE` grant.

If the grant is missing, say so plainly and scaffold the static pack path instead. Do
not ship a prompt whose first action fails.

## 3 · Build order

Build the pieces that must be right before the agent ever runs, then let the agent do
the UI.

1. **Server + client** from `assets/server/`. Boot-time secret validation, the
   warehouse registry, the HTTPS query helper, and the cache.
2. **Queries module** — every SQL string, server-side, parameterised.
3. **The recompute**, if the app has one, as a plain JS module. Port it from the
   notebook cell by cell, not from memory.
4. **The parity fixture** — `scripts/export_pack.py --parity` computes it from the
   notebook's own definitions. See `reference/parity.md`.
5. **The glossary** — every tooltip, caveat and limitation, harvested from the
   notebook's markdown and §7 output. See `reference/explainability.md`.
6. **`PROMPT.md`** from `assets/PROMPT_TEMPLATE.md`, last, once you know what the
   agent must *not* reinvent.
7. **A working demo**, if the app is compute-heavy. A zero-dependency vanilla version
   that already runs (`node server.js`) turns the agent's job from "invent this" into
   "productionise this", which it does far more reliably. `app.js` then becomes the
   reference for behaviour and the prompt tells the agent to replace it.

## 4 · The prompt's job

Replit's agent follows a prompt literally. That cuts both ways:

- **Name the files it must not rewrite**, in a table, with a one-line reason each.
  "Use as-is. Import it." is clearer than "please don't change".
- **State the deliberate weirdness.** Every model has behaviour that looks like a bug:
  composite scores that look small because of a geometric mean, counties clipped to
  zero, two modes that genuinely disagree. Give these their own section —
  *Things that are deliberate — do not "fix" them* — or the agent will helpfully
  "correct" them.
- **Give it sanity checks with expected answers.** A table of "search this artist,
  expect these results" is the single highest-value section in the prompt. These are
  the checks that caught real bugs during development; hand them over.
- **Definition of done as a checklist.** Including the boring ones: works at 390px, no
  console errors, no mapping or charting dependency added.

## 5 · Verify the port yourself

Before handing it over:

- Parity badge green, with a plausible point count.
- Re-run the notebook's own spot checks through the UI. If the notebook validated
  against known-good examples, those examples must come out the same in the app.
- Every glossary entry is reachable from the UI. An unreachable entry means a number
  somewhere has no tooltip.
- Deliberately break a secret and confirm the app fails loudly at boot rather than
  falling back.
- Confirm no credential reaches the client bundle (`grep` the built assets).

## 6 · Update prompts, not rebuilds

Once the app exists, every change is an **update prompt**. Its shape:

```
# Replit UPDATE prompt — <App name> (<version>)

> This is an update to the existing <app>, not a rebuild. Use it alongside
> <notebook>.ipynb (attached), which is the source of truth. Do NOT change
> <the scoring math / the weight sliders / the validation views> — only add
> what's below. Context: <why this is being asked for, in one sentence>.

## Data contract changes
  CRITICAL lines first (dedupe discipline, new filters), then new columns and
  new tables, with units and what each actually means.

## Feature 1 … Feature N
  One heading each, with the display rules inline.

## Out of scope for this update
  Name the things that stay as-is.
```

The "Context:" line matters more than it looks — it tells the agent *why*, which keeps
it from solving a different problem. A real one: "a reviewer couldn't reconcile the
app's numbers with the main Chartmetric app, and asked to see the raw metrics behind
the scores."

Keep every update prompt in the notebook's `data/` directory alongside the init prompt,
so the app's whole history is readable from the repo.

## 7 · Where the artifacts live

The Replit package lives with the notebook that produced it, on that project's feature
branch — `<repo>/data_science/<project>/replit/`. It is exploratory DS work: local
branch, no PR, Fred runs it. The distributable zip is a build artifact of its own
directory and is gitignored.

```bash
cd .. && zip -r <project>-replit.zip replit -x '*.pyc' '*/__pycache__/*'
```
