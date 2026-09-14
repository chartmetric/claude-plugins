# cm-maestro

Registers Chartmetric's internal MCP server, **Maestro**, so nobody has to hand-type a URL into
Claude Code or the Codex app.

| Server | URL | Default |
| --- | --- | --- |
| `maestro` | `https://maestro.chartmetric.com/mcp` | enabled |
| `maestro-dev` | `https://maestro-dev.chartmetric.com/mcp` | disabled (staging) |

## Install

Claude Code:

```bash
claude plugin marketplace add chartmetric/claude-plugins
claude plugin install cm-maestro@chartmetric-tools
```

Codex:

```bash
codex plugin marketplace add https://github.com/chartmetric/claude-plugins.git
codex plugin add cm-maestro@chartmetric-tools
```

## Authenticate

The plugin ships the connection, not the credentials. Maestro runs its own OAuth 2.1 server in
front of Google OIDC and only admits verified `@chartmetric.com` accounts, so each person logs in
once as themselves:

```bash
codex mcp login maestro     # Codex
/mcp                        # Claude Code — pick maestro, follow the browser flow
```

To enable staging, flip `enabled` for `maestro-dev` in your own config, or run
`codex mcp login maestro-dev`.

## What you get

Read-only Postgres, ClickHouse and Snowflake queries; `get_data_map` / `search_tables` /
`describe_table` for finding the right table; read-only Airflow DAG inspection; and the
`chartmetric-claude` GitHub App PR review, approve and recreate tools.

Database access is read-only by policy — `prepare_write` validates and previews a write and hands
back a statement you run yourself.
