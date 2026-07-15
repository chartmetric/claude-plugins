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
| `clickhouse-benchmark` | Benchmark/compare ClickHouse queries via system.query_log (P50/P90/P99, bytes read, memory) |
| `multi-repo-pr` | One piece of work spanning several repos: one branch + one PR per repo, cross-linked |
| `query-database` | READ-ONLY queries against RDS/ClickHouse/Elasticsearch/Snowflake via devin-secrets.env (local sessions only) |
| `ship-pr` | Finalize session PRs end-to-end: description, assignee = creator, Slack + Asana links (auto-created if missing), reviewer suggestion, PR Preview labels, poll until the preview deploys |
| `cm-pr-review` | Triage the PRs awaiting your review: discover direct review requests in `chartmetric`, draft a review per PR using each repo's own conventions, then post/approve/skip per PR on confirmation |
| `cm-takehome-review` | Score candidate take-home PRs against a rubric (runs each branch in a throwaway worktree to verify tests) and write local-only markdown scorecards + a comparison doc — never posts to GitHub |
| `release-notes` | Generate (and optionally post) the "Chartmetric Production Release" `#product-updates` message from a deploy message / PR / release tag, resolving Asana tasks and combining FE+BE release waves |
| `explain-code` | Explain code with an ASCII diagram, a step-by-step walkthrough, a gotcha, and a suggested improvement |
| `write-react-code` | Implement React + TypeScript features following project conventions (ESLint, strict types, context/hook thresholds, file organization, design-system usage) |
| `frontend-guidelines` | Chartmetric Web App frontend conventions & rules: Tailwind vs SCSS modules, design-system components, import ordering, i18n, TypeScript conventions. Pairs with `write-react-code` |

Skills from a plugin are invoked namespaced, e.g. `/cm-skills:slack-summary`.

## Updating

Plugins auto-update from this repo. To add or change a skill, edit `plugins/cm-skills/skills/<name>/SKILL.md` and merge to `main`.

## Requirements

- `slack-summary`, `session-report`, `slack-to-asana`, `ship-pr`, `release-notes` need the claude.ai Slack (and Asana) connectors: claude.ai → Settings → Connectors (`ship-pr` degrades gracefully — GitHub-only steps still run without them)
- `clickhouse-benchmark` needs `CLICKHOUSE_HOST` / `CLICKHOUSE_PORT` / `clickhouse_user` / `clickhouse_password` in your shell env
- `cm-pr-review`, `cm-takehome-review`, `release-notes`, `multi-repo-pr`, `ship-pr` need the `gh` CLI authenticated (`gh auth status`); `cm-takehome-review` also needs the take-home repos cloned under `~/code/chartmetric/`

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
