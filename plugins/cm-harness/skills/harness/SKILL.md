---
name: harness
description: Advance the Chartmetric phase harness — show phase status, propose a phase plan, triage a stuck phase, or run the current phase. Use when the user types /harness, or explicitly asks about phase status, what phase their feature is on, proposing phases for the monorepo, or running the next phase. Operates on the chartmetric-app-monorepo phase pipeline (phases/, scripts/execute.py, harness.config.json).
---

# /harness — loader

The real instructions live in the repo, at `.agents/commands/harness.md`. This skill's
only job is to find that file, follow it faithfully, and adapt its mechanics to whichever
environment this session is running in.

**Do not reimplement the command from memory.** It is versioned with the codebase and
changes without this plugin being republished. Read it every time.

## Procedure

1. **Locate the repo.** Follow Step 1 of `references/environments.md`. Without the repo
   there is nothing to do — say so plainly and ask the user to connect their clone.

2. **Establish what this environment can do.** Read Step 2 of `references/environments.md`
   before promising anything. The short version: everything except `execute.py run` works
   in all four environments. `run` spawns writer/fixer/reviewer/retro agents and needs a
   working `claude` binary — present and authenticated in a Claude Code terminal or cloud
   sandbox, **disabled** on the device VM a cloud Cowork session reaches.

3. **Read `<repo>/.agents/commands/harness.md` in full and follow it.** (Fall back to
   `.claude/commands/harness.md`; see Step 1 of `references/environments.md` for why.)
   It will have you run `precheck` first and stop hard if it fails, then `status`, then
   branch on the current phase's state.

4. **Adapt only the mechanics, never the decisions.** Running `python3 scripts/execute.py
   <cmd>` means `device_bash` in a cloud Cowork session and a plain `Bash` call otherwise.
   The command file's rules about what to do with the output are unchanged either way.

## Before you touch anything

Check `.harness/locks/` for a lock file. If one exists, a run may be in flight, and
`pipeline.py` runs `git add -A` at repo root — anything you write anywhere in that tree
gets swept into that phase's commit and flagged by the scope check.

You **cannot** verify the PID yourself from a cloud Cowork session; `device_bash` runs in
a different process namespace than the macOS process that wrote the lock. Ask the user to
check on their machine. While a run is live, restrict yourself to reads, and keep scratch
files under `.harness/` (gitignored, invisible to both `git add -A` and the scope check).

## Running a phase

`run` is the normal path; `start`/`finish`/`review`/`retro` are recovery tools — reach for
them only when the user asks or a run needs manual repair.

- **Repo directly accessible, `claude` spawnable** — run it in place, in the background,
  and monitor. This is the good case, and it covers both Claude Code terminal sessions
  and Claude Code cloud sandboxes. In a sandbox, confirm
  `node_modules/.bin/claude --version` first: an install run with `--ignore-scripts`
  leaves a shim that fails at first use, and `doctor` does not catch it.
- **Cloud Cowork session** — read the phase's `verification_cmd` first. If it filters to
  `apps/web`, stop: the container's proxy refuses `npm.fontawesome.com` outright, so
  install fails before any test runs and the phase has to go on the user's machine. If it
  filters to `apps/api`, bootstrap a container copy per Step 3 of
  `references/environments.md`, gate on `doctor: ok`, run, and hand the result back as a
  patch for the user to apply and push.

Never `git push` or open a PR without explicit user approval — the command file requires
this, and from a cloud Cowork container it will fail anyway (the device VM has no git
write credentials).

## When a phase is `✗ exhausted`

That glyph means it blew `max_attempts` or `max_review_cycles` and wants a human. Show
the status, stage, `review_findings`, and any backlog entry. Read the agent transcripts
under `.harness/transcripts/<phase-id>/` — they hold the full exchange, where the phase
JSON keeps only a 500-character error tail. Help the user decide before re-running
anything.

## Rules carried over from the command file

- Do not modify multiple phases at once. Finish the current one, then advance.
- Defer architectural choices not covered by `docs/ARCHITECTURE.md` to the user — never
  silently lock in a boundary, library, or schema shape.
- For product feature work not already covered by a `docs/PRD.md` entry, tell the user to
  run `/feature-intake` first rather than inventing requirements. Repo and tooling
  maintenance — harness changes, CI, lint rules, dependencies — needs no PRD entry.
- Do not invoke `/feature-intake` yourself. Slash commands recurse. Tell the user to run
  it.
