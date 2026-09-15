#!/usr/bin/env python3
"""Export a Replit data pack (and its parity fixture) from a DS notebook's output.

This is the OFFLINE path. ClickHouse Cloud is internet-facing and a Replit app can
query it directly — rw-standard and ro-standard already carry a Replit egress address
in their IP access lists. Use this exporter when you want a snapshot that cannot change
under the app, when the app must run without credentials, or while the account the app
would use still lacks SELECT on the output table.

Usage
-----
    source ~/code/chartmetric/devin-secrets.env      # MUST be sourced, see below
    python3 export_pack.py --all --limit 500         # bounded first pass, always
    python3 export_pack.py --all                     # then the real thing
    python3 export_pack.py --parity --out ../data    # fixture only

Stdlib only, HTTPS interface, read-only. Nothing here writes to any database.

Two gotchas that cost real time, both encoded below:

  * devin-secrets.env is UNQUOTED AND SHELL-ESCAPED — it is a bash script, not a dotenv
    file. `clickhouse_password` contains a `\\!` that `source` resolves to a bare `!`.
    python-dotenv, `docker --env-file` and naive regexes all pass a WRONG password and
    get `Code: 516 Authentication failed`, which reads like a permissions problem.

  * The shared `external_devin` account is HTTPS-ONLY. The native protocol on 9440
    rejects it with the same Code 516 while a request to 8443 with identical
    credentials succeeds. Personal accounts work on both. Hence HTTPS here.
"""
import argparse
import base64
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

# ── Warehouses ───────────────────────────────────────────────────────────────
# Each name is tried in order, in its exact, upper and lower spellings. The CH_* names
# belong to the notebook container; CLICKHOUSE_* is what Replit uses; the lowercase
# names are what devin-secrets.env carries. A script that must run in both places
# should accept all of them rather than picking one.
WAREHOUSES = {
    "rw": dict(
        host_envs=("CH_HOST", "CLICKHOUSE_HOST", "clickhouse_host"),
        host_default="grkyl47mbo.us-west-2.aws.clickhouse.cloud",
        user_envs=("CH_USER", "CLICKHOUSE_USER", "clickhouse_user"),
        pw_envs=("CH_PASSWORD", "CLICKHOUSE_PASSWORD", "clickhouse_password"),
        expect="chartmetric_analytics",
    ),
    "vert": dict(
        host_envs=("CH_VERT_HOST", "CLICKHOUSE_VERT_HOST", "clickhouse_newverticals_host"),
        host_default="j1ez4a7j4k.us-west-2.aws.clickhouse.cloud",
        user_envs=("CH_VERT_USER", "CLICKHOUSE_VERT_USER", "clickhouse_newverticals_user", "CH_USER"),
        pw_envs=("CH_VERT_PASSWORD", "CLICKHOUSE_VERT_PASSWORD", "clickhouse_newverticals_password", "CH_PASSWORD"),
        expect="new_vertical",
    ),
}
HTTP_PORT = os.environ.get("CLICKHOUSE_PORT", "8443")

SCORES_TABLE = "chartmetric_test.<your_table>"   # <-- the notebook's write-back
ID_CHUNK = 2000                                   # ids per IN literal


def _env_first(names, default=None):
    for n in names:
        for variant in (n, n.upper(), n.lower()):
            v = os.environ.get(variant)
            if v:
                return v.strip()
    return default


def _strip_host(h):
    return h.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]


def query(sql, warehouse="rw", params=None):
    """Run SQL, return a list of dicts. Read-only by construction — callers pass SELECTs.

    Scalars go through ClickHouse query parameters, never string interpolation.
    """
    cfg = WAREHOUSES[warehouse]
    host = _strip_host(_env_first(cfg["host_envs"], cfg["host_default"]))
    user, pw = _env_first(cfg["user_envs"]), _env_first(cfg["pw_envs"])
    if not (user and pw):
        sys.exit(f"no credentials for {warehouse}: set one of {cfg['user_envs']}. "
                 f"Did you `source ~/code/chartmetric/devin-secrets.env`?")
    qs = {
        "default_format": "JSONEachRow",
        # Without this, 64-bit ids arrive as strings and stay strings all the way into
        # the pack.
        "output_format_json_quote_64bit_integers": 0,
        "max_execution_time": 280,
    }
    for k, v in (params or {}).items():
        qs[f"param_{k}"] = v
    url = f"https://{host}:{HTTP_PORT}/?{urllib.parse.urlencode(qs)}"
    req = urllib.request.Request(url, data=sql.encode(), method="POST")
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode())
    try:
        body = urllib.request.urlopen(req, timeout=290, context=ssl.create_default_context()).read().decode()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"ClickHouse error on {warehouse}: {e.read().decode()[:500]}\n"
                         f"--- SQL ---\n{sql[:800]}")
    return [json.loads(line) for line in body.splitlines() if line.strip()]


def whoami(warehouse="rw"):
    """The account actually in use. Print it — the credential chain prefers CH_USER over
    the clickhouse_user in devin-secrets.env, so the same command picks a different
    account depending on the shell, and only one of them can read chartmetric_test."""
    return query("SELECT currentUser() AS u", warehouse)[0]["u"]


def assert_warehouse(warehouse="rw"):
    """`SELECT 1` succeeds on every warehouse and every account — it is a false-positive
    smoke test. Asserting the expected database is visible is the cheap way to prove you
    reached the cluster you meant."""
    expect = WAREHOUSES[warehouse]["expect"]
    dbs = {r["name"] for r in query("SHOW DATABASES", warehouse)}
    if expect not in dbs:
        sys.exit(f"{warehouse}: connected, but '{expect}' is not in SHOW DATABASES — "
                 f"this is not the warehouse you meant.")


def chunks(seq, size=ID_CHUNK):
    """Fixed-size slices. Chunk every id list before it becomes an IN literal: a
    14k-element literal is slow to parse and a memory risk on the server."""
    seq = list(seq)
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


# ── Notebook definitions ─────────────────────────────────────────────────────
def load_notebook_cells(cells_dir, names):
    """Execute the notebook's own cells and hand back their namespace.

    Do this rather than reimplementing the config, coercion and scoring. It is the only
    thing that keeps the pack from drifting from the definitions it is meant to carry,
    and it gives the parity fixture for free.
    """
    ns = {}
    for name in names:
        path = os.path.join(cells_dir, name)
        with open(path) as f:
            exec(compile(f.read(), path, "exec"), ns)
    return ns


# ── Pack ─────────────────────────────────────────────────────────────────────
def write_pack(entities, index, out_dir, shard_size=250, extra_manifest=None):
    """Sharded-JSON layout: manifest + lean index + shards of documents.

    For whole-population maths, write Float32Array payloads instead (see
    reference/static-pack.md) — the shape here is for per-entity documents.
    """
    os.makedirs(os.path.join(out_dir, "shards"), exist_ok=True)
    shards, shard_no, buf = [], 0, {}
    for row in index:
        buf[str(row["id"])] = entities[row["id"]]
        row["shard"] = shard_no
        if len(buf) >= shard_size:
            shards.append((shard_no, buf))
            shard_no, buf = shard_no + 1, {}
    if buf:
        shards.append((shard_no, buf))

    for n, payload in shards:
        with open(os.path.join(out_dir, "shards", f"{n}.json"), "w") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(out_dir, "index.json"), "w") as f:
        json.dump(index, f, ensure_ascii=False, separators=(",", ":"))

    manifest = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_entities": len(index),
        "shard_size": shard_size,
        "n_shards": len(shards),
        "files": {"index": "index.json", "shards": "shards/<shard>.json"},
        # Name what the pack deliberately lacks. The UI reads these into its provenance
        # footer, and an absent entity must never be read as an entity with no data.
        "notes": [
            "covers only the entities this model run scored, not the full catalogue",
            "<what else is deliberately absent>",
        ],
        **(extra_manifest or {}),
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1, ensure_ascii=False)
    return manifest


def write_parity(points, out_dir, source, tolerance=1e-6):
    """The fixture the app asserts against on load.

    Cover the edges, not just the middle: an entity missing a dimension, each taxonomy
    or label frame, the neutral/NULL-scored path, a clipped value, and every scoring
    mode. A few hundred well-chosen points beat thousands of typical ones.
    """
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": source,
        "tolerance": tolerance,
        "points": points,
    }
    with open(os.path.join(out_dir, "parity.json"), "w") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  parity: {len(points)} points, tolerance {tolerance:g}")
    return payload


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true", help="every entity in the write-back")
    ap.add_argument("--ids", help="comma-separated ids")
    ap.add_argument("--ids-file", help="file with one id per line")
    ap.add_argument("--limit", type=int, help="cap --all; always do a bounded pass first")
    ap.add_argument("--model-version", help="pin a version (default: latest present)")
    ap.add_argument("--shard-size", type=int, default=250)
    ap.add_argument("--parity", action="store_true", help="write parity.json only")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "data"))
    args = ap.parse_args()

    assert_warehouse("rw")
    print(f"rw-standard account: {whoami()}")

    version = args.model_version
    if not version:
        rows = query(f"SELECT max(model_version) AS v FROM {SCORES_TABLE}")
        version = rows[0]["v"] if rows else None
        if not version:
            sys.exit(f"{SCORES_TABLE} is empty or unreadable.\n"
                     f"  connected as '{whoami()}' — it needs SELECT on {SCORES_TABLE}.\n"
                     f"  external_devin CANNOT read chartmetric_test; use a personal account.")
        print(f"model_version: {version}")

    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)

    # ---- fill these in from the notebook -----------------------------------
    entities, index, parity_points = {}, [], []
    raise SystemExit(
        "Fill in the entity pull and the parity computation from the notebook, then "
        "delete this guard. See reference/static-pack.md for the pack layouts."
    )
    # ------------------------------------------------------------------------

    if args.parity:
        write_parity(parity_points, out_dir, source=f"{SCORES_TABLE} @ {version}")
        return

    # Refuse to write a pack that looks healthy and is empty. A pack of nulls renders
    # an empty card for every entity, which is exactly how it goes unnoticed for a week.
    if not index or not any(r.get("has_data") for r in index):
        sys.exit(
            f"REFUSING TO WRITE: not one of {len(index):,} entities carries data.\n"
            f"  connected to rw-standard as '{whoami()}'\n"
            f"  table: {SCORES_TABLE}   model_version filter: {version!r}\n"
            f"Fix the access or the version filter before shipping this pack.")

    manifest = write_pack(entities, index, out_dir, args.shard_size,
                          extra_manifest={"model_version": version})
    write_parity(parity_points, out_dir, source=f"{SCORES_TABLE} @ {version}")
    total = sum(os.path.getsize(os.path.join(dp, f))
                for dp, _, fs in os.walk(out_dir) for f in fs)
    print(f"wrote {manifest['n_entities']:,} entities in {manifest['n_shards']} shards "
          f"to {out_dir}  ({total / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
