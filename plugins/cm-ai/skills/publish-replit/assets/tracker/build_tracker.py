"""Build a Replit-port roadmap tracker page from a project's plan and tracker config.

Generic builder shipped with the cm-ai:publish-replit skill. Copy it, template.html and config_example.py into the
project's `tracker/` folder, rename the config to `config.py`, then:

    set -o pipefail; python3 tracker/build_tracker.py            # uses tracker/config.py
    python3 tracker/build_tracker.py --config path/to/config.py

Prompts are read from the plan: every blockquote whose first line is `> <HEADER> | Task <id>: <name>`.
Everything else (links, notes, deps, map position, extra prompts) lives in the config's TASKS list.
PR state is read from GitHub with `gh` on every build: a merged PR makes its task "done" and an open one
gets a live status line, so after a merge just re-run and republish. If `gh` fails for a PR, the
hand-written state and status are kept.
"""

import argparse
import datetime
import json
import re
import runpy
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "template.html"
STATES = ("done", "review", "running", "ready", "blocked")


def unwrap(lines):
    """Turn hard-wrapped blockquote lines into paragraphs and one-line bullets."""
    blocks = []  # [kind, text]
    fresh = True
    for raw in lines:
        if not raw.strip():
            fresh = True
            continue
        is_item = bool(re.match(r"(- |\d+\. )", raw))
        indented = raw.startswith("  ")
        if is_item:
            blocks.append(["item", raw.strip()])
        elif not fresh and blocks and (blocks[-1][0] == "para" or indented):
            blocks[-1][1] += " " + raw.strip()
        else:
            blocks.append(["para", raw.strip()])
        fresh = False
    out = ""
    for i, (kind, text) in enumerate(blocks):
        if i:
            out += "\n" if kind == "item" and blocks[i - 1][0] == "item" else "\n\n"
        out += text
    return out


def read_prompts(plan, header):
    md = plan.read_text().split("\n")
    pattern = re.compile(r"> " + re.escape(header) + r" \| Task (\w+):")
    prompts, i = {}, 0
    while i < len(md):
        m = pattern.match(md[i])
        if m:
            j = i
            while j < len(md) and md[j].startswith(">"):
                j += 1
            prompts[m.group(1)] = unwrap([line[2:] if line.startswith("> ") else "" for line in md[i:j]])
            i = j
        else:
            i += 1
    return prompts


def github_state(pr):
    """Live state of one PR: (merged, status line), or None when gh cannot be reached."""
    m = re.match(r"https://github.com/([^/]+/[^/]+)/pull/(\d+)", pr["url"])
    fields = "state,mergedAt,reviewDecision,reviewRequests,mergeStateStatus,statusCheckRollup"
    try:
        raw = subprocess.run(["gh", "pr", "view", m.group(2), "--repo", m.group(1), "--json", fields],
                             capture_output=True, text=True, timeout=60, check=True).stdout
        d = json.loads(raw)
    except Exception as err:  # offline, not logged in, gh missing: keep what the config says
        print(f"  gh failed for {pr['label']}: {str(err)[:120]}")
        return None
    if d["state"] == "MERGED":
        when = datetime.datetime.fromisoformat(d["mergedAt"].replace("Z", "+00:00"))
        return True, "Merged " + when.strftime("%-d %b")
    if d["state"] == "CLOSED":
        return False, "Closed without merging"
    parts = ["Open"]
    who = ", ".join(r.get("login") or r.get("name") or r.get("slug") or "" for r in d["reviewRequests"])
    review = {"APPROVED": "approved", "CHANGES_REQUESTED": "changes requested"}.get(d["reviewDecision"])
    parts.append(review or ("review required" + (f" ({who} requested)" if who else "")))
    merge = {"DIRTY": "conflicts with the base branch, needs a rebase", "BEHIND": "behind the base branch",
             "CLEAN": "ready to merge"}.get(d["mergeStateStatus"])
    if merge:
        parts.append(merge)
    checks = [(c.get("name") or c.get("context"), c.get("conclusion") or c.get("state")) for c in d["statusCheckRollup"]]
    bad = sorted({n for n, r in checks if r in ("FAILURE", "ERROR", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED")})
    waiting = [n for n, r in checks if r in (None, "", "PENDING", "QUEUED", "IN_PROGRESS", "EXPECTED")]
    if bad:
        parts.append("failing: " + ", ".join(bad[:4]) + (" and more" if len(bad) > 4 else ""))
    elif waiting:
        parts.append("checks running")
    elif checks:
        parts.append("checks green")
    return False, " · ".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(HERE / "config.py"))
    ap.add_argument("--offline", action="store_true", help="skip the GitHub lookups")
    args = ap.parse_args()
    cfg_path = Path(args.config).resolve()
    cfg = runpy.run_path(str(cfg_path))
    P, TASKS = cfg["PROJECT"], cfg["TASKS"]
    base = cfg_path.parent
    plan = (base / P["plan_path"]).resolve()
    out = (base / P["out_path"]).resolve()

    prompts = read_prompts(plan, P["header"])
    by_id = {t["id"]: t for t in TASKS}
    ids = [t["id"] for t in TASKS]
    assert len(ids) == len(set(ids)), "duplicate task ids"
    for t in TASKS:
        t.setdefault("state", None)
        t.setdefault("deps", [])
        t.setdefault("kind", "casper")
        t.setdefault("col", None)
        t.setdefault("row", 0)
        t.setdefault("short", t["title"])
        for d, _ in t["deps"]:
            assert d in by_id, f"task {t['id']} depends on unknown task {d}"
        live = github_state(t["pr"]) if t.get("pr") and not args.offline else None
        if live:
            merged, t["pr"]["status"] = live
            if merged:
                t["state"] = "done"
            elif t["state"] == "done":
                t["state"] = "review"
    for t in TASKS:
        t["base"] = t["state"]  # fixed state from the config; None = the page works it out from deps
        t["deps"] = [dict(id=d, need=n) for d, n in t["deps"]]

    def state(t, seen=()):
        assert t["id"] not in seen, f"dependency cycle through task {t['id']}"
        if t["state"]:
            return t["state"]
        ok = True
        for d in t["deps"]:
            s = state(by_id[d["id"]], seen + (t["id"],))
            d["met"] = s == "done" or (d["need"] == "built" and s == "review")
            ok = ok and d["met"]
        t["state"] = "ready" if ok else "blocked"
        return t["state"]

    for t in TASKS:
        state(t)
        for d in t["deps"]:
            s = by_id[d["id"]]["state"]
            d.setdefault("met", s == "done" or (d["need"] == "built" and s == "review"))
    for t in TASKS:
        t["unblocks"] = [u["id"] for u in TASKS if any(d["id"] == t["id"] for d in u["deps"])]
        t["prompts"] = []
        if t["id"] in prompts:
            sent = t["state"] in ("done", "review", "running")
            t["prompts"].append(dict(
                label="Prompt as sent" if sent else t.pop("prompt_label", "Prompt"),
                where="Already sent" if sent else t.pop("prompt_where", "Paste as a new Casper thread"),
                text=prompts[t["id"]], sent=sent))
        t.pop("prompt_label", None)
        t.pop("prompt_where", None)
        t["prompts"] += t.pop("extra_prompts", [])
    missing = [t["id"] for t in TASKS if not t["prompts"] and t["state"] != "done"]
    assert not missing, f"no prompt or checklist for {missing}: add a `> {P['header']} | Task N:` block or extra_prompts"
    unplaced = [t["id"] for t in TASKS if t["col"] is None]
    if unplaced:
        print("  not on the map (col=None):", unplaced)

    data = dict(
        asOf=datetime.date.today().strftime("%-d %b %Y"), title=P["title"], eyebrow=P.get("eyebrow", ""),
        intro=P["intro"], header=P["header"], key=P["storage_key"], org=P.get("github_org", "chartmetric"),
        planUrl=P["plan_url"], planName=plan.name, planBranch=P["plan_branch"], lanes=P["lanes"],
        tasks=TASKS, slackBase=P["slack_base"], channel=P["channel"], since=P["since"])
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text().replace("/*__DATA__*/null", blob).replace("__TITLE__", P["title"])
    out.write_text(html)
    print(out, {s: sum(t["state"] == s for t in TASKS) for s in STATES})


if __name__ == "__main__":
    main()
