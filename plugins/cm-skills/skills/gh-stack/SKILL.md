---
name: gh-stack
description: Manage stacked branches and pull requests with the `gh stack` GitHub CLI extension. Use when the user wants to build, navigate, rebase, sync, or merge a chain of dependent PRs — stacked diffs, incremental review layers.
---
# gh-stack

`gh stack` is a [GitHub CLI](https://cli.github.com/) extension for stacked branches and pull requests. A **stack** is an ordered chain of branches rooted on a **trunk** (usually the repo's default branch), where each branch builds on the one below it. Each branch maps to one PR whose base is the branch below, so a reviewer sees only that layer's diff.

```
main (trunk)
 └── auth-layer     → PR #1 (base: main)           bottom — closest to trunk
  └── api-endpoints → PR #2 (base: auth-layer)
   └── frontend     → PR #3 (base: api-endpoints)  top — furthest from trunk
```

The **bottom** is closest to trunk, the **top** furthest. Navigation follows this model: `up` / `top` move away from trunk, `down` / `bottom` move toward it.

## Non-interactive rules

Every `gh stack` command runs non-interactively — a command that would prompt hangs indefinitely. Supply the flags and arguments that avoid prompts, TUIs, and menus:

| Command | Required for non-interactive use |
|---------|----------------------------------|
| `init`, `add`, `checkout` | a positional branch / PR / stack argument (bare command prompts) |
| `submit` | `--auto` (else prompts for each PR title) |
| `view` | `--json` (else launches a TUI) |
| `merge` | `--yes` (`gh pr merge` does not work on stacks) |

Two environment constraints round this out:

- **Multiple remotes.** With more than one remote, set `git config remote.pushDefault origin`, or pass `--remote <name>` to the commands that accept it (`push`, `submit`, `sync`, `rebase`, `link`). `checkout`, `modify`, and `trunk` have no `--remote` flag and rely on `remote.pushDefault`; with multiple remotes and no default they exit with an error.
- **`checkout` onto a conflicting local stack.** If a different local stack already tracks those branches, `checkout <pr-number>` triggers an unbypassable conflict prompt. Run `gh stack unstack --local` first (this keeps the GitHub stack intact), then retry.

Branch names are used verbatim — never prefixed or transformed. `gh stack add refactor/foo` creates a branch named `refactor/foo`; slashes are kept as-is.

## Confirm before submitting or merging

Two commands act outward and deserve a check-in with the user first:

- `submit` opens or updates PRs — drafts by default, ready-for-review with `--open`. Confirm the branch list and whether they should be drafts before running it.
- `merge` lands the whole stack bottom-to-top and can trigger deploys. It's all-or-nothing and hard to undo, so confirm which PRs will land and the merge method first.

Everything else — `init`, `add`, `push`, navigation, `view`, `sync`, `rebase` — is local or moves only your own stack branches, so run it without pausing.

## Prerequisites

`gh` v2.0+, installed and authenticated. Then:

```bash
gh extension install github/gh-stack
git config rerere.enabled true        # remember conflict resolutions (skips a prompt on init)
git config remote.pushDefault origin  # only if multiple remotes exist
```

## Structuring a stack

Each branch is one discrete, logical unit of work a reviewer can read on its own, and the stack as a whole tells one cohesive story.

- **Order by dependency.** Foundational changes (models, shared APIs, utilities) go in lower branches; dependents (consumers, UI, tests) go higher. Plan the layers before writing code — if code in one layer depends on another, that dependency must live in the same branch or a lower one.
- **One stack, one story.** Keep a single feature or effort in one stack. Unrelated work — a different feature, an unrelated bug fix, an independent refactor — starts its own stack (`gh stack init`) or switches to another (`gh stack checkout`). A trivial incidental fix can ride along; once it grows into its own thing, give it its own stack.
- **Stage deliberately.** Use plain `git add` / `git commit` to control which changes land on which branch — stage a subset, commit, then `gh stack add <next>` and stage the rest there. Multiple commits per branch are fine as long as they share one concern. The `-Am "msg" <branch>` shortcut folds staging, commit, and branch creation into one step; reach for it on single-commit layers, not as the default.
- **Change lower layers in place.** Working high and realize you need a change below? Don't hack it in at the current layer — it lands in the wrong PR. Navigate down, commit it where it belongs, `gh stack rebase --upstack`, then navigate back. See [Making mid-stack changes](#making-mid-stack-changes).

## Quick reference

Full flags and behavior for each command live in topic files under `references/`: `build.md` (init, add, push, submit, link, unstack), `navigate.md` (view, movement, checkout), `sync.md` (sync, rebase), and `merge.md` (merge). For anything those omit, GitHub's [CLI reference](https://github.github.com/gh-stack/reference/cli/) is the authoritative per-command doc, and its [FAQ](https://github.github.com/gh-stack/faq/) covers policy behavior the CLI can't — merge queues, branch protection, CI triggers, and cross-fork limits.

| Task | Command |
|------|---------|
| Create a stack | `gh stack init auth` |
| Create a stack of multiple branches | `gh stack init auth api frontend` |
| Adopt existing branches | `gh stack init existing-a existing-b` |
| Set custom trunk | `gh stack init --base develop branch-a` |
| Add a branch to the stack | `gh stack add api-routes` |
| Add branch + stage all + commit | `gh stack add -Am "message" api-routes` |
| Push branches to remote | `gh stack push` |
| Push branches + create draft PRs | `gh stack submit --auto` |
| Create PRs as ready for review | `gh stack submit --auto --open` |
| Sync (fetch, rebase, push) | `gh stack sync` |
| Sync and prune merged branches | `gh stack sync --prune` |
| Rebase entire stack | `gh stack rebase` |
| Rebase upstack only | `gh stack rebase --upstack` |
| Continue / abort a rebase | `gh stack rebase --continue` / `--abort` |
| View stack details (JSON) | `gh stack view --json` |
| Move up / down in the stack | `gh stack up [n]` / `gh stack down [n]` |
| Jump to top / bottom | `gh stack top` / `gh stack bottom` |
| Check out by stack, PR, or branch | `gh stack checkout 7` |
| Tear down a stack to restructure | `gh stack unstack` |
| Merge the whole stack | `gh stack merge --yes` |
| Merge up to a specific PR | `gh stack merge 42 --yes` |
| Merge with a specific method | `gh stack merge --yes --squash` |

## Workflows

### End-to-end: create a stack from scratch

```bash
# 1. Init the stack with its first branch (creates + checks out `auth`)
gh stack init auth

# 2. Write the layer, then stage + commit with plain git (multiple commits per branch are fine)
git add auth.go && git commit -m "Add auth middleware"

# 3. Start the next concern — creates + checks out `api-routes`
gh stack add api-routes
git add api.go && git commit -m "Add API routes"

gh stack add frontend
git add frontend.go && git commit -m "Add frontend dashboard"
# stack: auth → api-routes → frontend

# 4. Push all branches and open PRs (drafts by default; add --open for ready-for-review)
gh stack submit --auto

# 5. Verify
gh stack view --json
```

### Making mid-stack changes

You're on a higher branch but the change belongs lower (e.g. building frontend, but need an API endpoint). Commit it where it belongs, then replay everything above.

```bash
# You're on `frontend`; the change belongs on `api-routes`
gh stack down                # or: gh stack checkout api-routes  (or a PR number)
git add users_api.go && git commit -m "Add get-user endpoint"
gh stack rebase --upstack    # replay every branch above onto the change
gh stack top                 # back to where you were
gh stack push                # (when you're done making changes)
```

Putting the change on the wrong branch mixes unrelated diffs into that layer's PR — always commit where the change logically belongs.

### Sync after merges

```bash
gh stack sync            # fetch, rebase onto moved parents, push, sync PR + stack state
gh stack sync --prune    # also delete local branches for merged PRs
```

`sync` handles squash-merged and newly-added-on-github.com PRs on its own (mechanics in `references/sync.md`). The one case that needs you: if the local and remote stacks have **diverged**, sync can't reconcile them non-interactively — it aborts cleanly (`ℹ Sync aborted`, nothing changed), and you resolve by unstacking and recreating the stack.

### Handle rebase conflicts

```bash
gh stack rebase
# on exit code 3:
#   parse stderr for conflicted paths; edit to resolve <<<<<<< ======= >>>>>>> markers
git add path/to/resolved-file
gh stack rebase --continue   # repeat for any further conflicts
gh stack rebase --abort      # or bail out — restores all branches to pre-rebase state
```

### Read stack state from `--json`

```bash
out=$(gh stack view --json)
echo "$out" | jq '[.branches[] | select(.needsRebase)] | length'       # how many need rebase
echo "$out" | jq -r '.branches[] | select(.pr.state=="OPEN") | .pr.url' # open PR URLs
echo "$out" | jq -r '.branches[] | select(.isMerged) | .name'          # merged branches
echo "$out" | jq -r '.currentBranch'                                    # current branch
echo "$out" | jq '[.branches[].isMerged] | all'                         # is the whole stack merged?
```

Full schema in `references/navigate.md`.

### Restructure a stack (remove / reorder / rename)

```bash
gh stack unstack                                     # drop tracking + GitHub grouping (PRs NOT deleted)
git branch -m old-branch new-branch                  # make structural changes
gh stack init --base main branch-a branch-b branch-c # rebuild in the new order
```

Teardown is clean only before any of the stack's PRs have landed: `unstack` leaves merged and queued PRs attached, so reorder or rename while the whole stack is still open, not after merges begin.

## Output conventions

- Status messages go to **stderr**, prefixed `✓` (success), `✗` (error), `⚠` (warning), `ℹ` (info).
- Data output (e.g. `view --json`) goes to **stdout**. Pipe with `2>/dev/null` to keep only data.

## Exit codes and error recovery

| Code | Meaning | Agent action |
|------|---------|--------------|
| 0 | Success | Proceed |
| 1 | Generic error | Read stderr; may indicate a commit/push failure |
| 2 | Not in a stack | Run `gh stack init` first |
| 3 | Rebase conflict | Resolve conflicts, then `gh stack rebase --continue` |
| 4 | GitHub API failure | Check `gh auth status`, retry |
| 5 | Invalid arguments | Fix the invocation (flags and arguments) |
| 6 | Disambiguation required | A branch belongs to multiple stacks — `gh stack checkout <non-shared-branch>` first |
| 7 | Rebase already in progress | `gh stack rebase --continue` or `--abort` |
| 8 | Stack is locked | Another `gh stack` process holds the lock; wait and retry (times out after 5s) |
| 9 | Stacked PRs unavailable | The repo doesn't have stacked PRs enabled — tell the user to enable them first |
| 10 | Modify recovery required | An interrupted `gh stack modify` session; run `gh stack modify --abort` to restore |

## Known limitations

1. **Linear only.** No branching stacks — each branch has one parent and at most one child. Parallel workstreams use separate stacks.
2. **No custom PR title/body at submit.** Titles and bodies are auto-generated from commit messages; edit afterward with `gh pr edit`.
3. **Remote checkout needs a stack or PR number.** `checkout <branch>` resolves locally-tracked stacks only; pull a stack from GitHub with `gh stack checkout <stack-number|pr-number>`.
4. **`modify` is interactive-only.** `gh stack modify` (drop, fold, insert, reorder, or rename branches in place) needs an interactive terminal, so it has no place in a non-interactive workflow — restructure with `unstack` + `init` instead (see the Restructure a stack workflow above). Its one non-interactive touchpoint is recovery: an interrupted session exits 10, cleared with `gh stack modify --abort`.
