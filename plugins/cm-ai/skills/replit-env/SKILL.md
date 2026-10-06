---
name: replit-env
description: Use when working in a Chartmetric repo whose app runs in a Replit workspace and a task needs the repl's own environment — its data-store credentials, interpreter, or installed deps — or needs to run commands there over SSH, sync its git checkout with GitHub, unstick a Replit↔GitHub sync, or reason about production (which SSH cannot reach).
author: tyler@chartmetric.com
---

# Replit workspace environments

A Replit workspace is reachable over SSH, checkout at `/home/runner/workspace`, login shell bash.
Replit is the source of truth and syncs to GitHub. No Chartmetric repo runs on Replit today; this
skill holds what applies to any repl built there.

## Before touching a repl

Answer these first — each one changes what is safe:

| Check | How | If yes |
|-------|-----|--------|
| Credentials point at prod-shared stores? | Inspect `DATABASE_URL`, ClickHouse, Snowflake, mail creds in the repl's env | Any write, send, or script run hits real customers and data — treat with prod-level caution |
| `GITHUB_TOKEN` set in env? | `ssh -n <alias> 'test -n "$GITHUB_TOKEN" && echo yes'` | The askpass-shim fetch works; otherwise the bundle transport is the only path |
| An auto-commit watcher on the tree? | `git log` on `origin` shows commits like `misc change from replit side` by `cm-replit` | See "Auto-commit watcher" below |

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

Read `references/replit-git-transport.md` and follow it, supplying the repl's SSH alias, its branch,
and whether `GITHUB_TOKEN` is set. It holds the askpass shim, the bundle transport in both
directions, stale `.git` lock recovery, and the done-when checks.

Replit's own sync failing or hanging is a stale `.git` lock often enough to check that first. Once
the locks are gone and the workspace is fast-forwarded, hand future syncs back to Replit's UI.
