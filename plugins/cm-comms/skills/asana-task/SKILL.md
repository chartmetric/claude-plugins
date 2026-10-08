---
name: asana-task
description: Create task(s) on the Chartmetric "Unified CM Tasks" Asana board from the session, a PR, free text, a Slack thread, or a GitHub issue. Auto-prefixes the title (BE:/FE:/MCP:/PE:/…) from the repo or task scope, sets the matching Team (default Product Engineering), defaults assignee/Engineer/Planner/follower to the current user, and links a detected GitHub PR via the PR body so Asana's native Github PR section fills. Given a Slack URL, reads the thread, can split it into N tasks, and drafts a reply in the thread with the task link(s). Triggers - /asana-task, "create asana task", "asana task from this slack thread", "asana task from this github issue", "asana task on unified board", "make CM task". Override with team=<TeamName>, prefix=<TOKEN>, assignee=<Name>, or engineer=<Name> in args.
---

# Create Chartmetric Unified CM Task

Use the Asana MCP to create a task on the **Unified CM Tasks** board with sensible defaults.

## Fixed IDs (do not look up)

- **Project**: `1213445772342530` (Unified CM Tasks)
- **Custom fields**:
  - `1213443514830840` — Engineer (people)
  - `1206124268189011` — Planner (people)
  - `1206132751421626` — Slack URL (text)
  - `1213462685458499` — PR Preview Link (text) — a **deploy-preview** URL, never the PR itself
  - `1207508719775201` — Team (enum)

### Team enum options

| Name | GID |
|---|---|
| Product Engineering (**default**) | `1207603513775115` |
| Backend | `1207508719775205` |
| Frontend | `1207508719775204` |
| Data Engineering | `1207508719775206` |
| Infrastructure | `1207534115761476` |
| Custom Dashboard | `1210254820038296` |
| Mobile (Native) | `1208423336018659` |
| Admin Tool | `1208493685092248` |
| Sales Engineering | `1210241524012353` |
| Onesheet | `1211537234638035` |
| Data Assistant | `1211689207392633` |
| Chartmetric Lite | `1213406542898351` |

## Title prefix (required)

Every title gets a `<TOKEN>: ` prefix. The prefix also picks the Team.

| Prefix | Team | Team GID |
|---|---|---|
| `PE:` (**default**) | Product Engineering | `1207603513775115` |
| `BE:` | Backend | `1207508719775205` |
| `FE:` | Frontend | `1207508719775204` |
| `MCP:` | Product Engineering | `1207603513775115` |
| `DE:` | Data Engineering | `1207508719775206` |
| `INFRA:` | Infrastructure | `1207534115761476` |
| `MOBILE:` | Mobile (Native) | `1208423336018659` |
| `ADMIN:` | Admin Tool | `1208493685092248` |
| `AI:` | Data Assistant | `1211689207392633` |
| `FLOW:` | Product Engineering | `1207603513775115` |
| `SE:` | Sales Engineering | `1210241524012353` |

### Picking the prefix — infer, never ask

Resolve in this order and stop at the first hit:

1. **Explicit**: `prefix=<TOKEN>` arg, or the title the user typed already starts with a
   table token (or any `Foo: ` prefix, e.g. `Devin:`) → keep it verbatim, do not double-prefix.
2. **Scope spans backend + frontend** (task text or session touches both an API repo and a
   web repo) → `PE:`. Append a `(api + web)` style hint to the title when it clarifies.
3. **Repo of the current working directory** (or the repo the task is clearly about):

   | Repo | Prefix |
   |---|---|
   | `chartmetric-api`, `back` | `BE:` |
   | `chartmetric-web-app`, `front`, `chartmetric-design-system` | `FE:` |
   | `chartmetric-mcp`, `chartmetric-maestro-mcp` | `MCP:` |
   | `chartmetric-infra`, `infra`, `terraform-modules` | `INFRA:` |
   | `admin-tool`, `admini-tool` | `ADMIN:` |
   | `chartmetric-native-mobile-app` | `MOBILE:` |
   | `chartmetric_data_script`, `data_infra`, `data_utils`, `chartmetric-data-ssr` | `DE:` |
   | `chartmetric-flow` | `FLOW:` |
   | `melodi-worker`, `casper` | `AI:` |

4. **Anything else** (new repo, no repo, unreadable scope) → `PE:`.

`team=<Name>` overrides the Team the prefix implies; it does **not** change the prefix.

## Title style

**Write the title as if the task were created before any PR existed** — because conceptually it
was. The task names the work; the PR is one artifact of doing it. The board is also read by
non-engineers, so a title that reads like a diff summary is noise to half its audience.

Never in a title:

- **PR numbers or links** — no `#6871`, no `PR 6871`, no `(see PR)`. Those go in the Links
  section of the notes.
- **Commit-message prefixes** — no `hotfix:`, `feat:`, `fix:`, `chore:`. The `BE:`/`PE:` prefix
  is the only prefix.
- **Branch or repo names**, file paths, line numbers, commit SHAs.

Technical is fine — this is code work. Endpoint paths, table names, and the actual feature name
belong in the title when they *are* what the task is about. What to avoid is dumping the
implementation: symbol chains, internal helper names, and enumerated edge cases read like a diff
summary, not a task. One clear noun phrase, roughly under 80 chars. Push the detail into
`html_notes`, which has room for it.

| Too much | Better |
|---|---|
| `BE: unit test rdcGet/rdcSet reportBytes callback and falsy-key guard` | `BE: Add Redis cache helper test coverage` |
| `BE: hotfix(sns) filter out null code entries in YouTube/TikTok audience-stats responses (PR #6871)` | `BE: Fix 500 on YouTube/TikTok artist audience stats` |
| `MCP: refactor _resolve_user_id() to read _meta.user_id before falling back to OAuth claims` | `MCP: Per-user identity resolution for MCP tools` |

Keeping endpoint paths is good when the endpoint is the subject: `PE: /location/list
server-side pagination (api + web)` is right as written.

## Inputs to extract from the user's message / args

1. **Task title** — required. If not given and no Slack thread or GitHub issue to derive it
   from, ask once.
   Prefix it per the rules above.
2. **Slack URL** — optional. Detect `https://*.slack.com/...` URLs in the message. See
   "Reading a Slack thread" below.
3. **GitHub PR URL** — optional. Detect `https://github.com/<owner>/<repo>/pull/<N>` in the
   message or session. See "Linking a PR" below.
4. **GitHub issue URL** — optional. Detect `https://github.com/<owner>/<repo>/issues/<N>`. See
   "Reading a GitHub issue" below.
5. **Team override** — optional. `team=<Name>` (case-insensitive).
6. **Prefix override** — optional. `prefix=<TOKEN>` (case-insensitive).
7. **Assignee / Engineer override** — optional. `assignee=<Name>` / `engineer=<Name>`, or
   plain phrasing ("assignee Jay, engineer Akshay"). Resolve each name with
   `mcp__claude_ai_Asana__search_objects` (`resource_type: "user"`); if a name matches
   several users or none, ask. Planner and follower stay `me`.
8. **Task count** — default one. "Create N tasks" splits the thread or context by topic,
   usually one task per PR or distinct issue. If the work spans api + web repos and the user
   asked for separate tasks, give each its own prefix and Team.
9. **Description / notes** — **always populate**. If the user supplied explicit description
   text, use it verbatim. Otherwise synthesize from session context (do NOT skip this step):
   - Why the task exists (1–2 sentences pulled from the current conversation, Slack thread, or PR being referenced).
   - Concrete scope / what "done" looks like, if discernible from context.
   - Relevant links: PR URLs, Slack thread URL, related Asana tasks, file paths with line numbers.
   - If no Slack URL, no PR, no issue, and no clear conversation context exists, ask the user once for a
     1–2 sentence description before creating. Do not create with empty notes.

## Reading a Slack thread

URL format: `https://chartmetric.slack.com/archives/<CHANNEL_ID>/p<TS_NO_DOT>[?thread_ts=<PARENT_TS>]`

- `channel_id` = the segment after `/archives/`.
- Parent ts = the `thread_ts` query param when present (the `p…` segment is then a reply).
  Otherwise convert `p…` by inserting a `.` before the last 6 digits:
  `p1776461959149649` → `1776461959.149649`.

Read the whole thread with `slack_read_thread` (`channel_id` + parent ts) — replies usually
carry the decision, fix, and PR links. Use it for the title, `html_notes`, and any PR to link.

## Reading a GitHub issue

```bash
gh issue view <N> --repo <owner>/<repo> --json title,body,comments,labels,url
```

- Use the title, body, and comments for the task title and `html_notes`, rewritten per "Title
  style" — the issue title is not the task title verbatim.
- The issue's repo picks the prefix (step 3 of "Picking the prefix").
- Link the issue under `<h2>Links</h2>` with a descriptive label.
- Read-only: do not comment on, label, or close the issue.

## How to create

Call `mcp__claude_ai_Asana__create_tasks` with `default_project: "1213445772342530"` and one
task object per task (several tasks go in the same call):

- `name`: `<PREFIX>: <title>`
- `assignee`: `me`, or the resolved `assignee=` GID
- `followers`: `me`
- `custom_fields`: **JSON string** with
  - `1207508719775201`: Team enum GID (from prefix, or `team=` override)
  - `1213443514830840`: `me`, or the resolved `engineer=` GID (Engineer)
  - `1206124268189011`: `me` (Planner)
  - `1206132751421626`: Slack URL string (omit key if no URL)
- `html_notes`: **required** — wrap in `<body>...</body>`. **Allowed tags**: `body, strong, em, u, s, code, ol, ul, li, a, blockquote, pre, h1, h2, hr/, img`. **Do not use `<br/>` or `<p>`** — Asana rejects those. Separate paragraphs with `<h2>` headings or `<ul>`/`<ol>` lists instead of blank lines.

### html_notes template (use this shape unless user supplied custom text)

```html
<body>
<h2>Context</h2>
<ul>
  <li>1–2 line why this exists, pulled from session/Slack/PR context.</li>
</ul>
<h2>Scope</h2>
<ul>
  <li>Bullet what's in scope. Skip section if not discernible.</li>
</ul>
<h2>Links</h2>
<ul>
  <li><a href="...">Root-cause fix — dependency bump</a></li>
  <li><a href="...">Slack thread</a></li>
</ul>
</body>
```

Omit any section that has no content rather than leaving it empty. If only links exist, just emit the `<h2>Links</h2>` block.

**Link labels are descriptive, never bare PR numbers.** `<a href="...">Root-cause fix —
dependency bump</a>`, not `<a href="...">PR #97</a>`. Same reason as the title rule: the board is
read by non-engineers, to whom a PR number is noise. This applies to notes body text too, not
just the title.

## Linking a PR

PRs often exist before the task. Asana's **Github PR** section on a task is an *external
attachment* created by the GitHub↔Asana integration — it is not a writable custom field, and
the Asana MCP has no attachment-create tool. The integration fires when the **PR body contains
an `app.asana.com` task URL**.

**Never put the PR URL in the `PR Preview Link` custom field** (`1213462685458499`) — that
field is for a deploy-preview URL, not the pull request.

Usually the task is created first and the PR follows, in which case `/cm-skills:ship-pr` puts
`**Asana**: <task url>` in the body at creation and the Github PR section fills on its own —
nothing to do here. Only when the **PR already exists** does it need patching:

```bash
# parse owner/repo/N from the PR URL
gh api repos/<owner>/<repo>/pulls/<N> -q .body > /tmp/.../body.md   # scratchpad, not the repo
# append:  \n\n**Asana**: <task permalink_url>
#          \n**Slack**: <slack thread URL>   # only if a Slack URL was given and isn't already in the body
gh api repos/<owner>/<repo>/pulls/<N> -X PATCH -F body=@/tmp/.../body.md
```

- **Never `gh pr edit`** — it fails on some Chartmetric repos (deprecated projects-classic
  GraphQL). Always the `gh api ... -X PATCH` form above.
- **If the PR body already contains an `app.asana.com` link**, do not touch the body. Report
  which task it already points at and move on.
- If the `gh api` PATCH fails, report it; the task itself is already created and correct.
- Preserve the existing body exactly; only append. Do not reformat or re-wrap it.
- **Patching an existing PR does not populate the Github PR section.** The integration scans
  the body only on `pull_request.opened`; a later edit, a comment carrying the URL, and a
  close/reopen all fail to re-trigger it (verified on PR #7164, 2026-08-06). So after
  patching, tell the user the section needs a manual "Add GitHub pull request" in Asana.
- **Exactly one `app.asana.com` URL in the PR body.** The integration attaches the PR to every
  task URL it finds, so listing follow-up tasks under "Relevant Links → Other" silently links
  the PR to work it does not implement. With N tasks, each PR gets only the task it implements.

## Replying in the Slack thread

Only when a Slack URL was given. After the task(s) exist, create a **draft** reply with
`mcp__claude_ai_Slack__slack_send_message_draft` (`channel_id` + parent ts as `thread_ts`) —
never `slack_send_message`; the user reviews and sends it.

```
Created Asana task(s) on Unified CM Tasks (assignee: <Name>, engineer: <Name>):
• <Short title>: <permalink_url>
```

Use `permalink_url` from the `create_tasks` response, not a hand-built URL. If the draft fails
(e.g. `draft_already_exists`), report it and include the message text so the user can paste it.

## Output

After creation, report:
- Task title (linked to `permalink_url`)
- Confirmed fields: Assignee / Engineer / Planner, Team, Slack URL
- Whether the PR body was patched, skipped (already linked — name the task), or failed
- Slack: whether the thread reply draft was created (with `channel_link`), or skipped/failed

Keep the report to ~3-5 lines. The user can see the task in Asana.

## Examples

> `/asana-task Migrate similar artists to CH https://chartmetric.slack.com/archives/C0AJ1LU8ETT/p1776806127834209`

→ cwd is `chartmetric-api` → title "BE: Migrate similar artists to CH", Team Backend. Slack URL
set. All human fields = me. `html_notes` synthesized from the linked thread (read it via
`slack_read_thread` if context isn't already in session). Thread reply drafted with the task link.

> `/asana-task create 2 tasks from https://chartmetric.slack.com/archives/C0AJ1LU8ETT/p1776806127834209?thread_ts=1776806100.000100 assignee Jay`

→ Parent ts `1776806100.000100` from `thread_ts`. Thread split into two tasks (one per PR),
both in one `create_tasks` call, assignee = Jay's GID from `search_objects`, Engineer/Planner =
me. Each existing PR body gets only its own task URL. One thread reply draft lists both tasks.

> `/asana-task Fix login spinner flicker` (cwd `chartmetric-web-app`)

→ "FE: Fix login spinner flicker", Team Frontend. No Slack URL and no session context → ask once
for a 1–2 sentence description, then populate `html_notes`.

> `/asana-task Plan per-user identity + prepaid credit billing` (cwd `chartmetric-mcp`)

→ "MCP: Plan per-user identity + prepaid credit billing", Team Product Engineering.

> `/asana-task getMoods payload restructure` (session touched both api and web)

→ "PE: getMoods payload restructure (api + web)", Team Product Engineering.

> `/asana-task https://github.com/chartmetric/chartmetric-api/pull/6871 hotfix(sns): filter out null code entries in YouTube/TikTok audience-stats responses`

→ Title rewritten to task language, not commit language: **"BE: Fix 500 on YouTube/TikTok artist
audience stats"** — no `hotfix(sns):`, no PR number. Because the PR already exists, PATCHes the
PR body to append `**Asana**: <task url>`, then reports that the Github PR section needs a
manual attach.

> `/asana-task team=Onesheet prefix=PE Ship onesheet export v2`

→ "PE: Ship onesheet export v2", Team Onesheet (override beats the prefix's implied team).

> `/asana-task https://github.com/chartmetric/chartmetric-api/issues/1234`

→ Reads the issue with `gh issue view`; repo `chartmetric-api` → `BE:`, Team Backend. Title
rewritten from the issue in task language; `html_notes` from body + comments with the issue
linked under Links. The issue itself is not touched.
