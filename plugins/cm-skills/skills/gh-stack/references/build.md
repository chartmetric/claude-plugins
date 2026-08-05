# gh stack — build & reconstruct a stack

Flags and behavior for the commands that create a stack, publish it to GitHub, and tear it down to rebuild. Non-interactive requirements and exit codes are in `SKILL.md`; this file assumes them.

## How a name resolves

The name you pass is resolved differently per command, and that difference is the footgun below:

- `init` / `add` — resolved against your **local** branches only. A local branch of that name is adopted; if none exists, a new one is created from your current HEAD (often trunk). The remote is never consulted, so a name whose only home is a remote branch (with an open PR) becomes a brand-new local branch.
- `link` — each argument is tried as a **PR number** first, then as a branch name. PR-number args are pure API (no push); branch-name args are pushed (non-force, atomic).

## `gh stack init` — create a stack

```
gh stack init [-b|--base <branch>] <branches...>
```

Creates a stack and checks out the last branch listed. Existing local branches are adopted; missing ones are created from the trunk. Enables `git rerere` — if it isn't already set (see Prerequisites in `SKILL.md`), the first run in a repo may prompt. Requires at least one positional branch.

| Flag | Description |
|------|-------------|
| `-b, --base <branch>` | Trunk branch (default: repo default branch) |

```bash
gh stack init auth                        # one new branch
gh stack init branch-a branch-b branch-c  # several
gh stack init --base develop branch-a     # custom trunk
```

**Adopting a remote-only branch clobbers it.** Because `init`/`add` resolve a name against local branches only (see [How a name resolves](#how-a-name-resolves)), a name whose only home is a remote branch with an open PR is treated as new and built from your current checkout (often local trunk), not `origin/<name>`. The next `submit`/`push`/`sync` then force-pushes that over the real remote branch, collapsing its PR diff (GitHub reports `No commits between <trunk> and <name>`) and possibly auto-closing the PR.

```bash
# State: PRs #42 (auth) and #57 (api) are open; you have no local auth/api
# branches; frontend is new local work.

# TRAP: init binds auth and api to NEW local branches (the remote is never
# consulted); submit force-pushes over #42 and #57 and collapses both PRs.
gh stack init auth api frontend
gh stack submit --auto

# SAFE: 42 and 57 resolve to the existing PRs (API-only, no push); only
# frontend is pushed.
gh stack link --base main 42 57 frontend
```

For an existing remote *branch* you must adopt through `init`/`add`, fetch and verify its local tracking branch first:

```bash
git fetch origin
git branch <name> origin/<name>                    # or: git switch <name>
git rev-parse <name>   # must equal  git rev-parse origin/<name>
```

then `gh stack init … <name>` / `gh stack add <name>`. Recovery if already clobbered: the old content is usually still reachable as the parent of the layer stacked on top of it — `git branch -f <name> <good-sha>`, `git push --force-with-lease origin <name>`, `gh pr reopen <pr-number>`.

## `gh stack add` — add a branch on top

```
gh stack add [-m <msg> [-A|-u]] <branch>
```

Creates a new branch on top of the stack and checks it out. Must run from the topmost branch (or the trunk when the stack is empty), else exits 5 (`can only add branches on top of the stack`) — `gh stack top` first. Uncommitted changes carry over to the new branch (standard git); commit or stash first for a clean start.

| Flag | Description |
|------|-------------|
| `-m, --message <string>` | Commit staged changes with this message |
| `-A, --all` | Stage all changes incl. untracked (needs `-m`) |
| `-u, --update` | Stage tracked files only (needs `-m`) |

`-A` and `-u` are mutually exclusive. With `-m` on a branch that has no commits yet (e.g. right after `init`), the commit lands on the current branch instead of creating a new one. With `-m` and no branch name, the name is auto-generated from the message (`MM-DD-slug`).

Naming a branch that exists only on the remote adopts it through the same broken path as `init` — see the clobber warning above before doing so.

```bash
gh stack add api-routes                       # then plain git add / commit
gh stack add -Am "Add API routes" api-routes  # stage-all + commit + branch in one
```

## `gh stack push` — push branches (no PRs)

```
gh stack push [--remote <name>]
```

Pushes all active (non-merged, non-queued) branches in one non-atomic multi-ref push, each guarded by `--force-with-lease`. If one ref is rejected, others may still update — fix the rejected branch and rerun. Does not create or update PRs (use `submit`). Reports `Pushed N branches`.

## `gh stack submit` — push and create/update PRs

```
gh stack submit --auto [--open] [--remote <name>]
```

Pushes each active branch (`--force-with-lease`, sequential, non-atomic) and creates a PR for any branch lacking one, chaining bases (each PR's base is its first non-merged ancestor). Links the PRs into a Stack on GitHub, then syncs metadata for existing PRs. Non-atomic: if a later push is rejected, earlier pushes and PR updates remain — fix and rerun.

| Flag | Description |
|------|-------------|
| `--auto` | Auto-title new PRs (required — see SKILL non-interactive rules) |
| `--open` | Mark new + existing PRs ready for review (default: draft) |
| `--remote <name>` | Target remote (multiple-remote setups) |

Auto-titles: a single-commit branch uses the commit subject as the title and its body as the PR body; a multi-commit branch uses the humanized branch name. If every PR in the stack is already merged, `submit` forks the unmerged branches into a new stack rooted at trunk. If stacks aren't enabled on the repo, exits 9.

## `gh stack link` — link PRs into a stack (no local tracking)

```
gh stack link [--base <branch>] [--open] [--remote <name>] <stack-number | branch-or-pr> <branch-or-pr> [...]
```

Creates or updates a GitHub Stack purely through the API — no local tracking state. Use it when branches are managed by another tool (jj, Sapling, git-town). Arguments are given bottom-to-top; each is a PR number (tried first) or a branch name. Branch args are pushed (non-force, atomic); branches without an open PR get one with the correct base chaining, and existing PRs with a wrong base are corrected. When the first argument is an existing stack number, the rest are appended to its top (args already in the stack are skipped; args in a different stack are rejected). Linking is additive — existing PRs are never removed.

Passing PR **numbers** (not branch names) keeps the whole operation API-side — no push happens — which makes `link` the safe way to group PRs that already exist: it can't clobber a branch the way `init` + `submit` can (see the clobber warning under `gh stack init`). It's also how to re-add a PR that dropped out of a stack while it was briefly closed.

**Mixed stack — some layers already have PRs, some are new.** Pass them in one `link` call, bottom-to-top: existing layers by PR number, new local branches by name. `link` touches the numbered PRs API-only and pushes only the new branches (non-force, atomic), opening their PRs with the correct bases. Don't reach for `init` + `submit` to fill in the missing PRs — that force-pushes every layer, re-exposing any branch you adopted from the remote to the clobber above. If the existing PRs are already grouped as a stack, give its number first and append the new branches: `gh stack link <stack-number> <new-branch> …`.

| Flag | Description |
|------|-------------|
| `--base <branch>` | Base for the bottom of the stack (default: repo default) |
| `--open` | Mark PRs ready for review |
| `--remote <name>` | Target remote |

```bash
gh stack link branch-a branch-b branch-c   # push, create PRs, create stack
gh stack link 10 20 30                      # link existing PRs by number
gh stack link 7 48 feature-auth             # append PR #48 + a branch to stack #7
```

## `gh stack unstack` — tear down a stack

```
gh stack unstack [<stack-number>] [--local]
```

Removes the stack grouping (on GitHub and/or locally); never deletes the underlying PRs or branches. Open, draft, and closed PRs are removed from the stack, but merged and queued PRs stay attached — a stack fully dissolves only when none of its PRs have merged or are queued. Pairs with `gh stack init` to rebuild in a new order. With no argument it targets the active stack (the one holding the current branch). A stack number unstacks that stack through the GitHub API from anywhere in the repo, tracked locally or not; if it is also tracked locally, local tracking is removed too.

| Flag | Description |
|------|-------------|
| `--local` | Remove local tracking only; never contacts GitHub |

`--local` with a number not tracked locally is an error. An unknown stack number returns "not found on GitHub."
