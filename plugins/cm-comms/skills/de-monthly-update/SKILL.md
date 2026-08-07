---
name: de-monthly-update
description: Compile the Data Engineering monthly all-hands update — sweep GitHub and Slack for what every engineer shipped, verify shipped-vs-in-flight, surface screenshots, and assemble themed sections with per-person attribution. Use when asked for the monthly DE update, all-hands update, or "what did the team accomplish this month".
---

# DE Monthly All-Hands Update

Produces a company-facing update: **themed sections, product-outcome bullets, engineer credited beneath each point**, 2–3 bullets per person, plus screenshot links and profile photos.

`roster.json` holds GitHub handles ↔ Slack IDs ↔ photo filenames. **Read it first.** Several handles are Korean-keyboard romanizations and cannot be guessed from names (`gkdms99` = 하은/Haeun, `febgkdud` contains 하영/Hayoung).

`roster.json`, `slack-sweep.md`, and `sections.md` sit alongside this file; the two scripts are invoked via `${CLAUDE_PLUGIN_ROOT}` below.

## Prerequisites

- **`gh` CLI** authenticated with org read access — the PR sweep needs it.
- **Slack MCP connector** configured for your account — passes A–D in `slack-sweep.md` need it.
  Without Slack you get the GitHub half only, which systematically undersells design-heavy
  engineers. If Slack is unavailable, say so up front rather than shipping a thin update.

## 1. Scope

Default is the last calendar month through today. Confirm the range if ambiguous.

## 2. Sweep GitHub (all repos, not just the current one)

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/de-monthly-update/collect-prs.sh" 2026-07-01 2026-08-04
```

Read `by-person.md`. It separates **merged** from **open** — open PRs are in-flight and must never be written as shipped.

Notes the script already handles, don't redo by hand:
- `gh search prs` caps near 200 and returns newest-first, so a whole-month query silently drops the early weeks. It chunks the range.
- Bot authors (`Casper-AI-CM`, `claude[bot]`, `devin-ai-integration[bot]`) hide the human who drove the work. Cross-reference Slack.
- Authors not in the roster are flagged — usually new joiners to add.

## 3. Sweep Slack — this is not optional

**Follow `slack-sweep.md`. Run all four passes** — announcements by channel, per person, screenshots, permalinks.

**PR count systematically undersells senior and design-heavy engineers.** In the first run, the two people with the fewest PRs turned out to be the two other senior engineers; their month was architecture specs, product coordination, and customer escalation. A GitHub-only sweep would have made them look idle.

**Inclusion bar:** did the work reach the team or a PM? Something announced, escalated, coordinated, or handed off belongs in the update. A silent internal refactor generally does not.

## 4. Verify before claiming

Every run so far has caught at least one claim that outran reality. Check each candidate bullet:

- **Is the PR merged or open?** Rejected examples: YouTube RPM imputation (open), catalog schema creation (open), a creator-tier sync that merged but whose files a bot revert had deleted.
- **Was it designed or built?** A spec posted to Slack is a real deliverable — describe it as *designed and handed to Product*, never as a live capability. Grep for the implementation before believing it exists.
- **Do the commit messages tell the truth?** One commit labeled "Added ATP ingestion pipeline" contained tiering code and no tennis whatsoever. Open the file list.
- **Does pipeline coverage equal what customers see?** ">95% coverage" meant the data existed; a downstream filter still blocked it from the product. Say "in the pipeline" or leave it out.
- **Are two similar-sounding systems being conflated?** Schema drift detection (Hayoung) and the freshness watchdog (Rafael) are different systems by different people. Check the PR author, not the topic.

When something is genuinely in flight, either put it under **What's next** or drop it. Ask which — the lead may not want a What's next section.

## 5. Balance

Target **2–3 bullets per person**. Count before delivering and report the distribution.

The lead's own count inflates naturally because they touch everything; say so and offer to trim. Same for anyone unusually prolific. Prefer **raising the quiet people by restoring dropped work** over cutting the busy ones — thin sections are usually a dropped theme, not an idle engineer.

## 6. Screenshots

Slack uploads are nearly all named `image.png`, so searching by filename is useless. Search **messages** with `has:file from:<@ID>` to see the text the image was attached to, then pull permalinks by searching a distinctive phrase from that message.

Prefer visuals showing a **product surface** over tables or code. Note that DMs only resolve for their participants — flag those as screenshot-not-link. Infrastructure work (repo splits, ID counters) has no visual; leave those sections text-only rather than forcing something.

## 7. Photos

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/de-monthly-update/fetch-photos.sh" urls.tsv   # filename <TAB> avatar_url
"${CLAUDE_PLUGIN_ROOT}/skills/de-monthly-update/fetch-photos.sh" --resize   # 128px, keeps the page light
```

Get current URLs from `slack_search_users` (the "Profile Pic" field) — avatars change. Bot accounts do not appear in user search or the profile endpoint; grab those manually.

## 8. Output format

**Use `sections.md` as the skeleton** — same sections, same bullet shape, every month.

Markdown that pastes cleanly into Notion. **One bullet per point** — bold outcome, one supporting sentence, attribution last — so each point is a single draggable block.

```markdown
## Data Shares

- **One authoritative view of what we ship to every customer.** shares.chartmetric.com —
  per-customer tables, delivery health, and history, with links into Airflow. — *Charlie*
```

Rules that made the format work:
- **Quantify cost and money wherever it exists.** This meeting already presents revenue numbers, so financial context lands well and is actively wanted. Vendor spend retired, proxy/bandwidth reduction, warehouse cost moved, storage reclaimed, paid-API calls replaced by first-party data, agent hours saved. Hunt for these deliberately — they are usually buried in PR bodies (`~63% bandwidth`, `2.2 TB/mo → 0.8 TB/mo`) and in `#proj-monetization-data`, `#team-data-engineering`, and `#ai-kanban` rather than stated in the announcement. If a figure is not in writing, ask rather than estimate.
- Lead with the **product outcome**, not the technical change. "Brand match scores are now correct" beats "re-keyed the demographic vector tables."
- The engineer is **attribution, not subject** — the team's contribution is the point.
- One sentence plus at most one supporting clause. Company audiences skim.
- Name the specific thing: "Shazam bandwidth cut ~63%", not "one source."
- Sections follow the product, not the org: Main App (+ Monetization) · New Verticals — Music / Sports / Creators · Data Shares · Data Architecture · Reliability · Vendor Migration · Internal Tooling & AI. Propose new themes when a month's work clusters somewhere new.

## 9. Deliver

Give the markdown **inline in chat**, not as a file — it gets pasted into Notion. Alongside it report: bullets-per-person distribution, anything excluded as in-flight and why, and any attribution you were unsure of.
