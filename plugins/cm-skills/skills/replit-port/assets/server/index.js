/**
 * Replit server for a DS notebook port. Zero dependencies — runs on a bare Node
 * template with no install step.
 *
 * Shape, which is the whole point of this file:
 *   - secrets validated at BOOT, not on first request
 *   - ONE bulk pull of the entity index into memory, refreshed on an interval
 *   - per-entity documents fetched on demand and cached for a few minutes
 *   - search runs against the in-memory index, never against the database
 *   - every SQL string lives in queries.js, server-side, parameterised
 *
 * Replace <entity> with the thing this app is about (artist, profile, track).
 */
import { createServer } from "node:http";
import { createReadStream, promises as fs } from "node:fs";
import { extname, join, normalize, resolve } from "node:path";
import { assertReady, query } from "./clickhouse.js";
import * as Q from "./queries.js";

const PORT = process.env.PORT || 3000;
const STATIC_ROOT = resolve(process.cwd(), "dist"); // Vite build output
const INDEX_REFRESH_MS = 30 * 60 * 1000;
const DOC_TTL_MS = 5 * 60 * 1000;

// ── State ───────────────────────────────────────────────────────────────────
// The index is small enough to hold entirely (tens of thousands of lean rows) and is
// the reason search never touches the database. If your population is in the hundreds
// of thousands with wide rows, seed a local SQLite/Parquet store at boot instead and
// keep only the searchable columns here.
const state = {
  index: [],
  search: [], // { id, haystack } — lowercased once, at load
  modelVersion: null,
  pulledAt: null,
  docs: new Map(), // id -> { at, doc }
};

/** One model version per process. Reading max() per request would mix two runs in one
 *  view the moment a write-back lands mid-session. */
async function loadIndex() {
  const version = await Q.latestModelVersion();
  const rows = await Q.entityIndex(version);

  // The dedupe discipline is not optional — assert it rather than trusting it. A table
  // that starts accumulating one row per entity per day turns every count into a
  // multiple of itself, silently.
  const distinct = new Set(rows.map((r) => r.id)).size;
  if (distinct !== rows.length) {
    throw new Error(
      `index has ${rows.length} rows but only ${distinct} distinct ids — ` +
        `the dedupe filter in queries.js is missing or wrong.`
    );
  }

  state.index = rows;
  state.search = rows.map((r) => ({ id: r.id, haystack: r.name.toLowerCase() }));
  state.modelVersion = version;
  state.pulledAt = new Date().toISOString();
  console.log(`index: ${rows.length.toLocaleString()} entities @ ${version}`);
}

async function getDoc(id) {
  const hit = state.docs.get(id);
  if (hit && Date.now() - hit.at < DOC_TTL_MS) return hit.doc;
  const doc = await Q.entityDocument(id, state.modelVersion);
  state.docs.set(id, { at: Date.now(), doc });
  return doc;
}

// ── Routes ──────────────────────────────────────────────────────────────────
const routes = {
  /** Prefix matches first, then substring, capped. Never a database round trip. */
  "/api/search": ({ url }) => {
    const q = (url.searchParams.get("q") || "").toLowerCase().trim();
    if (!q) return [];
    const prefix = [], substr = [];
    for (const row of state.search) {
      if (row.haystack.startsWith(q)) prefix.push(row.id);
      else if (row.haystack.includes(q)) substr.push(row.id);
      if (prefix.length >= 50) break;
    }
    const ids = [...prefix, ...substr].slice(0, 50);
    const byId = new Map(state.index.map((r) => [r.id, r]));
    return ids.map((id) => byId.get(id));
  },

  "/api/meta": () => ({
    model_version: state.modelVersion,
    n_entities: state.index.length,
    pulled_at: state.pulledAt,
  }),

  /** Admin: re-run the bulk pull. Never wired to a user-facing control that fires often. */
  "/api/refresh": async () => {
    await loadIndex();
    state.docs.clear();
    return { ok: true, pulled_at: state.pulledAt };
  },
};

async function handle(req, res) {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const path = url.pathname;

  if (path.startsWith("/api/")) {
    try {
      let body;
      const m = path.match(/^\/api\/entity\/(\d+)$/);
      if (m) body = await getDoc(Number(m[1]));
      else if (routes[path]) body = await routes[path]({ url, req });
      else return send(res, 404, { error: "not found" });
      return send(res, 200, body);
    } catch (err) {
      // Fail visibly. Never fall back to a cached entity and present it as live.
      console.error(err);
      return send(res, 502, { error: "data source unavailable", detail: String(err.message) });
    }
  }

  return serveStatic(res, path);
}

function send(res, status, body) {
  const json = JSON.stringify(body);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(json),
  });
  res.end(json);
}

const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".geojson": "application/json; charset=utf-8",
  // Float32Array payloads must arrive as clean bytes for fetch().arrayBuffer().
  ".f32": "application/octet-stream",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
};

async function serveStatic(res, path) {
  try {
    if (path.endsWith("/")) path += "index.html";
    // Contain every request inside the root — normalize collapses ../ before resolve.
    const target = join(STATIC_ROOT, normalize(decodeURIComponent(path)).replace(/^(\.\.[/\\])+/, ""));
    if (!target.startsWith(STATIC_ROOT)) return res.writeHead(403).end("forbidden");
    const stat = await fs.stat(target);
    if (!stat.isFile()) throw new Error("not a file");
    res.writeHead(200, {
      "Content-Type": TYPES[extname(target)] || "application/octet-stream",
      "Content-Length": stat.size,
    });
    createReadStream(target).pipe(res);
  } catch {
    // SPA fallback
    try {
      const html = await fs.readFile(join(STATIC_ROOT, "index.html"));
      res.writeHead(200, { "Content-Type": TYPES[".html"] }).end(html);
    } catch {
      res.writeHead(404, { "Content-Type": "text/plain" }).end("not found");
    }
  }
}

// ── Boot ────────────────────────────────────────────────────────────────────
console.log("checking ClickHouse configuration…");
await assertReady(); // throws on a missing secret or the wrong warehouse
await loadIndex();
setInterval(() => loadIndex().catch((e) => console.error("index refresh failed", e)), INDEX_REFRESH_MS);

createServer(handle).listen(PORT, "0.0.0.0", () => {
  console.log(`listening on http://0.0.0.0:${PORT}`);
});
