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

# Commands that post a PR review / approval / merge under the PERSONAL gh identity.
_BLOCKED = (
    re.compile(r"\bgh\s+pr\s+review\b"),
    re.compile(r"\bgh\s+pr\s+merge\b"),
    # Raw REST equivalents: POST .../pulls/<n>/reviews  and  PUT .../pulls/<n>/merge
    re.compile(r"\bgh\s+api\b[^\n]*/pulls/\d+/(?:reviews|merge)\b"),
)

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
    if any(pat.search(command) for pat in _BLOCKED):
        sys.stderr.write(_MESSAGE)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
