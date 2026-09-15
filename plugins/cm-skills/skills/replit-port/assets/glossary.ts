/**
 * Every user-facing string that explains a number.
 *
 * One module, on purpose. This is the part that gets reviewed, corrected, and
 * re-corrected, and the part an agent is most likely to paraphrase into something
 * subtly false. Keeping it here makes a correction a one-line edit and makes
 * "is everything covered?" answerable.
 *
 * Rule for every component: EXTEND this, never duplicate it. If a component needs copy
 * that isn't here, the fix is a new entry, not an inline string.
 *
 * Coverage test: every entry must be reachable from the UI. An unreachable entry means
 * some number on screen lost its tooltip.
 */

export interface Entry {
  /** Display name, as it appears in the UI. */
  term: string;
  /** One sentence, plain language, no jargon. A PM with no ML background is the reader. */
  short: string;
  /** Why it matters — what decision it should or should not inform. */
  why: string;
  /** Optional; rendered in monospace inside the tooltip. */
  formula?: string;
  /** Optional worked example with real numbers. These land better than definitions. */
  example?: string;
}

export const GLOSSARY: Record<string, Entry> = {
  // The headline number. Lead with the idea that, misread, makes the app harmful.
  score: {
    term: "<Score name>",
    short: "<What it measures, in one sentence.>",
    why: "<Scores are relative to similarly-sized peers — a small entity can outrank a huge one, and two scores from different peer groups are not comparable.>",
    formula: "<composite × modifier>",
    example: "<Worked example with real numbers from the notebook's own spot checks.>",
  },

  // One entry per column, axis, pillar and control that appears on screen.
  // <column_name>: { term, short, why, formula?, example? },
};

/**
 * Structural limits of the model. Rendered ON THE PAGE — collapsible is fine, a
 * separate route is not. Render every entry; do not paraphrase or trim to the three
 * that fit.
 *
 * Harvest these from the notebook's §7 sanity/validation section, not from memory. If
 * the notebook's validation FAILED against its baseline, that belongs here in plain
 * words, and the app must not be presented as predictive.
 */
export const LIMITATIONS: { title: string; detail: string }[] = [
  {
    title: "<The scope mismatch>",
    detail: "<e.g. the demographics describe the entity's whole worldwide audience, not its American one — the map is least trustworthy for entities that are big everywhere except the US.>",
  },
  {
    title: "<The independence assumption>",
    detail: "<The dimensions are combined as if independent. They are not.>",
  },
  {
    title: "<What this is not>",
    detail: "<It is a prior, not a measurement. Two entities with identical inputs get identical outputs; it knows nothing about who actually streams whom.>",
  },
];

/** What would make the model better. Pairs with LIMITATIONS so a reader can tell a
 *  known gap from an oversight. */
export const NEXT_STEPS: { title: string; detail: string }[] = [
  { title: "<Next step>", detail: "<What it would fix.>" },
];

/**
 * Per-entity caveats. These render as badges NEXT TO THE RESULTS in a warning colour —
 * not buried in a panel — because they change how the numbers on screen should be read.
 */
export const CAVEATS = {
  missingDimension: (dim: string) =>
    `No ${dim} data for this entity — it was left out of the score, not scored as zero.`,
  neutralScored: (field: string) =>
    `${field}: no data — scored neutral. This is different from an observed zero.`,
  coarseFrame: (dim: string) =>
    `${dim} uses the legacy, coarser labels for this entity. The signal is blunter.`,
  smallSample: (n: number, threshold: number) =>
    `Sample too small to estimate from (${n} observations, threshold ${threshold}).`,
  sampleNoise: (n: number) =>
    `Based on ${n} observations — roughly ±${Math.round(
      100 * Math.sqrt(0.25 / Math.max(n, 1))
    )} percentage points of sampling noise.`,
  globalScope:
    "These figures describe the entity's whole worldwide audience, not its audience in the area shown.",
} as const;

/** Taxonomy labels. Never render two schemes in one shared legend or imply the
 *  categories line up — label each block with its own scheme. */
export const TAXONOMIES: Record<string, { label: string; classes: string[] }> = {
  // vendor4: { label: "4-class (estimates)", classes: ["white", "black", "asian", "hispanic"] },
};
