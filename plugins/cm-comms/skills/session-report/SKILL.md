---
name: session-report
description: Summarize the work done in the current session with full context for teammates and post it to a given Slack channel. Use for requests like "report this work to Slack".
---

# Session Work Report

1. Grab the claude session link for this current claude session
2. Summarize this session's work in this format:
   - 🔍 **Goal**: what was wrong, or what we wanted to implement (error messages, symptoms, root cause)
   - 🔧 **Changes Made**: what was changed and how (files/logic summary)
   - ✅ **Current state**: test results, deploy status, remaining work
   - **Engineering Review needed**: what specifically need to be reviewed and tested before the changes are productionized
   - 🔗 **Links**:
       - Current Claude Session URL: 
       - Pull Request URLs:
       - related Slack threads:
       - Asana task:
3. Write it so a teammate with zero context can follow - no session-only shorthand. Give the full context but keep it concise not to bloat up the message, make it non-engineer friendly as well.
4. If no channel was given as an argument, ask which channel to post to. It will usually be in #claude-kanban channel (https://chartmetric.slack.com/archives/C0AJ1LU8ETT), so we should give this as a default option.
5. Show the draft to the user for approval, then send with `slack_send_message`
