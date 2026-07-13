---
name: session-report
description: Summarize the work done in the current session with full context for teammates and post it to a given Slack channel. Use for requests like "report this work to Slack".
---

# Session Work Report

1. Summarize this session's work in this format:
   - 🔍 **Problem**: what was wrong (error messages, symptoms, root cause)
   - 🔧 **Fix**: what was changed and how (files/logic summary)
   - ✅ **Current state**: test results, deploy status, remaining work
   - 🔗 **Links**: PR, related Slack threads, Asana tasks
2. Write it so a teammate with zero context can follow — no session-only shorthand
3. If no channel was given as an argument, ask which channel to post to. If a related Slack thread link wasn't provided, ask the user for it before posting
4. Show the draft to the user for approval, then send with `slack_send_message`
