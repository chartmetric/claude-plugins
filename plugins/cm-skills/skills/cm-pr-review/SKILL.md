---
name: cm-pr-review
description: Reviews every open PR that GitHub thinks the user should review. Discovers them via `gh search prs --review-requested=@me`, loads each PR's repo conventions (CLAUDE.md + .claude/skills) read-only, writes a markdown review per PR, then asks per-PR whether to post via `gh pr review --comment`. Triggers - /cm-pr-review, "review my PRs", "what do I need to review".
author: hyosik@chartmetric.com
---

# cm-pr-review — review the PRs awaiting you

Goal: turn the morning "what do I need to review" question into a single command. Discover every PR where the user is a requested reviewer (directly or via team delegation), generate one review draft per PR using each repo's own conventions, then let the user post or skip each draft.

The skill is one-shot. No background scheduling, no Slack, no posting until the user confirms per PR.

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

Two paths in priority order:

1. **Local clone** at `~/code/chartmetric/<repo_name>` (where `<repo_name>` is the repo's short name, e.g. `chartmetric-api`):
   - If the directory exists, read these files as-is from the working tree:
     - `<path>/CLAUDE.md`
     - every `*.md` under `<path>/.claude/skills/` (recursive)
   - Note that the local copy may not match the PR's base commit. State this in the review header: `_context loaded from local copy of <repo>_`.

2. **GitHub API fallback** (when the local clone is missing):
   - Fetch `CLAUDE.md`:
     ```bash
     gh api repos/<owner>/<repo>/contents/CLAUDE.md --jq '.content' | base64 -d
     ```
   - List the skills directory:
     ```bash
     gh api repos/<owner>/<repo>/contents/.claude/skills 2>/dev/null
     ```
     For each entry of `type: "file"` ending in `.md`, fetch via the `download_url` (no base64 step). For `type: "dir"`, recurse one level.
   - Header in the review: `_context fetched from origin via gh api_`.

If both paths fail (e.g. files don't exist in the repo), warn `_no repo conventions found — falling back to default review prompt_` and continue. This is the only case where you may review without repo context, and only because there is no context to load.

If a 404 from the API happens for `CLAUDE.md` but `.claude/skills` exists, use whatever you find. If the API itself errors (auth, rate limit), abort the PR with `_skipped: could not load repo context_` and continue to the next PR — do **not** fall through to diff-only review.

### 3c. Compose the review

Build the system prompt in this order (later sections override earlier ones on conflict):

1. Default reviewer baseline (below).
2. Repo `CLAUDE.md`.
3. Repo `.claude/skills/*.md` (sorted by file path for determinism).
4. _(future)_ User personal style at `~/.claude/cm-pr-review-style.md`. **Not loaded in v1.** Check the path exists and, if so, mention `_personal style file detected but not yet supported in this skill version_` once at the start of the run.

**Default reviewer baseline:**

> You are an experienced engineer reviewing a teammate's pull request. Be direct, terse, specific. Lead with the most load-bearing concern. Reference file paths and line ranges where relevant. Don't restate what the diff already shows. If the PR looks good, say so in one line and stop.

User message contains: PR number, title, author, URL, full diff, and an instruction to write the review as markdown.

### 3d. Decide a recommended verdict

After composing the review, judge whether the PR is in shape to approve, needs changes, or just deserves a comment. Use this rubric:

- **Approve** — no blocking issues; nits or optional suggestions are fine. The PR could merge as-is and the reviewer would be willing to approve in person.
- **Request changes** — at least one blocking issue: bug, regression risk, missing test for a behavior change, violation of repo conventions, breaking API change without justification. The PR must change before merging.
- **Comment** — neither. Open question, want author's input, want to flag something without blocking. Default when uncertain — never auto-escalate to request-changes when you could simply ask.

Record the verdict as `recommended: approve | request_changes | comment`. Keep it in the in-memory state for Step 4 — **do not** add a verdict line to the review body that ships to GitHub. The user's explicit key press in Step 4 conveys the actual verdict via the `--approve` / `--request-changes` / `--comment` flag; including a "Recommended: X" header in the published comment would muddy that.

The recommendation surfaces only:

1. In the terminal render (Step 3e), as a separator-level header so the user sees it before the body.
2. In the Step 4 prompt, where ENTER takes the recommendation.

### 3e. Render the draft

Print the review to the terminal with a clear separator:

```
═══════════════════════════════════════════════════════
PR #<num> — <title>  (<repo>)
<URL>
_context loaded from <local|api>_
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

Before any `gh pr review` call, prepend an attribution block to the body so the PR author and other reviewers can tell the comment was AI-assisted and that the engineer drove it:

```
> _Drafted with the [`cm-pr-review`](https://github.com/chartmetric/claude-plugins/tree/main/plugins/cm-skills/skills/cm-pr-review) Claude Code skill. @<GH_LOGIN> initiated the review and worked with Claude on the analysis before posting._

---

<review body>
```

`<GH_LOGIN>` is the value resolved at the start of Step 1.

Map keys to `gh pr review` calls (using the attribution-prefixed body):

- `A` → `gh pr review <num> --repo <owner>/<repo> --approve --body "<prefixed_body>"`
- `R` → `gh pr review <num> --repo <owner>/<repo> --request-changes --body "<prefixed_body>"`
- `C` → `gh pr review <num> --repo <owner>/<repo> --comment --body "<prefixed_body>"`
- `S` → log nothing, move on
- `Q` → stop the loop. Remaining drafts are dropped (not saved anywhere in v1)

Print the resulting review URL on success.

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
- Don't auto-escalate to `--request-changes`. Always require explicit confirmation, even when ENTER takes the default.

## Examples

> `/cm-pr-review`

Discovers 5 PRs, prints the list, asks. User types `y`, sees 5 drafts back-to-back, each with a `Recommended verdict:` header. Then 5 prompts of the form `[A]pprove / [R]equest changes / [C]omment / [S]kip / [Q]uit`. ENTER takes the recommendation; explicit keys override.

> `/cm-pr-review` (no PRs awaiting)

→ `No PRs awaiting your review.` Exit.

> `/cm-pr-review` (3 PRs, user types `1,3`)

→ Reviews #1 and #3 only. Skips #2 outright (no draft generated, no API call for it).
