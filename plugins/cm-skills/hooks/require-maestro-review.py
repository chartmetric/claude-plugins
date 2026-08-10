#!/usr/bin/env python3
"""PreToolUse guard: PR reviews/approvals/merges must go through the Maestro
`chartmetric-claude` GitHub App, never the caller's personal `gh` identity.

`gh pr review` / `gh pr merge` (and the equivalent raw REST calls) authenticate
as whoever is logged into `gh` locally, so a review posted that way lands under
an individual's account. Chartmetric requires these to be posted by the
`chartmetric-claude` App (write-capable, allowlisted, audited). This hook blocks
the personal-identity commands and points Claude at the Maestro MCP tools.

Blocking mechanism: exit code 2 on PreToolUse blocks the tool call and feeds
stderr back to Claude. Anything we don't recognize exits 0 (allow) — read-only
`gh` calls (`gh pr view`, `gh pr diff`, `gh search`, …) are never touched.
"""

import json
import re
import sys

# `gh pr review` / `gh pr merge` are always writes — no read-only variant exists.
_GH_PR_WRITE = re.compile(r"\bgh\s+pr\s+(?:review|merge)\b")

# The raw REST review/merge endpoints. Reading these (GET) is allowed; only a
# mutation must go through Maestro, so `gh api` calls are gated on method below.
_GH_API = re.compile(r"\bgh\s+api\b")
_REVIEW_MERGE_ENDPOINT = re.compile(r"/pulls/\d+/(?:reviews|merge)\b")

# `gh api` defaults to GET, but any body field flips the default to POST; -X/--method
# sets it explicitly. A call is a write unless it's an explicit GET with no body.
_EXPLICIT_GET = re.compile(r"(?:-X|--method)[=\s]+GET\b", re.IGNORECASE)
_WRITE_METHOD = re.compile(r"(?:-X|--method)[=\s]+(?:POST|PUT|PATCH|DELETE)\b", re.IGNORECASE)
_BODY_FLAG = re.compile(r"(?:^|\s)(?:-f|-F|--field|--raw-field|--input)\b")


def _is_blocked(command: str) -> bool:
    if _GH_PR_WRITE.search(command):
        return True
    if _GH_API.search(command) and _REVIEW_MERGE_ENDPOINT.search(command):
        if _EXPLICIT_GET.search(command):
            return False
        return bool(_WRITE_METHOD.search(command) or _BODY_FLAG.search(command))
    return False

_MESSAGE = (
    "BLOCKED by cm-skills: this posts a PR review/approval/merge as your PERSONAL "
    "GitHub account.\n"
    "Chartmetric requires PR reviews, approvals, and merges to be posted by the "
    "`chartmetric-claude` GitHub App (write-capable, allowlisted, audited) — never "
    "an individual's `gh` login.\n\n"
    "Use the Maestro MCP tools instead (they authenticate as the App via a "
    "short-lived installation token):\n"
    '  - submit_pr_review(owner, repo, number, event="APPROVE"|"REQUEST_CHANGES"|'
    '"COMMENT", body=...)\n'
    "  - approve_pull_request(owner, repo, number, body=...)\n\n"
    "If the Maestro MCP server is not connected, connect it (employee Google "
    "sign-in) and retry. Do NOT fall back to `gh pr review`/`gh pr merge`."
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        # Can't parse the hook payload — fail open so we never wedge Bash.
        return 0

    command = ((payload.get("tool_input") or {}).get("command")) or ""
    if _is_blocked(command):
        sys.stderr.write(_MESSAGE)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
