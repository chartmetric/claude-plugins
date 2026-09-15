# Explainability — tooltips, glossary, honesty

The audience is internal PMs with no ML background and the data scientists who built
the thing. Every number must be explainable in plain language, and every weakness the
notebook found must be on the screen. This is not polish; it is the reason the app is
trusted enough to be useful.

## The glossary module

**All user-facing copy lives in one module** — `src/glossary.ts`. Not inline in
components, not duplicated between a tooltip and a help page.

```ts
export const GLOSSARY = {
  fan_intensity: {
    term: "Fan Intensity",
    short: "How passionate an artist's audience is, relative to artists of similar size.",
    why: "It rewards intensity, not popularity — a small artist can outscore a huge one.",
    formula: "intensity_composite × size_fit",
  },
  ...
};
export const LIMITATIONS = [ ... ];
export const NEXT_STEPS  = [ ... ];
```

Why one module: the copy is the part that gets reviewed, corrected and re-corrected, and
it is the part an agent is most likely to paraphrase into something subtly false. One
file makes a correction a one-line edit and makes "is everything covered?" answerable.

Rule for the prompt: **extend the glossary, never duplicate it.** If a component needs
copy that isn't there, the fix is a glossary entry.

## Tooltip rules

1. **Every number on screen has a tooltip.** Not most. A number without one is a number
   someone will misread.
2. A tooltip says **what it is**, **how it was computed**, and where useful **the raw
   values behind it**. Hovering a pillar score should show the underlying signals:
   "grassroots: 24 creators · big-reach: 6 · curation slope +0.0007".
3. **Formulas render in monospace** where the glossary entry has one.
4. Prefer plain language with the number embedded over a formula alone: "62% of audience
   abroad, discounted to 38% because most of it is in Germany, a close neighbour of
   Austria" beats `dist_weighted_foreign = 0.38`.
5. **Raw vs normalized must be unmistakable.** When an app shows both, label them —
   headline value from the column that reconciles with app.chartmetric.com, and the
   scored/weighted variant visually secondary. A reviewer who cannot reconcile a number
   with the main app stops trusting the whole screen.
6. A **glossary page reachable from the nav** ("?"), with a one-line *why it matters* per
   entry. Every glossary entry must be reachable from the UI; an unreachable entry means
   some number lost its tooltip.

## The caveat taxonomy

Five kinds, and they belong in different places on the screen.

| Kind | Example | Where it goes |
|---|---|---|
| **Per-entity evidence gaps** | this artist has no ethnicity data; only 1 of 6 corroborating signals | A badge *next to the results*, in a warning colour — never buried in a panel |
| **Sample size** | "n classified commenters from m posts" | Always beside the observation. Below a threshold, grey it out and say "sample too small to estimate from" |
| **Scope mismatch** | the demographics are the artist's *global* audience, being mapped onto US counties | A prominent badge; this is usually the single most misleading thing on screen |
| **Structural model limits** | dimensions combined as if independent; chart credit goes to the primary artist | The on-page limitations section |
| **Known skews** | classical and instrumental artists score highly | Glossary, with the explanation — it is usually genuine, and a surprised PM assumes a bug |

### Per-entity honesty badges

The most valuable and most-often-skipped. Show which dimensions/pillars actually scored
*this* entity, which label frame or taxonomy is in play, and what was scored neutrally
for want of data.

**NULL is not zero, and the UI must say which.** A missing bonus scored at a neutral
0.5 percentile is completely different from a genuine zero ("did not chart anywhere").
Render NULL-valued inputs greyed as "no data — scored neutral", explicitly distinguished
from an observed zero.

### Taxonomies that differ must never share a legend

When one screen carries two or more classification schemes — a four-class estimate, a
four-plus-other observation, a seven-class finer scheme — label each block with its own
taxonomy and never imply the categories line up. Where two frames represent the same
dimension, collapse them into one column by *name*, never by position, and flag the
coarser frame as coarser.

## The limitations section

- **On the page.** Collapsible is fine. Behind a link, on a separate route, or in a
  README is not.
- **Render every entry.** Do not paraphrase, do not trim to the three that fit.
- Pair it with **next steps** — what would make the model better — so a reader can tell
  a known gap from an oversight.
- Add a **provenance footer**: data vintage, row counts, key constants, whether an
  optional correction is on, and the pack/pull generation date. All of it from the
  manifest, none of it hardcoded.

## Things that are deliberate

Every model has behaviour that reads as a bug. Give it its own prompt section titled
*Things that are deliberate — do not "fix" them*, with the reason, or an agent will
helpfully correct it and a PM will file it as a defect. Recurring examples:

- **Composite scores look small.** A weighted geometric mean turns a single-dimension
  lift of 4.6 at weight 0.20 into 1.36. Surface per-dimension columns rather than
  rescaling the composite.
- **Values clipped at a baseline.** "People above baseline" clipping below-baseline
  areas to zero is the definition, not a bug.
- **Two modes that disagree.** A 30%-Asian audience gets a perfect *similarity* score in
  a 30%-Asian county and a 5x *lift* there. Both ship on purpose.
- **A driver label that hides near-1.0 dimensions.** Naming the most over-represented
  cell of a dimension that did nothing implies an affinity the entity does not have.

## The validation readout

If the notebook validated the model, the app should let a PM re-run that validation
against whatever weighting they just invented — otherwise sliders are a way to silently
break the score.

Surface the properties that can be broken, with the expected value and a red flag when
it drifts:

- **Size-neutrality** — correlation between the score and popularity. Should sit near
  ~0.07; flag red above ~0.15, because that means the weighting made the score track
  popularity rather than the thing it claims to measure.
- **Coverage neutrality** — median score by data-completeness group should be within a
  point or two. A widening gap means the weighting rewards *having data*.
- **The external target** — whatever the notebook validated against, per peer group.
- **Distribution** — a histogram of the score and median-by-tier (want flat).

And where the notebook's own validation **failed**, say so in the app. A model that did
not beat its baseline must not be presented as predictive; a line in the limitations
section naming the result is the minimum.
