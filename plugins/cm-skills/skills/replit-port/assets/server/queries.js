/**
 * Every SQL string the app runs. Server-side only.
 *
 * The rule this file exists to enforce: the browser asks for an id, the server decides
 * the SQL. Nothing here accepts a table name, a column name or a fragment of a query
 * from a request — only scalar values, and only as ClickHouse query parameters
 * (`{id:UInt64}` in the statement, `{ id }` in the call).
 *
 * Replace SCORES_TABLE and the column lists with the notebook's own. Read the dedupe
 * discipline off the table before you write a line of this file:
 *
 *   accumulates one row per entity per day   -> WHERE timestp = (SELECT max(timestp) …)
 *   ReplacingMergeTree with a load timestamp -> FINAL, or argMax(col, ts) … GROUP BY
 *   cm_artist and friends                    -> argMax(name, modified_at) … GROUP BY id
 *
 * Getting this wrong does not error. It multiplies every count and score.
 */
import { query } from "./clickhouse.js";

const SCORES_TABLE = "chartmetric_test.<your_table>";

/** Pin one model version for the life of the process. */
export async function latestModelVersion() {
  const [row] = await query(`SELECT max(model_version) AS v FROM ${SCORES_TABLE}`);
  if (!row?.v) {
    throw new Error(
      `${SCORES_TABLE} is empty or unreadable. If this is a scratch database, the ` +
        `account may lack the grant: external_devin cannot read chartmetric_test.`
    );
  }
  return row.v;
}

/**
 * The searchable index: one lean row per entity, pulled once at boot.
 *
 * Keep it lean — id, name, and the few flags the picker shows. Images and documents
 * are fetched per entity. A wide index is the difference between an in-memory search
 * and a memory problem.
 *
 * cm_artist carries un-merged duplicate ids, so the name lookup needs argMax + GROUP BY.
 * Do NOT read cm_artist.image_url; it is populated for 0.03% of rows. Images come from
 * chartmetric_analytics_flattened.f_artist_image.
 */
export async function entityIndex(modelVersion) {
  return query(
    `
    WITH scored AS (
        SELECT s.cm_artist AS id
        FROM ${SCORES_TABLE} AS s
        WHERE s.model_version = {version:String}
        GROUP BY s.cm_artist
    )
    SELECT sc.id AS id, n.name AS name
    FROM scored AS sc
    LEFT JOIN (
        SELECT id, argMax(name, modified_at) AS name
        FROM chartmetric_raw_data.cm_artist
        WHERE is_duplicate = false
        GROUP BY id
    ) AS n ON n.id = sc.id
    `,
    { version: modelVersion }
  );
}

/**
 * One entity's document.
 *
 * Pivot server-side. A long-format table whose sorting key starts with the entity id
 * returns one entity in milliseconds when the pivot happens in SQL (`sumIf(weight,
 * col = '…')` per output column); selecting raw rows and pivoting in JS ships thousands
 * of rows to do the same thing slower.
 *
 * The inner argMax is the ReplacingMergeTree dedupe. It is cheaper than FINAL for a
 * single-key lookup and it is *required* for correctness if a write-back ever ran twice
 * for one model_version — summing undeduped long-format rows doubles every share.
 */
export async function entityDocument(id, modelVersion) {
  const rows = await query(
    `
    WITH d AS (
        SELECT s.<group_col> AS grp,
               s.<key_col>   AS key,
               argMax(s.<value_col>, s.created_at) AS val
        FROM ${SCORES_TABLE} AS s
        WHERE s.model_version = {version:String} AND s.cm_artist = {id:UInt64}
        GROUP BY grp, key
    )
    SELECT grp,
           sumIf(val, key = '<CELL_A>') AS cell_a,
           sumIf(val, key = '<CELL_B>') AS cell_b
    FROM d
    GROUP BY grp
    `,
    { version: modelVersion, id }
  );
  if (!rows.length) return null; // render the empty state; never fabricate
  return { id, rows };
}

/**
 * Chunk any id list before it becomes an IN literal. A 14k-element literal is slow to
 * parse and a memory risk on the server.
 */
export function chunks(seq, size = 2000) {
  const out = [];
  for (let i = 0; i < seq.length; i += size) out.push(seq.slice(i, i + size));
  return out;
}
