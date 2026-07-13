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
