---
name: cm-conflict
description: Given a chartmetric PR going into master (or main), create a companion PR going into staging by cherry-picking every commit from the master PR onto a fresh branch off origin/staging, then opening a PR to staging. Used to satisfy the "mergable-to-staging" and "merge to staging" checks on the master PR. Trigger when the user pastes a chartmetric PR URL and says "run cm-conflict on this" / "create the staging PR for this" / "make the staging companion".
---

# cm-conflict — staging companion PR

Automates the chartmetric workflow where every PR into `master` needs a companion PR into `staging` to satisfy the `mergable-to-staging` + `merge to staging` checks before the merge bot will run.

The script `/usr/local/bin/cm-conflict` does a *merge*-based version of this from a currently checked-out branch. This skill is the **PR-URL-driven cherry-pick variant**: cleaner history, no merge commit, works without having to check out the source branch yourself.

## Inputs

A single PR URL or `owner/repo#NNNN`. Required fields it must resolve to:

- `repo` (e.g. `chartmetric/chartmetric-web-app`)
- `pr_number`
- `head_branch` (the PR's source branch)
- `base_branch` — must be `master` or `main`. If it's already `staging`, refuse: this skill is for the master→staging direction.
- ordered list of commit SHAs in the PR

Get them in one shot:
```
gh pr view <NUMBER> --repo <REPO> --json number,title,headRefName,baseRefName,state,url,commits
```

If state isn't `OPEN`, warn but proceed if the user confirms.

## Workflow

1. **Pick a workspace.** Use a git worktree off the existing chartmetric clone — never reuse the main clone (it usually has in-progress work). Path pattern: `/tmp/cm-conflict-<pr_number>-<timestamp>`.
   ```
   cd ~/code/chartmetric/<repo-name>
   git fetch origin staging <head_branch>
   TS=$(date +%Y%m%d-%H%M%S)
   NEW_BRANCH="<head_branch>-to-staging-${TS}"
   WT="/tmp/cm-conflict-<pr_number>-${TS}"
   git worktree add -b "$NEW_BRANCH" "$WT" origin/staging
   cd "$WT"
   ```

2. **Cherry-pick every commit from the PR in order.** Use the `oid`s from `gh pr view ... --json commits` in array order (oldest first). Bypass hooks because the worktree has no `node_modules`:
   ```
   git -c core.hooksPath=/dev/null cherry-pick <oid1> <oid2> ... <oidN>
   ```
   - On conflict, FIRST diagnose the *kind* of conflict before stopping:
     - **Supersession conflict** (PR's commit body says "Supersedes #NNNN" and the conflicted code on staging matches the superseded version): resolve by `git checkout --theirs <file>` for the code files. Verify with `git log origin/staging -- <file>` that staging's version came from the superseded PR or a merge that carried it.
     - **Additive translation/locale conflict**: usually safe to keep both sides — just delete the conflict markers. The PR's later commits often add the same keys, which then no-op cleanly.
     - **Real semantic divergence** (different field names with consumers on both sides): STOP and surface to the user. This usually means the master PR itself won't merge cleanly into staging either, and the fix belongs there.
   - After resolving, continue with hooks bypassed:
     ```
     git -c core.hooksPath=/dev/null cherry-pick --continue --no-edit
     ```
   - If a commit is empty after cherry-pick (already on staging), use `git cherry-pick --skip`.
   - Sanity check before pushing: `git diff HEAD origin/<head_branch> -- <conflicted_files>` should be empty (or just trivial whitespace) for the files you resolved with `--theirs`. If it isn't, you took the wrong side.

3. **Push the branch with hooks bypassed:**
   ```
   git push -u --no-verify origin "$NEW_BRANCH"
   ```
   The pre-push `make check-format` also needs `node_modules`. Bypassing is fine because CI re-runs lint and format on the PR.

4. **Open the staging PR.** Title mirrors the original PR; body links back.
   ```
   gh pr create \
     --repo <REPO> \
     --base staging \
     --head "$NEW_BRANCH" \
     --title "[staging] <original PR title>" \
     --body "Staging companion to <ORIGINAL_PR_URL>.

   Cherry-picked commits from #<pr_number> to satisfy the mergable-to-staging / merge to staging checks.

   Do not review separately — review happens on the master PR."
   ```

5. **Apply chartmetric PR defaults via REST API** (`gh pr edit` is broken on chartmetric repos — Projects-classic GraphQL deprecation):
   - Assignee: the requesting user's GitHub login (`gh api user --jq .login`)
   - Label: `PR Preview`
   ```
   NEW_PR=<number returned by gh pr create, or parse from URL>
   gh api -X POST "repos/<REPO>/issues/${NEW_PR}/assignees" -f "assignees[]=$(gh api user --jq .login)"
   gh api -X POST "repos/<REPO>/issues/${NEW_PR}/labels"    -f labels[]="PR Preview"
   ```

6. **Report back to the user** with the full staging PR URL on its own line (no markdown link, no shorthand). Example:
   ```
   Staging companion PR:
   https://github.com/<REPO>/pull/<NEW_PR>

   Cherry-picked 4 commits onto origin/staging at <new_branch>.
   ```

7. **Do NOT add the `Merge Pull Request` label automatically.** That triggers the merge bot. Mention the label name to the user and let them apply it when they're ready to merge into staging.

## Worktree cleanup

The worktree is meant to be temporary — once the PR is merged (or abandoned), clean up:
```
git worktree remove /tmp/cm-conflict-<pr_number>-<ts>
git branch -D <new_branch>   # optional, only after merge
```
Don't do this automatically; just remind the user once the PR lands.

## Refusal cases

- Base branch is already `staging` → refuse with explanation.
- Repo isn't a chartmetric repo (no `chartmetric/` prefix) → confirm with the user before proceeding; the assignee + label defaults probably don't apply.
- PR has zero commits / is a draft with no changes → refuse.

## Why cherry-pick instead of merge

The legacy `/usr/local/bin/cm-conflict` shell script merges `<current-branch>` into a fresh staging branch. That works but produces a merge commit and requires you to have the source branch checked out. Cherry-picking from a PR URL is:
- Stateless — works from anywhere.
- Linear history — easier to review and diff against the master PR.
- Each commit lands cleanly so the staging PR's diff matches the master PR's diff 1:1 (modulo any staging-specific conflicts).
