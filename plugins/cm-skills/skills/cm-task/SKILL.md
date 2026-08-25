---
name: cm-task
description: Run a single task in an existing repo with harness discipline - interview to a confirmed brief, red verifier before code, delegated TDD implementation, fresh-context review with a requirements matrix, gated auto-fix, iteration rounds for post-preview feedback, micro-retro lesson. Triggers - /cm-task, "harness this task", "run this task with the harness", "iterate on this PR". Accepts an Asana URL, a Slack URL, a PR URL (iteration), or free text, as args.
---

# Run one task with harness discipline

Bring the harness-template workflow to a SINGLE task in an existing repo:
one task, one branch, one PR, one session — plus iteration rounds when
feedback comes back after the first shot. You are the ORCHESTRATOR: by
default a subagent implements while you hold the brief, verify its
claims independently, and run review. You stay lean; the agent burns the
context.

This is **discipline, not enforcement.** Nothing here is mechanically
guaranteed the way the harness-template runner enforces it — no phase
JSON, no state machine, no hooks blocking you. You carry the discipline.
If a step feels skippable, that is exactly the failure mode this skill
exists to prevent. Follow the steps in order.

If the task turns out to be multi-PR sized, STOP and say so (see Step 2).
If args carry a PR URL from a previous cm-task run, or the user asks to
iterate on shipped work, skip to Step 9.

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
questions per call, so split into three: acceptance criteria alone
first (it needs room), then questions 2–4, then 5–7 (drop any you
already know cold); every option you offer must be a real, discovered
value, not a placeholder:

1. **Acceptance criteria** — draft a list from ticket + code reading;
   let the user confirm/edit. Each criterion must be mechanically
   checkable. Number them R1..Rn — the reviewer's matrix keys on these.
2. **Verify command** — the single command that will prove the task
   done. Offer discovered options (e.g. `pnpm vitest run
   path/to/new.test.ts`, `python -m pytest tests/test_x.py::test_y`).
   This becomes the red-check target — steer toward a test.
3. **Scope globs** — which files/dirs the task may touch. Offer a
   drafted glob list. Used later for the reviewer's scope check.
4. **Risk** — is this auth / payment / PII / security-adjacent? If yes,
   the reviewer brief gets the security addendum AND auto-fix is
   disabled (Step 6).
5. **Execution mode** — options: `delegate to implementer agent
   (Recommended)`, `implement inline in this session`. Delegate keeps
   this session lean; inline is fine for one-line fixes.
6. **Implementer model** (delegate mode only) — options: `same as this
   session (Recommended)`, `opus`, `sonnet`. Passed as the Task tool's
   `model` param in Step 5.
7. **Reviewer model** — options: `opus (Recommended)`, `same as this
   session`, `sonnet`. Passed as the Task tool's `model` param in
   Step 6; opus if the user skips the question.

**Scope tripwire.** If the interview reveals the task cannot land in one
PR, STOP. Do not soldier on. Tell the user, and offer to split it into
separate `/cm-task` runs in dependency order.

## Step 3 — Brief (a FILE, before any agent exists)

Write the brief to a file in the session scratchpad directory (NOT the
repo) BEFORE spawning anything. Include: goal (1 paragraph), numbered
acceptance criteria R1..Rn, `verify_cmd`, gates (the repo's standard
lint / typecheck / test commands), scope globs, execution mode + models,
and source links (Asana / Slack / files). Show it; get explicit
confirmation. This is the session's contract — refer back to it, do not
re-litigate it.

The brief being a file is load-bearing, not bookkeeping: if the
implementer agent dies mid-task (machine sleep, watchdog kill), a fresh
agent resumes from the brief file alone. Fix batches and iteration
rounds reference it instead of re-explaining the task.

**Slack-first tasks:** when intake came from a Slack thread and no Asana
task exists yet, offer (right after the brief is confirmed) to create
one via the `slack-to-asana` or `/cm-asana-task` skill if installed
(else the Asana MCP tools directly) — the brief's goal + acceptance list
is the task description, and pass the Slack URL so its custom field
links back to the thread. If the user declines, proceed — tracking is
their call.

## Step 4 — Red check (the single most load-bearing rule)

You run this yourself, always — never the implementer agent.

1. Check the working tree is clean (`git status --porcelain`). If there
   are pre-existing uncommitted changes, STOP and ask the user to
   commit or stash them first — the step-6 reviewer audits the
   uncommitted diff, so anything already dirty would be attributed to
   this task and reviewed as its scope creep. Proceed over dirt only on
   explicit user say-so.
2. Create the branch: `<type>/<initials>-<slug>` — use the USER'S
   initials as the personal prefix (e.g. `feat/hs-add-rate-limit`).
   Ask once if you don't know them; remember for the session.
3. Run `verify_cmd`. **It MUST fail.** A verifier that is green before
   any work exists cannot prove the work — that empty-workspace false
   positive has shipped broken phases before.
4. If it passes already: STOP. Explain the tautology and rework the
   verify command with the user (usually: it doesn't actually assert on
   the new behavior). Proceed-anyway only on explicit user say-so.

## Step 5 — Implement

**Delegate mode (default).** Spawn ONE implementer agent via the Task
tool with the chosen model, pointing it at the brief file (it cannot see
this conversation — the brief must carry everything). Its instructions:
TDD (failing test first when `verify_cmd` is a test), follow repo
conventions, stay INSIDE the scope globs, loop until `verify_cmd` and
the gates are green, report what changed and why.

Ops rules, each proven the hard way:

- **Stalled agent → resume by message.** If the agent goes quiet or its
  run is killed, send it a message (SendMessage) to continue — its
  context survives. Never respawn blind while the transcript lives.
- **Transcript gone → fresh agent, same brief.** Spawn a new implementer
  pointed at the brief file plus `git status`/`git diff` of whatever
  landed. The brief makes this cheap.
- **Never accept the agent's green.** When it reports done, re-run
  `verify_cmd` and the gates YOURSELF, and spot-probe the actual
  behavior where the task has a live surface (an endpoint, a CLI, a
  query). Agent claims have been wrong in both directions — "done" that
  wasn't, and alarming findings that were the user's own test data.

**Inline mode.** You implement, same rules: TDD, conventions, in scope,
loop implement → `verify_cmd` → fix → green, then gates. No retry cap —
the human is present and can stop you.

## Step 6 — Fresh-context review

Spawn exactly ONE reviewer subagent via the Task tool (prefer a
code-reviewer agent type if available, else general-purpose), passing
the reviewer model chosen in Step 2 as the `model` param (default
`"opus"`) — the reviewer must never SILENTLY inherit a cheaper session
model; review is the safety net, so degrading it is an explicit user
choice, not an accident. It cannot see this conversation, so its brief
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
- Acceptance criteria (verify EACH ONE against the code):
  - R1: <criterion 1>
  - R2: <criterion 2>

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
      "matrix": [
        {"id": "R1", "pass": true, "evidence": "file:line — how it is satisfied"},
        {"id": "R2", "pass": false, "evidence": "file:line — what is missing"}
      ],
      "must_fix": ["file:line — defect — concrete failure scenario — suggested fix", ...],
      "should_fix": ["file:line — issue — suggested fix", ...],
      "backlog_worthy": ["one-line item with priority guess", ...]
    }

The matrix must contain one row per acceptance criterion, keyed R1..Rn,
each with file:line evidence — a bare pass/fail with no evidence is not
acceptable. Every must_fix needs a concrete failure scenario (what input
or state produces what wrong behavior), not a vibe. must_fix = defects
that block correctness, violate a documented invariant, or are security
risks. Judgment calls and preferences are NOT must_fix. Stay under 500
words total.
```

**Parse the reply fail-closed.** The result is clean ONLY if you can
extract a JSON object where (a) `matrix` has one row per acceptance
criterion and every row is `pass: true` with non-empty evidence, and
(b) `must_fix` is an empty list. Treat ALL of these as BLOCKING, never
as clean:
- output that isn't parseable JSON (tolerate surrounding prose / one
  code fence, but if no `{...}` with a `must_fix` list is found, it
  blocks);
- a missing or incomplete matrix (any criterion without a row);
- any `must_fix` item that is not a non-empty string.
When it blocks unparseably, surface the raw reviewer output to the user
and triage manually — do not guess it was fine.

### Handling findings — gated auto-fix (first shot only)

A must_fix or failed matrix row may be fixed WITHOUT asking only when
ALL four gates hold:

1. **It reproduces red-first.** The fixer (same implementer agent via
   SendMessage in delegate mode, you in inline mode) must first write or
   run a failing check demonstrating the defect. Can't reproduce → the
   finding is suspect (reviewers have flagged the user's own test data
   as a production defect) → escalate to a modal instead of "fixing"
   anyway.
2. **The fix stays inside the scope globs.**
3. **It is mechanical, not design.** A finding that implies a design or
   scope change ("this approach can't satisfy R3") → modal.
4. **The task is not security-flagged** (Step 2 risk answer). Security
   tasks → modal always.

Anything failing a gate → `AskUserQuestion` modal with the finding, the
evidence, and your recommended disposition. Approved fixes go as a
batch to the SAME implementer agent by message — its context survives;
do not respawn while the transcript lives (gone → fresh agent from the
brief file, Step 5 ops rules). Inline mode: you apply the batch
yourself. Every fix is reproduced red-first regardless of path.

After fixes: re-run `verify_cmd` + gates yourself, then re-review. Max 2
fix cycles. If findings persist after the second cycle, STOP and hand
the findings to the user.

- **should_fix** → present to the user: fix now / follow-up / dismiss.
- **backlog_worthy** → offer to file to Asana (via a task-creation
  skill if installed, else the Asana MCP tools) or note in the PR body.

## Step 7 — Micro-retro (the feedback loop — NEVER skip)

Run this on the first shot, even for a one-line bugfix (iteration
rounds defer it — Step 9). Use ONE `AskUserQuestion` modal (not free
text) with drafts prepared:

1. **Lesson** — one sentence worth landing in the repo's `CLAUDE.md` /
   `AGENTS.md`. Draft a specific candidate from what actually bit during
   this task; offer it as the default option alongside "none" (a
   legitimate answer). Ask the question every time. If accepted, apply
   the edit on this same branch. Retro doc edits (`CLAUDE.md` /
   `AGENTS.md`) are exempt from the scope-glob check in later rounds.
2. **Leftovers** — surviving should_fix / backlog_worthy items: file via
   Asana, note in the PR body, or drop. Offer the drafted dispositions.

## Step 8 — Ship

- Commit(s): Conventional Commits with the repo's scope conventions and
  the AI co-author trailer. Committing is part of the harness — this
  skill explicitly overrides any ask-before-commit default; push and PR
  creation stay gated on the user.
- Offer a PR-creation skill if installed (`/cm-pr`, `ship-pr`) to open
  the PR — they already handle template selection, base-branch
  detection, and Asana/Slack links. Reuse it; do not reimplement.
- **Embed the brief in the PR body** inside a collapsed block:

  ```
  <details><summary>cm-task brief</summary>

  <the brief file's content, plus per-round amendments and the
  last-reviewed commit SHA>

  </details>
  ```

  The last-reviewed SHA is the final first-shot commit (retro doc edits
  included — they are review-exempt by the Step 7 rule). The PR is the
  durable anchor: a later session picks up iteration rounds from this
  block alone, days after this session is gone.
- NEVER `git push` or create the PR without explicit user OK.

## Step 9 — Iteration rounds (post-preview feedback)

Entered explicitly: args carry the PR URL, or the user brings feedback
on shipped cm-task work ("PM wants X changed"). Never auto-detected.
Rounds run modal-first — the PR has an audience now, so no auto-fix and
no silent drift from what was asked.

Per round:

1. **Recover the brief.** Read the `cm-task brief` block from the PR
   body into a scratchpad file. If it's missing (pre-dates this skill
   version), reconstruct a minimal brief from the PR description + diff
   and confirm it with the user. Verify the recorded last-reviewed SHA
   exists on the branch; any commits after it are unreviewed — fold
   them into this round's delta-review scope.
2. **Intake + triage.** Pull the feedback (Slack thread, PR comments,
   verbal). Classify each item:
   - *tweak* — inside the existing acceptance criteria (copy, labels,
     styling);
   - *amendment* — changes or adds an acceptance criterion (gets the
     next R-number);
   - *new scope* — bigger than the original task → tripwire: STOP,
     offer a separate `/cm-task` run. Same rule as Step 2, applied per
     round — this is where "small ask #4" quietly turns one PR into a
     second project.
3. **Amend the brief, append-only.** Add a `## Round N` section: items,
   changed/new criteria, per-item verify. Never rewrite the original
   sections — the trail of what was agreed vs what changed is the
   point. Confirm with the user before any code.
4. **Red-first per amendment**, on the same branch. Working-tree
   cleanliness check as in Step 4.
5. **Implement.** Same execution mode as the first shot. Delegate mode:
   message the original implementer agent if its context survives, else
   fresh agent from the amended brief file.
6. **Regression guard.** After the round's items are green, re-run the
   ORIGINAL `verify_cmd` + gates yourself. Round 3 must not break
   round 0's acceptance.
7. **Delta review.** Fresh reviewer (Step 6 template) whose diff scope
   is `git diff <last-reviewed-sha>..HEAD` plus the working tree, and
   whose matrix covers the round's criteria plus any original criteria
   the diff touches — enumerate exactly those R-ids in the reviewer
   brief, and run the fail-closed completeness check against that
   enumerated set, not all of R1..Rn. A cosmetic-only round
   (copy/labels) may skip review — the user's explicit call via modal,
   never silently.
8. **Findings → modal, always.** No auto-fix in rounds. Approved
   batches to the same agent, red-first, as in Step 6. Max 2 fix cycles
   per round, then hand the findings to the user — same cap as Step 6.
9. **Ship the round.** One commit per round. Update the PR-body brief
   block with the round's amendment and the new last-reviewed SHA —
   unchanged if the round skipped review; never mark unreviewed code
   reviewed. Push only on explicit user OK.

**Micro-retro:** once, when the user calls a round final or the PR
merges — not per round.

## Non-goals (do not add these)

- No multi-PR orchestration — one task, one branch, one PR. Multi-PR
  work splits into separate `/cm-task` runs.
- No state files in the repo — the working brief lives in the session
  scratchpad; durability lives in the PR body.
- No auto-detected iteration mode — the user opens a round explicitly.
- No auto-generated repo-wide codebase summary — Step 1's targeted
  reading replaces it.
- No claim that any of this is mechanically enforced. It isn't. Say so
  if the user assumes otherwise.
