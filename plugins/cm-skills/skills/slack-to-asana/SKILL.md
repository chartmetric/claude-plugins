---
name: slack-to-asana
description: Convert a Chartmetric Slack thread into Asana task(s) on the "Unified CM Tasks" project, link any referenced GitHub PRs back to the task (Asana + Slack footer in each PR description), and reply in the source Slack thread with the task link(s). Use when the user pastes a chartmetric.slack.com URL and asks to create an Asana task / tasks from it. Handles thread parsing, project/user lookup, custom-field population (Engineer, Slack URL, Team, Task Type, Planning Priority), GitHub PR description updates, and posting back to Slack.
---

# Slack thread → Asana task(s) on Unified CM Tasks

End-to-end automation for "read this Slack thread, file Asana task(s), post the link back". The user normally just pastes a Slack thread URL and says "create an asana task" or "create N asana tasks, assignee X, engineer Y".

## Required MCP tools

This skill assumes both Slack and Asana MCP servers are connected in the current Claude Code session. If either is missing:

- Slack tools missing → tell the user to run `/mcp` and authenticate the Slack MCP, then retry.
- Asana tools missing → same, for Asana.

Do NOT fall back to Notion-search-as-Slack-proxy. If Slack isn't connected, stop and ask.

## Hard-coded Chartmetric IDs (verified 2026-04-27)

Verify these still resolve before using if the skill hasn't been run in a while — names/IDs can change. Re-run `asana_typeahead_search` to confirm.

```
workspace_gid          = 1198197264916217   # chartmetric.com
project_gid            = 1213445772342530   # "Unified CM Tasks"

# Custom fields on the project
engineer_field_gid     = 1213443514830840   # people
slack_url_field_gid    = 1206132751421626   # text
team_field_gid         = 1207508719775201   # enum
  team_frontend        = 1207508719775204
  team_backend         = 1207508719775205
  team_product_eng     = 1207603513775115
  team_data_eng        = 1207508719775206
  team_infra           = 1207534115761476
  team_admin_tool      = 1208493685092248
task_type_field_gid    = 1213716574992768   # enum
  task_type_ai         = 1213716574992769
  task_type_human      = 1213716574992770
  task_type_undet      = 1213763091162077
planning_priority_gid  = 1206322425179404   # enum
  pp_this_sprint       = 1207927494754339
  pp_next_sprint       = 1206322425179406
  pp_devin_tasks       = 1213445772342529
  pp_done              = 1209287002370157
pr_preview_field_gid   = 1213462685458499   # text
```

Common assignees (look up with `asana_typeahead_search` if not in this list):

```
Junbeom (Jay) Chi  = 1206743323863950
Akshay Vyas        = 1213020955290656
Nico Borromeo      = 1209544616047567
```

## Step-by-step

### 1. Parse the Slack URL

Format: `https://chartmetric.slack.com/archives/<CHANNEL_ID>/p<TS_NO_DOT>[?thread_ts=<PARENT_TS>...]`

- `channel_id` = the segment after `/archives/`.
- `message_ts` = the `p<digits>` segment, with a `.` inserted before the last 6 digits.
  Example: `p1776461959149649` → `1776461959.149649`.
- If `?thread_ts=...` is present, **that** is the parent message ts to read; the `p...` part may be a reply. Always prefer `thread_ts` query param when present.

### 2. Read the thread

Call `slack_read_thread` with `channel_id` and `message_ts` (the parent ts). Read the whole thread — replies usually carry the actual decision, fix details, PR links.

### 3. Decide how many tasks and clarify with user if ambiguous

If the user said "create an Asana task" (singular), default to one task summarizing the thread.
If the user said "create two/N tasks", split the thread by topic — usually each task maps to one PR or one distinct issue.

If the assignee or engineer wasn't specified, ask the user before creating anything.

### 4. Look up the project and people (verify, don't assume)

Run these in parallel to confirm IDs are still valid:

```
asana_list_workspaces                                                           # confirms workspace
asana_typeahead_search(workspace_gid, "Unified CM Task", resource_type=project) # confirms project gid
asana_typeahead_search(workspace_gid, "<assignee name>", resource_type=user)    # gets assignee gid
asana_typeahead_search(workspace_gid, "<engineer name>", resource_type=user)    # gets engineer gid
```

### 5. Create the task(s)

Use `asana_create_task` with:

- `project_id` = project_gid
- `name` = a one-line outcome-oriented title. If the work has a PR, reference it: `Fix X in Y (chartmetric-<repo>#<pr>)`.
- `assignee` = assignee gid
- `notes` = a tight summary of the thread:
  - Problem (1–2 sentences)
  - Fix / decision (1–2 sentences)
  - Links: PR(s), Slack thread, Devin session if mentioned, files touched with paths
- `custom_fields` (JSON):
  - `engineer_field_gid` → engineer user gid
  - `slack_url_field_gid` → the Slack thread URL the user pasted
  - `team_field_gid` → Frontend / Backend / etc. — infer from the repo or work area
  - `task_type_field_gid` → AI Task if Devin/Claude did the work, else Human Task
  - `planning_priority_gid` → Devin Tasks if Devin authored the PRs in the thread, else This Sprint / Next Sprint based on context (ask if unclear)

If creating multiple tasks, run `asana_create_task` calls in parallel.

### 6. Update each linked GitHub PR description (Asana + Slack footer)

If the thread references PRs that we own (chartmetric/* repos), update each PR's description to surface the Asana task and Slack thread under the existing `### Notes` section.

**Important — `gh pr edit` is broken in this org:** it fails with a Projects-classic GraphQL deprecation error. Use the REST API instead:

```bash
# Write the new body to a file (preserve everything; only inject Asana: / Slack: lines under ### Notes)
jq -Rs '{body: .}' < /tmp/pr_<num>_body.md > /tmp/pr_<num>_payload.json
gh api -X PATCH /repos/<owner>/<repo>/pulls/<num> --input /tmp/pr_<num>_payload.json --jq '.html_url'
```

How to inject the lines (preserve everything else verbatim):

1. `gh pr view <num> --repo <owner>/<repo> --json body` to fetch the current body.
2. Locate the `### Notes` heading. Insert these two lines on a new paragraph under it (above any "Link to Devin session:" / "Requested by:" lines if present):

   ```
   Asana: [<exact task name>](<task permalink_url>)
   Slack: <slack thread URL>
   ```

3. Leave the trailing Asana-GitHub-App auto-link footer (`---\n- To see the specific tasks where the Asana app for GitHub is being used...`) intact. The Asana app appends this automatically when the task description contains the PR URL — don't try to add or remove it manually.

If the PR has no `### Notes` section (rare), append a new `### Notes` section at the end with the Asana / Slack lines.

Verify each edit with `gh pr view <num> --repo <owner>/<repo> --json body` and confirm both lines are present.

### 7. Post the task link(s) back to the Slack thread

Use `slack_send_message` with `channel_id` and `thread_ts` set to the **parent message ts** (not a reply ts). Format:

```
Created Asana task(s) on Unified CM Tasks (assignee: <Name>, engineer: <Name>):
• <Short title>: <permalink_url>
• <Short title>: <permalink_url>
```

Use `permalink_url` from the `asana_create_task` response (not a hand-built URL).

### 8. Report back to the user

In the chat, give them:
- Bullet list of created task names + permalinks
- The Slack reply link (`message_link` from `slack_send_message` response)
- Flag any pre-existing tasks on the same project that look like duplicates of what you just created (do an `asana_search_tasks` if the thread mentions an autosana / pretzel reaction earlier — those create combined tasks). Don't delete them — just surface them and ask.

## Inference rules for custom fields

- **Team**: `chartmetric-web-app` / `cmf-*` repo → Frontend. `chartmetric-api` / data-eng repos → Backend or Data Engineering. If the thread covers both, create separate tasks per repo and tag each with the matching team.
- **Task Type**: thread mentions Devin (U09JD2RRXQ9) or app.devin.ai sessions → AI Task. Pure human discussion → Human Task. Unclear → Undetermined.
- **Planning Priority**: Devin authored PRs → Devin Tasks. Otherwise default to This Sprint and ask if you're unsure.

## Edge cases

- **Thread already has an autosana task**: the `:pretzel:` reaction in Chartmetric Slack auto-creates a combined Asana task. If you spot one in the thread (look for `autosana` user `U08UUNWC90T` posting "Your task was created: ..."), mention it in your final summary so the user can decide whether to dedupe.
- **No PR yet in the thread**: still fine to create the task — fill `notes` with the problem statement and leave the PR Preview Link field empty.
- **DM / private channel**: `slack_read_thread` works on these too if the user has access. No change in flow.
- **Slack URL points to a single message, not a thread parent**: the thread's parent ts is in the URL's `?thread_ts=...` query param. Use that, not the `p...` segment.
