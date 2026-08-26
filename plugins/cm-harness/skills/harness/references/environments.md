# Locating the repo, and what each environment can do

Both `cm-harness` skills load their real instructions from the repo, at
`<repo>/.agents/commands/<name>.md`. This file explains how to find `<repo>` and what
is actually possible once you have.

---

## Step 1 — Locate the repo

Try these in order. Stop at the first that succeeds.

1. **Direct filesystem access.** Try `Read` or `Glob` on `harness.config.json` and
   `.agents/commands/` from the working directory and any obvious parent. If the files
   come back, the repo is local to this session — work in place. This is the case for
   Claude Code in a terminal, Claude Code in a cloud sandbox, and Cowork running **on
   your computer**.

2. **Connected folder over the device bridge.** Call `mcp__remote-devices__device_list_dir`
   on each connected folder root. The repo is the one containing both
   `harness.config.json` and `phases/`. Read files with `device_stage_files`, run
   commands with `device_bash` (paths under `$HOME/mnt/<folder>/`).

3. **Nothing found.** Stop and tell the user, in plain language, that you need the
   monorepo. Ask them to either open this task from a folder that contains it, or click
   **Add folder** in the Claude desktop app and pick their clone. Do not guess a path and
   do not proceed without the repo — every instruction in the command files is relative
   to it.

### Which path holds the command files

`.agents/` is the tracked, tool-agnostic location and the one to read. `.claude` is a
committed symlink pointing at it, for Claude Code's benefit.

Read `<repo>/.agents/commands/<name>.md`. If that path does not exist, fall back to
`<repo>/.claude/commands/<name>.md` — some repos have not adopted the `.agents/` layout,
and a Windows checkout without Developer Mode may have materialized the symlink as a
one-line text file rather than a link.

If **neither** path resolves to a real command file, do not improvise the command from
memory. Say what you looked for and ask the user to run `python3 scripts/execute.py
doctor`, which diagnoses exactly this.

That command file is authoritative. Nothing in this plugin overrides it.

---

## Step 2 — Know what this environment can do

There are four, and they differ in ways that matter before you promise anything.

| | Claude Code **terminal** | Claude Code **cloud sandbox** | Cowork **on your computer** | Cowork **in the cloud** |
|---|---|---|---|---|
| Read/write repo files | ✅ | ✅ | ✅ | ✅ via bridge |
| `precheck` / `status` / `lint` / `doctor` | ✅ | ✅ | ✅ | ✅ via `device_bash` |
| Author phases, PRD, ADR, backlog | ✅ | ✅ | ✅ | ✅ |
| `execute.py run` (spawns agents) | ✅ | ✅ | ⚠️ unverified | ❌ — bootstrap into the container |
| Verify an `apps/api` phase | ✅ | ✅ | ✅ | ✅ in the container |
| Verify an `apps/web` phase | ✅ | ⚠️ needs a Font Awesome token | ✅ | ❌ registry unreachable |
| `git push` / open a PR | ✅ | ✅ | ✅ | ❌ auth is stripped |

### Claude Code cloud sandbox

The repo is cloned into the sandbox, so this behaves like a terminal session. **The
nested `claude` binary is authenticated there** — verified with
`node_modules/.bin/claude -p "Reply with exactly: PROBE_OK"` returning `PROBE_OK`, exit
0. So `execute.py run` works end to end, in place, with no bootstrap.

Two setup details that will bite otherwise:

```bash
corepack enable
HUSKY=0 pnpm install --filter api... --ignore-scripts
node node_modules/@anthropic-ai/claude-code/install.cjs   # ← required after --ignore-scripts
python3 scripts/execute.py doctor
```

`--ignore-scripts` skips the postinstall that downloads the platform-native `claude`
binary, leaving a shim that fails at first use. Running `install.cjs` by hand fixes it.
`doctor` currently checks only that the binary is on PATH, so it reports `✓` either way —
confirm with `node_modules/.bin/claude --version` before starting a run.

`apps/api` declares `engines.node: >=26` while the sandbox runs Node 22. pnpm warns and
installs anyway; the suites pass.

### Cowork in the cloud

**Cloud Cowork sessions cannot spawn agents on the user's machine.** The device VM's
`claude` is disabled (`claude: claude is not enabled in this environment`) and it has no
outbound network. `device_bash` also caps at 45 s per call, against
`agent_timeout_sec: 3600`. So `run` never happens on the user's disk from a cloud Cowork
session — it happens in the session container instead, via the bootstrap in Step 3.

The device VM also has **no git write credentials**. Reads (`git fetch`, `ls-remote`)
work; `git push` fails with `could not read Username for 'https://github.com'`. Hand
finished work back for the user to push.

A worktree created with `device_bash` records the VM's mount path in
`.git/worktrees/<name>/gitdir` and the worktree's own `.git` file, so it is unusable from
macOS until both are rewritten to the user's real path. The branch ref itself lives in the
shared `.git`, so the user can always push from the main checkout regardless.

Deleting files in a connected folder is blocked by default, which breaks git's own lock
and temp-object cleanup mid-commit. If a commit fails with `Unable to create ... .lock:
File exists`, call `mcp__remote-devices__device_request_delete_permission` on the folder
root, then clear the stale `*.lock` files.

### Cowork on your computer

Still unverified: nobody has confirmed whether `claude -p` can be spawned as a
subprocess there. Test it once with `claude -p "Reply with exactly: PROBE_OK"` before
relying on it. If it works, that mode is the best of both worlds — everything in place,
no copying. If it fails the way the cloud device VM does, fall back to the bootstrap.

---

## Step 3 — Bootstrapping a run in a cloud Cowork session

Only needed for `execute.py run`, and only in cloud Cowork. Everything else works over
the bridge directly, and a Claude Code cloud sandbox needs none of this.

### 3a. Check for a live run first

```bash
cat .harness/locks/<phase-id>.lock 2>/dev/null
```

If a lock exists, **do not write anything into the repo**. `pipeline.py` runs
`git add -A` at repo root, so any file you create anywhere in the tree gets swept into
that phase's commit, and `runner.py`'s scope check (`git status --porcelain`) will flag
it to the reviewer. Ask the user to confirm on their own machine whether the PID is
alive — you cannot check it yourself, because `device_bash` runs in a Linux VM with a
different process namespace than the macOS process that wrote the lock.

### 3b. Snapshot out

`.harness/` is gitignored, so scratch files there are invisible to both `git add -A` and
the scope check. That is the only safe place to stage from.

```bash
mkdir -p .harness/_cowork
nice -n 19 tar czf .harness/_cowork/repo-snapshot.tar.gz \
  --exclude=node_modules --exclude=.git --exclude=.worktrees \
  --exclude=.turbo --exclude=dist --exclude=.harness .
```

Roughly 800 KB. Stage it with `device_stage_files`, unpack in the container.

### 3c. Rebuild the environment

```bash
git config --global --add safe.directory <path>   # else: "dubious ownership"
git init -q && git add -A && git commit -q -m "baseline: snapshot <timestamp>"
export HUSKY=0 && corepack enable
corepack pnpm install --filter <app>... --ignore-scripts
node node_modules/@anthropic-ai/claude-code/install.cjs
python3 scripts/execute.py doctor        # expect: doctor: ok (0 warning(s))
```

`doctor` green is the gate. It checks the agent binary resolves for all five roles, that
`.claude -> .agents` and `CLAUDE.md -> AGENTS.md` survived the tar, and that
`dangerous_cmd_guard.py` is wired. Do not run a phase until it passes. Those two symlinks
are committed in the monorepo, so a clone has them without setup — but `tar` and `unzip`
do not always preserve links, so the check still earns its place.

### 3d. Run, then hand back

```bash
python3 scripts/execute.py run <phase-id>
```

Then produce a patch against the baseline commit and deliver it with `SendUserFile`, plus
`device_commit_files` to place it on the user's disk. **The user applies it themselves**
and pushes — never push from the container, and never write the result straight into
their working tree while anything else might be running there.

---

## Verification commands and the Font Awesome trap

`harness.config.json` sets `default_verification_cmd: "pnpm test"`, but phases override
it, and the override decides where the phase can run.

- **`apps/api` phases** work everywhere. `pnpm install --filter api...` pulls ~464
  packages in ~16 s and touches no private registry.
- **`apps/web` and `packages/ui` phases** depend on `@fortawesome`, which `.npmrc` maps
  to `npm.fontawesome.com`. What happens next differs by environment:
  - **Claude Code cloud sandbox** — the host is reachable (`401`, not a proxy `403`).
    The install fails only for want of a token, and pnpm ignores credentials in the
    project `.npmrc` by design. A `//npm.fontawesome.com/:_authToken=...` line in
    user-level `~/.npmrc` unblocks it.
  - **Cowork session container** — the proxy refuses the host outright
    (`CONNECT tunnel failed, 403`). No token helps. These phases need the user's machine.

Before bootstrapping, read the phase's `verification_cmd`. If it filters to `web`, decide
which of the two cases you are in rather than burning a bootstrap to find out.

---

## Status glyphs

From `scripts/harness/state.py`:

| Glyph | Status | Meaning |
|---|---|---|
| `✓` | `completed` | done |
| `→` | `in_progress` | mid-pipeline; the stage is shown in brackets |
| `·` | `pending` | not started |
| `✗` | `exhausted` | blew `max_attempts` or `max_review_cycles` — needs a human |

`✗` is not cosmetic. Surface it and help the user triage rather than re-running blindly.
