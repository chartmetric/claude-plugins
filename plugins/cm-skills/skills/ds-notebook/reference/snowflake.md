# Snowflake — when and how (ClickHouse first)

## Decision rule: ClickHouse first

Default to ClickHouse. Reach for Snowflake **only** when the data genuinely
isn't in ClickHouse. Before writing a Snowflake query, check whether the tables
you need are mirrored to ClickHouse:

```sql
-- run against ClickHouse
SELECT database, name FROM system.tables
WHERE name IN ('table_a','table_b', ...)
  AND database IN ('chartmetric_raw_data','chartmetric_analytics', ...)
ORDER BY name
```

If they exist there, use ClickHouse — it keeps the notebook single-connection,
avoids Snowflake warehouse cost, and (often) the ClickHouse copy is the fresher
one. Many A&R "metric" scripts run against Snowflake `RAW_DATA` / `ANALYTICS`
but their inputs are also present in `chartmetric_raw_data` /
`chartmetric_analytics`.

**Always still run the freshness sentinel** (`max(date)`) on whichever store you
pick — being in ClickHouse does not guarantee it is up to date.

## Connection (only if necessary)

```python
from data_utils.snowflake_access import get_snowflake_connect, get_snowpark_session

def query_sf(sql: str) -> "pd.DataFrame":
    with get_snowflake_connect(warehouse="DATA_SCRIPTS_XS") as con:
        cur = con.cursor()
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=cols)
```

- Pick the smallest warehouse that finishes (`DATA_SCRIPTS_XS`/`_S`); don't leave
  a large warehouse spinning.
- Credentials come from `devin-secrets.env` under the `SNOWFLAKE_*` keys.
- Snowflake identifiers are conventionally UPPERCASE (`RAW_DATA.TIKTOK_USER`,
  column names returned uppercase).
- Read-only: SELECT only. Never write from an analysis notebook.

## Mixed-store notebooks

If you truly need both, keep two clearly-named helpers (`query_df` for
ClickHouse, `query_sf` for Snowflake) and note in `§1` which `TABLES` entries
live where. Prefer pulling the smaller/reference side from whichever store has it
and doing the heavy scan on ClickHouse.
