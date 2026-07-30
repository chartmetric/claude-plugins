# Chartmetric Claude Code Plugins

Private plugin marketplace for Chartmetric's Claude Code skills. Access is controlled by this repo's visibility — anyone who can clone it can install from it.

The marketplace ships three plugins:

- **`cm-skills`** — engineering skills (code, PRs, databases, reviews)
- **`cm-comms`** — team communication & reporting skills (Slack + Asana)
- **`cm-ai`** — AI-related skills (reading Casper agent sessions)

Install whichever you need.

## Install

```bash
claude plugin marketplace add chartmetric/claude-plugins
claude plugin install cm-skills@chartmetric-tools    # engineering
claude plugin install cm-comms@chartmetric-tools     # comms & reporting
claude plugin install cm-ai@chartmetric-tools        # AI-related skills
```

Or inside a Claude Code session: `/plugin` → browse `chartmetric-tools` → install `cm-skills`, `cm-comms`, and/or `cm-ai`.

```
# 1. Refresh the marketplace clone (pulls the newest main from chartmetric/claude-plugins)
claude plugin marketplace update chartmetric-tools

# 2. Update each plugin to whatever version main now declares
claude plugin update cm-skills@chartmetric-tools
claude plugin update cm-comms@chartmetric-tools
claude plugin update cm-ai@chartmetric-tools
```

## What's in `cm-skills` (engineering)

| Skill | What it does |
| --- | --- |
| `cm-task` | Run a single task (one branch, one PR) with harness discipline: interview → confirmed brief, red verifier before code, TDD, fresh-context review subagent, micro-retro lesson into the repo's CLAUDE.md. Accepts an Asana or Slack URL |
| `clickhouse-benchmark` | Benchmark/compare ClickHouse queries via system.query_log (P50/P90/P99, bytes read, memory) |
| `query-database` | READ-ONLY queries against RDS/ClickHouse/Elasticsearch/Snowflake via devin-secrets.env (local sessions only) |
| `ds-notebook` | Scaffold & harden standalone Chartmetric data-science Jupyter notebooks: ClickHouse-first (or Snowflake) queries with memory-safe patterns, freshness sentinels, schema verification, server-side eligibility scratch tables, parquet caching, sanity/validation diagnostics, and disabled write-back cells |
| `cm-pr-review` | Triage the PRs awaiting your review: discover direct review requests in `chartmetric`, draft a review per PR using each repo's own conventions, then post/approve/skip per PR on confirmation |
| `cm-takehome-review` | Score candidate take-home PRs against a rubric (runs each branch in a throwaway worktree to verify tests) and write local-only markdown scorecards + a comparison doc — never posts to GitHub |
| `multi-repo-pr` | One piece of work spanning several repos: one branch + one PR per repo, cross-linked |
| `ship-pr` | Finalize session PRs end-to-end: description, assignee = creator, Slack + Asana links (auto-created if missing), reviewer suggestion, PR Preview labels, poll until the preview deploys |
| `gh-stack` | Manage stacked branches & PRs with the `gh stack` CLI extension: build, navigate, rebase, sync, and merge a chain of dependent PRs, run non-interactively so it never hangs on a prompt |
| `rag-add-endpoint` | Add an API endpoint to the Flow AI / Melodi RAG "sitemap" knowledge base: gate on whether a live endpoint exists (else "build the API first"), then edit chartmetric-one's `api-registry.ts` (`flow`) or emit reviewable Postgres SQL (`main`) + a PR, with the activation timeline |
| `explain-code` | Explain code with an ASCII diagram, a step-by-step walkthrough, a gotcha, and a suggested improvement |
| `write-react-code` | Implement React + TypeScript features following project conventions (ESLint, strict types, context/hook thresholds, file organization, design-system usage) |
| `frontend-guidelines` | Chartmetric Web App frontend conventions & rules: Tailwind vs SCSS modules, design-system components, import ordering, i18n, TypeScript conventions. Pairs with `write-react-code` |

Invoked as `/cm-skills:<skill>`, e.g. `/cm-skills:cm-pr-review`.

## What's in `cm-comms` (team communication & reporting)

| Skill | What it does |
| --- | --- |
| `cm-task` | Run a single task (one branch, one PR) with harness discipline: interview → confirmed brief, red verifier before code, TDD, fresh-context review subagent, micro-retro lesson into the repo's CLAUDE.md. Accepts an Asana or Slack URL |
| `slack-summary` | Summarize a Slack thread from its URL |
| `session-report` | Post a full-context work report (problem / fix / current state / links) to a Slack channel |
| `slack-to-asana` | File Asana task(s) on Unified CM Tasks from a Slack thread, link PRs, reply in-thread |
| `release-notes` | Generate (and optionally post) the "Chartmetric Production Release" `#product-updates` message from a deploy message / PR / release tag, resolving Asana tasks and combining FE+BE release waves |

Invoked as `/cm-comms:<skill>`, e.g. `/cm-comms:slack-summary`.

## What's in `cm-ai` (AI-related skills)

| Skill | What it does |
| --- | --- |
| `cm-task` | Run a single task (one branch, one PR) with harness discipline: interview → confirmed brief, red verifier before code, TDD, fresh-context review subagent, micro-retro lesson into the repo's CLAUDE.md. Accepts an Asana or Slack URL |
| `reading-casper-sessions` | Read a Casper agent session — its transcript and trace — via the session read API (`lean` / `full` / `nodes` / `export` views) to inspect, analyze, or diagnose behavior |

Invoked as `/cm-ai:<skill>`, e.g. `/cm-ai:reading-casper-sessions`.

## Updating

Plugins auto-update from this repo. To add or change a skill, edit `plugins/<plugin>/skills/<name>/SKILL.md` (pick `cm-skills` for engineering, `cm-comms` for comms/reporting) and merge to `main`.

## Requirements

- `slack-summary`, `session-report`, `slack-to-asana`, `ship-pr`, `release-notes` need the claude.ai Slack (and Asana) connectors: claude.ai → Settings → Connectors (`ship-pr` degrades gracefully — GitHub-only steps still run without them)
- `clickhouse-benchmark` needs `CLICKHOUSE_HOST` / `CLICKHOUSE_PORT` / `clickhouse_user` / `clickhouse_password` in your shell env
- `cm-pr-review`, `cm-takehome-review`, `release-notes`, `multi-repo-pr`, `ship-pr`, `rag-add-endpoint` need the `gh` CLI authenticated (`gh auth status`); `cm-takehome-review` also needs the take-home repos cloned under `~/code/chartmetric/`
- `rag-add-endpoint` needs read-only DB access (local session + `devin-secrets.env`) for its feasibility checks, and chartmetric-one cloned for the `flow`-endpoint path
- `reading-casper-sessions` needs a read-only `CASPER_SESSION_READ_TOKEN` in your shell env (mint one at https://casper.chartmetric.com/settings) and `curl`

## Contributing

`main` is protected — all changes go through a PR with one approval.

**Add or change a skill:**

1. Branch off `main`:
   ```bash
   git checkout -b feat/my-skill
   ```
2. Pick the plugin your skill belongs in — `cm-skills` (engineering) or `cm-comms` (team communication & reporting) — then create `plugins/<plugin>/skills/<skill-name>/SKILL.md`:
   ```markdown
   ---
   name: my-skill
   description: One or two sentences saying WHAT it does and WHEN to use it — this is what Claude reads to decide whether to invoke your skill.
   ---

   # My Skill

   Step-by-step instructions for Claude...
   ```
   That's it — skills are auto-discovered from each plugin's `skills/` directory, no registration needed. Supporting files (scripts etc.) go in the same folder; reference them as `"${CLAUDE_PLUGIN_ROOT}/skills/<skill-name>/<file>"`.
3. Test it locally before opening the PR:
   ```bash
   claude plugin marketplace add ~/code/chartmetric/claude-plugins   # local path works
   claude plugin install <plugin>@chartmetric-tools                  # cm-skills or cm-comms
   # new claude session → /<plugin>:my-skill
   ```
4. Bump `version` in that plugin's `.claude-plugin/plugin.json`.
5. Open a PR. After merge, everyone's plugin auto-updates from `main`.

## Get the latest versions

```
# 1. Refresh the marketplace clone (pulls the newest main from chartmetric/claude-plugins)
claude plugin marketplace update chartmetric-tools

# 2. Update each plugin to whatever version main now declares
claude plugin update cm-skills@chartmetric-tools
claude plugin update cm-comms@chartmetric-tools
claude plugin update cm-ai@chartmetric-tools
```


**Ground rules for skills:**

- Team-generic only: no hardcoded usernames or personal defaults — resolve the current user at runtime (e.g. `gh api user --jq .login`) or ask.
- Never embed secrets/tokens; read them from env vars and say which ones are needed.
- Write the `description` frontmatter carefully — it's the trigger. Say what the skill does AND when to use it.
- If the skill can post to Slack / create tasks / edit PRs, make it show a draft or confirm before the outward action.
