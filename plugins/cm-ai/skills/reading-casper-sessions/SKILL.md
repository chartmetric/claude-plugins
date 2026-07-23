---
name: reading-casper-sessions
description: Read a Casper agent session, its transcript and trace, via the session read API. Use when you need to inspect, analyze, or diagnose behavior in a specific Casper session. Use when handed a Casper console session link or if you grab the link yourself from an associated Slack thread.
---

# Reading Casper sessions

The session read API serves one Casper session (header, turns, and trace nodes) over four
sibling paths split by **scope × detail**. All four take a read-only bearer token or an admin
console session. Pick a path by how much you need; reach for one of two workflows.

## Setup

- Token: `CASPER_SESSION_READ_TOKEN`, a read-only bearer. Take it from the shell environment
  first; fall back to `~/code/secrets.env` if that file exists. If it's still unset after both,
  stop and tell the user to mint one at https://casper.chartmetric.com/settings, then export it
  (or drop it in `~/code/secrets.env`).
- Use `curl`, not WebFetch — WebFetch can't set the auth header, so it 401s.
- Session id is `channel:thread_ts`; URL-encode the `:` as `%3A`. A console session link
  works too — strip it down to the id.

```bash
# Use the token already in your shell env; source ~/code/secrets.env only as a fallback.
[ -n "$CASPER_SESSION_READ_TOKEN" ] || { [ -f ~/code/secrets.env ] && { set -a; . ~/code/secrets.env; set +a; }; }
[ -n "$CASPER_SESSION_READ_TOKEN" ] || echo "No token — mint one at https://casper.chartmetric.com/settings"
BASE='https://casper.chartmetric.com'   # or $CASPER_CONSOLE_URL
AUTH="Authorization: Bearer $CASPER_SESSION_READ_TOKEN"
SID='<channel>:<thread_ts>'
curl -s -H "$AUTH" "$BASE/api/sessions/${SID/:/%3A}/lean"            # skim
curl -s -H "$AUTH" "$BASE/api/sessions/${SID/:/%3A}/nodes?turn=4&format=md"    # one exchange
curl -s -H "$AUTH" "$BASE/api/sessions/${SID/:/%3A}/nodes?nodes=3-10"          # nodes (JSON)
curl -s -H "$AUTH" "$BASE/api/sessions/${SID/:/%3A}/export" -o dump.json       # lossless, for code
```

## The four paths

- `/lean` — the whole session, text and node I/O digested to head+tail. The default read:
  skim the shape, then drill in.
- `/full` — the whole session, untruncated. Token-heavy; prefer `/nodes` first.
- `/nodes?<filters>` — specific trace nodes in full detail: a flat list across turns plus a
  `turns` sidecar. A selector is required — a bare request returns a `missing_selector` 400.
- `/export` — JSON-only lossless dump, one row per trace node in start_time order,
  untruncated short of the capture cap. Not for reading by you directly, Have the response written to a file and analyze with code.

`format=md|json` (json default) applies to `/lean`, `/full`, `/nodes` only. `/export` is
always JSON.

Two routes are not the reader's surface — don't reach for them: `/api/sessions/<id>` (the raw
whole session, a frozen SPA/logging shape, token-heavy) and `/turns/<turn_id>/trace`
(admin-only, so a bearer token 401s).

## Two workflows

- **Progressive** — `/lean` to skim, then `/nodes?turn=N` for one exchange under the
  microscope or `/nodes?nodes=A-B` for specific nodes; `/full` only when you truly need
  everything.
- **Thorough** — `curl .../export -o dump.json` and analyze with code (jq/python). Never load
  the dump into the context window.

## `/nodes` filters

- `nodes`, `turn` — a value, comma list, or inclusive range (`2-4`). `nodes` wins over `turn`.
- `type`, `status`, `name` — strings.
- `min_ms`, `max_ms`, `min_tokens` (in+out), `min_reasoning`, `limit` — ints. An unparseable
  numeric or selector returns a `bad_filter` 400 rather than silently coercing.

The response carries the matched nodes (flat, each tagged with its turn), a `turns` sidecar
(each involved turn's request/answer text, untruncated), and `applied`/`matched`/`returned`
counts (`matched` before `limit`, `returned` after).

## Gotchas

- Node ids are session-global view ordinals (1..M in transcript order, after plumbing nodes
  are pruned) — not `trace_runs` UUIDs, and not the `turn_id` in the trace path.
- `turn=N` is the 1-based ordinal in the view (each DB exchange splits into a user turn and an
  agent turn). The `turn_id` in the trace path is the DB primary key — a different number.
- `truncated: [...]` on a node means the value hit the capture cap at record time; ground
  truth needs `/export` or psql, not the view.
- JSON and Markdown render the same view dict.
