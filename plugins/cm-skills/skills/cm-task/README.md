# cm-task

## The problem it solves

Hand an AI agent a ticket and it will produce something that looks
right. The tests it writes pass because it wrote them to pass. The scope
quietly widens into files nobody asked it to touch. Three days later the
work fails in review, or worse, in production, and the reasoning that
produced it is gone.

And even when the first shot lands clean, it isn't the end: at
Chartmetric the PM or an exec previews the work and comes back with
changes. That's where discipline usually evaporates — ad-hoc edits on
the branch, nobody re-running the original checks, "one more small ask"
turning one PR into a second project.

`cm-task` is a Claude Code skill that wraps a single task in the same
discipline the Chartmetric harness uses on full projects: interview you
to a confirmed brief, prove a verifier fails *before* any code exists,
delegate implementation to a subagent whose claims are independently
verified, then hand the diff to a fresh-context reviewer that never saw
the conversation — and keep that same discipline through every feedback
round after the preview. One task, one branch, one PR.

## When to use it — and when not to

There are three tiers. Match the tool to the work or people will hate it.

| Work | Use | Why |
|------|-----|-----|
| Trivial 15-minute fix (typo, config bump, one-line guard) | Plain Claude Code | `cm-task` would be pure ceremony |
| One task with real acceptance criteria (a feature, a bug with a repro, an endpoint change) | **`/cm-task`** | Worth a brief, a red check, and a review |
| Multi-phase project or a new repo | [harness-template](https://github.com/chartmetric/harness-template) | Needs enforced state, phases, resume |

Be honest with yourself about the first row. If you run `cm-task` on a
one-line change, you will sit through three question modals and a review
subagent for something you could have typed faster by hand, and you will
never open the skill again. Save it for work where being wrong is
expensive.

## Entry points

- `/cm-task <asana-url>` — pulls the task as enrichment for the interview.
- `/cm-task <slack-thread-url>` — reads the thread; after you confirm the
  brief it offers to create the Asana task for you (Slack-first is the
  team's normal order — issue in Slack, task after).
- `/cm-task <free text>` — describe the task inline.
- `/cm-task <pr-url>` — **iteration mode**: pick up feedback rounds on a
  PR a previous run shipped, however much later, in a fresh session.
- `/cm-task` — bare; it interviews you from nothing.

Whatever a ticket says is treated as *enrichment, never a complete
spec* — tickets are chronically under-specified, so the interview always
runs.

## What the first shot feels like from your seat

You are touched a handful of times. Everything between your touches is
autonomous but visible in the transcript.

1. **Intake (silent).** It reads your repo's `CLAUDE.md`/`AGENTS.md`,
   skims the code area you'll touch, and discovers the real test commands
   before asking you anything.
2. **Interview — touches 1–3.** Up to three `AskUserQuestion` modals.
   First: confirm or edit the drafted acceptance criteria (numbered
   R1..Rn — the review matrix keys on these). Then: the verify command,
   scope globs, whether the task is security-sensitive. Then: execution
   mode (delegate to an implementer agent, the default, or inline), the
   implementer model, and the reviewer model. Every option offered is a
   real value it discovered, not a placeholder.
3. **Brief (visible).** A compact contract — goal, criteria, verify
   command, gates, scope, models — written to a *file* before any agent
   exists. That file is load-bearing: if the implementer dies mid-task
   (machine sleep, watchdog kill), a fresh agent resumes from the brief
   alone.
4. **Red check (visible).** It creates the branch, then runs your verify
   command and confirms it **fails**. This is the load-bearing rule: a
   verifier that is green before any work exists cannot prove the work —
   that false positive has shipped broken code before. If it passes
   already, the run stops and asks you to fix the verifier.
5. **Implement (visible).** By default an implementer subagent works
   from the brief — test-first, inside the scope globs — while your
   session stays lean. When the agent reports done, its green is **not
   trusted**: the orchestrator re-runs the verifier and gates itself and
   probes the live behavior. Agent claims have been wrong in both
   directions.
6. **Review (visible).** One fresh-context subagent audits the diff and
   returns a **requirements matrix** — one row per criterion, pass/fail,
   with file:line evidence — plus severity-ranked findings, each with a
   concrete failure scenario. A blocking finding is auto-fixed *only*
   when it reproduces red-first, stays in scope, is mechanical, and the
   task isn't security-flagged; anything else comes to you in a modal.
   Up to two fix cycles, then it stops and hands you the findings.
7. **Micro-retro — one modal.** The single lesson worth keeping (see
   below).
8. **Ship — final touch.** It commits (committing is part of the
   harness), embeds the brief in a collapsed block in the PR body, and
   offers to open the PR. It never pushes or opens a PR without your
   explicit OK.

**Example.** You run `/cm-task` on a ticket to rate-limit the
`POST /v1/events` ingestion endpoint. Intake reads the service's
`AGENTS.md` and finds the vitest command. The interview lands on
criteria (R1: "429 with `Retry-After` after N requests/min per caller",
R2: "callers under the limit unaffected"), a verify command
(`pnpm vitest run test/rate-limit.test.ts`), scope globs
(`src/middleware/**`, `test/**`), and a *yes* on the security question —
which also disables auto-fix. The red check confirms the new test
fails, the implementer brings it green, the orchestrator re-runs the
suite and curls the endpoint itself, and the reviewer — briefed with the
security addendum — returns a matrix showing R1/R2 pass with line-level
evidence before you commit.

**Scope tripwire.** If the interview reveals the task won't fit one PR,
the run stops there and offers to split it into separate `/cm-task` runs
in dependency order, rather than soldiering on into a sprawling diff.

## Iteration rounds — after the preview

Sooner or later the PM previews the work and wants changes — possibly
long after the original session is gone. You open a fresh session and
run `/cm-task <pr-url>` (rounds are always explicit — never
auto-detected). Each round:

- **Brief recovery.** The contract is read back out of the PR body — no
  repo state files, no dependence on the dead session.
- **Triage.** Each feedback item is classified: a *tweak* inside the
  existing criteria, an *amendment* that gets the next R-number, or *new
  scope* — which trips the same one-PR tripwire and becomes a separate
  run. This is the check that stops "small ask #4" from swallowing the PR.
- **Append-only amendments.** Round N is added to the brief; the
  original sections are never rewritten, so the trail of what was agreed
  vs what changed survives.
- **Red-first, then regression guard.** New behavior gets a failing
  check before code, and after the round is green the *original* verify
  command is re-run — round 3 must not break round 0's acceptance.
- **Delta review.** A fresh reviewer audits only the diff since the last
  reviewed commit. A cosmetic-only round can skip review — your explicit
  call in a modal, never silently.
- **Modal-first fixes.** No auto-fix in rounds: the PR has an audience
  now, so every finding comes to you before anything changes.
- **One commit per round**, the PR-body brief updated, push on your OK.

The retro runs once, when you call a round final — not as a per-round nag.

## The model story

Three model choices, all explicit. Intake, interview, and orchestration
run on whatever model your session is using — pick that before you
invoke. The **implementer** model is asked in the interview (default:
same as the session). The **reviewer** model is a separate question,
defaulting to **opus**: review is the safety net, so it never silently
inherits a cheaper session model — downgrading it is a choice you make
in the modal, not an accident.

## The micro-retro — why it always asks

The first shot ends, every single time even on a small fix, by asking
for one sentence worth landing in the repo's `CLAUDE.md` or `AGENTS.md`.
"None" is a legitimate answer, but the question is never skipped. If you
accept the lesson, the edit lands on the same branch as the work.

This is the compounding loop. Whatever bit you during this task —
a convention the agent missed, a gotcha in the test setup — becomes a
rule the next agent reads before it starts. The repo gets smarter about
itself one task at a time.

## What it does NOT do

- **Discipline, not enforcement.** Nothing here mechanically prevents
  skipping a step. There are no hooks blocking you, no state machine. If a
  step feels skippable, that is exactly the failure mode the skill exists
  to counter — but the guarantee lives in the full harness, not here.
- **No state files in the repo.** The working brief lives in the session
  scratchpad; durability lives in the PR body. Iteration rounds resume
  from there — mid-first-shot, a dead session still means re-briefing.
- **No multi-PR orchestration.** One task, one branch, one PR. Bigger
  work splits into separate runs.
- **Never pushes or opens PRs on its own.** Commits are part of the
  harness and local; pushing and PR creation always wait for your
  explicit OK.

## Install

Ships with the `cm-skills` plugin:

```bash
claude plugin marketplace add chartmetric/claude-plugins
claude plugin install cm-skills@chartmetric-tools
```

It uses the Asana and Slack MCP connectors to read tickets and threads
from URLs — without them, the URL entry points degrade to free-text
intake. It pairs with PR-creation and Asana-task skills when installed
(`ship-pr` from this plugin, `slack-to-asana` from cm-comms, or personal
`/cm-pr` / `/cm-asana-task`); without them the run still completes and
does those hand-offs via the MCP tools or manually.

## FAQ

**Why did it refuse to start?** Three common reasons: your working tree
has pre-existing uncommitted changes (any dirt — the reviewer would
attribute it to this task), the verify command is already green (it can't prove work that doesn't exist yet — fix the verifier),
or the interview revealed the task needs more than one PR (it offered a
split).

**Can I skip the interview?** No — that's the point. A ticket is
enrichment, not a spec, and the confirmed brief is the contract the whole
run is measured against. You can answer fast when a ticket is unusually
clear, but the modals still appear.

**Why did it fix a review finding without asking?** Because all four
auto-fix gates held: the defect reproduced red-first, the fix stayed in
scope, it was mechanical rather than a design change, and the task
wasn't security-flagged. Everything else — and *everything* in iteration
rounds — comes to you in a modal first. The red-first gate exists
because reviewers have confidently flagged "defects" that turned out to
be the user's own test data.

**What if the reviewer blocks twice?** After two fix-and-re-review cycles
with findings still standing (per round, in iteration), the run stops
and hands you the findings. It does not grind indefinitely or quietly
ship past them.

**The implementer agent died mid-task — now what?** If its transcript
survives, it's resumed by message, context intact. If not, a fresh agent
picks up from the brief file plus the git diff of whatever landed.
That's why the brief is written to a file before any agent exists.

**How is this different from just asking Claude to do the task?** Plain
Claude will happily write code and self-attest that it works. `cm-task`
forces a failing check first, refuses to take the implementer's word for
green, holds the work inside a scope you agreed to, and puts the diff in
front of a reviewer with no memory of the conversation that produced
it — one that must show file:line evidence per criterion, not a
thumbs-up. That fresh context is what catches the plausible-but-wrong
work.

**Where do lessons and leftover findings go?** Lessons land in the repo's
`CLAUDE.md`/`AGENTS.md` on the same branch. Surviving should-fix and
backlog items are filed to Asana or noted in the PR body —
your call in the retro modal.

**Is any of this enforced?** No. It's discipline you carry, backed by a
skill that makes the disciplined path the default one. If you need
mechanical guarantees, that's what the harness tiers are for.
