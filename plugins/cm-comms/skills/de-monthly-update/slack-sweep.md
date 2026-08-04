# Slack sweep — run all four passes

GitHub says what was written. Slack says what was **communicated, coordinated, and landed**,
which is what a company audience cares about. Run every pass; skipping C and D is why early
drafts have no screenshots.

Set `include_context:false` and `response_format:"concise"` on every search or the output
buries you. Substitute `<START>` with the range start (e.g. `2026-08-01`).

---

## Pass A — announcements by channel

Where shipped work gets announced. This is the richest source of product-outcome phrasing,
because people already wrote it for a non-DE audience.

```
in:#data-updates after:<START>
in:#proj-data-shares after:<START>
in:#proj-flow after:<START>
in:#proj-new-verticals-new-app after:<START>
in:#proj-influencers-brands-games after:<START>
in:#customer-issues-and-requests after:<START>
in:#proj-monetization-data after:<START>
in:#casper-testing after:<START>
in:#team-data-engineering after:<START>
```

Look for: launch posts, `[Date] Updates on …` recaps, `@channel` announcements, and any
message written to explain something to Product.

## Pass B — per person

For each `slack` id in `roster.json`:

```
from:<@SLACK_ID> after:<START>
```

Catches design specs, priority statements, customer escalations, and handoffs — the work
that leaves no PR. Also catches people saying they have **not** started something, which is
how you avoid crediting unstarted work.

## Pass C — screenshots

Slack uploads are almost all named `image.png`, so file-name search is useless. Search
**messages carrying files** so you see the text the image was attached to:

```
has:file after:<START> from:<@SLACK_ID>
```

Then per channel for cross-team visuals:

```
has:file after:<START> in:#proj-monetization-data
has:file after:<START> in:#proj-new-verticals-new-app
```

Prefer images showing a **product surface** over tables, code, or Airflow. DMs resolve only
for their participants — mark those "screenshot it, don't link it".

## Pass D — permalinks

Concise output omits permalinks. For each screenshot you intend to use, search a distinctive
phrase from its message to retrieve the link:

```
"Data Shares Catalog is live"
"Demographics for Tier 2/3 creators are ready"
```

Deliver screenshots as a table: **which bullet it supports · what it shows · link**.

---

## Attribution traps

- A person announcing a fix is not always its author — check the PR author.
- Adjacent systems get conflated. Schema drift detection and the freshness watchdog are
  different systems owned by different people.
- Work done *by* someone versus *investigated* by them: if the investigation drove another
  engineer's change, credit reads "*A, with B*".
- Bot-authored PRs (`Casper-AI-CM`, `claude[bot]`, `devin-ai-integration[bot]`) hide the human
  who drove them. Pass B tells you who.
