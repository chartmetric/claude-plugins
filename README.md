# Chartmetric Claude Code Plugins

Private plugin marketplace for Chartmetric's Claude Code skills. Access is controlled by this repo's visibility — anyone who can clone it can install from it.

## Install

```bash
claude plugin marketplace add chartmetric/claude-plugins
claude plugin install cm-skills@chartmetric-tools
```

Or inside a Claude Code session: `/plugin` → browse `chartmetric-tools` → install `cm-skills`.

## What's in `cm-skills`

| Skill | What it does |
| --- | --- |
| `slack-summary` | Summarize a Slack thread from its URL |
| `session-report` | Post a full-context work report (problem / fix / current state / links) to a Slack channel |
| `slack-to-asana` | File Asana task(s) on Unified CM Tasks from a Slack thread, link PRs, reply in-thread |
| `cm-conflict` | Create the staging companion PR for a master PR (cherry-pick based) |
| `clickhouse-benchmark` | Benchmark/compare ClickHouse queries via system.query_log (P50/P90/P99, bytes read, memory) |

Skills from a plugin are invoked namespaced, e.g. `/cm-skills:slack-summary`.

## Updating

Plugins auto-update from this repo. To add or change a skill, edit `plugins/cm-skills/skills/<name>/SKILL.md` and merge to `main`.

## Requirements

- `slack-summary`, `session-report`, `slack-to-asana` need the claude.ai Slack (and Asana) connectors: claude.ai → Settings → Connectors
- `clickhouse-benchmark` needs `CLICKHOUSE_HOST` / `CLICKHOUSE_PORT` / `clickhouse_user` / `clickhouse_password` in your shell env

## Contributing

`main` is protected — all changes go through a PR with one approval.

**Add or change a skill:**

1. Branch off `main`:
   ```bash
   git checkout -b feat/my-skill
   ```
2. Create `plugins/cm-skills/skills/<skill-name>/SKILL.md`:
   ```markdown
   ---
   name: my-skill
   description: One or two sentences saying WHAT it does and WHEN to use it — this is what Claude reads to decide whether to invoke your skill.
   ---

   # My Skill

   Step-by-step instructions for Claude...
   ```
   That's it — skills are auto-discovered from the `skills/` directory, no registration needed. Supporting files (scripts etc.) go in the same folder; reference them as `"${CLAUDE_PLUGIN_ROOT}/skills/<skill-name>/<file>"`.
3. Test it locally before opening the PR:
   ```bash
   claude plugin marketplace add ~/code/chartmetric/claude-plugins   # local path works
   claude plugin install cm-skills@chartmetric-tools
   # new claude session → /cm-skills:my-skill
   ```
4. Bump `version` in `plugins/cm-skills/.claude-plugin/plugin.json`.
5. Open a PR. After merge, everyone's plugin auto-updates from `main`.

**Ground rules for skills:**

- Team-generic only: no hardcoded usernames or personal defaults — resolve the current user at runtime (e.g. `gh api user --jq .login`) or ask.
- Never embed secrets/tokens; read them from env vars and say which ones are needed.
- Write the `description` frontmatter carefully — it's the trigger. Say what the skill does AND when to use it.
- If the skill can post to Slack / create tasks / edit PRs, make it show a draft or confirm before the outward action.
