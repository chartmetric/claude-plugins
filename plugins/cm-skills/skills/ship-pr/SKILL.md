---
name: ship-pr
description: Finalize this session's finished work into fully-dressed PRs - create/collect the PRs, write a proper description, set the assignee to the PR creator, link the related Slack thread (or post a session report to #claude-kanban and use that), link the Asana task (or create one via slack-to-asana), suggest reviewers, attach PR Preview labels, then poll until the preview pool is deployed and report the preview URLs back into the session. Use when the coding work in a session is done and the user says "ship this", "ship the PRs", "finalize the PRs", "PR 마무리해줘", "PR 올려줘 (with previews)".
---

# ship-pr — finalize session PRs end-to-end

Turns "the code is done" into "the PR is fully dressed": description, assignee, Slack + Asana links, reviewer suggestion, preview labels, and a deployed-preview report — without the user having to remember each step.

## Required tools

- `gh` CLI authenticated (always available in local sessions).
- Slack + Asana MCP connectors for steps 4–5. If missing, tell the user to run `/mcp` and authenticate, then continue from where you stopped — the GitHub-only steps (1–3, 6–8) never block on Slack/Asana.

## Known org quirks (do not rediscover these)

- **`gh pr edit` is broken on chartmetric repos** (Projects-classic GraphQL deprecation). Always use the REST API:
  - body: `jq -Rs '{body: .}' < body.md | gh api -X PATCH /repos/<repo>/pulls/<num> --input -`
  - assignee: `gh api -X POST repos/<repo>/issues/<num>/assignees -f "assignees[]=<login>"`
  - labels: `gh api -X POST repos/<repo>/issues/<num>/labels -f "labels[]=PR Preview"`
- **Preview deploys are label-triggered.** Adding the `PR Preview` label kicks off a preview-pool deployment; completion is signaled by a `github-actions[bot]` PR comment starting with `## Preview Pool Deployed` that contains the pool instance name and the preview URLs.
- **`ensure-asana-link` check**: repos nudge (bot comment) when the PR body has no `Asana: [task name](https://app.asana.com/...)` line. Step 5 satisfies this.

## Step-by-step

### 1. Inventory the session's work → PRs exist for every repo

Figure out which repos this session touched and whether PRs already exist:

```bash
cd <repo> && git status --short && git branch --show-current && gh pr view --json url,number,title 2>/dev/null
```

- **PR already open** → collect its URL/number; don't recreate.
- **Branch pushed, no PR** → create the PR (step 2 covers the body).
- **Uncommitted work** → commit and push first (branch names `feat/` or `fix/` + short description). If there are uncommitted changes that don't look like this session's work, stop and ask.
- **Multiple repos** → follow the `multi-repo-pr` skill's conventions: one branch (same name) + one PR per repo, cross-linked `### Related PRs` sections. Never mix repos in one PR.

### 2. Write a real PR description

If the repo has `.github/PULL_REQUEST_TEMPLATE.md`, fill that template. Otherwise use:

```markdown
### Summary
<what & why, 2–4 sentences — written for a reviewer with zero session context>

### Changes
- <file/area>: <what changed>

### Testing
- <what was run/verified, with results>

### Notes
<placeholder — Asana / Slack lines land here in steps 4–5>
```

Create with `gh pr create --title "<type>: <what changed>" --body-file <file>`, or PATCH the body of an existing PR via the REST API. Preserve any existing body content (especially auto-appended Asana-app footers) — inject, never overwrite blindly.

### 3. Assignee = PR creator, always

```bash
LOGIN=$(gh api user --jq .login)
gh api -X POST "repos/<repo>/issues/<num>/assignees" -f "assignees[]=$LOGIN"
```

If the PR was authored by a bot on the user's behalf, still assign the human user.

### 4. Slack thread link

Priority order:

1. A Slack thread URL the user gave or that appeared in this session's context → use it.
2. Otherwise, run the `session-report` skill targeting **#claude-kanban**: draft the 🔍 Problem / 🔧 Fix / ✅ Current state / 🔗 Links summary (include every PR URL from step 1), **show the draft and confirm with the user**, then post with `slack_send_message`. Use the returned `message_link` as the Slack thread URL.

### 5. Asana task link

Priority order:

1. An Asana task already linked in the session/thread → use it.
2. Otherwise, run the `slack-to-asana` skill with the Slack thread URL from step 4. It creates the task on Unified CM Tasks, fills custom fields, and replies in the thread. Confirm assignee/engineer with the user if not obvious (default both to the current user for self-driven session work).

Then inject into **every** PR body's `### Notes` section (REST PATCH, preserve everything else):

```
Asana: [<exact task name>](<task permalink_url>)
Slack: <slack thread URL>
```

Verify with `gh pr view <num> --repo <repo> --json body` that both lines are present.

### 6. Suggest reviewers (suggest — don't auto-request)

For each PR, rank recent committers to the touched files:

```bash
gh pr view <num> --repo <repo> --json files --jq '.files[].path' | while read -r f; do
  gh api "repos/<repo>/commits?path=$f&per_page=20" --jq '.[].author.login // empty'
done | sort | uniq -c | sort -rn | head
```

- Exclude the PR author and bots (`github-actions`, `devin-ai-integration`, anything `[bot]`).
- Check `.github/CODEOWNERS` if it exists and surface matching owners first.
- Report the top 1–2 names per PR **with a one-line reason** ("owns most recent commits to `src/foo/`"). Do NOT call the review-request API — the user picks.

### 7. Attach PR Preview labels

Check which preview labels the repo actually defines, then attach:

```bash
gh api "repos/<repo>/labels" --paginate --jq '.[].name' | grep -i preview
gh api -X POST "repos/<repo>/issues/<num>/labels" -f "labels[]=PR Preview" -f "labels[]=PR Preview: Deploy Faster"
```

- Always add `PR Preview`.
- Add `PR Preview: Deploy Faster` only if the repo defines it.
- Skip labels entirely (and say so) for repos with no `PR Preview` label — not every repo has previews.
- Never add merge-triggering labels (e.g. `Merge Pull Request`).

### 8. Poll until the preview pool is deployed, then report

Launch ONE background Bash poll per previewed PR (`run_in_background: true`), checking every 60s for up to 30 minutes:

```bash
for i in $(seq 1 30); do
  BODY=$(gh api "repos/<repo>/issues/<num>/comments" \
    --jq '[.[] | select(.user.login=="github-actions[bot]") | select(.body | contains("Preview Pool Deployed")) | .body] | last // empty')
  if [ -n "$BODY" ]; then echo "DEPLOYED"; echo "$BODY"; exit 0; fi
  sleep 60
done
echo "TIMEOUT"
```

While polls run, give the user the interim report (step 9) — don't sit silent.

When a poll returns:
- **DEPLOYED** → relay the pool instance name and every preview URL from the comment (Web / API / etc.), verbatim, each on its own line.
- **TIMEOUT** → check the repo's Actions runs for the preview workflow on this branch (`gh run list --repo <repo> --branch <branch> --limit 5`); report whether it's still running, queued, or failed, with the run URL. Don't restart anything automatically.

### 9. Final report format

```
PRs:
<full PR URL per line, with repo name>

Assignee: <login> · Reviewer suggestion: <name> (<reason>)
Slack: <thread URL>
Asana: <task permalink>
Preview: <deploying — will report URLs when ready | URLs once deployed>
```

Full URLs on their own lines — no markdown-shortened links for PR/preview URLs.

## Edge cases

- **PR already fully dressed** (has Asana + Slack lines, labels, assignee): verify each item instead of re-doing it; only fill gaps. This skill is idempotent — safe to run twice.
- **Draft PR**: mark ready for review first (`gh api -X PATCH /repos/<repo>/pulls/<num>` won't do this — use `gh pr ready <num> --repo <repo>`), unless the user wants it kept draft; ask if unclear.
- **Master PR that needs a staging companion**: mention that `cm-conflict` exists; don't run it unprompted.
- **User declines the Slack post**: skip Asana auto-creation too (it needs the thread), leave a `TODO` note in `### Notes`, and say what's missing.
