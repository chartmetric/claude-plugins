---
name: asana-task
description: Create a task on the Chartmetric "Unified CM Tasks" Asana board. Auto-prefixes the title (BE:/FE:/MCP:/PE:/…) from the repo or task scope, sets the matching Team (default Product Engineering), defaults assignee/Engineer/Planner/follower to the current user, and links a detected GitHub PR via the PR body so Asana's native Github PR section fills. Accepts a Slack URL. Triggers - /asana-task, "create asana task", "asana task on unified board", "make CM task". Override with team=<TeamName> or prefix=<TOKEN> in args.
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
   | `melodi-worker`, `kevin-slack-bot` | `AI:` |

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

1. **Task title** — required. If not given, ask once. Prefix it per the rules above.
2. **Slack URL** — optional. Detect `https://*.slack.com/...` URLs in the message.
3. **GitHub PR URL** — optional. Detect `https://github.com/<owner>/<repo>/pull/<N>` in the
   message or session. See "Linking a PR" below.
4. **Team override** — optional. `team=<Name>` (case-insensitive).
5. **Prefix override** — optional. `prefix=<TOKEN>` (case-insensitive).
6. **Description / notes** — **always populate**. If the user supplied explicit description
   text, use it verbatim. Otherwise synthesize from session context (do NOT skip this step):
   - Why the task exists (1–2 sentences pulled from the current conversation, Slack thread, or PR being referenced).
   - Concrete scope / what "done" looks like, if discernible from context.
   - Relevant links: PR URLs, Slack thread URL, related Asana tasks, file paths with line numbers.
   - If no Slack URL, no PR, and no clear conversation context exists, ask the user once for a
     1–2 sentence description before creating. Do not create with empty notes.

## How to create

Call `mcp__claude_ai_Asana__create_tasks` with `default_project: "1213445772342530"` and one
task object:

- `name`: `<PREFIX>: <title>`
- `assignee`: `me`
- `followers`: `me`
- `custom_fields`: **JSON string** with
  - `1207508719775201`: Team enum GID (from prefix, or `team=` override)
  - `1213443514830840`: `me` (Engineer)
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
  the PR to work it does not implement.

## Output

After creation, report:
- Task title (linked to `permalink_url`)
- Confirmed fields: Assignee / Engineer / Planner, Team, Slack URL
- Whether the PR body was patched, skipped (already linked — name the task), or failed

Keep the report to ~3-5 lines. The user can see the task in Asana.

## Examples

> `/asana-task Migrate similar artists to CH https://chartmetric.slack.com/archives/C0AJ1LU8ETT/p1776806127834209`

→ cwd is `chartmetric-api` → title "BE: Migrate similar artists to CH", Team Backend. Slack URL
set. All human fields = me. `html_notes` synthesized from the linked thread (read it via
`slack_read_thread` if context isn't already in session).

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
