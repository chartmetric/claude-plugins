---
name: demo-presentations
description: Use when building or reworking an artifact for executives, leadership or other non-engineers at Chartmetric, or when asked to make a technical artifact "demo-friendly", "engaging", "animated", "visual", "non-technical", "simpler" or "fit for a team demo".
author: tyler@chartmetric.com
---

# Exec demo artifacts

An exec artifact is visual first: the audience should get the point from the pictures with the text removed. Three things make it land: the page shows instead of tells, the detail is simplified without being faked, and motion is spent only on cause and effect. Everything on the page is real; what changes is how much of it is visible at once and in what form.

## Visual first

- **The visual is the content; text is its label.** Every section opens with the thing itself (the product surface, a drawing of the mechanism, a record moving, a before/after pair), and the words around it are a title, one sentence, and labels. Execs read about 5% of a text-heavy page; the drawings are what they take away.
- **Test by deleting the words.** If a section still makes its point with only its visuals and labels, it is done. If a point only exists as a paragraph, either draw it or move the paragraph to the collapsed detail.
- **Draw the real mechanism, not a decoration.** A drawing shows what actually passes, blocks, splits or accumulates, with real counts on it. Stock illustrations, icons as filler and abstract "AI" imagery say nothing.
- **Prefer the product's own pixels.** A rendered panel, chat or page beats a redrawn version; a stored output beats a description of it.
- **One visual per idea.** A step gets one drawing; a comparison gets one pair; a result gets one chart. Two visuals for one idea compete.
- **Numbers live on the visual.** Put the count on the chip, the duration on the step, the size on the row. A number next to its picture is understood; a number in a sentence is skimmed.
- **Text that remains is short and sentence-case.** Titles are verbs. Captions are one line. Bold and bullets only where they carry structure.

## Composition: cause and effect in one viewport

When one action changes several things, the page's centrepiece is a single stage with adjacent panes that advance together, not a sequence of sections.

- **One pane per thing that changes.** Typically the surface the audience knows (what the user sees), the mechanism (what is happening), and the state it mutates (files, rows, a table, a queue). Two panes is the minimum; four is too many.
- **A shared timeline drives all panes.** One step changes every pane at once: the mechanism shows the step, the state pane gains or highlights a row, the surface shows what the user had at that moment. The audience sees cause in one pane and effect in the next in the same moment, without scrolling or holding anything in memory.
- **Steps carry real timestamps**, grouped by the unit the audience thinks in (question, request, batch). The clock on each step is proof the run is recorded, and it paces the presenter.
- **The stage fits one screen.** Fixed height, each pane scrolling inside itself. Nothing below the fold is needed to follow a step.
- **Later sections are addenda.** A comparison (the same stage for the old way), a numbers table, the collapsed detail. They come after the stage, never instead of it.

## Simplifying for execs

- **Show one real instance, not the system.** One real record, one real conversation, one real job, followed from input to what the user ended up with. An architecture diagram tells; an instance shows.
- **Lead with the product surface.** The thing the audience already recognises (the panel, the chat, the page) is the anchor. Render it from the product's own components and stored output, scaled down to the user's aspect ratio, so it looks like the product and not a mock-up.
- **Titles are verbs for the audience; names are for the detail layer.** A step is "Writes a program", "Drops the duplicates", "Attaches artist details". Tool names, table names, endpoint paths, job ids and file names appear only in a small exact-call strip under the step, in the state list, or in the collapsed log. Never in a heading.
- **Technical text is one click away, never gone.** Code, SQL, queries and config show as four to eight plain-English lines (naming what is read and what is saved) with a toggle to the real text. Hiding it entirely invites "how do we know?"; showing it by default loses the room.
- **Say each thing once.** When a pane already shows the outcome, the step beside it says "Answers" or "Panel updates" and nothing more. No caption that restates what is visible.
- **Numbers are a list, not a dashboard.** A left-aligned label/value list of five to seven facts under the header (what ran, when, how long, how much, what it produced, what it cost). KPI cards, count-ups, sparklines and pills read as marketing and get pulled in review.
- **Cut what the story does not need.** Internal bookkeeping (system log files, run records, mode names, flags) goes unless it carries the point, and goes when it blurs a comparison.
- **Compare with the old way in the same form.** When the work replaces something, show the replaced path in the identical layout directly below, then a short table of hard numbers from both. Include the rows where the new path loses; execs trust a table that has one.
- **Engineering depth survives, collapsed.** The full log, every query, every call, at the bottom in a closed `<details>`. A footer says where it ran, what was sampled or rebuilt, and how.

## Motion

Motion is explanation. Each animation should answer "what caused what?"; if it cannot, it is decoration and comes out.

- **Step, don't scroll.** The audience moves through the work at the presenter's pace with Back, Play and Next and a timeline of labelled steps. The page never animates on scroll-into-view.
- **Arrows carry cause to effect.** When a step creates something, a curve draws from the step to the new item as it appears; when a step reads something, the curve runs the other way in a second colour. Arrows fade after a beat and clear on scroll or resize.
- **State enters at its final size.** New rows, chips and cards arrive at the height they will keep. Nothing grows, reflows or shifts when a label changes; keyed, fixed-height rows.
- **Output that arrives over time streams from the top.** An answer, a feed or a panel filling in reveals block by block, with the view following, so it reads as live.
- **Processes have a start and a finish mark.** A running box shows "running", then a finished tick and its real result, not a spinner that is replaced wholesale.
- **One thing moves at a time.** Stagger entries by a few hundred milliseconds. Simultaneous animations in different panes read as noise.
- **Nothing opens by itself.** A menu, a file viewer or a tooltip appears only on a click. Auto-opening after an animation reads as a bug.
- **Respect `prefers-reduced-motion`**, and keep every state reachable with motion off.

## Quick reference

| To convey | Use |
|---|---|
| A step created or read something | Flow arrow from the step to the item |
| Something now exists or changed | A keyed, fixed-height state row, coloured by state, clickable to the real content |
| One step's work | Input chips → process box with a finished tick → output chips |
| The outcome of a step | Two or three small counts inline with the step |
| Output the user watches arrive | Streaming from the top |
| Code, SQL or config | Plain-English lines with a toggle to the real text |
| Old way versus new way | The same layout twice, then a numbers table with losses included |
| A record moving through a pipeline | One real row's fields shown at each stage |

## Verify

Headless Chrome can check layout and errors but not timing: see [verifying-motion.md](verifying-motion.md). Tell the user what was not seen and ask them to press Play once before presenting.

## Common mistakes

| Mistake | Instead |
|---|---|
| A section that is a paragraph with a picture beside it | The picture, with a title and labels |
| Cause in one section, effect three scrolls later | Adjacent panes on one shared timeline |
| An explanatory paragraph before the first visual | Open on the visual; the sentence goes under it |
| KPI cards, count-ups, hero taglines | Label/value list under the header |
| Architecture diagram as the centrepiece | One real instance moving through the system |
| Jargon in headings, or code hidden entirely | Verbs in headings, real text one click away |
| Animations triggered by scrolling | Presenter-paced steps with controls |
| Rows that grow when a label is added | Fixed-height keyed rows |
| A caption restating what the pane shows | Say it once |
| Comparison as a sentence | Same layout twice plus a numbers table |
| Only the numbers where the new way wins | Every number from both, losses included |
