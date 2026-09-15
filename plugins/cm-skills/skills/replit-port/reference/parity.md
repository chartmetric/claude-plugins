# Parity — proving the app still matches the notebook

## Why

The app and the notebook diverge silently. Nothing errors. The numbers just stop being
the same, and nobody notices until a reviewer tries to reconcile them against the main
app and cannot.

The fix is cheap: ship a fixture of notebook-computed values, recompute them in the app
on load, and put the result on screen.

Two real divergences this would have caught immediately:

- A pack exported only the seven-way ethnicity frame, silently dropping ethnicity for
  24% of artists. The app rendered confidently and wrongly — one artist's map went from
  a coherent Black Belt to a scatter of college towns and military bases. Spearman
  between the two rankings was 0.685.
- An output table started accumulating one row per artist per day. Without a
  `timestp = max(timestp)` filter every count tripled.

## The fixture

`data/parity.json` — inputs plus the notebook's own answers.

```json
{
  "generated_at": "2026-09-15T18:22:41Z",
  "source": "demographic_geo_v1.ipynb §6",
  "tolerance": 1e-6,
  "points": [
    {"artist": 3963, "area": "06085", "mode": "lift", "expected": 1.3874219},
    ...
  ]
}
```

Rules:

- **Generate it from the notebook's own cells**, not from a reimplementation. The
  exporter should import or exec the notebook's config and scoring cells so the fixture
  cannot drift from the definitions it is meant to pin. `scripts/export_pack.py`
  does this with `--parity`.
- **Cover the edge cases, not just the middle.** A few hundred points is plenty, but
  they must include: an entity missing a dimension, each label frame or taxonomy
  variant, the neutral/NULL-scored path, a zero-clipped value, and both scoring modes
  if there are two. Parity over 300 typical rows proves almost nothing.
- **Record a tolerance and honour it.** `Float32Array` payloads round-trip to about
  1e-7; a 1e-12 tolerance will flap. State the tolerance in the fixture and report the
  observed maximum deviation, not just pass/fail.
- **Regenerate it with the data.** If the exporter writes `data/`, it writes
  `parity.json` in the same run. A stale fixture that passes is worse than none.

## The check

Run it at module load, not behind a button:

```js
export function checkParity(pack) {
  let worst = 0, failed = [];
  for (const p of pack.parity.points) {
    const got = score(pack, p);                    // the app's own code path
    const dev = Math.abs(got - p.expected);
    if (dev > worst) worst = dev;
    if (dev > pack.parity.tolerance) failed.push({ ...p, got, dev });
  }
  return { ok: failed.length === 0, n: pack.parity.points.length, worst, failed };
}
```

It must call **the same code path the UI calls**. A parity check with its own private
implementation of the maths tests nothing.

## The badge

- Green: "Parity ✓ 384 points, max deviation 1.0e-7". The point count matters — a badge
  that goes green on an empty fixture is the failure mode to avoid.
- Red: name the count of failures and the worst offender, and say plainly that the app
  and the notebook have diverged and **every number on screen is suspect**. Do not
  render the results as though nothing happened.
- Keep it visible. Header or footer, always on screen, not in an admin panel nobody
  opens.

## The other parity check: reproduce the stored score

When the notebook wrote a score to a table *and* the app recomputes that score from its
inputs, the stored value is a second, free fixture covering the whole population.

> Reproducing the stored `international_score` at default weights is the app's
> correctness test — assert it matches to within rounding on load, and show a small
> green/red indicator in the admin panel. If it doesn't match, the recompute is wrong.

Assert it at default weights on load, over the whole cached population. This catches
the class of bug a hand-picked fixture misses — a percentile computed globally instead
of within peer group, for instance, which is silent, plausible, and completely wrong.

## When it goes red

In order:

1. **Did the data contract change?** A new `timestp`, a new `model_version`, a column
   whose units changed. Most red badges are this.
2. **Did the pack lose a variant?** Check coverage counts per label frame / taxonomy /
   dimension against the notebook's own coverage numbers, not against zero.
3. **Did the recompute drift?** Diff the JS module against the notebook cell it was
   ported from, line by line.
4. Only then suspect the fixture.

Do not "fix" a red badge by loosening the tolerance.
