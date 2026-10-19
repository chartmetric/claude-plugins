# gh stack — inspect & move around a stack

Flags and behavior for reading stack state and moving between branches. Non-interactive requirements and exit codes are in `SKILL.md`; this file assumes them.

## `gh stack view` — show the stack (JSON)

```
gh stack view --json
gh stack view --short   # compact one-line-per-branch text, no TUI
```

`--json` prints stack data to stdout; `--short` prints a compact list; with neither the command launches a TUI.

```json
{
  "trunk": "main",
  "currentBranch": "api-routes",
  "branches": [
    {
      "name": "auth",
      "head": "abc1234...",
      "base": "def5678...",
      "isCurrent": false,
      "isMerged": true,
      "isQueued": false,
      "needsRebase": false,
      "pr": { "number": 42, "url": "https://github.com/owner/repo/pull/42", "state": "MERGED" }
    },
    {
      "name": "api-routes",
      "head": "789abcd...",
      "base": "abc1234...",
      "isCurrent": true,
      "isMerged": false,
      "isQueued": false,
      "needsRebase": false,
      "pr": { "number": 43, "url": "https://github.com/owner/repo/pull/43", "state": "OPEN" }
    }
  ]
}
```

Fields per branch:
- `name` — branch name
- `head` — current HEAD SHA
- `base` — parent branch's HEAD SHA at last sync
- `isCurrent` — whether this is the checked-out branch
- `isMerged` — whether the PR has been merged
- `isQueued` — whether the PR is in a merge queue
- `needsRebase` — whether the base is not an ancestor (non-linear history)
- `pr` — PR metadata (omitted if no PR exists); `state` is `"OPEN"`, `"MERGED"`, or `"QUEUED"`

## Navigation — `up` / `down` / `top` / `bottom` / `trunk`

Fully non-interactive. Clamps to stack bounds; skips merged branches when moving from active ones.

```bash
gh stack up [n]     # away from trunk (default 1)
gh stack down [n]   # toward trunk
gh stack top        # furthest from trunk
gh stack bottom     # first non-merged branch above trunk
gh stack trunk      # the trunk branch (e.g. main)
```

If the target branch is checked out in another worktree, add `--print-path`: it prints that worktree's path instead of switching, and you work there.

## `gh stack checkout` — check out a stack

```
gh stack checkout <stack-number | pr-number | pr-url | branch> [--print-path]
```

Resolves a bare number as a stack number first, then a locally tracked PR number, then a PR number looked up on GitHub, then a branch name. A stack/PR number or URL fetches from GitHub and sets up the stack locally. A branch name checks locally tracked stacks first, then GitHub stacks, and pulls down the match. `--print-path` prints the worktree path that holds the target instead of switching (requires an explicit target). If a local stack already tracks the target branches with a different composition, checkout triggers an unbypassable prompt — run `gh stack unstack --local` first, then retry (see the non-interactive rules in `SKILL.md`).
