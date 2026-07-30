# gh stack — build & reconstruct a stack

Flags and behavior for the commands that create a stack, publish it to GitHub, and tear it down to rebuild. Non-interactive requirements and exit codes are in `SKILL.md`; this file assumes them.

## `gh stack init` — create a stack

```
gh stack init [-b|--base <branch>] <branches...>
```

Creates a stack and checks out the last branch listed. Existing branches are adopted; missing ones are created from the trunk. Enables `git rerere` — if it isn't already set (see Prerequisites in `SKILL.md`), the first run in a repo may prompt. Requires at least one positional branch.

| Flag | Description |
|------|-------------|
| `-b, --base <branch>` | Trunk branch (default: repo default branch) |

```bash
gh stack init auth                        # one new branch
gh stack init branch-a branch-b branch-c  # several
gh stack init --base develop branch-a     # custom trunk
```

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
