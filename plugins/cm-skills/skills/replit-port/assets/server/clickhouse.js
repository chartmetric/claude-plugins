/**
 * ClickHouse over the HTTPS interface. Server-side only — this module reads
 * credentials from process.env and must never be imported by client code.
 *
 * Zero dependencies: Node 18+ has global fetch.
 *
 * Why HTTPS (8443) and not the native protocol (9440): the shared `external_devin`
 * service account is HTTPS-only and rejects 9440 with `Code: 516 Authentication
 * failed`, which reads like a wrong password. Personal accounts work on both, so this
 * fails only once you switch to the service account. Use HTTPS everywhere.
 */

/**
 * The two Chartmetric warehouses. They are separate ClickHouse Cloud services with
 * separate storage: no account holds the REMOTE grant, so they cannot be joined in
 * SQL. If you need both, query both and merge here in the server.
 *
 * `expect` is the database that must appear in SHOW DATABASES for the connection to be
 * the one you think it is. `SELECT 1` succeeds on both warehouses and against every
 * account — it is a false-positive smoke test and cannot tell them apart.
 */
export const WAREHOUSES = {
  rw: {
    env: {
      host: "CLICKHOUSE_HOST",
      port: "CLICKHOUSE_PORT",
      user: "CLICKHOUSE_USER",
      password: "CLICKHOUSE_PASSWORD",
    },
    expect: "chartmetric_analytics",
  },
  vert: {
    env: {
      host: "CLICKHOUSE_VERT_HOST",
      port: "CLICKHOUSE_PORT",
      user: "CLICKHOUSE_VERT_USER",
      password: "CLICKHOUSE_VERT_PASSWORD",
    },
    expect: "new_vertical",
  },
};

/** Warehouses this app actually uses. Trim to what you need — every name listed here
 *  is required at boot, and requiring a secret nobody set is its own kind of outage. */
export const USED = ["rw"];

const DEFAULT_PORT = "8443";

function config(name) {
  const wh = WAREHOUSES[name];
  if (!wh) throw new Error(`unknown warehouse ${name}`);
  const get = (key, fallback) => {
    const v = process.env[wh.env[key]];
    return v ? v.trim() : fallback;
  };
  // No fallback for host/user/password on purpose: a default would turn a missing
  // secret into a connection to the wrong place that returns plausible rows.
  return {
    host: (get("host") || "").replace(/^https?:\/\//, "").split("/")[0].split(":")[0],
    port: get("port", DEFAULT_PORT),
    user: get("user"),
    password: get("password"),
    expect: wh.expect,
    names: wh.env,
  };
}

/**
 * Run a SELECT and return rows as objects.
 *
 * Parameters are passed as ClickHouse query parameters, never interpolated into the
 * SQL — write `{id:UInt64}` in the statement and pass `{ id }` here. The browser asks
 * for an id; this module decides the SQL. Never let a request supply a query, a table
 * name or a column name.
 */
export async function query(sql, params = {}, warehouse = "rw") {
  const cfg = config(warehouse);
  const search = new URLSearchParams({
    default_format: "JSONEachRow",
    // Without this, 64-bit ids arrive as strings and silently become strings
    // everywhere downstream.
    output_format_json_quote_64bit_integers: "0",
    max_execution_time: "30",
  });
  for (const [k, v] of Object.entries(params)) search.set(`param_${k}`, String(v));

  const auth = Buffer.from(`${cfg.user}:${cfg.password}`).toString("base64");
  const res = await fetch(`https://${cfg.host}:${cfg.port}/?${search}`, {
    method: "POST",
    headers: { Authorization: `Basic ${auth}`, "Content-Type": "text/plain" },
    body: sql,
  });

  if (!res.ok) {
    const detail = (await res.text()).slice(0, 500);
    // Surface the warehouse and the account: most failures here are a grant or a
    // wrong-warehouse problem, and the ClickHouse message alone does not say which.
    throw new Error(`ClickHouse ${res.status} on ${warehouse}: ${detail}`);
  }

  const body = await res.text();
  return body
    .split("\n")
    .filter((line) => line.trim())
    .map((line) => JSON.parse(line));
}

/** The account actually in use. Worth logging at boot — which account you get depends
 *  on the environment, and only some of them can read a scratch database. */
export async function whoami(warehouse = "rw") {
  const [row] = await query("SELECT currentUser() AS u", {}, warehouse);
  return row.u;
}

/**
 * Validate configuration before the app serves a single request.
 *
 * Fails loudly and specifically: a missing secret is a boot-time crash naming the
 * variable, not a 500 on someone's first search. Also asserts the expected database is
 * visible, which is the only cheap way to prove you reached the warehouse you meant.
 */
export async function assertReady(warehouses = USED) {
  const missing = [];
  for (const name of warehouses) {
    const cfg = config(name);
    for (const key of ["host", "user", "password"]) {
      if (!cfg[key]) missing.push(cfg.names[key]);
    }
  }
  if (missing.length) {
    throw new Error(
      `missing Replit Secrets: ${missing.join(", ")}\n` +
        `Set them in the Secrets pane. Note the spelling is CLICKHOUSE_* — the CH_* ` +
        `names belong to the notebook container and are not read here.`
    );
  }

  for (const name of warehouses) {
    const cfg = config(name);
    const dbs = (await query("SHOW DATABASES", {}, name)).map((r) => r.name);
    if (!dbs.includes(cfg.expect)) {
      throw new Error(
        `${name}: connected, but '${cfg.expect}' is not in SHOW DATABASES — ` +
          `this is not the warehouse you meant. Check ${cfg.names.host}.`
      );
    }
    console.log(`  ${name}: ${await whoami(name)} @ ${cfg.host} ✓`);
  }
}
