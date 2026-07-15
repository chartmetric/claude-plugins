---
name: cm-takehome-review
description: Reviews take-home assignment PRs from job candidates and produces local-only markdown scorecards plus one side-by-side comparison doc. Discovers candidate PRs across locally-cloned `~/code/chartmetric/takehome*` repos, runs each candidate's branch in an isolated git worktree to verify tests, scores against a rubric derived from the JD + hiring criteria + the assignment README, and never posts anything to GitHub. Triggers - /cm-takehome-review, "review the take-homes", "score the candidate assignments".
author: hyosik@chartmetric.com
---

# cm-takehome-review — score candidate take-home assignments

Goal: turn "we have N candidates who submitted take-home PRs" into a per-candidate scorecard and one consolidated comparison doc, generated consistently against the same rubric. Humans still review live with the candidate — this is a second, independent agent read to surface signal before the call.

The skill is **local-only and read-only toward GitHub**. It never posts a comment, never approves, never requests changes. All output is markdown files on disk. The hire decision stays with humans — the comparison doc deliberately stops short of a hire/no-hire verdict.

## What it evaluates (rubric)

Four dimensions, scored 1–5, each with a one-line justification. The scale anchors:

| Score | Meaning |
|-------|---------|
| 5 | Excellent — nothing a senior would change |
| 4 | Strong — minor nits only |
| 3 | Adequate — works, but notable gaps |
| 2 | Weak — partially solves or introduces concerns |
| 1 | Poor — wrong, broken, or misses the point |

**Dimensions:**

1. **Issue understanding** — Did the candidate identify the *real root cause*, not just a symptom? Did they reason from the right source of truth (the assignment README states what "correct" means)? Hard-coding a fix for the one reported case scores low even if tests pass.
2. **Correctness** — Does the fix actually resolve the bug, and does the test suite pass? This dimension is anchored by the **worktree test run** (see Step 3c) — a green suite is necessary but not sufficient (a green suite from a hacked fix is still capped at 3).
3. **Well-targeted fix** — Did the change touch only the relevant code? The assignments explicitly warn that sort/query helpers are *shared* across the app. A clean, localized fix that keeps shared helpers generic and doesn't break sibling behavior scores high. Tweaking a shared util/component in a way that risks other call sites scores low.
4. **Communication** — Quality of the PR description against `pr_description_template.md`: clear root-cause explanation, sound implementation rationale, and the **customer-facing** + **team-facing** messages. This role is Client Success Engineer — communication is load-bearing, not a footnote.

Derive "what good looks like" for each assignment from that repo's `README.md` ("What we're evaluating" section) and `pr_description_template.md`. Reason out the actual root cause from the code yourself — there is no reference solution to diff against.

### Role context (for grounding the rubric)

Position: **Client Success Engineer (Remote)**. The role investigates and resolves client-reported issues across APIs, dashboards, and data pipelines, reads and modifies production code, uses AI coding tools, and communicates with clients professionally. Weight communication and "well-targeted, low-blast-radius fix" accordingly — this person ships fixes into production-adjacent code and talks to customers about them.

### Hiring criteria (from the hiring manager)

- Did the candidate understand the issue correctly?
- Did the candidate resolve the issue correctly?
- Was the fix efficient and well-targeted? (Well-targeted, touched only relevant code **vs.** tried to tweak a shared component / util in a risky way.)

## Step 1 — Discover candidate PRs

Take-home repos are cloned locally under `~/code/chartmetric/` with names starting `takehome`. Find them — require a `.git` dir so the skill's own output folder (`takehome-reviews/`, see Step 3) is never mistaken for a repo:

```bash
for d in ~/code/chartmetric/takehome*/; do [ -d "$d/.git" ] && echo "${d%/}"; done
```

If none found, report `No takehome repos cloned under ~/code/chartmetric/. Clone them first.` and exit.

For each repo, get its `owner/name` from the origin remote and list **open** PRs:

```bash
# inside each repo dir:
SLUG=$(gh repo view --json nameWithOwner --jq .nameWithOwner)   # e.g. chartmetric/takehome-playlist-position
gh pr list --repo "$SLUG" --state open \
  --json number,title,author,headRefName,headRepositoryOwner,additions,deletions,changedFiles \
  --jq '.[] | select(.author.login | test("\\[bot\\]|devin-ai-integration") | not)'
```

**Filters:**
- **Open only.** Merged/closed PRs (e.g. the bot template-fix PRs) are out of scope.
- **Exclude bots.** Drop authors matching `[bot]` or `devin-ai-integration` — those are maintenance PRs on the base repo, not candidate submissions.

**Group by candidate** (`author.login`). A candidate may have PRs across multiple repos (one per assignment) and **may have more than one PR on the same repo**. When multiple PRs from the same author target the same repo, treat the one that actually fixes the assignment as the graded submission and treat the rest as **extra work** (see Step 3 / Step 4). If it's ambiguous which is the graded one, pick the PR whose diff touches the files named in the README's "Project layout" and note the ambiguity.

## Step 2 — Show the plan and confirm

Print the discovered matrix and ask once:

```
🎓 Take-home review — found <M> candidates across <N> assignments:

  @<candidateA>
    • <assignment-repo-1> #<num>   (+X -Y, N files)
    • <assignment-repo-2> #<num>   (+X -Y, N files)
  @<candidateB>
    • <assignment-repo-1> #<num>   (+X -Y, N files)
    • <assignment-repo-2> #<num>   (+X -Y, N files)   ← graded
    • <assignment-repo-2> #<num>   (+X -Y, N files)   ← extra (noted, not scored)

This will check out each PR in a throwaway worktree and run its tests. Nothing is posted to GitHub.
Proceed? [y / n / specific candidates e.g. "<candidateA>"]
```

(The matrix is built dynamically from Step 1 — PR numbers and repos shown above are placeholders.)

- `y` / ENTER → review all
- `n` → exit
- A name or comma list → review only those candidates
- Invalid → re-ask once, then exit

## Step 3 — Per-assignment evaluation

Decide an output directory once, at the start of the run:

```bash
OUTDIR=~/code/chartmetric/takehome-reviews/$(date +%Y-%m-%d)
mkdir -p "$OUTDIR"
```

Then, for each graded PR, run these substeps.

### 3a. Fetch PR data and assignment context (read-only)

```bash
gh pr view <num> --repo <slug> --json number,title,body,author,headRefName,additions,deletions,changedFiles,files
gh pr diff <num> --repo <slug>
```

Read the assignment's own context from the **local clone** (do not fetch from origin for these — they're committed in the base repo):
- `<repo>/README.md` — the assignment + "What we're evaluating".
- `<repo>/pr_description_template.md` — the communication bar.
- `<repo>/CLAUDE.md` if present.

The PR `body` is the candidate's filled-in template — that is the artifact you score for **Communication**.

### 3b. Hard rule — protect the local working tree

The local clones may be in any state. Do **not** disturb them.
- No `git checkout`, `git pull`, `git reset`, `git stash`, `git merge` on the repo's main working tree.
- No writes to any tracked file in the clone.
- The only mutations allowed are: `git fetch` of the PR head ref, and `git worktree add/remove` into a **throwaway temp dir outside the repo**.

### 3c. Run the candidate's branch in an isolated worktree

PRs come from candidate **forks**, so fetch the PR head by its pull ref (works for forks) and check it out detached in a temp worktree — never a branch in the main tree:

```bash
cd ~/code/chartmetric/<repo>
WT=$(mktemp -d "/tmp/takehome-<repo>-pr<num>.XXXX")
git fetch origin "pull/<num>/head"
git worktree add --detach "$WT" FETCH_HEAD

# run in the worktree; capture results, don't fail the skill on a red suite
( cd "$WT" && npm install && npm test ) ; TEST_EXIT=$?

git worktree remove --force "$WT"
```

Record: did `npm install` succeed, did `npm test` pass (`TEST_EXIT == 0`), and capture the failing test names if not. This is the hard evidence behind the **Correctness** score. If `npm install` itself fails, note `_could not build candidate branch_` and score Correctness from static reading, flagged as unverified.

Always `git worktree remove --force` even if tests fail. Leaving stray worktrees pollutes the clone.

### 3d. Score and write the per-candidate scorecard

Score all four rubric dimensions 1–5 with a one-line justification each, grounded in: the diff, the worktree test result, the README's evaluation criteria, and the PR body. Be direct and specific — cite file paths and the actual root cause. Don't restate the diff.

**Refer to candidates with they/them.** A GitHub login does not tell you a candidate's gender — never infer it. Use "they/them/their" throughout every report.

For a candidate who did **extra PRs** (out of scope, e.g. adding skills), add a short **Additional work** note: what they did and the initiative signal it shows — but **do not fold it into the four scores**. The scores reflect the graded assignment only, so candidates stay comparable on the same task.

Write one file per candidate, `$OUTDIR/<candidate-login>.md`, covering every assignment that candidate submitted:

```markdown
# Take-home review — @<login>

_Generated <date> by cm-takehome-review. Local-only, not posted. Humans review live._

## Assignment: <repo>  (PR #<num>)
<PR url>

**Tests:** ✅ passing / ❌ failing (`<failing test names>`) / ⚠️ could not build

| Dimension | Score | Justification |
|-----------|:-----:|---------------|
| Issue understanding | N/5 | … |
| Correctness | N/5 | … |
| Well-targeted fix | N/5 | … |
| Communication | N/5 | … |

**Root cause (as the candidate found it / as it actually is):** …

**Notes:** … (specific, file-referenced observations — what's strong, what's risky)

### Additional work (not scored)
… only if the candidate submitted extra PRs …

---
## Assignment: <next repo> …
```

### 3e. Render to terminal

Print the same scorecard to the terminal as you write each file, with a separator:

```
═══════════════════════════════════════════════════════
@<login> — <repo> #<num>   Tests: <pass/fail>
═══════════════════════════════════════════════════════
<scorecard>
```

## Step 4 — Consolidated comparison doc

After all candidates are scored, write `$OUTDIR/COMPARISON.md`: a side-by-side, **no ranking and no hire/no-hire verdict**. Present the data; let humans judge.

```markdown
# Take-home comparison

_Generated <date> by cm-takehome-review. Side-by-side only — no ranking, no hire recommendation. Humans decide._

## <Assignment A name>

| Dimension | @cand1 | @cand2 |
|-----------|:------:|:------:|
| Issue understanding | N | N |
| Correctness | N | N |
| Well-targeted fix | N | N |
| Communication | N | N |
| Tests | ✅/❌ | ✅/❌ |

**One-line read per candidate:** neutral, factual contrast (e.g. "cand1 fixed in the shared util with a guard; cand2 localized to the column config"). No "better/worse" language.

## <Assignment B name>
… same shape …

## Cross-assignment notes
Factual observations only — consistency across assignments, extra work submitted, anything a human interviewer should probe live. No verdict.
```

Do not sum or average scores into a single "winner" number. Different dimensions matter differently per the live panel; collapsing them hides signal.

## Output contract

End with a one-line summary and the paths written:

```
✅ Done. Scored 2 candidates across 2 assignments. 0 posted (local-only).
   Reports: ~/code/chartmetric/takehome-reviews/<date>/
     @nerdyfitzy.md, @ella-yschoi.md, COMPARISON.md
```

## Edge cases

- **No PRs / no repos:** report and exit, don't fabricate.
- **Multiple PRs, same candidate + repo:** grade the assignment-fix PR; note the rest as extra work (don't score).
- **`npm install` / `npm test` infra failure** (not the candidate's fault — e.g. network): score Correctness from static reading, flag `unverified`.
- **PR from a fork that won't fetch** by `pull/<num>/head`: fall back to the PR's `headRepositoryOwner` + `headRefName` via `gh pr checkout` **into a worktree only**, never the main tree; if that also fails, static review flagged unverified.
- **Candidate edited the test or seed data** (README says not to): call it out explicitly — green tests mean less if they moved the goalposts.
- **Stray worktree from a prior aborted run:** `git worktree prune` before adding a new one.
- **Massive diff (>200kB):** truncate at the file boundary nearest 200kB, note `_diff truncated_`, but still run the full suite in the worktree.

## Don'ts

- Don't post, comment, approve, or request changes on any PR. Ever. This skill is local-only.
- Don't mutate the local clone's working tree or main branch — worktrees in temp dirs only, always removed.
- Don't include a hire/no-hire verdict or an overall ranking in any output.
- Don't trust a green test suite alone — a hacked or test-edited fix is capped regardless.
- Don't fold extra/out-of-scope PRs into the rubric scores.
- Don't average the four dimensions into one number.

## Examples

> `/cm-takehome-review`

Finds 2 candidates across 2 take-home repos, prints the matrix, asks. User hits ENTER. For each graded PR it fetches the diff, checks the branch out in a throwaway worktree, runs `npm test`, scores 4 dimensions, and writes `@nerdyfitzy.md`, `@ella-yschoi.md`, and `COMPARISON.md` under `~/code/chartmetric/takehome-reviews/<date>/`. Nothing touches GitHub.

> `/cm-takehome-review ella`

Reviews only @ella-yschoi's submissions, including a note on her extra PR #4 (support skills) as unscored initiative signal.
