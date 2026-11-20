# Plan skeleton and Casper prompt rules

## `casper_production_plan.md` skeleton

```markdown
# <Name> — bringing the Replit app to the site (Casper task plan)

Written <date>. Conventions read from the remote default branches of <repos> on that date.

Each numbered task is one Casper thread ending in one PR (or one written note). Hand them
over one at a time, in order.

## Status (updated <date>)

| Task | State | Casper thread |
|---|---|---|
| 0. Prep | Done | — |
| 1. <title> | Not started | — |

## Decisions (settled <date>)
1. **URL / app:** …
2. **Table names and database:** …
3. **Interactive features (sliders, filters):** …
4. **Deferred:** …

## Reference material on GitHub
Repo, branch, folder; file map of the Replit source (what → file).

## What the app source showed (and how the tasks changed)
Numbered findings, each ending "→ tasks N, M".

## How to prompt Casper
(the rules below, tailored)

The reference block (if it changes, change it in every prompt):
> Reference material (read-only): repo `…`, branch `…`, folder `…`. <source of truth> is
> the source of truth for <the numbers>. `replit_app/` is the source of the existing app;
> read it for behaviour and wording, but do not port its code or stack. Where a brief and
> the app's code disagree, the code is what people have been using.

## Phase 1 — <name>
### Task 1: <title> (`<repo>`)
Goal, what to copy, the spec bullets.

**Example prompt**

> <Name> | Task 1: <title>
>
> @Casper In `<repo>`, …
>
> Done when: …
>
> When you finish, end your final message with the PR link as a full URL on its own
> line, and repeat it after any later change to the PR.

### Task 1b: <human step> (human step)
What the user runs, when, where; not an agent prompt.

## Not confirmed
Assumptions still to check.
```

The builder only parses blockquotes whose first line is `> <Name> | Task <id>:`; keep
every other blockquote (like the reference block) from starting that way.

## Prompt anatomy

1. Header line `<Name> | Task N: <title>` (the thread list in Slack then shows which task
   each thread is; the tracker's Refresh finds threads by it).
2. `@Casper In <repo>, <the one thing to build>.`
3. **The file to copy**, by path. Casper follows a concrete example far better than a
   description of a convention.
4. Spec: names, types, schedule, limits, links to earlier threads/PRs (fill in
   `[task 5 PR]` placeholders before pasting).
5. **Out of scope:** what not to touch (other repos, triggering jobs, prod writes, nav entries).
6. **Stop and ask** where a guess would be expensive: table names, grants, anything that
   writes to a warehouse, a choice between data sources.
7. **Done when:** checkable, not "works well". Good criteria from the Fan Intensity port:
   - unit tests named by behaviour ("guard logic", "zero views → null");
   - parity: "matches the notebook on the August snapshot for every artist", with max diff;
   - performance evidence: `EXPLAIN ANALYZE` / `EXPLAIN ESTIMATE`, timings, bytes read;
   - `--dry-run` end to end printing row counts and guard values;
   - the PR description lists the exact one-off DDL a human runs first;
   - a preview URL showing X for an employee and the 404 for anyone else.
8. The reference block, when the task leans on the source.
9. PR tasks end by asking for the PR link as a full URL on its own line.

## Sizing and ordering

- One deliverable per thread. Split "port the queries" from "port the scoring" from
  "write path"; a design note (names, types, DDL) comes before any table-writing code.
- Investigation tasks (which data source? is there an existing route?) end with findings
  and a recommendation and stop; the user replies "go with X" in the same thread.
- Don't start a task until what it depends on is merged (or "built", when an open PR is
  enough to read from). Encode that as `deps` in the tracker.
- Human steps sit between tasks: one-off DDL after the write-path PR merges, the first
  run after the DAG merges, then a read-only verification prompt for Casper.

## Follow-up replies (same thread, no header)

- Rebase after a parent PR merged: ask that shared files become identical to main and
  drop out of the diff, no behaviour change, re-run pre-commit + tests, report head
  commit, file list, whether approval survived, whether the DDL changed.
- Go-ahead after an investigation: restate the choice, the response shape, and the
  evidence the PR must show.
