---
name: cm-pr-review
description: Reviews every open PR that GitHub thinks the user should review. Discovers them via `gh search prs --review-requested=@me`, loads each PR's repo conventions (AGENTS.md + .agents/skills, else CLAUDE.md + .claude/skills) read-only, writes a markdown review per PR, then asks per-PR whether to post. Pass a PR URL or `owner/repo#N` to review just that PR. Reviews are always submitted as the `chartmetric-claude` GitHub App via the Maestro MCP `submit_pr_review` tool — never the reviewer's personal account. Triggers - /cm-pr-review, "review my PRs", "what do I need to review".
author: hyosik@chartmetric.com
---

# cm-pr-review — review the PRs awaiting you

Goal: turn the morning "what do I need to review" question into a single command. Discover every PR where the user is a requested reviewer (directly or via team delegation), generate one review draft per PR using each repo's own conventions, then let the user post or skip each draft.

The skill is one-shot. No background scheduling, no Slack, no posting until the user confirms per PR.

## Posting identity — always the `chartmetric-claude` App

Every review this skill posts — **approve, request-changes, or comment** — is submitted as the **`chartmetric-claude` GitHub App** (`chartmetric-claude[bot]`), the same way [chartmetric-one#231](https://github.com/chartmetric/chartmetric-one/pull/231) got its bot review-and-approval. It lands under the shared bot's name for **everyone**, never the individual reviewer's GitHub account.

- **Reads** (discovery, `gh pr view`, `gh pr diff`, loading repo conventions) run as the user via `gh` — read-only, fine.
- **Writes** (posting the review) go **exclusively** through the Maestro MCP `submit_pr_review` tool, which authenticates as the App via an installation token.
- **Never** post a review with `gh pr review` — that attributes it to whoever is logged into `gh` locally (e.g. the review on chartmetric-api#7035 posted as a personal account instead of the bot). If Maestro can't post, the skill refuses and skips rather than falling back to `gh`. See [Step 4](#step-4--post-approve-or-skip-after-all-drafts-are-shown).

## Single-PR mode

If the args name a PR — a URL like `https://github.com/<owner>/<repo>/pull/<num>` (any trailing `/files`, `/changes`, etc. ignored) or `<owner>/<repo>#<num>` — skip Steps 1–2 and review only that PR. Still resolve `GH_LOGIN` (Step 1's first command) for the attribution block, then continue at Step 3. The PR doesn't need to have requested you, and the org filter doesn't apply.

## Step 1 — Discover PRs

**Two filters apply to the search:**

1. **Org scope** — only PRs in the `chartmetric` GitHub org. The user may have personal/study repos on GitHub; those are out of scope for this skill.
2. **Direct request only** — exclude PRs where the user is reachable only through team membership. GitHub's `review-requested:@me` qualifier is team-inclusive (returns every PR where any of the user's teams was requested, which for a Chartmetric engineer is the entire back-end + front-end + senior-product-engineers queue — ~70+ PRs, most handled by someone else). Filter client-side to PRs where the user is a direct reviewer.

First, resolve the user's GitHub login:

```bash
GH_LOGIN=$(gh api user --jq .login)
```

Then run one GraphQL search that pulls each PR's `reviewRequests` inline, scoped to `org:chartmetric`, and filter to entries where the requested reviewer is a `User` matching `$GH_LOGIN`:

```bash
gh api graphql -f query='
query {
  search(query: "is:pr is:open review-requested:@me org:chartmetric", type: ISSUE, first: 100) {
    nodes {
      ... on PullRequest {
        number
        title
        url
        additions
        deletions
        changedFiles
        baseRefName
        headRefName
        headRefOid
        repository { nameWithOwner }
        author { login }
        reviewRequests(first: 20) {
          nodes {
            requestedReviewer {
              __typename
              ... on User { login }
              ... on Team { slug }
            }
          }
        }
      }
    }
  }
}' --jq ".data.search.nodes[] | select(.reviewRequests.nodes[].requestedReviewer.login? == \"$GH_LOGIN\")"
```

One round trip, no N+1. If the result set is empty, report "No PRs directly awaiting your review" and exit. Do not proceed.

Note for users: PRs only requested to a team you're on are intentionally hidden here. Team delegation (`github_team_settings` in chartmetric-infra) is meant to pick a specific individual per team request, which then becomes a direct request and will appear in this list.

## Step 2 — Show the list and ask for confirmation

Print the count and a one-line summary per PR:

```
🔍 Found 3 PRs awaiting your review:
  1. chartmetric/chartmetric-api#1234     Add retry to webhooks         (+120 -40, 3 files)  @alice
  2. chartmetric/chartmetric-web-app#5678 Dashboard filter UI           (+340 -12, 8 files)  @bob
  3. chartmetric/chartmetric-infra#42     Tighten preview env IAM       (+18 -4, 1 file)     @carol

Review all? [y / n / specific PRs e.g. "1,3"]
```

- `y` or empty Enter → review all
- `n` → exit
- Comma-separated indices → review only those
- Any other input → re-ask once, then exit on second invalid

## Step 3 — Per-PR review (batch, sequential)

For each selected PR, run these substeps in order:

### 3a. Fetch PR data

```bash
gh pr view <number> --repo <owner>/<repo> --json number,title,body,baseRefName,headRefName,headRefOid,additions,deletions,changedFiles,files,author
gh pr diff <number> --repo <owner>/<repo>
```

Keep the diff in memory for the review prompt.

### 3b. Load repo conventions (REQUIRED, read-only)

The skill must always have repo context before reviewing. Never generate a review from the diff alone.

**Hard rule — do NOT touch the user's local working tree.**
- No `git fetch`, `git pull`, `git checkout`, `git stash`, `git reset`.
- No writes to any file inside the repo.
- No `cd` that persists past the read.

**Which files.** Agent-neutral docs first, Claude-specific docs only as a fallback:

1. **`AGENTS.md` exists** → load it plus every `*.md` under `.agents/skills/` (recursive, all depths). Don't also load `CLAUDE.md` / `.claude/skills` — in repos that have both, they're a pointer (`@AGENTS.md`) and a symlink to the same files.
2. **No `AGENTS.md`** → load `CLAUDE.md` plus every `*.md` under `.claude/skills/` (recursive, all depths).
3. **Neither** → warn `_no repo conventions found — falling back to default review prompt_` and continue. This is the only case where you may review without repo context.

**Read every file in the set, not just the index `SKILL.md`s** — rule files under `references/` are where the actual conventions live.

**Where from**, in priority order:

1. **Local clone** at `~/code/chartmetric/<repo_name>` (e.g. `chartmetric-api`): read the files as-is from the working tree. It may not match the PR's base commit; say so in the header.
2. **GitHub API** (no local clone): list the tree once at the PR's base branch, then fetch each file raw.
   ```bash
   gh api "repos/<owner>/<repo>/git/trees/<baseRefName>?recursive=1" \
     --jq '.tree[] | select(.type == "blob") | .path' | grep -E '^(AGENTS\.md|CLAUDE\.md|\.agents/skills/.*\.md|\.claude/skills/.*\.md)$'
   gh api "repos/<owner>/<repo>/contents/<path>?ref=<baseRefName>" -H 'Accept: application/vnd.github.raw'
   ```
   Pick the file set from the listing using the rules above. If the tree response has `"truncated": true`, list `.agents/skills` (or `.claude/skills`) with the contents API instead, recursing into every `dir`. Don't list `.claude/skills` via the contents API — when it's a symlink the API returns a link, not a directory.

If the API itself errors (auth, rate limit), abort the PR with `_skipped: could not load repo context_` and continue to the next PR — do **not** fall through to diff-only review.

**Record what was loaded** for the 3e header: the source (`AGENTS.md` or `CLAUDE.md`), the number of skill files loaded vs. found, and `local` or `api`. Loaded must equal found; if you skipped any, go back and read them.

### 3c. Compose the review

Build the system prompt in this order (later sections override earlier ones on conflict):

1. Default reviewer baseline (below).
2. Reviewer's personal rules — the first that exists of `~/.claude/cm-pr-review-style.md`, `~/.claude/AGENTS.md`, `~/.claude/CLAUDE.md`. Load it once per run. Its coding and writing rules (comments, style, conventions) count as review criteria, not just tone — flag violations like any repo rule.
3. Repo `AGENTS.md` (or `CLAUDE.md` in the fallback case).
4. Repo skill files from 3b (sorted by file path for determinism).

The repo wins over personal rules on conflict.

**Default reviewer baseline:**

> You are an experienced engineer reviewing a teammate's pull request. Be direct, terse, specific. Lead with the most load-bearing concern. Reference file paths and line ranges where relevant. Don't restate what the diff already shows. If the PR looks good, say so in one line and stop.

User message contains: PR number, title, author, URL, full diff, and an instruction to write the review as markdown.

### 3d. Decide a recommended verdict

After composing the review, judge whether the PR is in shape to approve, needs changes, or just deserves a comment. Use this rubric:

- **Approve** — no blocking issues; nits or optional suggestions are fine. The PR could merge as-is and the reviewer would be willing to approve in person.
- **Request changes** — at least one blocking issue: bug, regression risk, missing test for a behavior change, violation of repo conventions, breaking API change without justification. The PR must change before merging.
- **Comment** — neither. Open question, want author's input, want to flag something without blocking. Default when uncertain — never auto-escalate to request-changes when you could simply ask.

Record the verdict as `recommended: approve | request_changes | comment`. Keep it in the in-memory state for Step 4 — **do not** add a verdict line to the review body that ships to GitHub. The user's explicit key press in Step 4 conveys the actual verdict via the `submit_pr_review` `event` (`APPROVE` / `REQUEST_CHANGES` / `COMMENT`); including a "Recommended: X" header in the published comment would muddy that.

The recommendation surfaces only:

1. In the terminal render (Step 3e), as a separator-level header so the user sees it before the body.
2. In the Step 4 prompt, where ENTER takes the recommendation.

### 3e. Render the draft

Print the review to the terminal with a clear separator:

```
═══════════════════════════════════════════════════════
PR #<num> — <title>  (<repo>)
<URL>
_context: <AGENTS.md|CLAUDE.md> + <loaded>/<found> skill files (<local|api>); personal: <file name|none>_
Recommended verdict: <approve | request changes | comment> — <one-line reason>
═══════════════════════════════════════════════════════

<review markdown>
```

The verdict line is for the user only — it is **not** included in the body that will be posted to GitHub.

Do NOT prompt for Post/Skip yet. Continue to the next PR.

## Step 4 — Post, approve, or skip (after all drafts are shown)

Once every selected PR has a rendered draft, walk through them once. For each PR, show the title and the model's recommended verdict, then ask:

```
PR #<num> — <title>
Recommended: <approve | request changes | comment> — <one-line reason from 3d>
[A]pprove  /  [R]equest changes  /  [C]omment  /  [S]kip  /  [Q]uit (drop remaining)
```

Default action when the user presses ENTER without typing anything: take the **recommended verdict**. Print it explicitly before posting so the user can Ctrl-C if they misread.

### Preflight — Maestro must be able to post as the App (once per run, before the first post)

Confirm the Maestro MCP `submit_pr_review` tool is available in this session (the Maestro MCP server is connected and you are signed in as a @chartmetric.com employee). If it is **not** available, do not post anything. Print:

```
⚠️  Maestro MCP isn't connected, so reviews can't be posted as the chartmetric-claude App.
    Connect the Maestro MCP server (employee Google sign-in) and re-run.
    Refusing to post as your personal GitHub account.
```

Then treat every PR as skipped and go to the output contract. **Never** fall back to `gh pr review` — posting as an individual is the exact bug this skill avoids.

### Attribution block

Because the review lands under the bot's name, this block is what tells the author and other reviewers which human drove it. Prepend it to the body before every post:

```
> _Drafted with the [`cm-pr-review`](https://github.com/chartmetric/claude-plugins/tree/main/plugins/cm-skills/skills/cm-pr-review) Claude Code skill. @<GH_LOGIN> initiated the review and worked with Claude on the analysis before posting._

---

<review body>
```

`<GH_LOGIN>` is the value resolved at the start of Step 1.

### Post via the Maestro App tool

Map keys to `submit_pr_review` calls (using the attribution-prefixed body as `body`). Split `<owner>/<repo>` into the `owner` and `repo` arguments and pass the PR `number`:

- `A` → `submit_pr_review(owner=<owner>, repo=<repo>, number=<num>, event="APPROVE", body=<prefixed_body>)`
- `R` → `submit_pr_review(owner=<owner>, repo=<repo>, number=<num>, event="REQUEST_CHANGES", body=<prefixed_body>)`
- `C` → `submit_pr_review(owner=<owner>, repo=<repo>, number=<num>, event="COMMENT", body=<prefixed_body>)`
- `S` → log nothing, move on
- `Q` → stop the loop. Remaining drafts are dropped (not saved anywhere in v1)

`APPROVE` requires a non-empty `body` (the tool rejects a silent rubber stamp); the attribution block plus the review summary always satisfies this. A single `APPROVE` review carries the full write-up **and** the approval in one submission — exactly how chartmetric-one#231's bot review landed.

Print the `html_url` the tool returns on success.

**If the tool errors, surface the message and skip that PR — never fall back to `gh pr review`:**

- `Repo '<slug>' is not in the GitHub allowlist` → the `chartmetric-claude` App isn't cleared for this repo in Maestro yet. Report it so the repo can be added to `MAESTRO_GITHUB_ALLOWED_REPOS`; skip the PR.
- `... is not permitted to submit GitHub reviews` → the caller's email isn't in `MAESTRO_GITHUB_APPROVERS`; report and skip.
- Any other GitHub error → print it verbatim and skip.

**Guardrails — never auto-escalate.** If the user just presses ENTER and the recommendation is `request changes`, still print the verdict line explicitly and pause for a beat so the user sees what's about to happen. Do not buffer multiple ENTERs into auto-confirmations of consecutive request-changes verdicts.

If the recommended verdict is `approve` and the review body contains the phrase "request changes" or "blocking" (suggesting the model contradicted itself), downgrade the recommendation to `comment` and note `_recommendation downgraded — review body conflicts with approve verdict_`.

## Output contract

End the run with a one-line summary:

```
✅ Done. Approved 1, requested changes 1, commented 0, skipped 1, dropped 0.
```

## Edge cases

- **Draft PRs**: include them. The user can decide whether to skip.
- **PRs the user authored**: `--review-requested=@me` shouldn't return these, but if it does (rare), include them anyway and let the user skip.
- **Massive diff (> 200kB)**: truncate the diff at the file boundary closest to 200kB and prepend `_diff truncated — N of M files included_`. Mention in the review header.
- **Binary files in the diff**: list them, don't try to review.
- **PR head SHA changed between Step 3a and Step 4**: don't re-check. Trust the user to notice.
- **Same PR appears twice in `gh search`**: dedupe by `<owner>/<repo>#<number>`.

## Don'ts

- Don't post anything without an explicit key press (or ENTER to take the recommended verdict) for that specific PR.
- Don't modify any file in the local repo.
- Don't run `git` commands that mutate state.
- Don't review from the diff alone if repo context fetch errored (skip instead).
- Don't paginate output — render everything and let the terminal scroll.
- Don't auto-escalate to `REQUEST_CHANGES`. Always require explicit confirmation, even when ENTER takes the default.
- **Never post a review with `gh pr review` or any personal-account path.** Every posted review goes through the Maestro `submit_pr_review` tool so it lands as the `chartmetric-claude` App. If Maestro can't post, skip — do not post as yourself.

## Examples

> `/cm-pr-review`

Discovers 5 PRs, prints the list, asks. User types `y`, sees 5 drafts back-to-back, each with a `Recommended verdict:` header. Then 5 prompts of the form `[A]pprove / [R]equest changes / [C]omment / [S]kip / [Q]uit`. ENTER takes the recommendation; explicit keys override.

> `/cm-pr-review` (no PRs awaiting)

→ `No PRs awaiting your review.` Exit.

> `/cm-pr-review` (3 PRs, user types `1,3`)

→ Reviews #1 and #3 only. Skips #2 outright (no draft generated, no API call for it).

> `/cm-pr-review https://github.com/chartmetric/chartmetric-api/pull/7732/changes`

→ Single-PR mode: no discovery, no list. One draft for chartmetric-api#7732, then the Step 4 prompt.
