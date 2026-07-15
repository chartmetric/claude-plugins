---
name: slack-summary
description: Given a chartmetric Slack thread URL, read the full thread and summarize it. Use when the user pastes a Slack URL and asks for a summary.
---

# Slack Thread Summary

1. If no Slack thread URL was given as an argument, ask the user for it before doing anything else
2. Parse the channel ID and thread timestamp from the Slack URL argument
3. Read the entire thread with `slack_read_thread` (paginate to the end for long threads)
4. Summarize in this format:
   - **Topic**: one line
   - **Discussion**: 3-5 bullets covering the key flow (include who argued/decided what)
   - **Decisions / Action items**: with owners
   - **Open questions**: if any
5. If the thread references GitHub PRs or Asana tasks, include the links in the summary
