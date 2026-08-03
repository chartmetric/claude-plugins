# Replit workspace git transport

Moving commits between a Replit workspace and GitHub when the workspace's shell cannot
authenticate. Repl-agnostic — the calling skill supplies the SSH alias, the branch, and whether
`GITHUB_TOKEN` is set in that repl's env.

## The CLI is blind

`git fetch` and `git push` from an SSH shell fail:

    error: unable to read askpass response from 'replit-git-askpass'
    fatal: could not read Username for 'https://github.com': No such device or address

`GIT_ASKPASS=replit-git-askpass` only answers inside Replit's own runtime, so a headless shell gets
nothing back. The blindness is CLI-only — Replit's UI still syncs over its own OAuth. Everything
local still works: `status`, `log`, and fast-forwarding onto an already-fetched tracking ref.

`git remote -v` also lists a `gitsafe-backup` and several `subrepl-*` remotes. Ignore them;
`origin` is GitHub.

## Sighted fetch: the askpass shim

Where the repl has `GITHUB_TOKEN`, a four-line shim answers what the broken helper cannot:

```bash
ssh -n <alias> 'cd /home/runner/workspace
[ -n "$GITHUB_TOKEN" ] || { echo "no token, use a bundle"; exit 1; }
cat > /tmp/ap.sh <<"EOF"
#!/bin/sh
case "$1" in *[Uu]sername*) echo "x-access-token" ;; *) echo "$GITHUB_TOKEN" ;; esac
EOF
chmod +x /tmp/ap.sh
GIT_ASKPASS=/tmp/ap.sh GIT_TERMINAL_PROMPT=0 git fetch origin
rm -f /tmp/ap.sh
git merge --ff-only origin/<branch>'
```

`-c credential.helper='!f(){ …$GITHUB_TOKEN…; };f'` also works, but it puts the token in argv where
`ps` can read it. Prefer the shim file.

## Sneakernet: bundle over scp

With no token, `git bundle` carries the commits over `scp` so nothing in the repl has to
authenticate.

Inbound — GitHub into the repl:

```bash
# local — REPL_HEAD is whatever the repl is sitting at
git bundle create /tmp/sync.bundle <REPL_HEAD>..origin/<branch>
git bundle list-heads /tmp/sync.bundle        # the ref name it carries
scp /tmp/sync.bundle <alias>:/tmp/
```

```bash
ssh -n <alias> 'cd /home/runner/workspace
git bundle verify /tmp/sync.bundle            # names the commits it needs already present
git fetch /tmp/sync.bundle refs/remotes/origin/<branch>:refs/remotes/origin/<branch>
git merge --ff-only origin/<branch>
rm -f /tmp/sync.bundle'
```

A `<ref>..origin/<branch>` range carries the ref as `refs/remotes/origin/<branch>`, so fetching it
into that same name advances the repl's tracking ref and leaves no stray local branch behind.

Outbound — repl-only commits to your machine, so you can read them before they reach `origin`:

```bash
ssh -n <alias> 'cd /home/runner/workspace; git bundle create /tmp/out.bundle origin/<branch>..HEAD'
scp <alias>:/tmp/out.bundle /tmp/
git fetch /tmp/out.bundle +HEAD:refs/heads/repl-sync  # a <ref>..HEAD range carries the ref as HEAD; + so a leftover repl-sync re-runs
```

Merge `repl-sync` in your own checkout, push the result, then fast-forward the repl onto it.

## Stale git lock

Replit's own sync failing or hanging is usually a stale `.git/*.lock` from an interrupted
operation. A lock on `index`, `HEAD`, `ORIG_HEAD`, or a ref blocks the pull/merge/reset that sync
runs, even while `git status` still answers. In `/home/runner/workspace`, in order:

1. `pgrep -a git` — empty means any lock is stale. A lock with a live git process is not stale:
   wait for it, and ask before killing it.
2. `find .git -name '*.lock' -exec ls -la {} \;` — compare each mtime against `date`.
3. `rm -v .git/<name>.lock` for each stale one, then re-run the `find` (expect empty).
4. Recover the interrupted step with no network: `git merge --ff-only origin/<branch>`, which also
   rewrites `ORIG_HEAD`. Not fast-forwardable means the branches diverged — stop and go read the
   divergence rather than merging blindly.

## Done when

- `git status --porcelain` in the workspace is empty.
- `git rev-list --left-right --count origin/<branch>...HEAD` there prints `0	0`.
- The repl's tracking ref is current, not just self-consistent: its `origin/<branch>` equals
  `git rev-parse origin/<branch>` on your machine after a local `git fetch`.

## Troubleshooting

- **`git merge --ff-only` refuses** — the repl is ahead. Bundle those commits out rather than
  discarding them; once they are on your machine, `git reset --soft origin/<branch>` collapses the
  repl's divergence while keeping the files.
- **`git bundle verify` reports a missing prerequisite** — the range was cut from a base the repl
  does not have. Re-cut it from a commit it does (`git rev-parse HEAD` there).
- **`Refusing to create empty bundle`** — the range is empty, so the two sides are already level.
