#!/usr/bin/env python3
"""Claude Design -> repo: apply colour and shadow token edits made in a Design System artifact to
chartmetric-design-system's styles/index.css.

usage: python3 tokens_to_css.py <artifact tokens.json> <repo>/styles/index.css [--write]

Without --write it only reports. It changes the value of a `--<name>:` declaration that already exists in the
:root block and lists, never applies, everything it cannot map safely:
  - tokens that exist only in Claude Design (added on the page)  -> "added"   (a new token needs a code review)
  - variables that exist only in the repo                         -> "missing" (never deleted from here)
  - values the CSS cannot take as written (aliases, per-theme)     -> "skipped"
Spacing, radius and type live in SCSS/TS in the repo (styles/_spacing.scss, _radius.scss, src/variants/text.ts):
they are reported as "manual" when they differ, never rewritten.
"""
import json
import re
import sys


def light(value):
    """The first theme's value; the artifact's tokens.json puts light first."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("light") or next(iter(value.values()), None)
    return None


def norm(v):
    v = " ".join(str(v).split()).lower()
    m = re.fullmatch(r"#([0-9a-f])([0-9a-f])([0-9a-f])", v)  # #f90 == #ff9900
    return "#" + "".join(c * 2 for c in m.groups()) if m else v


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    write = "--write" in sys.argv
    if len(args) != 2:
        sys.exit(__doc__)
    tokens = json.load(open(args[0]))
    css_path = args[1]
    css = open(css_path).read()
    start = css.index(":root")
    end = css.index("@keyframes", start) if "@keyframes" in css[start:] else len(css)
    root = css[start:end]
    repo = {m.group(1): m.group(2).strip() for m in re.finditer(r"--([a-z0-9-]+):\s*([^;]+);", root)}

    report = {"changed": [], "added": [], "missing": [], "skipped": [], "manual": []}
    seen = set()
    for family in ("color", "shadow"):
        for t in tokens.get(family, {}).get("tokens", []):
            name, raw = t["name"], t["value"]
            seen.add(name)
            v = light(raw)
            if isinstance(raw, dict) and len({norm(x) for x in raw.values()}) > 1:
                report["skipped"].append(f"{name}: per-theme values {raw} (the repo uses separate -dark-* tokens)")
                continue
            if v is None or str(v).startswith("{"):
                report["skipped"].append(f"{name}: {raw!r} (alias or empty)")
                continue
            if name not in repo:
                report["added"].append(f"{name}: {v}")
                continue
            if norm(repo[name]) != norm(v):
                report["changed"].append((name, repo[name], v))
    for name in repo:
        if name not in seen and not name.startswith("cm-mood"):
            report["missing"].append(name)

    scale = {
        "spacing": {"spacing-3xs": "2px", "spacing-2xs": "4px", "spacing-xs": "6px", "spacing-sm": "8px", "spacing-md": "12px",
                    "spacing-lg": "16px", "spacing-xl": "24px", "spacing-2xl": "32px", "spacing-3xl": "40px", "spacing-4xl": "48px", "spacing-5xl": "56px"},
        "radius": {"radius-2xs": "0.125rem", "radius-xs": "0.25rem", "radius-sm": "0.375rem", "radius-md": "0.5rem",
                   "radius-lg": "0.75rem", "radius-xl": "1rem", "radius-full": "9999px"},
    }
    for family, expected in scale.items():
        for t in tokens.get(family, {}).get("tokens", []):
            if t["name"] in expected and norm(t["value"]) != norm(expected[t["name"]]):
                report["manual"].append(f"{t['name']}: {expected[t['name']]} -> {t['value']} (edit styles/_{family}.scss and the Tailwind config)")

    if write and report["changed"]:
        new_root = root
        for name, old, new in report["changed"]:
            new_root, n = re.subn(rf"(--{re.escape(name)}:\s*){re.escape(old)}(\s*;)", rf"\g<1>{new}\g<2>", new_root, count=1)
            if n != 1:
                sys.exit(f"could not rewrite --{name}")
        open(css_path, "w").write(css[:start] + new_root + css[end:])

    print(json.dumps({**report, "changed": [f"{n}: {o} -> {v}" for n, o, v in report["changed"]], "written": write}, indent=1))


if __name__ == "__main__":
    main()
