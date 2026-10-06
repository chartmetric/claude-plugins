---
name: replit-env
description: Use when working in a Chartmetric repo whose app runs in a Replit workspace (cm-workspace) and a task needs the repl's own environment — its data-store credentials, interpreter, or installed deps — or needs to run commands there over SSH, sync its git checkout with GitHub, unstick a Replit↔GitHub sync, or reason about production (which SSH cannot reach).
author: tyler@chartmetric.com
---

# Replit workspace environments

Some Chartmetric repos run their app in a Replit workspace, reachable over SSH, checkout at
`/home/runner/workspace`, login shell bash. Replit is the source of truth and syncs to GitHub. One
such repl today:

| Repl | SSH alias | `GITHUB_TOKEN` in env | Central hazard |
|------|-----------|-----------------------|----------------|
| cm-workspace | `replit-workspace` | No → bundle transport only | Shares prod data stores, live tokens, `hi@` mailbox |

The rest of this skill splits into what's true for every repl, then the per-repl specifics, then how
to sync one with GitHub.

## Every repl

### No alias yet? First connection

Everything else here assumes the repl's `Host <alias>` block already exists in `~/.ssh/config`; on a
fresh machine it won't. Open the repl's Tools → SSH pane — it shows the `HostName`, `User`, and
`Port`. Add a matching block to `~/.ssh/config`, naming its `Host` line for the alias this skill uses
(`replit-workspace`) and pointing `IdentityFile` at `~/.ssh/replit` — generate that
key first if it's missing (`ssh-keygen -t ed25519 -f ~/.ssh/replit`). For cm-workspace, also register
`~/.ssh/replit.pub` under the Replit account's SSH keys (the same registry the host-rotation note
below refers to).

### Always `ssh -n`

`ssh` reads stdin, which in a non-interactive harness is a pipe nobody closes, so the call hangs —
reliably when you redirect stdout to a file. `-n` points stdin at `/dev/null`. (`scp` is unaffected.)

### The host rotates

The host rotates whenever the repl moves machines, so a timeout usually means a stale
`HostName`/`User`, not a down repl. Refresh both from the workspace's Tools → SSH pane and update the
`Host <alias>` entry in `~/.ssh/config` (key `~/.ssh/replit`). For cm-workspace, also confirm
`~/.ssh/replit.pub` is still registered under the account's SSH keys.

### SSH reaches only the dev workspace

SSH reaches the dev workspace, never the production autoscale deployment — those containers are
ephemeral and not SSH-accessible.

- **Prod logs** — browser only, via the Publishing tool's Logs tab, 7-day retention. Replit exposes
  no API, CLI, SSH, or log drain for deployment logs. A programmatic path means adding app-level log
  forwarding in code.
- **Prod state and behavior** — reachable without a browser when the workspace's credentials already
  point at prod-shared stores (see cm-workspace below). Prod's HTTP API answers `curl` with a token
  (`WORKSPACE_API_TOKEN` for the public service endpoints, or a Firebase token).

## cm-workspace: prod side effects

cm-workspace shares prod data stores, live API tokens, and the same `hi@` mailbox as production.
Running the app or scripts, sending mail, claiming mailbox rows, or writing the app DB here hits real
customers and real data. Treat any write or send with prod-level caution.

Its credentials point at prod-shared stores: treat `DATABASE_URL`, ClickHouse, and Snowflake alike;
melodi RDS stays read-only.

## Sync a repl with GitHub

Read `references/replit-git-transport.md` and follow it, supplying the repl's alias, branch, and
whether `GITHUB_TOKEN` is set:

| Repl | `<alias>` | `<branch>` | Token |
|------|-----------|------------|-------|
| cm-workspace | `replit-workspace` | the branch the workspace is on | no `GITHUB_TOKEN` — skip the askpass-shim section; the bundle transport is the only path |

The doc holds the bundle transport in both directions, stale `.git` lock recovery, and the done-when
checks.

- **cm-workspace:** Replit's sync failing or hanging is a stale `.git` lock often enough to check
  that first. Once the locks are gone and the workspace is fast-forwarded, hand future syncs back to
  Replit's UI.
