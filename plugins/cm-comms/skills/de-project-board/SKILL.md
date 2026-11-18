---
name: de-project-board
description: Create, update or close cards on the Data Engineering GitHub Project board (orgs/chartmetric/projects/1). Use when starting a piece of work that should be visible to the lead, when opening or merging a PR that belongs to a card, when the user asks to "make a card", "update the board", "move my card", or at the start/end of a week.
---

# Data Engineering project board

Board: https://github.com/orgs/chartmetric/projects/1 ("Data Engineering").
Purpose: the lead (lbouis) reads it to see what the team is working on, what
finished, and why something took longer. Each teammate keeps their own cards
current. Weekly snapshots are taken from this board, so the fields below are
what the numbers are built from.

## 1. When to make a card

Make a card when:
- The work takes half a day or more, or the lead would ask about it.
- Something came up mid-week (incident, request) and takes half a day or more.
  Set Planned to No.

Do not make a card for:
- Small fixes under 1-2 hours, PR reviews, answering questions, routine checks.
- Sub-steps of a bigger piece of work. Put them as a checklist in that card's body.

Rules:
- One card per outcome (a problem solved), not per PR. A card usually has 1-15 PRs.
- Make it when you start, not after merging. Then the PRs can link to it (section 5).
- Search the board for the subject first (the part before ":" in titles). If a card
  already covers it, add your PRs there instead of making a new one.
- Work that carries over to the next week keeps its card. Move Week forward; never
  make a second card for the same outcome.
- Only DE work goes on this board. Do not add issues from other teams.

Which repo the issue lives in: the repo where most of the card's PRs are, so PRs
close it with a plain `Closes #N`. Only these repos (issues enabled, DE-owned):

| Repo | Use for |
|---|---|
| chartmetric/chartmetric-nv-data | NV pipelines, DAGs, DDL (default when unsure) |
| chartmetric/chartmetric_data_script | Legacy data_script DAGs and scripts |
| chartmetric/chartmetric-data-eks | EKS, Karpenter, Airflow infra, IAM, terraform |
| chartmetric/data_infra | data_infra DAGs (analytics, dashboard, ad_tool, email reports) |
| chartmetric/data_utils | Shared data_utils library |

For work in any other repo, put the issue in chartmetric-nv-data and use
`Closes chartmetric/chartmetric-nv-data#N` in the PR.

## 2. Fields (all required unless noted)

| Field | Values | How to choose |
|---|---|---|
| Assignees | GitHub login | The owner. One person. |
| Status | Todo / In progress / Waiting / Done | See section 4. |
| Project | EKS platform, Analytics cache, Raw cache, Legacy DAG migration, Link processing, Cost, Observability, NV ingestion, Playlist, Album, Audience, Snowflake | The stream the work belongs to. Ask gkdms99 to add an option rather than forcing a bad fit. |
| Work type | Build / Investigate / Monitor / Ops | Build = new or changed pipeline/code. Investigate = finding a cause or a number. Monitor = watching runs or data after a change. Ops = infra, upgrades, permissions, incidents. |
| Size | S / M / L | S = 1 day or less. M = 2-3 days. L = more than 3 days or spread over weeks. Measure elapsed work, not lines changed. |
| Min effort | free text | The shortest honest time if nothing got in the way, e.g. "1 day", "half a day per DAG". |
| Size reason | Waiting / Unknowns / External / Staged | Required for M and L, empty for S. Why it took longer than Min effort: Waiting = needed a daily run or soak to confirm. Unknowns = the cause only showed up by running it. External = blocked on a vendor, another team or a review. Staged = had to ship in ordered steps (e.g. one EKS version per PR). |
| Week | e.g. "2026 - Nov 16-22" | One value only: the week the card is being worked on now. If it carries over, move it to the new week (carry-over is one of the weekly numbers). The full span is in Start date and Target date, and the weekly snapshots record which weeks it was in. |
| Planned | Yes / No | Yes if it was on the plan at the start of the week. No if it came up mid-week (incident, request). |
| Start date | date | Day work started (first PR opened). |
| Target date | date | Expected finish. Set it when you start; update it if it slips. For Done cards it is the day of the last merge. Leave empty only when truly unknown. |

Do not use Labels, Milestone or Sub-issues for this board.

## 3. Card text

Write in English. No emojis.

Title = `<Subject>: <outcome>`. The title is often seen without the Project field
(issue lists, notifications, PR "Closes" links, Slack previews), so lead with what
the card is about:
- Subject = the concrete thing being changed: a platform (Spotify, TikTok catalog,
  Genius), a system (data-eks, Snowflake), or a table/DAG (cm_track_cache,
  Chartmetric_Insert_Artist_Stage). Not the Project field value ("NV ingestion" is
  too broad and duplicates the field).
- Outcome = what is true when it is done, starting with a verb. Not the PR title.

Examples:
- "SSM Parameter Store: cut cost (~$32/day) by caching lookups"
- "data-eks: upgrade EKS 1.31 to 1.37 and Karpenter 1.9 to 1.15 before the 1.31 support deadline"
- "Boomplay: restore scraping behind Cloudflare"

Body template:

```markdown
## Problem
What was broken or missing, with numbers (cost, failure count, lag).

## How it was solved
The approach in 2-5 sentences. Name tables, DAGs and settings.

## Done / Verification
- Evidence that it works: a query result, a run id, a row count, a cost figure.

Pending post-merge checks:
- [ ] Anything that can only be checked after merge (next daily run, cost after a week).

## Size
- Size: M
- Minimum effort: 1 day per platform
- Size reason: Unknowns

## PRs
- https://github.com/chartmetric/<repo>/pull/<n>
```

Use full PR URLs, not "#123", because the PRs are often in another repo.

## 4. Status lifecycle

| Status | Meaning |
|---|---|
| Todo | Card exists, work not started. |
| In progress | Working on it, or PRs open. |
| Waiting | Merged or paused, blocked on something outside your control (a scheduled run, an unpause date, another team). Write the date or condition in "Pending post-merge checks". |
| Done | Merged AND verified. Every "Pending post-merge checks" box is ticked. |

Merged is not Done. If checks are still pending, the card stays In progress or Waiting.

## 5. Automatic closing and the Done column

- A card's issue is closed when a PR whose body contains a closing keyword is merged
  into the repo's default branch (main):
  - PR in the same repo as the issue: `Closes #1430`
  - PR in another repo: `Closes chartmetric/<issue-repo>#1430`
- The board workflow "Item closed" then sets Status to Done.
- Only the last PR of a card should use `Closes`. Earlier PRs use `Refs #1430`
  (or `Refs chartmetric/<issue-repo>#1430`). Refs does not close anything, but the
  PR still shows on the issue timeline.
- If the card has pending post-merge checks, do not use `Closes` at all. Use `Refs`,
  and close the issue by hand once the checks pass (`gh issue close <n> -R chartmetric/<issue-repo> -c "<evidence>"`).
- A PR merged before the card existed cannot be linked afterwards, so its
  "Linked pull requests" cell stays empty. List it under "## PRs" instead.
- Cross-repo `Closes` has not been tested on this board yet. If the issue stays open
  after merge, close it by hand and tell gkdms99.

## 6. Doing it with gh

Needs the project scope once: `gh auth refresh -s project`.

```bash
REPO=chartmetric/<issue-repo>; OWNER=chartmetric; NUM=1; PID=PVT_kwDOAf8yC84BsIew

# Check for an existing card on the same subject first
gh project item-list $NUM --owner $OWNER --format json --limit 500 --jq '.items[].title' | grep -i "<subject>"

url=$(gh issue create -R $REPO --title "<outcome>" --body-file /tmp/card.md --assignee <login>)
item=$(gh project item-add $NUM --owner $OWNER --url "$url" --format json --jq .id)

# Field and option ids (look them up every time, do not hardcode)
gh project field-list $NUM --owner $OWNER --format json

# Single-select field (Status, Project, Work type, Size, Size reason, Planned)
gh project item-edit --project-id $PID --id $item --field-id <field-id> --single-select-option-id <option-id>
# Text field (Min effort) and date fields (Start date, Target date)
gh project item-edit --project-id $PID --id $item --field-id <field-id> --text "1 day"
gh project item-edit --project-id $PID --id $item --field-id <field-id> --date 2026-11-18
```

Week ids are not in field-list. Get them by title with GraphQL. Iteration ids change
whenever the Week field is edited, so always look them up:

```bash
gh api graphql -f query='{organization(login:"chartmetric"){projectV2(number:1){field(name:"Week"){... on ProjectV2IterationField{id configuration{iterations{id title} completedIterations{id title}}}}}}}'
gh project item-edit --project-id $PID --id $item --field-id <week-field-id> --iteration-id <iteration-id>
```

If the current week is missing from Week, do not create it with another name format.
Ask gkdms99, or add it in the field settings as "YYYY - Mon D-D" (e.g. "2026 - Nov 30-Dec 6").

## 7. Before you finish

- The card meets section 1 and does not duplicate an existing card.
- Every field in section 2 is set (check with `gh project item-list 1 --owner chartmetric --format json`).
- Status matches section 4: no Done card with an unticked pending check.
- Last PR uses `Closes`, earlier PRs use `Refs`.
- Title is "<Subject>: <outcome>". Card text is English, has numbers, and lists full PR URLs.
