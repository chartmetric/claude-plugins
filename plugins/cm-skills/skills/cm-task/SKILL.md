---
name: cm-task
description: Run a single task in an existing repo with harness discipline - interview to a confirmed brief, red verifier before code, TDD implement, fresh-context review subagent, micro-retro lesson. Triggers - /cm-task, "harness this task", "run this task with the harness". Accepts an Asana or Slack URL, or free text, as args.
---

# Run one task with harness discipline

Bring the harness-template workflow to a SINGLE task in an existing repo:
one task, one branch, one PR, one session. You are the driver — you
implement in this session with the human watching. The ONLY thing you
spawn is a fresh-context reviewer.

This is **discipline, not enforcement.** Nothing here is mechanically
guaranteed the way the harness-template runner enforces it — no phase
JSON, no state machine, no hooks blocking you. You carry the discipline.
If a step feels skippable, that is exactly the failure mode this skill
exists to prevent. Follow all eight steps in order.

If the task turns out to be multi-PR sized, STOP and say so (see Step 2).

## Step 1 — Intake

Args may hold an Asana URL, a Slack thread URL, free text, or nothing.

- Asana URL → `mcp__claude_ai_Asana__get_task`. Slack URL →
  `mcp__claude_ai_Slack__slack_read_thread`. Treat whatever you pull as
  ENRICHMENT, never a complete spec — tickets are chronically
  under-specified.
- Read the repo's `CLAUDE.md` / `AGENTS.md` and skim the relevant code
  area BEFORE you ask anything. Discover real test commands from
  `package.json` / `pyproject.toml` / `Makefile`, and real file paths in
  the area you'll touch. An informed interview proposes concrete
  options; an uninformed one wastes the user's turns.

## Step 2 — Interview (AskUserQuestion modals, not free text)

Ask only what intake could not establish. `AskUserQuestion` caps at 4
questions per call, so send acceptance criteria alone first (it needs
room), then the rest in a second call (drop any you already know cold);
every option you offer must be a real, discovered value, not a
placeholder:

1. **Acceptance criteria** — draft a list from ticket + code reading;
   let the user confirm/edit. Each criterion must be mechanically
   checkable.
2. **Verify command** — the single command that will prove the task
   done. Offer discovered options (e.g. `pnpm vitest run
   path/to/new.test.ts`, `python -m pytest tests/test_x.py::test_y`).
   This becomes the red-check target — steer toward a test.
3. **Scope globs** — which files/dirs the task may touch. Offer a
   drafted glob list. Used later for the reviewer's scope check.
4. **Risk** — is this auth / payment / PII / security-adjacent? If yes,
   the reviewer brief gets the security addendum.
5. **Reviewer model** — options: `opus (Recommended)`, `same as this
   session`, `sonnet`. Whatever is chosen is passed as the Task tool's
   `model` param in step 6; opus if the user skips the question.

**Scope tripwire.** If the interview reveals the task cannot land in one
PR, STOP. Do not soldier on. Tell the user, and offer to split it into
separate `/cm-task` runs in dependency order (harness-lite is the future
home for multi-phase work; it does not exist yet).

## Step 3 — Brief

Write a compact brief to the session scratchpad directory (NOT the
repo). Include: goal (1 paragraph), acceptance list, `verify_cmd`, gates
(the repo's standard lint / typecheck / test commands), scope globs, and
source links (Asana / Slack / files). Show it; get explicit confirmation.
This is the session's contract — refer back to it, do not re-litigate it.

**Slack-first tasks:** when intake came from a Slack thread and no Asana
task exists yet, offer (right after the brief is confirmed) to create
one via the `slack-to-asana` or `/cm-asana-task` skill if installed
(else the Asana MCP tools directly) — the brief's goal + acceptance list
is the task description, and pass the Slack URL so its custom field
links back to the thread. Creating it now means the work is tracked
before code exists and step 8's PR has a task to reference. If the user
declines, proceed — tracking is their call.

## Step 4 — Red check (the single most load-bearing rule)

1. Check the working tree is clean (`git status --porcelain`). If there
   are pre-existing uncommitted changes, STOP and ask the user to
   commit or stash them first — the step-6 reviewer audits the
   uncommitted diff, so anything already dirty would be attributed to
   this task and reviewed as its scope creep. Proceed over dirt only on
   explicit user say-so.
2. Create the branch: `<type>/<initials>-<slug>` — use YOUR initials
   as the personal prefix (e.g. `feat/hs-add-rate-limit`,
   `fix/th-n1-lister`). Ask once if you don't know the user's
   initials; remember them for the session.
3. Run `verify_cmd`. **It MUST fail.** A verifier that is green before
   any work exists cannot prove the work — that empty-workspace false
   positive has shipped broken phases before.
4. If it passes already: STOP. Explain the tautology and rework the
   verify command with the user (usually: it doesn't actually assert on
   the new behavior). Proceed-anyway only on explicit user say-so.

## Step 5 — Implement (TDD, in scope)

- TDD: write the failing test first when `verify_cmd` is a test (it
  usually is — Step 2 steers there).
- Follow repo conventions (`CLAUDE.md` / `AGENTS.md`); match surrounding
  code style; stay INSIDE the scope globs.
- Loop: implement → run `verify_cmd` → fix → until green. Then run the
  gates. No retry cap — the human is present and can stop you.

## Step 6 — Fresh-context review

Spawn exactly ONE subagent via the Task tool (prefer a code-reviewer
agent type if available, else general-purpose), passing the reviewer
model chosen in the step-2 interview as the `model` param (default
`"opus"`) — the reviewer must never SILENTLY inherit a cheaper session
model; review is the safety net, so degrading it is an explicit user
choice, not an accident. It cannot see this conversation, so the brief
must be fully self-contained.

**Before spawning, precompute the scope check yourself:** run `git
status --porcelain`, and for each changed path decide whether it matches
any scope glob from the brief. Collect the non-matching paths — that
list goes into the brief's scope section for the reviewer to judge.

Fill and pass this brief verbatim (drop the two optional blocks when they
don't apply):

```
You are a fresh-context reviewer auditing a just-implemented task. Do
NOT modify code — surface defects only. You are running inside the repo;
use git and file reads to inspect.

## Task under review

- Goal: <goal paragraph from the brief>
- Acceptance criteria:
  - <criterion 1>
  - <criterion 2>

The changes are the UNCOMMITTED working tree: run `git status
--porcelain` and `git diff`, and read new untracked files, to see
exactly what was written.

## Project conventions (load before reviewing)

- Read CLAUDE.md / AGENTS.md at the repo root, every numbered section,
  plus any docs they point to. Any CRITICAL / MUST NOT token in those
  docs is non-negotiable; flag violations as must_fix.

## Scope check (mechanical pre-computation)

These changed files match none of the task's declared scope globs:
<out-of-scope list, one per line — OMIT THIS WHOLE BLOCK if empty>

Judge each: unjustified out-of-scope work is scope creep and a must_fix
finding; incidental necessary changes (lockfiles, generated files,
unavoidable wiring) may pass — note those in should_fix or
backlog_worthy instead.

## Security focus
<INCLUDE ONLY when the risk answer was yes>
This task is security-sensitive. Threat-model the change: authn/authz
surfaces, secret handling, injection, unsafe deserialization, PII leaks
to logs/stdout. Report findings in the same buckets.

## Output contract (machine-parsed — follow exactly)

Your final reply must be ONLY a JSON object, no prose, no code fences:

    {
      "must_fix": ["file:line — defect — suggested fix", ...],
      "should_fix": ["file:line — issue — suggested fix", ...],
      "backlog_worthy": ["one-line item with priority guess", ...]
    }

An empty must_fix array means clean to ship. must_fix = defects that
block correctness, violate a documented invariant, or are security
risks. Judgment calls and preferences are NOT must_fix. Each finding is
one string. Stay under 400 words total.
```

**Parse the reply fail-closed.** The result is clean ONLY if you can
extract a JSON object whose `must_fix` is a list of non-empty strings and
that list is empty. Treat ALL of these as BLOCKING, never as clean:
- output that isn't parseable JSON (tolerate surrounding prose / one code
  fence, but if no `{...}` with a `must_fix` list is found, it blocks);
- any `must_fix` item that is not a non-empty string (an object, a
  number, an empty string).
When it blocks unparseably, surface the raw reviewer output to the user
and triage manually — do not guess it was fine.

Handling findings:
- **must_fix** → fix, re-run `verify_cmd` + gates, then re-review. Max 2
  fix cycles. If findings persist after the second cycle, STOP and hand
  the findings to the user (the harness's `needs_human`).
- **should_fix** → present to the user: fix now / follow-up / dismiss.
- **backlog_worthy** → offer to file to Asana (via a task-creation
  skill if installed, else the Asana MCP tools) or note in the
  PR body.

## Step 7 — Micro-retro (the feedback loop — NEVER skip)

Always run this, even for a one-line bugfix. Use ONE `AskUserQuestion`
modal (not free text) with drafts prepared:

1. **Lesson** — one sentence worth landing in the repo's `CLAUDE.md` /
   `AGENTS.md`. Draft a specific candidate from what actually bit during
   this task; offer it as the default option alongside "none" (a
   legitimate answer). Ask the question every time. If accepted, apply
   the edit on this same branch.
2. **Leftovers** — surviving should_fix / backlog_worthy items: file via
   Asana, note in the PR body, or drop. Offer the drafted
   dispositions.

## Step 8 — Ship

- Commit(s): Conventional Commits with the repo's scope conventions and
  the AI co-author trailer.
- Offer a PR-creation skill if installed (`/cm-pr`, `ship-pr`) to open
  the PR — they already handle template selection,
  base-branch detection, and Asana/Slack links. Reuse it; do not
  reimplement.
- NEVER `git push` or create the PR without explicit user OK.

## Non-goals (do not add these)

- No spawned writer agent — you are the writer.
- No state files in the repo, no resume across sessions. If the session
  dies, re-brief from scratch; that cost is acceptable at 1-PR scope.
- No auto-generated repo-wide codebase summary — Step 1's targeted
  reading replaces it.
- No claim that any of this is mechanically enforced. It isn't. Say so if
  the user assumes otherwise.
