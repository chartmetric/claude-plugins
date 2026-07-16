#!/usr/bin/env python3
"""Regenerate the self-contained, droppable SKILL.md bundle from the multi-file
ds-notebook skill, so the desktop app can be kept in sync with the CLI copy.

The CLI reads the lean multi-file skill at ~/.claude/skills/ds-notebook/. The
desktop app reads its own store and only accepts a single SKILL.md that starts
with YAML frontmatter. This script inlines the reference docs, the build script,
and the rendered template into one valid SKILL.md and writes it to a target the
user drags into the desktop app (default ~/Downloads/SKILL.md).

Modes:
  python3 sync_bundle.py                 # regenerate unconditionally -> default target
  python3 sync_bundle.py /path/out.md    # regenerate to a specific target
  python3 sync_bundle.py --hook          # hook mode: read a PostToolUse JSON event on
                                         # stdin; regenerate ONLY if the changed file is
                                         # under the skill dir. Always exits 0 (never
                                         # blocks the tool). Used by the autosync hook.
"""
import json
import os
import re
import sys

HOME     = os.path.expanduser("~")
SKILL_DIR = os.path.join(HOME, ".claude", "skills", "ds-notebook")
DEFAULT_TARGET = os.path.join(HOME, "Downloads", "SKILL.md")

REFERENCES = ["workflow", "clickhouse", "snowflake", "validation", "caching"]


def _read(path):
    with open(path) as f:
        return f.read().rstrip("\n")


def _demote(md, by=2):
    """Shift every ATX heading down `by` levels so inlined docs nest under an appendix."""
    return re.sub(r'(?m)^(#{1,6})(\s)',
                  lambda m: "#" * min(len(m.group(1)) + by, 6) + m.group(2), md)


def build_bundle():
    skill = _read(os.path.join(SKILL_DIR, "SKILL.md"))
    skill = skill.replace(
        "## Reference files (load as needed)",
        "## Reference material\n\n_This is the single-file build of the skill — the "
        "reference docs, build script, and template that normally live in "
        "`reference/`, `scripts/`, and `assets/` are inlined in the appendices below._\n\n"
        "### Original file map")

    parts = [skill, "\n\n---\n\n# Appendices (inlined for single-file import)\n"]
    for letter, name in zip("ABCDE", REFERENCES):
        parts.append(f"\n## Appendix {letter} · reference/{name}.md\n")
        parts.append(_demote(_read(os.path.join(SKILL_DIR, "reference", f"{name}.md"))))

    build_py = os.path.join(SKILL_DIR, "scripts", "build_notebook.py")
    if os.path.exists(build_py):
        parts.append("\n## Appendix F · scripts/build_notebook.py\n")
        parts.append("```python\n" + _read(build_py) + "\n```\n")

    tmpl = os.path.join(SKILL_DIR, "assets", "notebook_template.ipynb")
    if os.path.exists(tmpl):
        parts.append("\n## Appendix G · assets/notebook_template.ipynb (rendered cells)\n")
        parts.append("_Recreate as a `.ipynb`; markdown cells are quoted, code cells fenced._\n")
        nb = json.load(open(tmpl))
        for i, cell in enumerate(nb["cells"]):
            src = "".join(cell["source"])
            if cell["cell_type"] == "markdown":
                parts.append(f"\n**[cell {i} · markdown]**\n\n> " + src.replace("\n", "\n> "))
            else:
                parts.append(f"\n**[cell {i} · code]**\n\n```python\n{src}\n```")

    text = "\n".join(parts).rstrip() + "\n"
    assert text.startswith("---\n"), "bundle does not start with YAML frontmatter"
    return text


def regenerate(target):
    if not os.path.isdir(SKILL_DIR):
        return False
    text = build_bundle()
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w") as f:
        f.write(text)
    return True


def _changed_under_skill_dir(event):
    """Return True if a PostToolUse event touched a file under the skill dir."""
    ti = (event or {}).get("tool_input") or {}
    paths = []
    if isinstance(ti.get("file_path"), str):
        paths.append(ti["file_path"])
    for edit in ti.get("edits", []) or []:            # MultiEdit
        if isinstance(edit, dict) and isinstance(edit.get("file_path"), str):
            paths.append(edit["file_path"])
    sd = os.path.realpath(SKILL_DIR)
    return any(os.path.realpath(p).startswith(sd) for p in paths)


def main(argv):
    if "--hook" in argv:
        try:
            event = json.load(sys.stdin)
        except Exception:
            return 0                                   # not a JSON event; do nothing, never block
        if _changed_under_skill_dir(event):
            try:
                if regenerate(DEFAULT_TARGET):
                    print(f"[ds-notebook autosync] refreshed {DEFAULT_TARGET}", file=sys.stderr)
            except Exception as e:
                print(f"[ds-notebook autosync] skipped: {e}", file=sys.stderr)
        return 0                                       # always succeed — never fail the tool

    target = next((a for a in argv[1:] if not a.startswith("-")), DEFAULT_TARGET)
    ok = regenerate(target)
    print(("wrote " + target) if ok else f"skill dir not found: {SKILL_DIR}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
