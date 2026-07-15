---
name: release-notes
description: Generate the "Chartmetric Production Release" Slack message for #product-updates after a frontend (or backend) deploy. Given a deployment-monitoring Slack message, a PR number, or a release version, gathers Asana task name(s) + URL(s) from the PR description — falling back to searching related Slack threads when the PR body has no Asana link — handles BATCH PRs by enumerating sub-PRs, formats the post in the exact template, and optionally posts it to #product-updates. Use when the user pastes a "Production deployment succeeded" message or says "post the release update for vXXXXXXXX-XX" / "release notes for PR #NNNNN".
author: Chartmetric Eng (originally junbeom@chartmetric.com)
---

# Production release notes → #product-updates

End-to-end automation for the post-deploy ritual: read the deployment-monitoring message, dig out every Asana task that shipped (PR body OR linked Slack thread), and format the `#product-updates` post.

## Required MCP tools

- **Slack MCP** — to read `#product-deployment-monitoring`, search for related threads, and (optionally) post the final message.
- **Asana MCP** — to resolve Asana task URLs into human-readable task names.
- **`gh` CLI** — for PR bodies and commit metadata.

If Slack or Asana MCP is missing, tell the user to run `/mcp` and authenticate, then retry. Don't fall back to web scraping or guesswork.

## Identifying "the current user"

The skill auto-discovers a user's pending releases from `#product-deployment-monitoring`. The deploy bot's success message contains `cc <@U…>` for the PR author, so the skill needs the caller's Slack user ID.

Resolution order:

1. Environment variable `CM_RELEASE_NOTES_SLACK_USER_ID` (set by the `cm-release-notes` script wrapper, or by the user).
2. If not set, look up by name: take the caller's name from `git config user.name` (or `CM_RELEASE_NOTES_USER_NAME` env var) and call `slack_search_users(query=<name>)`. Pick the chartmetric.com workspace match.
3. If still ambiguous, ask the user once and remember for the session.

Cache the resolved user ID in memory for the conversation.

## Output template (must match exactly)

One post per **release wave**, where a release wave is "all the FE and BE tags that shipped together for the same set of changes." If FE and BE deployed companion PRs (same branch name across both repos, deployed within ~30 min of each other), **combine them into ONE post**, not two. Title concatenates the tags. Body merges both repos' Asana tasks and dedupes.

Task names must be **hyperlinks** to the Asana task. The release tag(s) must also be hyperlinks. Never plain text with URL-in-parens.

**Slack mrkdwn (what `slack_send_message` sends):**

```
Chartmetric Production Release - <SCOPE> - <TAG_HYPERLINKS>

<<Asana URL>|<Asana task name>>
<<Asana URL 2>|<Asana task name 2>>
...
```

- `<SCOPE>`:
  - FE-only deploy → `FE`
  - BE-only deploy → `BE`
  - Combined FE + BE release wave → `FE/BE`
- `<TAG_HYPERLINKS>`:
  - Single side: `<<TAG_URL>|<RELEASE_VERSION>>`
  - Combined wave: `<<FE_TAG_URL>|<FE_VERSION>>/<<BE_TAG_URL>|<BE_VERSION>>` (FE first, slash, BE second — even if the version numbers differ, e.g. `v20260428-18/v20260428-10`)
- Body: one hyperlinked task name per line. **No `FE:` / `BE:` prefix.** **No bullet character.** Just the task name as a Slack hyperlink.
- Dedupe tasks by Asana gid. If the same task appears in both the FE and BE BATCH (typical for full-stack features), emit one line.
- Order: tasks from the FE BATCH first (in BATCH order), then tasks from the BE BATCH that weren't already listed (in BATCH order).
- **No `cc` line by default.** Only add one if the user explicitly asks for it.

`<TAG_URL>` — GitHub release-tag URL:

- FE: `https://github.com/chartmetric/chartmetric-web-app/releases/tag/<RELEASE_VERSION>`
- BE: `https://github.com/chartmetric/chartmetric-api/releases/tag/<RELEASE_VERSION>`

Verify the **git tag** exists before posting (the deploy bot pushes a tag, but rarely a published Release object — so use the tag-refs API, not `gh release view`):

```bash
gh api repos/<owner>/<repo>/git/refs/tags/<RELEASE_VERSION> --jq '.ref'
```

If that 404s, the deploy may still be wrapping up — pause and confirm with the user. The `/releases/tag/<TAG>` URL works on plain git tags even when no Release object is published.

### Detecting a release wave (FE + BE combined)

Treat FE and BE deploys as one wave if **any** of these hold:

1. A sub-PR in one BATCH explicitly references a "Companion BE PR" / "Companion FE PR" pointing at a sub-PR in the other BATCH (look for `Companion BE PR:` / `Companion FE PR:` in the PR body, or the same branch name across the two repos).
2. Both BATCHes share at least one Asana task gid.
3. The two successful deploy messages in `#product-deployment-monitoring` are within ~30 minutes of each other AND both cc the same user.

If yes → one combined post. If only FE or only BE deployed (no companion in the other repo) → single-side post with `FE` or `BE` scope.

### Worked example — combined FE + BE wave

FE release `v20260428-18` (BATCH #11669 with sub-PRs #11658, #11666) deployed alongside BE release `v20260428-10` (BATCH #6293 with sub-PRs #6279, #6285). #11658 and #6285 are companions sharing the Data Assistant Asana task.

```
Chartmetric Production Release - FE/BE - <https://github.com/chartmetric/chartmetric-web-app/releases/tag/v20260428-18|v20260428-18>/<https://github.com/chartmetric/chartmetric-api/releases/tag/v20260428-10|v20260428-10>

<https://app.asana.com/1/1198197264916217/project/1213445772342530/task/1214364557043913|Devin: enable Data Assistant for Artist and Manager Plans>
<https://app.asana.com/1/1198197264916217/project/1213445772342530/task/1214324350538939|Devin: Fix incorrect pricing on API plan and Japanese pricing page>
<https://app.asana.com/1/1198197264916217/project/1213445772342530/task/1214286852524138|Devin: Fix 'Internal Server Error' for LINE Music track submission>
```

Renders as:

> Chartmetric Production Release - FE/BE - **v20260428-18**/**v20260428-10**
>
> **Devin: enable Data Assistant for Artist and Manager Plans**
> **Devin: Fix incorrect pricing on API plan and Japanese pricing page**
> **Devin: Fix 'Internal Server Error' for LINE Music track submission**

(All bold parts are clickable hyperlinks.)

### cc handle is usually omitted

The user usually does **not** include a `cc` line — omit it by default. Only add a `cc` line if the user explicitly asks for one for this release.

When a cc is needed, look up the Slack user ID with `slack_search_users` and use the real `<@U…>` mention so it pings.

## Step-by-step

### 1. Resolve the input to {pr_number, release_version, repo, scope}

**Default mode — no input from the user:** auto-discover their pending releases from `#product-deployment-monitoring`.

```
channel_id = C0AKWPMTQG1   # #product-deployment-monitoring (hardcoded)
slack_read_channel(channel_id, limit=30, response_format="detailed")
```

Filter for messages where:
- Headline starts with `:white_check_mark:` (succeeded — skip `:x:` failed and `:warning:` cancelled)
- `cc <@<USER_SLACK_ID>>` matches the current caller (see "Identifying the current user" above)

Each match gives you:
- `Frontend` → repo `chartmetric/chartmetric-web-app`, scope `FE`
- `API` → repo `chartmetric/chartmetric-api`, scope `BE`
- Message `ts` (for posting back if you ever need to)

**MCP limitation:** the deploy-bot's message body (with `PR:`, `Release:`, `Commit:` lines) lives in Slack message *attachments/blocks*, which the Slack MCP server does **not** expose. You only get the headline. So the PR# and release version must be discovered another way — via GitHub.

#### Resolving repo + headline → {pr_number, release_version}

Use the message timestamp as the deploy-completion time:

```bash
# 1. List recent tags on the repo, find the one created closest to (and before) the success ts
gh api 'repos/<repo>/tags?per_page=20' --jq '.[] | select(.name | startswith("v"))'

# 2. For candidate tags, get the tag/commit date:
gh api repos/<repo>/git/refs/tags/<TAG> --jq '.object.url' | xargs -I {} gh api {} --jq '.committer.date // .author.date // .tagger.date'

# 3. Pick the tag whose date is just before the deploy-success ts (typically <15 min earlier)

# 4. Resolve the tag → commit → PR:
TAG_OBJ=$(gh api repos/<repo>/git/refs/tags/<TAG> --jq '.object.sha')
COMMIT_SHA=$(gh api "repos/<repo>/git/tags/$TAG_OBJ" --jq '.object.sha' 2>/dev/null || echo $TAG_OBJ)
gh api "repos/<repo>/commits/$COMMIT_SHA/pulls" --jq '.[] | {number, title, html_url}'
```

This gives you the BATCH (or single) PR that shipped in that release.

**(b) Alternative inputs the user may provide:**

- **Pasted deployment-monitoring message** (text). Parse `PR:` and `Release:` lines directly from the user's paste — no GitHub round-trip needed.
- **Just a PR number.** Find the merge commit, then find the tag containing it: `gh api 'repos/<repo>/commits/<merge_sha>/tags'` or list recent tags and check which contains it.
- **Just a release version (`v20260428-NN`).** Use the tag → commit → PR resolution above.

### 2. Fetch the PR body and detect BATCH

```bash
gh pr view <pr_number> --repo <repo> --json title,body,url,commits
```

- If the PR title starts with `[BATCH]`, it aggregates multiple sub-PRs. The body typically lists them as `#NNNNN` references or markdown links. Parse the sub-PR numbers and recurse step 2 on each.
- If non-BATCH, you have a single PR to process.

### 3. Extract Asana URLs from each PR body

Look for URLs matching:

```
https?://app\.asana\.com/(?:0|1)/(?:\d+/)?(?:project/\d+/)?(?:task/)?\d+(?:/\d+)?
```

Common shapes:
- `https://app.asana.com/0/<project_gid>/<task_gid>`
- `https://app.asana.com/1/<workspace_gid>/project/<project_gid>/task/<task_gid>`

Also scan commit messages from `gh pr view --json commits` — sometimes the Asana link only appears there.

### 4. Fallback — search Slack thread when a PR has no Asana link

For each sub-PR (or the single PR) where step 3 found no Asana URL:

1. Search Slack for the PR URL or PR number:

   ```
   slack_search_public_and_private(query="<PR URL>")
   # or, if that's empty:
   slack_search_public_and_private(query="chartmetric-web-app #<pr_number>")
   ```

2. Pick threads in chartmetric channels (skip `#product-deployment-monitoring` itself — that's the deploy bot, not the discussion).
3. For each candidate, `slack_read_thread(channel_id, message_ts=<thread_parent_ts>)` and scan messages + replies for:
   - Direct `app.asana.com/...` URLs
   - Autosana posts from `U08UUNWC90T` ("Your task was created: ..." with a task URL)
   - Pretzel-reaction outcome messages
4. If multiple threads match, prefer the one where the PR was originally posted (the message that opened the discussion).

If still nothing, fall back to:
- The PR title itself as the "task name" with a `<no Asana — PR: <PR URL>>` placeholder, and tell the user this PR didn't have a discoverable Asana task.

### 5. Resolve each Asana URL → task name

For each unique Asana URL found, parse the task gid (last numeric segment for `/0/<proj>/<task>`, or after `/task/` for the new format) and call:

```
asana_get_task(task_id=<gid>)
```

Use `task.name` verbatim and `task.permalink_url` (not the URL you scraped — Asana sometimes returns a canonical URL that differs).

Dedupe by task gid — a single task is often referenced from multiple sub-PRs in a BATCH.

### 6. Format the message

Use the template at the top. Detect whether the deploys form a release wave (FE + BE combined) or are single-side. Dedupe tasks by Asana gid. No bullets, no per-line scope prefix. See the worked example in the template section.

### 7. Show & confirm before posting

Print the assembled message in the chat and ask:

> Ready to post this to `#product-updates`? (yes / edit / no)

Default to **not posting** unless the user explicitly says yes. They might want to tweak the wording.

**Important — this skill always sends via `slack_send_message`, never via copy-paste.** Slack's WYSIWYG composer does not parse `<URL|text>` mrkdwn — pasting the formatted text shows the raw `<...|...>` syntax verbatim. The only way to get hyperlinked task names + version is through the API. If the user asks "can I just copy-paste it?" — answer no, and offer to send via API instead. If they want to edit before sending, they edit in the chat with you, then you send the edited version.

### 8. Post to #product-updates (only if user confirms)

```
slack_search_channels(query="product-updates")  # cache channel_id
slack_send_message(channel_id=<#product-updates>, text=<formatted message>)
```

Use `<@U…>` mention syntax for the cc handle if you have the Slack user ID, otherwise leave the `@Name` literal — Slack will render it as a non-pinging text mention. Prefer the real mention.

Report back to the user with the posted message link (`message_link` from the response).

## Useful hardcoded IDs

```
chartmetric Slack workspace      = chartmetric.slack.com
#product-deployment-monitoring   = C0AKWPMTQG1
#product-updates                 = C014BMSCGS2

Asana workspace_gid              = 1198197264916217   # chartmetric.com
Asana project "Unified CM Tasks" = 1213445772342530   # most FE/BE tasks live here
```

`<URL|text>` mrkdwn confirmed working when sent via the `slack_send_message` MCP tool — the API renders the hyperlinks correctly in `#product-updates`.

Repo → scope mapping:

```
chartmetric/chartmetric-web-app  → FE
chartmetric/chartmetric-api      → BE
```

## Edge cases

- **Deploy was for a non-master branch / staging**: stop and confirm — this skill is for prod releases only.
- **Companion FE/BE deploys (same branch name on both repos)**: combine into ONE `#product-updates` post with `FE/BE` scope and concatenated tags (`<FE_TAG>/<BE_TAG>`). Dedupe shared Asana tasks. This is the normal case for full-stack changes — see worked example above.
- **PR description includes Asana URL of an unrelated task** (e.g. linked-from issue, parent epic): when in doubt, prefer Asana URLs that appear under a `### Notes` / `Asana:` line in the PR body — that's the convention. Surface ambiguous matches to the user.
- **Asana task is in a different project**: that's fine — `asana_get_task` doesn't care about project. Use the name and permalink as-is.
- **Same task appears via multiple sub-PRs**: dedupe on task gid; emit one line.
- **No Asana found anywhere**: emit the line as the PR title hyperlinked to the PR URL, and flag it to the user — they may want to file the Asana task post-hoc.
- **Release version doesn't match PR**: trust the deployment-monitoring message, not the PR. Multiple PRs can ship under one version (BATCH).

## Quick recipe (when the user pastes the deploy message)

1. Parse → `pr_number`, `release_version`, `repo`, `scope`.
2. `gh pr view <pr_number> --repo <repo> --json title,body,url,commits`
3. If BATCH → parse sub-PR list → recurse for each sub-PR body.
4. Asana URLs: PR body → commit messages → Slack-thread fallback.
5. `asana_get_task` for each unique gid → name + permalink.
6. Format using template; show; ask to post; post on confirm.

Don't over-engineer the first run — if any step is ambiguous, ask the user. It's faster than guessing wrong.
