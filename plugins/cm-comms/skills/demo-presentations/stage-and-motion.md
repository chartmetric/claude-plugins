# Multi-pane stage and motion

Read this when the centrepiece is a multi-pane stage, or when any form has a sequence the presenter steps through.

## The stage: cause and effect in one viewport

Use a stage when one action changes several things and the audience needs to see cause and effect together.

- **One pane per thing that changes.** Typically the surface the audience knows (what the user sees), the mechanism (what is happening), and the state it mutates (files, rows, a table, a queue). Two panes is the minimum; four is too many.
- **A shared timeline drives all panes.** One step changes every pane at once: the mechanism shows the step, the state pane gains or highlights a row, the surface shows what the user had at that moment. The audience sees cause in one pane and effect in the next in the same moment, without scrolling or holding anything in memory.
- **Steps carry real timestamps**, grouped by the unit the audience thinks in (question, request, batch). The clock on each step is proof the run is recorded, and it paces the presenter.
- **Step titles are verbs for the audience** ("Writes a program", "Drops the duplicates", "Attaches artist details"). The exact call, tool or table name sits in a small strip under the step.
- **The stage fits one screen.** Fixed height, each pane scrolling inside itself. Nothing below the fold is needed to follow a step.
- **A step says its outcome once.** When a pane already shows the result, the step beside it says "Answers" or "Panel updates" and nothing more.
- **Later sections are addenda.** A comparison, a numbers table, the collapsed detail. They come after the stage, never instead of it.

## Motion mechanics

- **Step, don't scroll.** The audience moves through the sequence with Back, Play and Next and a timeline of labelled steps. The page never animates on scroll-into-view.
- **Arrows carry cause to effect.** When a step creates something, a curve draws from the step to the new item as it appears; when a step reads something, the curve runs the other way in a second colour. Arrows fade after a beat and clear on scroll or resize.
- **State enters at its final size.** New rows, chips and cards arrive at the height they will keep. Nothing grows, reflows or shifts when a label changes; keyed, fixed-height rows.
- **Output that arrives over time streams from the top.** An answer, a feed or a panel filling in reveals block by block, with the view following, so it reads as live.
- **Processes have a start and a finish mark.** A running box shows "running", then a finished tick and its real result, not a spinner that is replaced wholesale.
- **One thing moves at a time.** Stagger entries by a few hundred milliseconds. Simultaneous animations in different panes read as noise.
- **Nothing opens by itself.** A menu, a file viewer or a tooltip appears only on a click. Auto-opening after an animation reads as a bug.
- **Respect `prefers-reduced-motion`**, and keep every state reachable with motion off.

## Stage elements

| To convey | Use |
|---|---|
| A step created or read something | Flow arrow from the step to the item |
| Something now exists or changed | A keyed, fixed-height state row, coloured by state, clickable to the real content |
| One step's work | Input chips → process box with a finished tick → output chips |
| The outcome of a step | Two or three small counts inline with the step |
| Output the user watches arrive | Streaming from the top |

## Stage mistakes

| Mistake | Instead |
|---|---|
| Cause in one section, effect three scrolls later | Adjacent panes on one shared timeline |
| Rows that grow when a label is added | Fixed-height keyed rows |
| A caption restating what the pane shows | Say it once |
| A spinner replaced wholesale by the result | A running mark, then a finished tick and the result |
| Several panes animating at once | One thing moves at a time |
