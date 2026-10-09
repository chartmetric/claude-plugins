# Recovering a stuck Replit ↔ GitHub sync

Use this when a repl's Git pane or `git pull` stops working and the repl and GitHub have drifted
apart. It covers two problems, which usually show up together:

1. **The repl can't reach GitHub.** Fetches fail with a credentials-looking error.
2. **The repl and GitHub have diverged.** While sync was broken, the Replit Agent kept committing in
   the repl and PRs kept merging on GitHub, so `--ff-only` refuses.

Fix them in that order. You can't move commits in either direction until the repl's shell can
authenticate, unless you fall back to the bundle transport in `replit-git-transport.md`.

With an SSH alias, run the repl-side commands with `ssh -n <alias> '...'`. Without one, hand each
block to the user to paste into the repl's Shell tab and ask for the output. Every repl-side step
below is written so it can be pasted as is. Blocks that change state run in a `( set -e ... )`
subshell, so a failed check stops the rest of the block without closing the user's shell.
A top-level `set -e` would close the Shell tab. Never ask the user to paste raw env values or
credentials; the commands below redact what they print.

`<date>` below is the day's `yyyymmdd`. `<clone>` is your local clone of the repo; clone it first if
you don't have one.

## Contents

- Triage the fetch error
- "Repository not found": the Replit GitHub App can't see the repo
- Diverged: the sync-branch relay
- Resolving the conflicts
- Verify with the repo's own build
- Landing the result
- Done when

## Triage the fetch error

In the repl's own Shell tab, Replit's `replit-git-askpass` helper does answer. A failing fetch there
is a real access problem, not the headless-SSH blindness described in `replit-git-transport.md`.

```bash
cd /home/runner/workspace
git status -sb
git remote get-url origin | sed -E 's#//[^@/]*@#//<redacted>@#'
GIT_TERMINAL_PROMPT=0 git fetch origin 2>&1 | tail -5
```

If Replit's UI sync hangs or fails without an error, check for a stale lock first. If the fetch above
prints an error, start from this table.

| Error | Cause | Fix |
|-------|-------|-----|
| `unable to read askpass response` / `could not read Username` in the Shell tab | The Replit↔GitHub connection isn't answering | Git pane → gear → reconnect GitHub, then open a new Shell tab (`GIT_ASKPASS` is set when a shell starts) |
| Same error over SSH | Expected: the helper only answers inside Replit's runtime | `replit-git-transport.md` (askpass shim or bundles) |
| `Authentication failed` / `Invalid username or token`, or the remote URL shows `<redacted>@` | A stale token is in the remote URL or a `store` credential helper | `git remote set-url origin https://github.com/<org>/<repo>.git`; check `git config --show-origin --get-all credential.helper` and remove a `store` helper and `~/.git-credentials` |
| `Repository not found`, even though the connected GitHub user has access | The Replit GitHub App's org installation doesn't include this repo | Next section |
| `Unable to create '.git/index.lock'` | Stale lock | "Stale git lock" in `replit-git-transport.md` |
| Fetch succeeds, then `Not possible to fast-forward` | Diverged | "Diverged: the sync-branch relay" below |

Check the remote URL's spelling against GitHub's repo name before anything else. On a private repo,
GitHub answers a typo with the same "not found" it gives for no access.

## "Repository not found": the Replit GitHub App can't see the repo

The Git pane's **GitHub (App)** connection authenticates as Replit's GitHub App acting for the user.
That token reaches only repos that both the user and the app's installation on the org can see. If
the org installed Replit with **Only select repositories** and this repo isn't on the list, GitHub
hides the repo from Replit, whatever the user's own role on it. A repo created or moved into the org
after the installation was set up starts out off the list.

Confirm both halves:

```bash
# The user's own access (expect write/maintain/admin)
gh api repos/<org>/<repo>/collaborators/<github-login>/permission -q '"\(.permission) / \(.role_name)"'

# The org's Replit installations (needs an org owner's gh auth)
gh api 'orgs/<org>/installations?per_page=100' \
  -q '.installations[] | select(.app_slug|test("replit")) | "\(.app_slug) id=\(.id) repos=\(.repository_selection)"'
```

The Git pane's "Commit author" list shows which GitHub account is connected.

`repos=all` means the app isn't the problem; go back to the triage table. With `repos=selected`, the
repo list is only on the web page `https://github.com/organizations/<org>/settings/installations/<id>`.
The REST listing needs a GitHub App user token, so `gh`'s OAuth token gets a 403. Read the page in
the browser and check every `replit*` installation, since there may be more than one, such as
`replit` and `replit-nexus`.

**Fix:** on that page, an org owner adds the repo under Repository access → Select repositories →
Save. The user does this, or you do it through browser automation once they say go ahead, since it's
an org settings change. If neither of you is an org owner, the installations call above returns 403.
In that case, list the owners (`gh api 'orgs/<org>/members?role=admin' -q '.[].login'`) and give the
user the page link and the repo name to send one of them. Then open a new Shell tab and fetch again.

If the repo is already on the list, check two other causes:

- **Wrong connected account.** The Git pane's "Commit author" list shows the GitHub account Replit
  is using. It can differ from the one that has access.
- **SAML SSO.** If the org enforces SSO, the user's Replit authorization must be SSO-authorized:
  GitHub → Settings → Applications → Authorized GitHub Apps → Replit.

## Diverged: the sync-branch relay

Once the repl can fetch and push, don't merge in the repl. Relay the repl's commits through a
temporary GitHub branch, merge and verify on your machine, and leave the repl one job: take a
fast-forward. Why:

- The repl's dev server serves the working tree, so conflict markers break Preview the moment the
  merge stops.
- If the repl has an auto-commit watcher (see SKILL.md), it publishes whatever is in the tree,
  conflict markers included.
- Your machine has `gh`, the browser, prod `curl`, and a full build. The repl has none of the context
  needed to judge a conflict.

Merge rather than rebase. Replit checkpoints and rollback point at the repl's commit SHAs, and a
rebase rewrites every one of them.

If the repl can't push but you have SSH, use the outbound bundle in `replit-git-transport.md` for
steps 1–2 instead.

**1. Freeze the repl.** Ask the user not to apply pending agent tasks ("Apply changes") or start new
agent work until the sync lands. Any new repl commit invalidates the merge you're about to build.

**2. Push the repl's HEAD to a sync branch** (repl side):

```bash
cd /home/runner/workspace
git merge --abort 2>/dev/null           # if a merge was attempted in the repl, clear its markers
( set -e
  test -z "$(git status --porcelain)" || { echo "STOP: tree is dirty"; git status -s; exit 1; }
  git log -1 --format='HEAD %h, parents: %p | %s'
  GIT_TERMINAL_PROMPT=0 git push origin HEAD:refs/heads/replit-sync-<date>
  git rev-parse --short HEAD )          # note it: the repl must still be here at landing time
```

This only creates a branch; `main` isn't touched.

If the printed HEAD has two parents and its subject is a merge of `origin/main`, the merge was
already committed in the repl. The watcher or a Git pane click can do this, sometimes with conflict
markers in it. Don't relay that commit. Check for markers with
`git grep -n -E '^(<<<<<<<|>>>>>>>) ' HEAD`. Then push the repl's own side instead
(`git push origin HEAD^1:refs/heads/replit-sync-<date>`) and note `HEAD^1`'s SHA. At landing time the
repl can't fast-forward past its own merge, so the user resets instead:
`git reset --hard origin/replit-sync-<date>`. Do that only after confirming
`git diff HEAD^1 HEAD --stat` shows nothing but `origin/main`'s files.

**3. Merge locally** in a worktree. Fetch the branch with an explicit refspec, because a
single-branch clone's default refspec only fetches `main`:

```bash
git -C <clone> fetch origin main replit-sync-<date>:refs/remotes/origin/replit-sync-<date>
git -C <clone> worktree add <wt> -b replit-sync-<date> origin/replit-sync-<date>
git -C <wt> rev-list --left-right --count origin/main...HEAD   # GitHub-only / repl-only
git -C <wt> log --format='%h %ad %an | %s' --date=short --no-merges origin/main..HEAD | grep -v 'Published your App'
git -C <wt> merge origin/main --no-commit
```

## Resolving the conflicts

For each conflicted file, find out what each side meant before choosing:

- `git log --oneline --merge -- <file>` lists the commits on both sides that touched it, and
  `git show <sha>` shows what each one was for. Replit Agent commits carry a `Replit-Task-Id`
  trailer. PRs carry their reasoning in the PR body (`gh pr view <n>`).
- Check what production serves (`curl` the live page, or the header that tells you which layer
  answered). The repl is usually what's published, so its side is usually what's live.

Patterns that come up:

- **The same change made twice.** Someone asks the Replit Agent for a change while a PR makes the same
  change on GitHub. Keep the live wording, drop the duplicate, and say so in the merge message.
- **Opposite decisions.** One side deliberately removed something the other side updated. The later
  commit isn't automatically right; it may not have known about the earlier one. Look for guard
  scripts or tests that encode the decision, and for whoever actually owns the behavior in prod. If
  intent is still unclear, ask the user rather than guess.

Mechanics:

- Resolve hunk by hunk. `git checkout --ours/--theirs <file>` replaces the whole file, which silently
  drops the other side's non-conflicting hunks in that file. To start over on a file, use
  `git checkout -m -- <file>`, which restores its conflict markers. To keep one side of every hunk in
  a file while keeping auto-merged changes elsewhere in it:

  ```bash
  # keep "ours" (the repl side) in every conflict hunk
  awk '/^<<<<<<< /{s=1;next} /^=======$/&&s==1{s=2;next} /^>>>>>>> /{s=0;next} s!=2' f > f.tmp && mv f.tmp f
  ```

- After resolving, grep for identifiers the dropped side introduced (keys, components, props). An
  auto-merged line that uses something whose definition you just dropped is a bug neither side had
  on its own, and only the build catches it.
- Stage each file as you resolve it (`git add <file>`). You're done when
  `git diff --name-only --diff-filter=U` prints nothing and
  `git grep -n -E '^(<<<<<<<|>>>>>>>) '` finds no markers.
- In zsh, put file lists in an array (`FILES=(a b)` then `"${FILES[@]}"`). A space-separated string
  isn't word-split and becomes one path.

## Verify with the repo's own build

Before pushing, run the repo's typecheck and build. Its guard scripts often encode the decisions a
conflict touched. Find them in the root and app `package.json` scripts (or the repo's equivalent). A
merge that typechecks but fails a `check:*` guard is a wrong resolution.

### Building a Replit pnpm monorepo locally

Replit's pnpm workspace template (apps under `artifacts/<app>`) often can't build on a Mac out of
the box:

- `pnpm-workspace.yaml` `overrides` set every non-linux-x64 native binary to `"-"` (rollup, esbuild,
  lightningcss, `@tailwindcss/oxide`, …), so the build fails with
  `Cannot find module @rollup/rollup-darwin-arm64`.
- pnpm 11 fails `install` with `ERR_PNPM_IGNORED_BUILDS` and re-runs that install before every
  `pnpm run`. It reads `pnpm_config_*` env vars; `npm_config_*` is ignored.

Make a temporary local-only exception, build, and restore:

```bash
cd <wt>
export pnpm_config_verify_deps_before_run=false pnpm_config_strict_dep_builds=false
sed -i '' '/darwin-arm64": "-"/d' pnpm-workspace.yaml
pnpm install --no-frozen-lockfile
pnpm run typecheck
(cd artifacts/<app> && pnpm run build)        # the app's build usually chains its check:* guards
git checkout -- pnpm-workspace.yaml pnpm-lock.yaml
git status --porcelain | grep -v '^[MADR] '   # expect nothing unstaged or untracked
```

`git checkout -- <file>` during a merge restores the index copy, which is the merged version, so
this undoes only your local exception.

## Landing the result

Commit the merge with a message that names each conflict and which side won and why, then push the
sync branch:

```bash
git -C <wt> commit                                    # message: per-file resolution + reasons
git -C <wt> rev-list --left-right --count origin/main...HEAD   # expect 0 behind
git -C <wt> push origin HEAD:refs/heads/replit-sync-<date>
```

Before handing over the landing block, check branch protection
(`gh api repos/<org>/<repo>/branches/main -q .protected`) and the rulesets
(`gh api repos/<org>/<repo>/rulesets`). Pushing `main` is the user's call either way.

**`main` unprotected:** the repl fast-forwards onto the sync branch and pushes it (repl side):

```bash
cd /home/runner/workspace
( set -e
  test -z "$(git status --porcelain)" || { echo "STOP: tree is dirty"; exit 1; }
  test "$(git rev-parse --short HEAD)" = "<sha from step 2>" || { echo "STOP: repl moved, rebuild the merge"; exit 1; }
  GIT_TERMINAL_PROMPT=0 git fetch origin
  git merge --ff-only origin/replit-sync-<date>
  GIT_TERMINAL_PROMPT=0 git push origin HEAD:main
  git rev-list --left-right --count origin/main...HEAD )   # expect: 0	0
```

Delete the sync branch only after that block reports `0	0`:
`GIT_TERMINAL_PROMPT=0 git push origin --delete replit-sync-<date>`.

**`main` protected:** open a PR from the sync branch and merge it with a merge commit, not a squash
or rebase merge. A squash or rebase gives the repl's commits new SHAs on `main`, so the repl can't
fast-forward onto it. Once merged, the repl runs the same block with `origin/main` in place of
`origin/replit-sync-<date>`, minus the push.

Then the user clicks **Republish**, because a git sync doesn't redeploy a published repl. Once the
Git pane fetches cleanly, Replit's UI can handle future syncs again.

Finish by telling the user how each conflict was resolved, plus any follow-up the merge can't do.
For example, a PR's intent may depend on something outside the repo, like edge redirects or DNS.
Remove your local worktree once the repl is level.

## Done when

- The repl's `git status --porcelain` is empty.
- `git rev-list --left-right --count origin/main...HEAD` in the repl prints `0	0`.
- The sync branch is deleted, and the user has republished, or knows they need to.
