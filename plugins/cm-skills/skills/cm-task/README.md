# cm-task

## The problem it solves

Hand an AI agent a ticket and it will produce something that looks
right. The tests it writes pass because it wrote them to pass. The scope
quietly widens into files nobody asked it to touch. Three days later the
work fails in review, or worse, in production, and the reasoning that
produced it is gone.

`cm-task` is a Claude Code skill that wraps a single task in the same
discipline the Chartmetric harness uses on full projects: interview you
to a confirmed brief, prove a verifier fails *before* any code exists,
implement test-first, then hand the diff to a fresh-context reviewer that
never saw the conversation. One task, one branch, one PR, one session.

## When to use it — and when not to

There are three tiers. Match the tool to the work or people will hate it.

| Work | Use | Why |
|------|-----|-----|
| Trivial 15-minute fix (typo, config bump, one-line guard) | Plain Claude Code | `cm-task` would be pure ceremony |
| One task with real acceptance criteria (a feature, a bug with a repro, an endpoint change) | **`/cm-task`** | Worth a brief, a red check, and a review |
| Multi-phase project or a new repo | [harness-template](https://github.com/chartmetric/harness-template) | Needs enforced state, phases, resume |

Be honest with yourself about the first row. If you run `cm-task` on a
one-line change, you will sit through two question modals and a review
subagent for something you could have typed faster by hand, and you will
never open the skill again. Save it for work where being wrong is
expensive.

## Entry points

- `/cm-task <asana-url>` — pulls the task as enrichment for the interview.
- `/cm-task <slack-thread-url>` — reads the thread; after you confirm the
  brief it offers to create the Asana task for you (Slack-first is the
  team's normal order — issue in Slack, task after).
- `/cm-task <free text>` — describe the task inline.
- `/cm-task` — bare; it interviews you from nothing.

Whatever a ticket says is treated as *enrichment, never a complete
spec* — tickets are chronically under-specified, so the interview always
runs.

## What the run feels like from your seat

Eight steps happen; you are touched about three times. Everything between
your touches is autonomous but visible in the transcript.

1. **Intake (silent).** It reads your repo's `CLAUDE.md`/`AGENTS.md`,
   skims the code area you'll touch, and discovers the real test commands
   before asking you anything.
2. **Interview — touch 1 and 2.** Two `AskUserQuestion` modals. First:
   confirm or edit the drafted acceptance criteria. Second: the verify
   command, the scope globs, whether the task is security-sensitive, and
   which model reviews it. Every option offered is a real value it
   discovered, not a placeholder.
3. **Brief (visible).** A compact contract — goal, acceptance list,
   verify command, gates, scope — written to the scratchpad and shown to
   you. It refers back to this; it does not re-litigate it.
4. **Red check (visible).** It creates the branch, then runs your verify
   command and confirms it **fails**. This is the load-bearing rule: a
   verifier that is green before any work exists cannot prove the work —
   that false positive has shipped broken code before. If it passes
   already, the run stops and asks you to fix the verifier.
5. **Implement (visible).** Test-first, inside the scope globs, looping
   until the verifier and your repo's gates are green.
6. **Review (visible).** One fresh-context subagent audits the diff and
   returns findings. Blocking findings get fixed and re-reviewed, up to
   twice.
7. **Micro-retro — touch 3-ish.** One modal asking for the single lesson
   worth keeping (see below).
8. **Ship — final touch.** It commits and offers to open the PR. It never
   pushes or opens a PR without your explicit OK.

**Example.** You run `/cm-task` on a ticket to rate-limit the
`POST /v1/events` ingestion endpoint. Intake reads the service's
`AGENTS.md` and finds the vitest command. The interview lands on
acceptance criteria ("429 with `Retry-After` after N requests/min per
caller; existing callers under the limit unaffected"), a verify command
(`pnpm vitest run test/rate-limit.test.ts`), scope globs
(`src/middleware/**`, `test/**`), and a *yes* on the security question
because it touches per-caller behavior. The red check confirms the new
test fails, TDD brings it green, and the reviewer — briefed with the
security addendum — checks the limiter for bypasses before you commit.

**Scope tripwire.** If the interview reveals the task won't fit one PR,
the run stops there and offers to split it into separate `/cm-task` runs
in dependency order, rather than soldiering on into a sprawling diff.

## The model story

The driver roles — intake, interview, implementation — run on whatever
model your Claude Code session is using. Pick that before you invoke
(Fable or Opus are typical). The **reviewer** model is a separate choice,
asked during the interview, defaulting to **opus**. Review is the safety
net, so it never silently inherits a cheaper session model; downgrading
it is an explicit choice you make in the modal, not an accident.

## The micro-retro — why it always asks

Step 7 asks, every single time even on a one-line fix, for one sentence
worth landing in the repo's `CLAUDE.md` or `AGENTS.md`. "None" is a
legitimate answer, but the question is never skipped. If you accept the
lesson, the edit lands on the same branch as the work.

This is the compounding loop. Whatever bit you during this task —
a convention the agent missed, a gotcha in the test setup — becomes a
rule the next agent reads before it starts. The repo gets smarter about
itself one task at a time.

## What it does NOT do

- **Discipline, not enforcement.** Nothing here mechanically prevents
  skipping a step. There are no hooks blocking you, no state machine. If a
  step feels skippable, that is exactly the failure mode the skill exists
  to counter — but the guarantee lives in the full harness, not here.
- **No state files, no resume.** Nothing is written into the repo to track
  progress. If the session dies mid-task, you re-brief from scratch. At
  one-PR scope that cost is acceptable.
- **No spawned writer.** You (the driver session) write the code with the
  human watching. The only thing it spawns is the reviewer.
- **Never pushes or opens PRs on its own.** Committing is local; pushing
  and PR creation always wait for your explicit OK.

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
is dirty and out of the declared scope, the verify command is already
green (it can't prove work that doesn't exist yet — fix the verifier),
or the interview revealed the task needs more than one PR (it offered a
split).

**Can I skip the interview?** No — that's the point. A ticket is
enrichment, not a spec, and the confirmed brief is the contract the whole
run is measured against. You can answer fast when a ticket is unusually
clear, but the modals still appear.

**What if the reviewer blocks twice?** After two fix-and-re-review cycles
with findings still standing, the run stops and hands you the findings.
It does not grind indefinitely or quietly ship past them.

**How is this different from just asking Claude to do the task?** Plain
Claude will happily write code and self-attest that it works. `cm-task`
forces a failing check first, holds the work inside a scope you agreed to,
and puts the diff in front of a reviewer with no memory of the
conversation that produced it. That fresh context is what catches the
plausible-but-wrong work.

**Where do lessons and leftover findings go?** Lessons land in the repo's
`CLAUDE.md`/`AGENTS.md` on the same branch. Surviving should-fix and
backlog items are filed to Asana or noted in the PR body —
your call in the retro modal.

**Is any of this enforced?** No. It's discipline you carry, backed by a
skill that makes the disciplined path the default one. If you need
mechanical guarantees, that's what the harness tiers are for.
