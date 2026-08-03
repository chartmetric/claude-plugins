# gh stack — merge a stack

Flags and behavior for landing a stack. Non-interactive requirements and exit codes are in `SKILL.md`; this file assumes them.

## `gh stack merge` — merge the stack

```
gh stack merge [<pr-number> | <stack-number>] --yes [--squash|--rebase|--merge|--merge-method <m>]
```

Merges the whole stack bottom-to-top, atomically. `--yes` is required for non-interactive use. Scope with a PR number (merges everything up to and including that PR) or a stack number (needs no local checkout). Choose a method with `--squash` / `--rebase` / `--merge` / `--merge-method`; without one, the last-used method applies.

All-or-nothing: if any PR can't merge, none do, and the reason is reported. Only basic state is checked (open, not draft) — merge requirements can't be bypassed for stacks. If the base branch uses a **merge queue**, the stack is added to the queue instead of merging directly: the queue picks the method (any passed method is ignored with a warning), and the PRs, though queued together, may land in separate groups as the queue processes them.

How merge queues, branch-protection rules, partial merges, and closed mid-stack PRs interact with a stack is covered in GitHub's [gh-stack FAQ](https://github.github.com/gh-stack/faq/).
