---
name: reading-casper-sessions-db
description: Read a Casper agent session (turns, answers, tool calls, trace) straight from the casper Postgres schema with Maestro's query_postgres. Use when you need to inspect, analyze, or diagnose a Casper session, or are handed a Casper console session link or Slack thread, while the Casper console and its session read API are down.
---

# Reading Casper sessions from the database

Use this skill while the Casper console is down. The session read API that `reading-casper-sessions`
uses lives in the console, so it returns 503 until the console is back. These queries read the same data
from the `casper` schema on the read replica through Maestro's `query_postgres`. No token needed.

A session id is `channel:thread_ts`, such as `C05GH9DQAJ3:1795539685.653749`. From a console link, take
the id from the URL. From a Slack thread, it's the channel id and the thread's parent `ts`.

## Tables

- `casper.sessions`: one row per session (`id`, `title`, `status`, `turn_count`, `started_at`,
  `last_activity_at`, totals).
- `casper.turns`: one row per user request (`id`, `session_id`, `request_text`, `answer_text`, `status`,
  `model`, `steps_used`, `cost_usd`, `error`, `created_at`).
- `casper.trace_runs`: one row per trace node (`turn_id`, `session_id`, `run_type` = `llm` | `tool` |
  `chain`, `name`, `status`, `start_time`, `end_time`, `inputs`, `outputs`, `error`, token counts).
  Sessions run to thousands of rows here.

## Queries

Results are capped, so pass `max_rows`, and wrap `request_text`, `answer_text`, `inputs` and `outputs` in
`left(..., N)` until you know which row you need in full.

```sql
-- 1. The session and its turns
SELECT id, title, status, turn_count, started_at, last_activity_at FROM casper.sessions WHERE id = '<sid>';
SELECT id AS turn_id, created_at, status, model, steps_used, cost_usd,
       left(request_text, 300) AS request, left(answer_text, 300) AS answer, error
FROM casper.turns WHERE session_id = '<sid>' ORDER BY created_at;

-- 2. Shape of one turn: what ran, how often, how long, what failed
SELECT run_type, name, status, count(*) AS n, sum(total_tokens) AS tokens,
       round(sum(extract(epoch FROM end_time - start_time))::numeric, 1) AS secs,
       count(*) FILTER (WHERE error IS NOT NULL) AS errors
FROM casper.trace_runs WHERE session_id = '<sid>' AND turn_id = <turn_id>
GROUP BY 1, 2, 3 ORDER BY n DESC;

-- 3. Tool calls in order
SELECT row_number() OVER (ORDER BY start_time) AS n, name, status,
       round(extract(epoch FROM end_time - start_time)::numeric, 1) AS secs,
       left(inputs::text, 300) AS inputs, left(outputs::text, 300) AS outputs, error
FROM casper.trace_runs
WHERE session_id = '<sid>' AND turn_id = <turn_id> AND run_type = 'tool'
ORDER BY start_time;

-- 4. One node in full, once you know which (run_id from a query like 3 with run_id added)
SELECT inputs, outputs, error, truncated FROM casper.trace_runs WHERE run_id = '<uuid>';
```

Start with 1, then 2 for the turn you care about, then 3 and 4. Never pull a whole session's
`trace_runs` with full `inputs`/`outputs`. It won't fit in the result cap or your context.

## Gotchas

- `turn_id` in `trace_runs` is `turns.id`, the database key. It is not the 1-based turn number the
  console shows.
- While Casper is down, a turn with `status = 'running'` and no answer was cut off when it stopped.
- `truncated` on a node lists fields that hit the capture cap when recorded. The full value is gone.
- Maestro is read-only. Don't try to change rows here.
