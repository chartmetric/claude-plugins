---
name: multi-repo-pr
description: Plan and ship one piece of work that spans multiple chartmetric repos in a single session — create a branch, commit, push, and PR in EACH affected repo, then report all PR links together. Use when a request touches more than one repo (e.g. backend + frontend), when the user says "make PRs in both repos", or when working from a parent folder that contains several repos.
---

# Multi-Repo Work → One PR per Repo

Chartmetric work often spans repos (an API change + the frontend that consumes it). One session can handle all of it: the session just needs to be opened on a folder that contains the repos (e.g. `~/code/chartmetric`), or have them added as additional working directories.

## Repo mapping (task type → repo)

- main app frontend = chartmetric-web-app
- main app backend / API = chartmetric-api
- refresh server = chartmetric_data_script
- data sync issues = chartmetric_data_script and/or data_infra
- flow UI = chartmetric-one
- background worker = melodi-worker

## Workflow

### 1. Plan the split BEFORE writing code

Map each part of the request to its repo using the mapping above. Tell the user the plan first:

```
This touches 2 repos:
- chartmetric-api: add the endpoint
- chartmetric-web-app: consume it
```

If a part doesn't clearly map to a repo, ask — don't guess.

### 2. Confirm repo state per affected repo

For each repo, before changing anything:

```bash
cd <repo> && git status --short && git branch --show-current
```

- If there are uncommitted changes that aren't yours, stop and ask.
- Note each repo's default branch (`gh repo view --json defaultBranchRef -q .defaultBranchRef.name`) — don't assume it's the same across repos.

### 3. One branch per repo, same name across repos

Use a shared branch name so the PRs are recognizably one piece of work:
`feat/<short-description>` in every affected repo.

```bash
cd <repo>
git checkout -b feat/<short-description> origin/<default-branch>
```

### 4. Make the changes, repo by repo

Do the dependency-order repo first (usually backend before frontend). Run each repo's own checks (see its CLAUDE.md for lint/test commands) before committing.

### 5. Commit, push, PR — in each repo

```bash
cd <repo>
git add <files> && git commit -m "<type>: <what changed>"
git push -u origin feat/<short-description>
gh pr create --title "<title>" --body "<body>"
```

PR body must cross-link the sibling PRs: after creating all PRs, edit each body to add a `### Related PRs` section listing the other repos' PR URLs. (`gh pr edit` is broken on chartmetric repos — use `gh api -X PATCH /repos/<owner>/<repo>/pulls/<num>` with a JSON body instead.)

### 6. Report

Give the user every PR URL on its own line, grouped by repo, plus what order to merge them in (dependencies first) and whether any repo still needs work.

## Rules

- Never mix changes for two repos into one commit or one PR — each repo gets its own.
- Never push to a repo's default branch directly.
- If only ONE repo turns out to be affected, say so and fall back to the normal single-repo flow.
- If a repo isn't cloned locally, tell the user the exact `git clone` command rather than silently skipping it.
