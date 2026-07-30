# gh stack — keep a stack current

Flags and behavior for rebasing the stack as trunk and parents move, and for resolving the conflicts that fall out. Non-interactive requirements and exit codes are in `SKILL.md`; this file assumes them.

## `gh stack sync` — fetch, rebase, push, sync state

```
gh stack sync [--remote <name>] [--prune]
```

The routine one-shot synchronizer. In order: fetch → reconcile the remote stack (pull down PRs added on github.com; abort cleanly if local and remote have diverged) → fast-forward trunk → cascade-rebase branches onto moved parents (handles merged PRs; on conflict restores all branches and exits 3) → push active branches atomically → sync PR state → link open PRs into the GitHub stack (only when ≥2 PRs exist; never opens PRs). Pruning of merged local branches happens only with `--prune` in non-interactive terminals.

| Flag | Description |
|------|-------------|
| `--remote <name>` | Fetch/push remote (multiple-remote setups) |
| `--prune` | Delete local branches for merged PRs |

## `gh stack rebase` — pull and cascade-rebase

```
gh stack rebase [--downstack|--upstack] [--no-trunk] [--continue|--abort] [--remote <name>] [branch]
```

Rebases stack branches onto their parents. Use it for finer control than `sync`, or to resolve a conflict `sync` hit. Merged PRs are handled with `--onto`. `git rerere` (enabled by `init`) auto-resolves previously-seen conflicts. The optional `[branch]` argument targets a branch other than the current one.

| Flag | Description |
|------|-------------|
| `--downstack` | Only rebase trunk → current branch |
| `--upstack` | Only rebase current branch → top |
| `--no-trunk` | Skip fetch + trunk rebase; only rebase branches onto each other |
| `--continue` | Continue after resolving conflicts (stage with `git add` first) |
| `--abort` | Abort and restore all branches |
| `--remote <name>` | Fetch remote (multiple-remote setups) |

Conflict resolution: see the Handle rebase conflicts section in `SKILL.md`.
