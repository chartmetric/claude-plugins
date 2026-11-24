"""Tracker config for one Replit port. Copy to `tracker/config.py` and edit.

Paths are relative to this file. The builder reads Casper prompts from the plan; everything else is here.

Task fields
  id        "1", "5b", "13a" ... must match the plan's `> <HEADER> | Task <id>:` blocks
  title     card title;  short: label in the map box (≤ 14 chars)
  phase     group label shown on the card
  repo      repo the task's PR lands in (used to match PR links and merge lines in the Casper thread)
  kind      "casper" (a Casper thread) or "human" (the user runs it themselves: no agent prompt)
  state     "done" | "review" (PR open) | "running" (Casper working, or waiting on the user) | None
            None = worked out from deps: "ready" when every dep is met, otherwise "blocked"
  deps      [(task id, need)]; need "merged" = dep must be done, "built" = an open PR is enough
  col, row  position on the dependency map (col None = not on the map); rows grouped into lanes below
  summary   one sentence: the goal
  thread    Slack permalink of the task's Casper thread, once started (SLACK + "p<ts without the dot>")
  pr        dict(label="repo#N", url=..., status="Open") once Casper opens it; the build refreshes status
  notes     list of short strings: verification outcome, open issues, what is waiting on whom
  extra_prompts  list of dict(label, where, text, sent=False[, steps=True]): follow-up replies for the
            thread, or (steps=True) a checklist the user runs by hand, shown as "Show steps"/"Copy steps"
  prompt_label / prompt_where  override the main prompt's label and hint (e.g. a verification prompt)
"""

SLACK = "https://chartmetric.slack.com/archives/D0XXXXXXXXX/"  # the user's DM channel with Casper

PROJECT = dict(
    title="Example Rollout",
    eyebrow="Chartmetric · data science",
    intro="Moving the Example Replit app onto the Chartmetric site.",
    header="Example",                      # prompts start "Example | Task N: name"
    storage_key="example",                 # localStorage prefix; unique per tracker
    github_org="chartmetric",
    plan_path="../casper_production_plan.md",
    plan_url="https://github.com/chartmetric/chartmetric-flow/blob/feat/example/data_science/example/casper_production_plan.md",
    plan_branch="feat/example",
    out_path="example_tracker.html",
    slack_base=SLACK,
    channel="D0XXXXXXXXX",
    since="1794600000.000000",             # Slack ts just before the first Casper thread; Refresh reads from here
    lanes=[["chartmetric-web-app", 0], ["chartmetric_data_script", 2], ["chartmetric-api", 3]],  # [label, first row]
)

TASKS = [
    dict(id="0", title="Prep", phase="Prep", repo="chartmetric-flow", kind="human", state="done",
         col=None, summary="Replit source exported and pushed as reference material."),
    dict(id="1", title="Design note", phase="Phase 1 · Design", repo="chartmetric_data_script",
         deps=[], col=0, row=2, short="Design note",
         summary="Table names, types and DDL, written as a note in the thread. No code."),
    dict(id="2", title="Port the queries", phase="Phase 2 · Pipeline", repo="chartmetric_data_script",
         deps=[("1", "merged")], col=1, row=2, short="Queries",
         summary="The app's SQL as a module with tests, checked against the source numbers."),
    dict(id="2b", title="Create the tables", phase="Phase 2 · Pipeline", repo="chartmetric_data_script",
         kind="human", deps=[("2", "merged")], col=2, row=2, short="Create tables",
         summary="You run the one-off CREATE TABLE statements by hand, after the PR merges.",
         extra_prompts=[dict(label="Your checklist", where="For you to run · not an agent prompt", sent=False,
                             steps=True, text="1. Check the PR is merged.\n2. Run the statements from ddl.sql on main.")]),
    dict(id="3", title="API route", phase="Phase 3 · API", repo="chartmetric-api",
         deps=[("2b", "merged")], col=3, row=3, short="API",
         summary="A read-only route returning the page's data, employee-only."),
    dict(id="4", title="Hidden page", phase="Phase 4 · UI", repo="chartmetric-web-app",
         deps=[("3", "built")], col=4, row=0, short="Page",
         summary="The page behind the employee gate, reading the new route."),
]
