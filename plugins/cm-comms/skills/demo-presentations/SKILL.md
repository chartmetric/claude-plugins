---
name: demo-presentations
description: Use when building or reworking an artifact for executives, leadership or other non-engineers at Chartmetric, or when asked to make a technical artifact "demo-friendly", "engaging", "animated", "visual", "non-technical", "simpler" or "fit for a team demo". Not for design docs or handoffs an engineer will build from.
author: tyler@chartmetric.com
---

# Demo presentations

An exec artifact is visual first: the audience should get the point from the pictures with the text removed. Three things make it land: the page shows instead of tells, the detail is simplified without being faked, and motion is spent only on cause and effect. Everything on the page is real; what changes is how much of it is visible at once and in what form.

These are principles, not a template. Two demos about different work should not look alike, and a page has only the parts its content calls for.

## Artifact format

"Demo" and "presentation" here describe the audience, not the file type. The artifact is a scrolling web page or a document, published as an ordinary page (Artifact quickstart `intent: "other"`, or `"document"` for mostly prose).

- If the user asked for slides or a deck, make slides (`intent: "slides"`).
- If the user asked for a design or prototype, make a design (`intent: "design"`).
- Otherwise make the page. Do not start from a Slides, Design or other typed template because the request mentions a demo, a presentation or motion.

## Choose the form from the content

Pick the centrepiece by what the work is, then build only that. A page has one centrepiece; everything else on it is an addendum to the centrepiece.

| The work is | Centrepiece |
|---|---|
| One action that changes several things at once (an agent run, a job writing rows) | A multi-pane stage on a shared timeline: read [stage-and-motion.md](stage-and-motion.md) |
| A replacement for something the audience already uses | The same moment on both paths, then a numbers table |
| A new capability with no old version | The product surface doing it once, annotated |
| A data finding or result | One chart with the numbers on it |
| A pipeline or data flow | One real record shown at each stage |
| A tool people will use | A working interactive example they can try |
| A plan, migration or rollout | A timeline of real dates and states |
| A UI or design change | The real screens, large, with callouts |

A rendered product surface (a chat, a panel, a page) appears only when the work changes what the user sees in the product. A before/after appears only when there is a real before the audience knows. Step controls appear only when the content is a sequence the presenter walks through.

### Building each form

- **Both paths, same moment.** The same real instance (same input, same second into the run) on each path, in the identical layout, side by side when each fits half the width and stacked otherwise. Real timestamps on each step. Under the pair, a short table of hard numbers from both, with the rows where the new path loses; execs trust a table that has one. Describe the old path from the current source or the live product, never from memory.
- **Product surface, annotated.** The surface rendered from the product's own components and stored output, at the user's aspect ratio, once. Numbered callouts in reading order, each a verb phrase and the real value at that spot ("Flags 3 chart-days with under 200 rows"). One surface, not a gallery of states.
- **One chart.** The finding is the chart's title, written as a sentence. The series are the groups the audience thinks in, the values are printed on the marks that carry the point, and the rest is grey. The cohort size and method sit under the chart in one line, with the query one click away. Follow the dataviz skill for the chart when it is installed.
- **One record at each stage.** One real record's fields shown as each stage's output, arranged in flow direction, with what changed between stages highlighted. Each stage box says what it does, as a verb, and carries the count for the whole run as a number ("Picks channels not fetched in 23 h: 76,912"), not one mark per item. Stages share one height. Failures and retries are drawn where they happen, with their counts.
- **Interactive example.** The tool's real controls with the real defaults, prefilled with a recorded run, and the recorded result already on screen when the page opens, so the first screen shows the tool having done its job. The viewer can re-run it or change an input; any input other than the recorded one shows a computed or illustrative result and says so on the panel. The recorded run's log is one click away.
- **Timeline.** Real dates on a horizontal or vertical axis, one state per date (done, in progress, planned), today marked. Done items carry what shipped; planned items carry what will exist, not a task name.
- **Screens with callouts.** Screens at the product's aspect ratio, large, in the order the user meets them. Each callout says what the user does and what they get. Spotify's or another vendor's screen stays as the vendor renders it. The old screens appear beside the new only when the comparison is the point.

## Let the subject set the look

Take the background, palette, type and shape of the page from the subject, before writing any stylesheet. Test it: if the page would look the same with a different subject, the look did not come from this one.

| The subject is | The page takes |
|---|---|
| A product surface | The product's own background, colours, type and component shapes, so the surface looks lifted from the product |
| A dataset or finding | A white page, one accent colour for the finding, grey for everything else, tabular numbers |
| A pipeline, job or system | A colour per state (waiting, running, done, failed) used consistently, monospace for ids and timestamps, a wide left-to-right layout; dark only when the subject is a terminal or a log stream |
| A flow people go through | The screens' own colours, narrow columns, one per path |
| A plan | A single axis, muted colour for the past, saturated for what is next |

The background is part of the look. A dark page is a choice the subject makes (a terminal, a log stream, a dark product UI), never a default; a finding, a plan or a set of light product screens sits on a light page.

The first screen is the centrepiece with its title. A header block, a facts list or a paragraph above the first visual pushes the point below the fold.

## Page frame

Each of these appears only when its condition holds. Otherwise it is left out.

- **A facts list under the title** (left-aligned label/value, five to seven rows) when the page is about one run or event and the audience will ask what ran, when, how long, how much, what it produced and what it cost. A finding, a set of screens or a plan puts its numbers on the visual instead.
- **A collapsed `<details>` at the bottom** when there is technical text the audience could ask for: the full log, every query, every call, the raw data. A page with no such text has no `<details>`.
- **A footer line** when something was sampled, replayed, rebuilt or illustrative; it says where it ran and how. Otherwise no footer.
- **Verb titles** on steps and actions ("Writes a program", "Drops the duplicates"). A finding is titled with the finding as a sentence. A comparison is titled with the two things compared. A screen is titled with what the user does on it.
- **A one-line caption** under a visual only when the visual needs a reader's question answered that its labels do not. When the labels carry the point, no caption.

## Writing that stands on its own

These hold for any reader, technical or not.

- **The page works without its companions.** Readers may never see the demo, the chat or the earlier draft. Open with what the thing is in terms the reader already knows, plus one real instance of it (a quoted line, a rendered panel). A coined label for the idea ("one transcript instead of two") explains nothing on its own.
- **Each headline is proved in its own section.** A section titled with a claim shows the claim happening: real content at real timestamps or real counts, next to the old behaviour. Abstract bars or boxes with no content in them do not prove anything.
- **Section names say what is in them.** "What the user sees after the change", not "The cases that will bite". No idioms, puns or teaser headings.
- **Illustrative content is labelled where it sits.** When one panel cannot use real data, say so on that panel. A footnote elsewhere gets missed, and an unlabelled mock-up next to real output reads as real.

## Visual first

- **The visual is the content; text is its label.** Every section opens with the thing itself (the product surface, a drawing of the mechanism, a record moving, a chart), and the words around it are a title, one sentence, and labels. Execs read about 5% of a text-heavy page; the drawings are what they take away.
- **Test by deleting the words.** If a section still makes its point with only its visuals and labels, it is done. If a point only exists as a paragraph, either draw it or move the paragraph to the collapsed detail.
- **Draw the real mechanism, not a decoration.** A drawing shows what actually passes, blocks, splits or accumulates, with real counts on it. Stock illustrations, icons as filler and abstract "AI" imagery say nothing.
- **Prefer the product's own pixels.** A rendered panel, chat or page beats a redrawn version; a stored output beats a description of it.
- **One visual per idea.** A step gets one drawing; a comparison gets one pair; a result gets one chart. Two visuals for one idea compete.
- **Numbers live on the visual.** Put the count on the chip, the duration on the step, the size on the row. A number next to its picture is understood; a number in a sentence is skimmed.
- **Text that remains is short and sentence-case.** Bold and bullets only where they carry structure. KPI cards, count-ups, sparklines and hero taglines read as marketing and get pulled in review.

## Simplifying for execs

- **Show one real instance, not the system.** One real record, one real conversation, one real job, followed from input to what the user ended up with. An architecture diagram tells; an instance shows.
- **Lead with what the audience recognises.** When the work has a product surface (a panel, a page, a report), it is the anchor. Render it from the product's own components and stored output, scaled down to the user's aspect ratio, so it looks like the product and not a mock-up.
- **Names are for the detail layer.** Tool names, table names, endpoint paths, job ids and file names appear only in a small exact-call strip under the step, in the state list, or in the collapsed log. Never in a heading.
- **Plain words reach inside diagrams and tables too.** A diagram box says what happens ("Checks for internal words"), and a branch carries its condition and its count ("Nothing found: 21 of 27"). Table columns are the reader's questions ("Where does it come from?", "Is it saved?") and the cells are sentences. Internal component names ("middleware", "registry", "envelope") stay out of both.
- **Technical text is one click away, never gone.** Code, SQL, queries and config show as four to eight plain-English lines (naming what is read and what is saved) with a toggle to the real text. Hiding it entirely invites "how do we know?"; showing it by default loses the room.
- **Complex logic can be loose pseudo-code on the page.** When the point is a rule or a decision (what gets kept, what gets dropped, in what order), a few lines of loose pseudo-code in the reader's words can sit in the exec-facing part as the visual, with the real code behind the toggle. Plain words for the conditions, no identifiers, no syntax the reader would have to parse.
- **Say each thing once.** When a visual already shows the outcome, the label beside it names the outcome and nothing more. No caption that restates what is visible.
- **Cut what the story does not need.** Internal bookkeeping (system log files, run records, mode names, flags) goes unless it carries the point, and goes when it blurs a comparison. Acceptance checklists and "where this sits" stage strips go too unless the page is about the plan; one sentence covers ordering when it matters.

## Motion

Motion is explanation. Each animation answers "what caused what?"; if it cannot, it is decoration and comes out. A page with no sequence to show (a chart, a set of screens, a plan) has no motion and no step controls.

When there is a sequence: the audience steps through it at the presenter's pace, never on scroll; new state enters at its final size; `prefers-reduced-motion` is respected and every state is reachable with motion off. The mechanics (arrows, streaming, stagger, start and finish marks) are in [stage-and-motion.md](stage-and-motion.md).

## Quick reference

| To convey | Use |
|---|---|
| A finding | One chart titled with the finding, values on the marks |
| Old way versus new way (only when there is an old way) | The same layout twice, then a numbers table with losses included |
| A record moving through a pipeline | One real row's fields shown at each stage, counts on the stages |
| What a new surface does | The surface once, numbered callouts with real values |
| A tool | Its real controls prefilled with a recorded run |
| When things happen | A timeline of real dates, today marked |
| A screen the user meets | The screen large, a callout for what they do and get |
| Cause and effect in one action | A multi-pane stage ([stage-and-motion.md](stage-and-motion.md)) |
| Code, SQL or config | Plain-English lines with a toggle to the real text |
| Complex logic or a decision rule | A few lines of loose pseudo-code in the reader's words, real code behind the toggle |
| Something that is not real data | "Illustrative" on the panel itself |

## Verify

Headless Chrome can check layout and errors but not timing: see [verifying-motion.md](verifying-motion.md). Tell the user what was not seen and, when the page has motion, ask them to press Play once before presenting.

## Common mistakes

| Mistake | Instead |
|---|---|
| A slide deck when nobody asked for slides | A web page or document |
| Chat window, stage and before/after on every demo | The one centrepiece the content calls for |
| Reusing the look of a previous demo | Background, palette, type and shape taken from the subject |
| A dark page because the last page was dark | Light unless the subject itself is dark |
| Header, facts list and footer on a page about a finding | The chart first; numbers on the chart |
| Step controls on a page with nothing to step through | No controls, no motion |
| A section that is a paragraph with a picture beside it | The picture, with a title and labels |
| An explanatory paragraph before the first visual | Open on the visual; the sentence goes under it |
| KPI cards, count-ups, hero taglines | Numbers on the visual, or a facts list when the page is about a run |
| Architecture diagram as the centrepiece | One real instance moving through the system |
| Jargon in headings, or code hidden entirely | Plain headings, real text one click away |
| Animations triggered by scrolling | Presenter-paced steps with controls |
| A caption restating what the visual shows | Say it once |
| Comparison as a sentence | Same layout twice plus a numbers table |
| Only the numbers where the new way wins | Every number from both, losses included |
| An opening that only makes sense after the demo | What it is in the reader's terms, plus one real instance |
| A claim headline over an abstract timeline | Real content at real timestamps, beside today's behaviour |
| Diagram boxes named after internal components | What happens, with the condition and count on each branch |
| A clever section name | A literal one |
| A mock-up panel with no label | "Illustrative" on the panel itself |
