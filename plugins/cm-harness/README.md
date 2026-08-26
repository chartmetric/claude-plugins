# cm-harness

Brings `/feature-intake` and `/harness` into Claude **Cowork** for the
`chartmetric-app-monorepo` phase harness.

## The design in one paragraph

Cowork does not read a repo's `.agents/commands/`, which is why these commands are
invisible in Cowork even with the folder connected. This plugin does **not** copy those
command bodies. Each skill here is a thin loader: it locates the repo, reads
`.agents/commands/<name>.md` at runtime, and follows it. The repo stays the single source
of truth — edit a command file and the change takes effect on the next run, with no
release here. What the plugin owns is the part the repo can't know: how to find the repo,
and what is actually possible in each environment.

`.agents/` is the tracked, tool-agnostic location. `.claude` is a committed symlink to it
for Claude Code's benefit, and the loaders fall back to `.claude/commands/` for repos that
haven't adopted the `.agents/` layout.

## What each skill does

- **`/feature-intake`** — turns a plain-language feature ask into an ADR-grounded entry in
  `docs/PRD.md`. Written for PMs and designers; no engineering detail expected. Stops and
  asks when no architectural decision covers the surface, rather than inventing one.
- **`/harness`** — advances the phase pipeline: precheck, status, phase proposals, triage,
  and running a phase.

## What works where

| | Claude Code terminal | Claude Code cloud sandbox | Cowork on your computer | Cowork in the cloud |
|---|---|---|---|---|
| `/feature-intake`, end to end | ✅ | ✅ | ✅ | ✅ |
| `precheck` / `status` / `lint` / `doctor` | ✅ | ✅ | ✅ | ✅ |
| Authoring phases, PRD, ADR, backlog | ✅ | ✅ | ✅ | ✅ |
| `execute.py run` (spawns agents) | ✅ | ✅ | ⚠️ unverified | ✅ for `apps/api`, in the container |
| `git push` / open a PR | ✅ | ✅ | ✅ | ❌ |

Three known limits behind that table:

**Cloud Cowork sessions can't spawn agents on your machine.** The device VM's `claude` is
disabled and it has no outbound network. So `/harness run` from a cloud Cowork session
happens in the session container instead — the skill bootstraps a copy of the repo there
and hands the result back as a patch you apply and push. Verified end to end for
`apps/api` phases.

**Claude Code cloud sandboxes are the good case.** The repo is cloned in, and the nested
`claude` binary is authenticated — `run` works in place with no bootstrap. One gotcha: an
install with `--ignore-scripts` skips the postinstall that downloads the platform-native
binary, so run `node node_modules/@anthropic-ai/claude-code/install.cjs` afterwards.
`doctor` does not catch this; `claude --version` does.

**`apps/web` phases need a Font Awesome token, or your machine.** `.npmrc` maps
`@fortawesome` to `npm.fontawesome.com`. A Claude Code sandbox can reach that host and
fails only for want of a token in user-level `~/.npmrc`; the Cowork container's proxy
refuses it outright, and no token helps.

## Setup

1. Install the plugin.
2. Clone `chartmetric-app-monorepo` if you don't have it.
3. Connect that folder — **Add folder** in the Claude desktop app.
4. Type `/feature-intake` or `/harness`.

Step 3 is the one people miss. Without a connected folder there is no repo to read, and
both skills will say so rather than guessing.

**In Claude Code you do not need this plugin.** The monorepo's `.claude/commands/` already
exposes `/harness` and `/feature-intake` natively, from the same files these skills load.
Installing it there gives you two paths to one set of instructions, with the plugin's copy
able to fire on description match where the command files set
`disable-model-invocation: true`. This plugin exists for Cowork, which does not read
`.claude/commands/` at all.

## Note on triggering

The repo's command files set `disable-model-invocation: true`. Cowork skills have no
equivalent — a skill can fire on description match alone. The descriptions here are
written narrowly to require an explicit ask. If either starts firing when nobody asked
for it, tighten the `description` field in that skill's `SKILL.md`.
