---
name: feature-intake
description: Turn a plain-language feature ask into an ADR-grounded technical PRD entry for the Chartmetric monorepo, before /harness proposes phases. Use when the user types /feature-intake, or explicitly asks to write up a feature ask, turn a feature idea into a PRD, or check a feature against the repo's architecture decisions. Written for PMs, designers, and engineers new to the codebase — no engineering detail expected of the person asking.
---

# /feature-intake — loader

The real instructions live in the repo, at `.agents/commands/feature-intake.md`. This
skill's only job is to find that file, follow it faithfully, and adapt its mechanics to
whichever environment this session is running in.

**Do not reimplement the command from memory, and do not substitute your own judgment for
what that file says.** It is versioned with the codebase and changes without this plugin
being republished. Read it every time.

## Procedure

1. **Locate the repo and read the command.** Follow Step 1 of
   `${CLAUDE_PLUGIN_ROOT}/skills/harness/references/environments.md`. Then read
   `<repo>/.agents/commands/feature-intake.md` in full (falling back to
   `.claude/commands/feature-intake.md`; that same Step 1 says when and why).

2. **Follow it exactly.** It will have you read `docs/ARCHITECTURE.md` and everything it
   links under `docs/architecture/` and `docs/contracts/`, every entry in `docs/ADR.md`,
   and the `## Learned rules` section of `AGENTS.md` — then translate the ask into
   concrete technical surface, cross-check that surface against existing decisions, and
   write a `docs/PRD.md` entry.

   In a cloud Cowork session, read those files by staging them over the device bridge and
   search the code with `device_bash` (`grep`/`rg` run natively on the user's machine).
   The whole doc corpus is about 41 KB — read all of it rather than sampling.

3. **Honour the three rules that matter most**, because they are why this command exists:
   - When no architectural decision covers the surface, **stop and ask the user** with a
     small set of concrete options and their real consequences. Never pick for them.
   - When the ask conflicts with an existing decision, **stop and explain the conflict**
     in plain terms, then ask whether to adjust the ask or supersede the decision.
   - `docs/ADR.md` is **append-only**. A changed decision is a new numbered entry that
     says what it supersedes — never an edit to a past entry.

4. **Confirm before writing.** Show the user the drafted PRD section, and any new or
   superseding ADR entry, and get explicit agreement before writing either file.

## Writing the result back

How the PRD entry reaches the repo depends on where this session runs.

- **Repo directly accessible** — write `docs/PRD.md` in place, after confirmation. This
  covers Claude Code in a terminal, Claude Code in a cloud sandbox, and Cowork running on
  your computer.
- **Cloud Cowork session with the folder connected** — write via `device_bash`, or
  deliver the file and use `device_commit_files`. Check `.harness/locks/` first: if a
  harness run is live, **do not write into the repo at all**. `pipeline.py` runs
  `git add -A` at repo root, so your file would be swept into that phase's commit. Hold
  the draft, tell the user, and write once the run clears.
- **No repo access** — do not fabricate one. Produce the PRD entry as a file, deliver it
  with `SendUserFile`, and tell the user it needs to land in `docs/PRD.md`.

The person running this often cannot commit or push. Say plainly what you wrote, where it
went, and what still needs an engineer — do not leave them assuming the change is live.

## Handoff

End by telling the user the next step is `/harness`, which reads `docs/PRD.md` and
`docs/ARCHITECTURE.md` to propose phases.

**Do not invoke `/harness` yourself.** The command file is explicit about this — slash
commands recurse. Tell the user to run it.
