---
name: reading-casper-sessions
description: Read a Casper agent session, its transcript and trace, from the casper Postgres schema with Maestro's query_postgres. Use when you need to inspect, analyze, or diagnose behavior in a specific Casper session. Use when handed a Casper console session link or if you grab the link yourself from an associated Slack thread.
---

# Reading Casper sessions

A session lives in three tables in the `casper` schema: `sessions` (one row), `turns` (one row per
user request) and `trace_runs` (every trace node, often thousands per session). Read them with
Maestro's `query_postgres`. It is read-only and needs no token. Every result lands in your context,
so read the session the lean way: skim it, then pull only the nodes you need.

The session id is `channel:thread_ts`, such as `C05GH9DQAJ3:1795539685.653749`. Take it from a
console link, or from a Slack thread's channel id and parent `ts`. Replace `<sid>` below with it.

## The node view

Every node query starts with this CTE. It mirrors the console's session view:

- It drops plumbing nodes. These are successful `chain` wrappers named `model` or `tools`, or ending
  in `.before_model`, `.after_model`, `.before_agent` or `.after_agent`. That usually removes about
  three quarters of the rows.
- It numbers the remaining nodes `n` = 1..M across the whole session, in start-time order.
- It numbers the turns `turn` = 1..T.
- It extracts the readable fields: a tool's `inputs` and `output`, and an LLM's `output` text,
  `reasoning` and `tool_calls`. An LLM's prompt history is never shown.

```sql
WITH t AS (SELECT id, row_number() OVER (ORDER BY created_at) AS turn
           FROM casper.turns WHERE session_id = '<sid>'),
v AS (
  SELECT row_number() OVER (ORDER BY r.start_time, r.run_id) AS n, t.turn, r.run_id,
         r.run_type AS type, r.name, r.status,
         (extract(epoch FROM r.end_time - r.start_time) * 1000)::int AS ms,
         r.total_tokens AS tokens, r.reasoning_tokens,
         CASE WHEN r.run_type = 'tool' THEN r.inputs::text END AS inputs,
         CASE WHEN r.run_type = 'tool' THEN coalesce(r.outputs->>'output', r.outputs::text)
              WHEN r.run_type = 'llm' THEN r.outputs->'generations'->0->0->'message'->'kwargs'->>'content'
         END AS output,
         r.outputs->'generations'->0->0->'message'->'kwargs'->'additional_kwargs'->>'reasoning' AS reasoning,
         (SELECT string_agg((tc->>'name') || ' ' || (tc->'args')::text, ' | ')
            FROM jsonb_array_elements(r.outputs->'generations'->0->0->'message'->'kwargs'->'tool_calls') tc
         ) AS tool_calls,
         r.error, r.truncated
  FROM casper.trace_runs r JOIN t ON t.id = r.turn_id
  WHERE r.session_id = '<sid>'
    AND NOT (r.run_type = 'chain' AND r.error IS NULL AND coalesce(r.status, 'success') = 'success'
             AND (r.name IN ('model', 'tools')
                  OR r.name ~ '\.(before_agent|after_model|before_model|after_agent)$')))
```

## Reads, leanest first

**1. Lean: the session and its turns.** Run this first. Long text is cut to its first 600 and last
200 characters, with the number of cut characters shown in the middle.

```sql
SELECT row_number() OVER (ORDER BY created_at) AS turn, id AS turn_id, created_at, user_id, status,
       model, steps_used, cost_usd, error,
       CASE WHEN length(q) <= 800 THEN q ELSE left(q, 600) || ' …(+' || (length(q) - 800) || ' chars)… ' || right(q, 200) END AS request,
       CASE WHEN length(a) <= 800 THEN a ELSE left(a, 600) || ' …(+' || (length(a) - 800) || ' chars)… ' || right(a, 200) END AS answer
FROM casper.turns
CROSS JOIN LATERAL (SELECT regexp_replace(request_text, '\s+', ' ', 'g') AS q,
                           regexp_replace(answer_text, '\s+', ' ', 'g') AS a) x
WHERE session_id = '<sid>' ORDER BY created_at;
```

**2. Outline: what ran, with no I/O.** Use it to find the nodes worth reading.

```sql
-- <the node view CTE>
SELECT n, turn, type, name, status, ms, tokens, reasoning_tokens, error IS NOT NULL AS failed
FROM v WHERE turn = 2 ORDER BY n LIMIT 200;
-- or a per-turn summary: SELECT turn, type, count(*), min(n), max(n), sum(ms) FROM v GROUP BY 1, 2 ORDER BY 1, 2;
```

**3. Nodes: chosen nodes with their I/O, cut to the first 400 and last 150 characters.**

```sql
-- <the node view CTE>
SELECT n, turn, type, name, status, ms, tokens,
  CASE WHEN length(x.i) <= 550 THEN x.i ELSE left(x.i, 400) || ' …(+' || (length(x.i) - 550) || ' chars)… ' || right(x.i, 150) END AS inputs,
  CASE WHEN length(x.o) <= 550 THEN x.o ELSE left(x.o, 400) || ' …(+' || (length(x.o) - 550) || ' chars)… ' || right(x.o, 150) END AS output,
  CASE WHEN length(x.r) <= 550 THEN x.r ELSE left(x.r, 400) || ' …(+' || (length(x.r) - 550) || ' chars)… ' || right(x.r, 150) END AS reasoning,
  CASE WHEN length(x.c) <= 550 THEN x.c ELSE left(x.c, 400) || ' …(+' || (length(x.c) - 550) || ' chars)… ' || right(x.c, 150) END AS tool_calls,
  error, truncated
FROM v CROSS JOIN LATERAL (SELECT regexp_replace(v.inputs, '\s+', ' ', 'g') AS i,
                                  regexp_replace(v.output, '\s+', ' ', 'g') AS o,
                                  regexp_replace(v.reasoning, '\s+', ' ', 'g') AS r,
                                  regexp_replace(v.tool_calls, '\s+', ' ', 'g') AS c) x
WHERE n BETWEEN 40 AND 50 ORDER BY n;
```

**4. Full: one node uncut.** Select `inputs, output, reasoning, tool_calls, error` from `v` for a
single `n`. Do this only after a cut view showed you need the middle.

## Filters

Put these in the `WHERE` of reads 2 and 3. A node query always needs at least one, because the
whole session won't fit in the result cap or in your context.

- `n = 7`, `n BETWEEN 3 AND 10`, `n IN (3, 9)`
- `turn = 2`, `turn BETWEEN 2 AND 4`
- `type = 'tool'` (`llm`, `tool` or `chain`), `name = 'execute'`, `status <> 'success'`, `error IS NOT NULL`
- `ms >= 10000`, `tokens >= 50000`, `reasoning_tokens >= 2000`
- `ORDER BY n LIMIT 20`

## Questions about the whole session

Answer these with SQL aggregates over `v`, never by pulling rows. Examples: count tool failures by
`name`, find the slowest nodes with `ORDER BY ms DESC LIMIT 10`, or sum tokens per turn.

## Gotchas

- `n` and `turn` come from this query. They match each other across your queries, but they are not
  `trace_runs.run_id` and not `turns.id`. Read 1 returns `turn_id` (`turns.id`) for joining.
- `truncated` lists fields that hit the capture cap when the node was recorded. The rest of that
  value was never stored.
- A turn with `status = 'running'` and no answer either is still running or was cut off. Check
  `last_activity_at` in `casper.sessions`.
- Pass `max_rows` to `query_postgres` to match your `LIMIT`. Maestro caps results and flags them as
  `truncated`.
