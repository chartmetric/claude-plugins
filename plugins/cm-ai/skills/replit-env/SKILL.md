---
name: replit-env
description: Use when working in a Chartmetric repo whose app runs in a Replit workspace and a task needs the repl's own environment — its data-store credentials, interpreter, or installed deps — or needs to run commands there over SSH or the repl's Shell tab, sync its git checkout with GitHub, or reason about production (which SSH cannot reach). Also use whenever a repl won't sync with GitHub — the Git pane or `git pull` fails with a credentials error or "Repository not found", `--ff-only` refuses because the repl and `origin/main` diverged, or Replit Agent commits conflict with merged PRs, even if the user only says "Replit sync is broken".
author: tyler@chartmetric.com
---

# Replit workspace environments

A Replit workspace is reachable over SSH, checkout at `/home/runner/workspace`, login shell bash.
Replit is the source of truth and syncs to GitHub. This skill holds what applies to any repl, not to
one in particular.

No SSH alias? For a one-off job like a sync recovery, work through the user rather than setting
one up. Give them each repl-side command block to paste into the repl's Shell tab, and ask for the
output. Keep the blocks self-contained (start with `cd /home/runner/workspace`), say what output to
expect, and never have them paste raw secrets. Set up SSH ("First connection" below) when you'll be
in the repl repeatedly, or the user asks for it.

## Before touching a repl

Answer these first — each one changes what is safe:

| Check | How | If yes |
|-------|-----|--------|
| Credentials point at prod-shared stores? | Inspect `DATABASE_URL`, ClickHouse, Snowflake, mail creds in the repl's env | Any write, send, or script run hits real customers and data — treat with prod-level caution |
| `GITHUB_TOKEN` set in env? | `ssh -n <alias> 'test -n "$GITHUB_TOKEN" && echo yes'` | Over SSH the askpass-shim fetch works; without it, SSH's only path is the bundle transport. The Shell tab doesn't need either, because Replit's own askpass answers there |
| An auto-commit watcher on the tree? | `git log` on `origin` shows commits like `misc change from replit side` by `cm-replit` | See "Auto-commit watcher" below |
| Can the repl's shell reach GitHub at all? | `GIT_TERMINAL_PROMPT=0 git fetch origin` in the repl | If it fails, triage the error with `references/replit-sync-recovery.md` before moving any commits |

## Every repl

### No alias yet? First connection

Everything else here assumes the repl's `Host <alias>` block already exists in `~/.ssh/config`; on a
fresh machine it won't. Open the repl's Tools → SSH pane — it shows the `HostName`, `User`, and
`Port`. Add a matching block to `~/.ssh/config`, naming its `Host` line `replit-<repl>` and pointing
`IdentityFile` at `~/.ssh/replit` — generate that key first if it's missing
(`ssh-keygen -t ed25519 -f ~/.ssh/replit`) — and register `~/.ssh/replit.pub` under the Replit
account's SSH keys if the repl requires it.

### Always `ssh -n`

`ssh` reads stdin, which in a non-interactive harness is a pipe nobody closes, so the call hangs —
reliably when you redirect stdout to a file. `-n` points stdin at `/dev/null`. (`scp` is unaffected.)

### The host rotates

The host rotates whenever the repl moves machines, so a timeout usually means a stale
`HostName`/`User`, not a down repl. Refresh both from the workspace's Tools → SSH pane and update the
`Host <alias>` entry in `~/.ssh/config` (key `~/.ssh/replit`). If the repl needs a registered key,
confirm `~/.ssh/replit.pub` is still listed under the account's SSH keys.

### SSH reaches only the dev workspace

SSH reaches the dev workspace, never the production autoscale deployment — those containers are
ephemeral and not SSH-accessible.

- **Prod logs** — browser only, via the Publishing tool's Logs tab, 7-day retention. Replit exposes
  no API, CLI, SSH, or log drain for deployment logs. A programmatic path means adding app-level log
  forwarding in code.
- **Prod state and behavior** — reachable without a browser when the workspace's credentials already
  point at prod-shared stores. Prod's HTTP API answers `curl` with whatever API token the app
  issues.

## Auto-commit watcher

Replit's git integration can watch the tree and, on its own, commit working/staged changes and push
them to `origin`. When a repl has one:

- **Resolve locally, fast-forward the repl.** Never merge, rebase, or resolve conflicts in the repl —
  the watcher publishes whatever is in the tree, conflict markers included. Do that work in your own
  checkout, push it, and leave the repl one job: take a fast-forward.
- **A multi-step CLI git flow gets raced.** The watcher commits the staged delta before your
  `git commit` does. Git identity is usually unset there too.
- **Clean tree first.** `git status --porcelain` empty is the precondition for a sync — anything
  dirty is the watcher mid-flight.

## Sync a repl with GitHub

Two references, picked by what's wrong:

- **`references/replit-sync-recovery.md`** — sync is stuck or the two sides have drifted. It
  triages the fetch error (including "Repository not found" from a Replit GitHub App installation
  that doesn't include the repo). It also resolves a diverged repl through a temporary sync branch:
  the repl pushes its HEAD, you merge and build locally, and the repl fast-forwards. Start here when
  the user reports a broken sync.
- **`references/replit-git-transport.md`** — moving commits when the repl's shell can't
  authenticate at all (typically over SSH): the askpass shim, the bundle transport in both
  directions, stale `.git` lock recovery, and the done-when checks. Supply the repl's SSH alias, its
  branch, and whether `GITHUB_TOKEN` is set.

When Replit's UI sync hangs or fails without an error, the cause is a stale `.git` lock often
enough to check that first. An explicit `git fetch` error goes to the recovery doc's triage table.
With no SSH and a repl that can't authenticate, no transport works: fix access first. Once the
workspace is fast-forwarded, hand future syncs back to Replit's UI.
