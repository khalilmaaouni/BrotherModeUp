Status: RESEARCH. Lens C of the visual surface program. Fable, 2026-08-05.
Nothing here is built. This document is evidence plus a proposed vocabulary,
not an implementation plan and not a claim that anything works yet.

# Lens C: the visual language for showing process, state and progress to a non expert, and the accessibility floor under it

## 0. What this covers, and how to read the evidence markers

The founder's complaint names four missing things: visual documentation and
support, process and workflow drawings inside the chat, recurrent insight boxes
and key alerts, and a visible way to take the work back. This lens answers one
slice of that: what BrotherMode is allowed to DRAW, what it is allowed to
SHOUT, and what floor both must clear so a person with colour vision deficiency
or a screen reader is not locked out.

Every claim below carries one of these markers:

    FETCHED     I opened the page named and read it in this session.
    MEASURED    I computed the number myself in this session, with the script
                and its output shown.
    PARTIAL     I read a summary of a source, not the source itself. Treat as
                indicative and re-read before anyone relies on it.
    UNVERIFIED  I could not confirm it. It is written down so it can be tested,
                not so it can be believed.
    JUDGEMENT   My design choice. No citation exists because none applies. It
                is labelled so it can be argued with rather than inherited.

---

# PART ONE: drawing process for comprehension rather than completeness

## 1.1 What mermaid can actually do, and where it stops

Mermaid is the only diagram engine available inside a Claude Code artifact
without violating the no external assets rule, because artifacts render mermaid
natively (fenced ```mermaid blocks in markdown, `<pre class="mermaid">` blocks in
HTML) with no library to load. FETCHED, from the Artifact tool contract in this
session's own tool definitions rather than a web page.

Diagram inventory. Mermaid documents flowchart, sequence, class, state, entity
relationship, gantt, pie, quadrant, requirement, gitgraph, user journey,
swimlanes, mindmap, timeline, zenuml, sankey, xy chart, block, packet, kanban,
architecture, radar, event modeling, treemap, venn, ishikawa, wardley, cynefin
and treeview. Entity relationship is marked experimental; sankey, xy chart,
block, packet, kanban, architecture, radar, event modeling, treemap, venn,
ishikawa, wardley, cynefin and treeview are marked with the new or beta
indicator. FETCHED https://mermaid.js.org/intro/

Four documented limits matter more than the inventory, because each one kills a
design that otherwise looks obvious:

1. **Clicks are off by default.** `securityLevel` defaults to `"strict"`, and
   the documentation describes that level as: HTML tags in the text are encoded
   and click functionality is disabled. FETCHED
   https://mermaid.js.org/config/schema-docs/config.html
   Consequence: a diagram whose nodes are meant to be clickable links into the
   store cannot be relied on. Interactivity has to live in the surrounding HTML,
   never in the mermaid source. The flowchart page does document
   `click nodeId callback`, but explicitly notes it requires
   `securityLevel='loose'`. FETCHED https://mermaid.js.org/syntax/flowchart.html

2. **Subgraph direction is not honoured when the subgraph is wired to the
   outside.** The flowchart page states that if any of a subgraph's nodes are
   linked to the outside, subgraph direction will be ignored, and it inherits
   the parent direction. FETCHED https://mermaid.js.org/syntax/flowchart.html
   Consequence: a lane layout built from subgraphs cannot mix per lane
   directions with cross lane arrows. Pick one direction for the whole picture.

3. **Hard ceilings exist.** `maxEdges` defaults to 500 and `maxTextSize` to
   50000. FETCHED https://mermaid.js.org/config/schema-docs/config.html
   These are engine limits, not comprehension limits, and they are roughly
   fifty times larger than anything a non expert should ever be shown. They are
   worth noting only because a generated diagram that reads unbounded rows from
   a store will hit them silently one day.

4. **State diagram styling has holes.** `classDef` on a state diagram cannot be
   applied to start or end states, or to composite states.
   FETCHED https://mermaid.js.org/syntax/stateDiagram.html
   Consequence: any status colour coding on a state diagram has to live on
   ordinary states, and the terminal states have to carry their meaning in their
   label. Which, given WCAG 1.4.1 below, they had to anyway.

Two syntax traps in flowcharts, both documented: the word `end` breaks a
flowchart unless capitalised in whole or part, and a node id starting with `o`
or `x` needs spacing or capitalisation. FETCHED
https://mermaid.js.org/syntax/flowchart.html
Consequence for a generator that interpolates store values into node labels:
these are not style preferences, they are escaping requirements, and the
generator needs a sanitiser with a test.

## 1.2 State diagrams

Mermaid's state diagram supports states, transitions with labels, `[*]` for
start and stop, composite states via `state id { }`, `<<choice>>` for branching,
`<<fork>>` and `<<join>>` for concurrency, `note right of` / `note left of`, and
`--` for concurrent regions. FETCHED https://mermaid.js.org/syntax/stateDiagram.html

The honest reading: a state diagram answers "what condition is this one thing
in, and what can happen to it next". It does not answer "how far along are we"
and it does not answer "who is doing it". It is the right shape for the
lifecycle of a single unit of work, and the wrong shape for a project overview,
because a non expert reading a state chart of a whole project has to simulate
the machine in their head to find themselves on it.

`<<fork>>`, `<<join>>` and the `--` concurrency separator should be treated as
off limits for founder facing drawings. JUDGEMENT. They express a machine
concept (parallel regions) whose visual form is a bar, which carries no meaning
to a reader who has not been taught UML.

## 1.3 Sankey

Mermaid's sankey diagram is documented as experimental, in the documentation's
own words: this is an experimental diagram, its syntax is very close to plain
CSV but it is to be extended in the nearest future. The CSV must be exactly
three columns (source, target, value). Configuration covers `linkColor`
(`source`, `target`, `gradient` or a hex value), `nodeAlignment`, and from
v11.15.0 label style, node width, node padding and per node colours. FETCHED
https://mermaid.js.org/syntax/sankey.html

What a sankey is FOR: the Financial Times Visual Vocabulary places sankey in the
**flow** category, defined as volumes or intensity of movement between two or
more states or conditions, and describes the sankey as showing changes in flows
from one condition to at least one other, good for tracing the eventual outcome
of a complex process. FETCHED
https://github.com/Financial-Times/chart-doctor/tree/main/visual-vocabulary
The full FT category set is deviation, correlation, ranking, distribution,
change over time, part to whole, magnitude, spatial and flow.

The verdict for BrotherMode: a sankey is a magnitude-of-flow chart, and
BrotherMode's founder facing questions are almost never about magnitude of flow.
"Where are we", "what is blocked", "who holds the pen", "what did you decide"
are sequence, state and ownership questions, not flow volume questions. There is
exactly one plausible sankey in this product (how a cohort of findings moved
between the states raised, refuted, deferred, repaired and re-checked) and even
that reads better as five numbers in a row. Combined with the experimental
label, sankey should be banned. JUDGEMENT, resting on the two FETCHED sources
above.

## 1.4 Swimlanes

Mermaid now documents a swimlane diagram. It opens with the keyword
`swimlane-beta`, lanes are declared with `subgraph` (top level subgraphs are
rendered as swimlanes), and the documentation carries the warning: this is a new
diagram type in Mermaid, its syntax may evolve in future versions. Its stated
purpose is the sharpest one line justification for lanes I found anywhere: use
swimlane diagrams when the most important question is not only "what happens
next?" but also "who owns this step?", and it names approval flows, support
processes and delivery workflows, recommending plain flowcharts, sequence
diagrams or state diagrams when ownership is not the primary concern. FETCHED
https://mermaid.js.org/syntax/swimlanes.html

Whether `swimlane-beta` parses in the mermaid build that ships inside a Claude
Code artifact is UNVERIFIED. I have no way to inspect the rendered output of a
published artifact from here (fetching an artifact URL returns source, not the
rendered SVG). The safe engineering answer is to get the swimlane READING while
using only syntax that has existed for years: a `flowchart LR` with one
`subgraph` per owner. That renders the same idea, and it is the construction the
swimlane page itself says its lanes are built from.

Note the collision with limit 2 above: lanes wired to each other lose their own
direction. So a lane map must be single direction throughout. That is not a
hardship, it is a discipline: a founder facing lane map that needs two
directions is too complicated to show a founder.

## 1.5 Cognitive effectiveness of a notation

Moody's Physics of Notations proposes nine principles for designing visual
notations that are cognitively effective, defined as the speed, ease and
accuracy with which information can be processed by the human mind: semiotic
clarity, perceptual discriminability, visual expressiveness, semantic
transparency, dual coding, graphic economy, cognitive integration, complexity
management and cognitive fit. PARTIAL: I read search result summaries and
abstract pages, not the paper itself. Re-read
https://www.semanticscholar.org/paper/The-%22physics%22-of-notations%3A-a-scientific-approach-Moody/73f214edc7e36c1c9aeca212ed828116a2db5522
before quoting it in anything the founder signs.

Four of the nine map directly onto decisions later in this document, and I am
using them as vocabulary rather than as proof:

    graphic economy       the number of distinct symbols must stay small
    dual coding           carry meaning in text as well as in graphics
    perceptual            symbols must be told apart at a glance, not by
    discriminability      squinting at two similar hues
    complexity management a notation needs a way to show less, not just a way
                          to show everything

Dual coding is the interesting one, because it is independently required by WCAG
1.4.1 for a completely different reason (section 3.2). When an accessibility
rule and a comprehension theory demand the same thing, that thing is not a
tradeoff, it is a floor.

## 1.6 Complexity management: the only cited number I trust here

Nielsen Norman Group on progressive disclosure: initially show users only a few
of the most important options, then offer a larger set of specialised options
upon request; it improves three of usability's five components (learnability,
efficiency of use and error rate); and, the number worth keeping, designs beyond
two disclosure levels typically have low usability because users often get lost
when moving between the levels. FETCHED
https://www.nngroup.com/articles/progressive-disclosure/

That gives a hard architectural rule with a citation behind it: BrotherMode's
visual surface gets AT MOST two levels. Level one is the picture in the chat.
Level two is the artifact page it opens. There is no level three. A drill down
inside the artifact that opens another artifact is a design failure.

For per diagram size I have no citable threshold and will not fake one. The node
and edge caps in section 5.3 are JUDGEMENT, derived from graphic economy and
from the two level rule, and they are stated as testable numbers precisely so
they can be argued down by anyone with better evidence.

## 1.7 Diagrams and system status

Nielsen's first usability heuristic: the design should always keep users
informed about what is going on, through appropriate feedback within a
reasonable amount of time. The fourth: users should not have to wonder whether
different words, situations, or actions mean the same thing, follow platform and
industry conventions. The sixth: minimise the user's memory load by making
elements, actions and options visible, the user should not have to remember
information from one part of the interface to another. FETCHED
https://www.nngroup.com/articles/ten-usability-heuristics/

Heuristic six is the argument against BrotherMode's current shape. A chat
transcript is pure recall: the founder must remember what was said two hours
ago, because nothing on screen holds the state. A generated view is recognition.
That is the whole case for this program in one sentence, and it is cited.

---

# PART TWO: alerts, insights, and not burning the founder out

## 2.1 Alert fatigue is a documented failure mode with named mitigations

AHRQ Patient Safety Network defines alert fatigue as busy workers becoming
desensitised to safety alerts, and as a result ignoring or failing to respond
appropriately to such warnings; it observes that clinicians generally override
the vast majority of computerised order entry warnings, even critical alerts
that warn of potentially severe harm. Its mitigations, in its own words: tier
alerts according to severity, with warnings presented in different ways in order
to key clinicians to alerts that are more clinically consequential; increase
alert specificity by reducing or eliminating clinically inconsequential alerts;
make only high level (severe) alerts interruptive; and tailor alerts to patient
risk so they trigger only for patients at high risk. FETCHED
https://psnet.ahrq.gov/primer/alert-fatigue

Read the third one again, because it is the single most transferable rule in
this entire document: **make only the top rung interruptive.** Everything below
the top rung is available, not thrown.

## 2.2 The software industry's version of the same finding

Google SRE, Monitoring Distributed Systems, defines an alert as a notification
intended to be read by a human and pushed to a system such as a bug or ticket
queue, an email alias, or a pager, and classifies those three destinations as
tickets, email alerts and pages. On noise it says: when pages occur too
frequently, employees second-guess, skim, or even ignore incoming alerts,
sometimes even ignoring a "real" page that's masked by the noise; outages can be
prolonged because other noise interferes with a rapid diagnosis and fix;
effective alerting systems have good signal and very low noise. On thresholds:
you should never trigger an alert simply because "something seems a bit weird".
On construction: rules that generate alerts for humans should be simple to
understand and represent a clear failure. And on the split that matters most
here: "what" versus "why" is one of the most important distinctions in writing
good monitoring with maximum signal and minimum noise, where the what is the
symptom and the why is the cause. FETCHED
https://sre.google/sre-book/monitoring-distributed-systems/

Three things transfer to BrotherMode intact:

- The same event can be delivered at three different intensities, and the
  intensity is a separate decision from the event.
- "Seems a bit weird" is never a reason to interrupt.
- Symptom and cause are different objects. This is the technical basis for
  separating an ALERT from an INSIGHT, which the founder's brief already
  intuited by asking for both.

## 2.3 What documentation systems actually ship, and how little they agree

| System | Types | Source |
| --- | --- | --- |
| GitHub | NOTE, TIP, IMPORTANT, WARNING, CAUTION | FETCHED docs.github.com basic writing and formatting syntax |
| Docusaurus | note, tip, info, warning, danger | FETCHED https://docusaurus.io/docs/markdown-features/admonitions |
| MDN | NOTE, WARNING, CALLOUT | FETCHED https://developer.mozilla.org/en-US/docs/MDN/Writing_guidelines/Howto/Markdown_in_MDN |

GitHub's five, in GitHub's own definitions:

    NOTE       Useful information that users should know, even when skimming
               content.
    TIP        Helpful advice for doing things better or more easily.
    IMPORTANT  Key information users need to know to achieve their goal.
    WARNING    Urgent info that needs immediate user attention to avoid
               problems.
    CAUTION    Advises about risks or negative outcomes of certain actions.

And GitHub's restraint rule, verbatim and load bearing: "Use alerts only when
they are crucial for user success and limit them to one or two per article to
prevent overloading the reader. Alerts cannot be nested within other elements."
It also defines the family: "Alerts, also sometimes known as callouts or
admonitions, are a Markdown extension based on the blockquote syntax that you can
use to emphasize critical information." FETCHED
https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax
(note: this domain was blocked to my primary fetcher and was retrieved through a
second scraper in this session, quoting the live page.)

MDN, running one of the largest documentation sites in the world, deliberately
supports only three and explicitly refuses the other GitHub types: it states
that MDN does not support `[!TIP]`, `[!CAUTION]` or `[!IMPORTANT]`, and adds a
custom `[!CALLOUT]` whose distinguishing property is that it does NOT prepend a
localised label, which makes it the right choice when an author wants to provide
a custom title. FETCHED
https://developer.mozilla.org/en-US/docs/MDN/Writing_guidelines/Howto/Markdown_in_MDN

The finding: there is no industry standard ladder. Three serious systems ship
three, five and five, and the two that ship five disagree on what the five are
(GitHub has no `danger`, Docusaurus has no `important`). Copying any one of them
would be cargo cult. The transferable parts are not the type names, they are
(a) the small count, (b) the one or two per page cap, and (c) MDN's insight that
a box which does not shout is a distinct and useful thing.

## 2.4 Banners, and the evidence that people miss them

The GOV.UK Design System notification banner tells a user about something they
need to know about that is not directly related to the page content. Its
restraint guidance carries actual evidence: notification banners should be used
sparingly, because there is evidence that people often miss them, and using them
too often is likely to make this problem worse. It refuses two uses outright: do
not use a notification banner to tell the user about validation errors, and do
not show a notification banner and an error summary on the same page. It ships
exactly two variants, a neutral important one and a success one, and its
accessibility construction is instructive: the neutral banner uses
`role="region"` with `aria-labelledby`, the success banner uses `role="alert"`
so focus shifts to it, and the success version uses a text heading reading
"Success" rather than relying on the green. FETCHED
https://design-system.service.gov.uk/components/notification-banner/

Two variants. A government design system serving tens of millions of people
ships two. That is the strongest single argument in this document for keeping
BrotherMode's ladder short.

## 2.5 The assistive technology side of interrupting

MDN on `role="alert"`: it communicates an important and usually time sensitive
message; it is an assertive live region, equivalent to `aria-live="assertive"`
plus `aria-atomic="true"`, which means alerts are intrusive and interrupt the
user; because of its intrusive nature the alert role must be used sparingly and
only in situations where the user's immediate attention is required; several
alerts at once, and unnecessary alerts, create bad user experiences; dynamic
changes that are less urgent should use a less aggressive method such as
`aria-live="polite"` or the `status` role; and the element with the alert role
does not have to be able to receive focus, since screen readers announce the
updated content regardless of where keyboard focus is. FETCHED
https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/alert_role

This gives the severity ladder a MECHANICAL definition rather than a stylistic
one. A rung is not "red" or "important sounding". A rung is a delivery
behaviour: assertive, polite, or silent. Everything else is decoration on top of
that choice.

## 2.6 The signal word ladder from outside software

ANSI Z535 uses DANGER, WARNING, CAUTION and NOTICE. DANGER is for an imminently
hazardous situation which, if not avoided, will result in death or serious
injury; WARNING for a potentially hazardous situation which, if not avoided,
could result in death or serious injury; CAUTION for potentially hazardous
situations which may result in minor injury; and NOTICE is the preferred signal
word for practices not related to personal injury. The safety alert symbol (an
exclamation mark in a triangle) accompanies DANGER, WARNING and CAUTION but is
NOT used with NOTICE. PARTIAL: Z535 is a paid standard and I read vendor and
association summaries, chiefly
https://blog.ansi.org/ansi/ansi-z535-4-2023-product-safety-sign-or-label/ and
https://www.safetysign.com/safety-header , not the standard text. Treat the
definitions as indicative.

The transferable idea is not the four words. It is the structural separation
between the hazard rungs and NOTICE, and the fact that a DIFFERENT GLYPH marks
the boundary. The rungs that mean "act" share a mark. The rung that means "know"
does not. BrotherMode should copy that structure and not the vocabulary, since
"DANGER" in a software assistant is theatre.

## 2.7 So what is the difference between an alert and an insight?

Nothing I fetched defines this pair directly, so this is JUDGEMENT built on top
of the cited material, mainly the SRE symptom/cause split and MDN's callout that
deliberately does not shout.

    An ALERT is about the reader's next action.
      It states a condition that is true right now.
      It names exactly one action, and who must take it.
      It is dismissed by doing the thing, not by reading it.
      It ages: once the condition clears, the alert disappears from the view,
      because the view is generated from rows.
      It answers WHAT and it interrupts.

    An INSIGHT is about the reader's model of the work.
      It states a claim, the evidence class behind it, what else was considered,
      and what would change it.
      It requires no action, and offering one is optional.
      It does not age out. It is a permanent ledger row.
      It answers WHY and it never interrupts.

The practical test, which is the sentence I would put in the implementation
brief: if the reader could do nothing about it and the project would be
unaffected, it is not an alert. If the reader could act on it but the reason
does not matter, it is not an insight. Anything that is genuinely both gets
written as an insight with an alert pointing at it, never duplicated as two
independent boxes, since duplication is exactly the noise the SRE chapter warns
about.

This maps cleanly onto the already designed ledger in
`docs/program/absolute-lead/DESIGN-insight-ledger-and-handback.md`: the
`insights` table with `kind` in DECISION, CALIBRATION, RISK, LEARNING, HANDBACK
is the insight side, and `evidence_class` (EXECUTED, MEASURED, READ, REASONED)
is precisely the field that lets an insight box show its own strength. The alert
side has no table yet, and section 5.5 argues it should not get one: alerts
should be DERIVED from existing rows, not stored, so that they cannot go stale.

---

# PART THREE: the accessibility floor

## 3.1 Contrast minimums

WCAG 2.2 Success Criterion 1.4.3 Contrast (Minimum), level AA: the visual
presentation of text and images of text has a contrast ratio of at least 4.5:1,
except that large scale text and images of large scale text have a contrast
ratio of at least 3:1. Large scale is defined as at least 18 point, or 14 point
bold, or a font size that would yield an equivalent size for Chinese, Japanese
and Korean fonts; the Understanding document gives approximately 18.5px and 24px
as the pixel equivalents of 14pt and 18pt. Exceptions cover incidental text
(inactive components, pure decoration, invisible text, or text that is part of a
picture containing significant other visual content) and logotypes. And the
detail that catches implementations out: when comparing the computed contrast
ratio to the success criterion ratio, the computed values should not be rounded,
so 4.499:1 does not meet the 4.5:1 threshold. FETCHED
https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html

WCAG 2.2 Success Criterion 1.4.11 Non-text Contrast, level AA, 3:1: the visual
presentation of user interface components (visual information required to
identify components and states, excepting inactive components or appearance
determined by the user agent) and of graphical objects (parts of graphics
required to understand the content, except when a particular presentation is
essential) must have a contrast ratio of at least 3:1 against adjacent colours.
FETCHED https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html

The consequence people miss: **the lines and node borders in a diagram are
graphical objects required to understand the content.** A mermaid default theme
that draws pale grey strokes on white fails 1.4.11 even if every label passes
1.4.3. Any BrotherMode diagram must therefore ship an explicit theme, not a
default one.

## 3.2 Colour is never the only carrier

WCAG Success Criterion 1.4.1 Use of Color, level A: colour is not used as the
only visual means of conveying information, indicating an action, prompting a
response, or distinguishing a visual element. The Understanding document's chart
example is exactly our case: a diagram whose legend carries both colour and
numeric identifiers remains usable by someone who cannot perceive the colour
differences. It also states plainly that the criterion is not discouraging the
use of colour, only its use as the sole mechanism. FETCHED
https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html

Level A. Not AA. This is the floor of the floor.

## 3.3 Colour Universal Design, from people who cannot see the difference

The Okabe and Ito Color Universal Design page states three plus one principles,
verbatim:

1. Choose color schemes that can be easily identified by people with all types
   of color vision, in consideration with the actual lighting conditions and
   usage environment.
2. Use not only different colors but also a combination of different shapes,
   positions, line types and coloring patterns, to ensure that information is
   conveyed to all users including those who cannot distinguish differences in
   color.
3. Clearly state color names where users are expected to use color names in
   communication.
   Plus one: moreover, aim for visually friendly and beautiful designs.

Its most important practical points for graphs and line drawings, verbatim:
"For graphs and line drawings, label elements of the graph on the graph itself
rather than making a separate color-coded key, since matching same colors in
distant places is extremely difficult." And: "Do not convey information in color
only. Show difference BOTH in color and shape (solid and dotted lines, different
symbols, various hatching, etc.)."

On red specifically: for colourblind readers red is as dull as blue or dark
green, and for protanopes dark red appears almost as black, so red characters on
black backgrounds should be avoided and black text and red text look the same to
protanopes; instead of pure dark red the page recommends vermilion (RGB 100%,
32%, 0%, that is #FF2000) or light red (#FF1414). On combining palette colours:
use warm and cool colours alternately; when using two warm or two cool colours,
put distinct differences in brightness or saturation; avoid combinations of
colours with low saturation or low brightness. On talking about diagrams: avoid
indicating objects only by names, for example avoid saying "this red cell",
instead say "this red, round cell on the top left". Frequency: one in twelve
Caucasian (8%), one in twenty Asian (5%) and one in twenty five African (4%)
males are red-green colourblind. FETCHED https://jfly.uni-koeln.de/color/

The eight hex values of the Okabe-Ito palette (#E69F00 orange, #56B4E9 sky blue,
#009E73 bluish green, #F0E442 yellow, #0072B2 blue, #D55E00 vermilion, #CC79A7
reddish purple, #000000 black) are published on that page only as an IMAGE, so I
could not read them from the page itself. The list above comes from secondary
references and is therefore PARTIAL. The palette proposed in section 5.6 uses
#D55E00, #E69F00, #0072B2, #56B4E9 and #009E73 as its hue anchors, but every
value actually shipped is contrast tested by me (section 5.6), so nothing in the
proposal depends on the unverified hex list being right.

## 3.4 Diagrams need a text alternative in two parts

W3C WAI's complex images tutorial splits the alternative in two: a short
description to identify the image and, where appropriate, indicate the location
of the long description; and a long description, being a textual representation
of the essential information conveyed by the image. It recommends putting the
long description on the page (adjacent text, or a `figure` with `figcaption`
enclosing both image and description, or a data table inside the `figcaption`),
and notes that when the description is on the page it is available to everyone,
not only to assistive technology users. FETCHED
https://www.w3.org/WAI/tutorials/images/complex/

Mermaid supports the machine readable half of this natively. `accTitle: single
line title` produces a `<title>` element referenced by `aria-labelledby`, and
`accDescr: single line` or `accDescr { multi line }` produces a `<desc>`
referenced by `aria-describedby`; mermaid also sets `aria-roledescription` to
the diagram type key. FETCHED https://mermaid.js.org/config/accessibility.html

So the rule writes itself: every generated diagram carries `accTitle` and
`accDescr`, AND sits in a `<figure>` whose `<figcaption>` states the same
content in prose that a sighted non expert can read without decoding the
picture. The prose is not a duplicate cost, it is the thing that makes the
picture optional, which is what a founder who cannot read logs actually needs.

## 3.5 Progress, stated accessibly

`role="progressbar"` requires an accessible name (`aria-label` or
`aria-labelledby`), and supports `aria-valuenow` (required unless the value is
indeterminate, and omitted entirely when it is), `aria-valuemin` (defaults 0),
`aria-valuemax` (defaults 100) and `aria-valuetext` for when a percentage would
not be an accurate representation. MDN's recommended alternative is the native
`<progress>` element with a `<label>`. FETCHED
https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/progressbar_role

`aria-valuetext` is the one to actually use here, because "4 of 7 gates passed"
is a truthful statement about BrotherMode and "57%" is not.

## 3.6 Both themes, no assets

`prefers-color-scheme` accepts `light` (the user prefers a light theme or has
expressed no active preference) and `dark`. It is a pure CSS media feature
requiring no external resources, scripts or libraries, widely available since
January 2020. FETCHED
https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-color-scheme

Mermaid is themed via `mermaid.initialize({ theme: ... })` or per diagram
frontmatter, with built in themes default, neutral, dark, forest and base, where
base is the only theme that can be modified, through `themeVariables`
(`primaryColor`, `primaryTextColor`, `lineColor` and diagram specific keys), and
no external assets are involved. FETCHED
https://mermaid.js.org/config/theming.html

Consequence: to satisfy both 1.4.11 and the artifact theme rule, BrotherMode
must render mermaid with `theme: 'base'` plus an explicit `themeVariables` block
computed for the active scheme, and must not rely on `default` or `dark`.

## 3.7 What GOV.UK learned about status labels

The GOV.UK task list component writes statuses in sentence case rather than
uppercase, on the stated grounds that the use of uppercase in task statuses
makes them harder to read; it moved the completed status to black text with no
background colour so that colour draws attention to the tasks that still require
action rather than to the finished ones; and it introduced a status colour
palette using colour contrasts that meet accessibility guidance. FETCHED
https://design-system.service.gov.uk/components/task-list/

The second point is a genuinely good idea and inverts the naive design: do not
paint the done things green. Paint nothing done, and spend the colour budget on
the things that are not done. A founder scanning a list should have their eye
pulled to work, not to trophies.

---

# PART FOUR: what BrotherMode has today, so this proposal does not duplicate it

Read in this session from `/Users/khalil.maaouni/Documents/BrotherModeUp`:

- The documentation exporter (`tools/bm_docs_export.py`, 407 lines) contains no
  HTML, no SVG and no styling. Its own comment says markdown plus mermaid is
  always produced. So mermaid is ALREADY the drawing medium in this codebase;
  this proposal constrains it rather than introducing it.
- `Documentation/` is a numbered folder set (00-START-HERE, 10-business,
  20-technical, 30-decisions, 40-handover, 90-generated).
- The insight ledger, half hour briefing and handback are designed and not
  built, with the schema, the six line briefing block and the handback wording
  already specified.

So the gap this lens fills is narrow and specific: there is a medium (mermaid),
there is a generator, there is a designed ledger, and there is no VOCABULARY
saying which shapes may be drawn, what the rungs mean, and what the boxes look
like. That is what follows.

---

# PART FIVE: the proposed visual vocabulary

Everything in this part is JUDGEMENT unless it carries a marker. The citations
above constrain it; they do not dictate it. None of it is implemented.

## 5.0 Four laws the vocabulary obeys

    L-V1  Generated, never authored. Every diagram, badge, box and number is a
          pure function of store rows. There is no hand written picture, for the
          same reason CANVAS.md is generated.
    L-V2  Two levels, no more. The chat carries level one. One artifact page
          carries level two. Nothing carries level three.
          (Cited: NN/g progressive disclosure, section 1.6.)
    L-V3  Monochrome first. Every element must survive being printed in black
          and white and being read aloud. Colour is the third carrier, after
          word and shape.
          (Cited: WCAG 1.4.1 level A, and CUD principle 2, sections 3.2 and 3.3.)
    L-V4  One vocabulary, two renderings. The same five diagrams, four rungs and
          one box shape render as plain text in the terminal chat and as styled
          HTML in the artifact. A concept that only works in one of the two does
          not enter the vocabulary.

L-V4 is the one that will be violated first and should be defended hardest.
Claude Code is a terminal. A design that assumes a browser is a design the
founder only sees when he goes looking, which is the current failure restated.

## 5.1 The five diagrams, and nothing else

BrotherMode draws five shapes. Each one exists because a specific founder
question has no other good answer.

### D1. The pipeline. "Where are we?"

    Mermaid: flowchart LR
    Shape:   3 to 7 stages in a single line, one marked as current.
    Reads:   phase rows, the current work record.
    Level:   one (chat) and two (artifact).

```mermaid
---
config:
  theme: base
---
flowchart LR
  accTitle: Where the project is now
  accDescr: Five stages left to right. Understand and Design are complete.
    Build is in progress. Verify and Ship have not started.
  A["Understand<br/>complete"]:::done --> B["Design<br/>complete"]:::done
  B --> C["Build<br/>NOW"]:::now
  C --> D["Verify<br/>waiting"]:::idle
  D --> E["Ship<br/>waiting"]:::idle
  classDef done fill:#E8F6F0,stroke:#009E73,color:#00543A
  classDef now fill:#EAF3FA,stroke:#0072B2,color:#00436B,stroke-width:3px
  classDef idle fill:#F1F2F4,stroke:#767B84,color:#3F4650
```

The current stage is marked three ways: the word NOW in the label, a thicker
stroke, and a different fill. That is L-V3 in one node.

### D2. The gate ladder. "What has to be true before this ships?"

    Mermaid: flowchart TD, one column
    Shape:   the ordered gates, each with pass, fail or not run.
    Reads:   gate results for the current unit.
    Level:   two (artifact), summarised as a count line at level one.

A vertical list of gates with a status word per row answers "why is this not
shipped yet" without the founder reading a single log line. A failed gate is the
only node permitted to carry the stop colour, and it carries the word BLOCKED
next to it.

### D3. The lane map. "Who holds the pen?"

    Mermaid: flowchart LR with one subgraph per owner
    Shape:   2 to 4 lanes, single direction throughout.
    Reads:   fence ownership, dispatch rows, founder step rows.
    Level:   two.

Built from `subgraph`, not from `swimlane-beta`, until the artifact renderer's
mermaid version is confirmed (section 1.4, UNVERIFIED). Mermaid's own criterion
governs when this is drawn at all: only when the important question is who owns
the step, not merely what happens next. FETCHED, section 1.4.

Remember limit 2: cross lane arrows void per lane direction, so the whole map is
LR or the whole map is TD.

### D4. The decision fork. "You are being asked something."

    Mermaid: flowchart TD
    Shape:   exactly one question node, two or three outcome nodes, one of which
             is always the handback.
    Reads:   the open decision window plus the insight row behind it.
    Level:   one (chat) and two.

```mermaid
---
config:
  theme: base
---
flowchart TD
  accTitle: Open decision, three options
  accDescr: One question with three outcomes. Option A keeps the current
    approach. Option B changes it. Option C hands the work back to you.
  Q{"Supersede the flaky test,<br/>or chase the race it found?"}:::ask
  Q -->|"A. Chase the race<br/>slower, keeps coverage"| A["I continue"]:::go
  Q -->|"B. Supersede it<br/>faster, loses a check"| B["I continue"]:::go
  Q -->|"C. Hand it back"| C["You take this<br/>and the work under it"]:::hand
  classDef ask fill:#FFF6E5,stroke:#A06A00,color:#6B4400
  classDef go fill:#F1F2F4,stroke:#767B84,color:#3F4650
  classDef hand fill:#EAF3FA,stroke:#0072B2,color:#00436B,stroke-width:3px
```

The handback branch is always present, always last, always the emphasised node.
That is the founder's "giving him the hand to take over" made structural rather
than polite, and it matches the already designed rule that a decision window
rendered without a handback option is a test failure.

### D5. The count row. "How much, against what limit?"

    Not mermaid. Hand written HTML divs (artifact) or a text bar (chat).
    Shape:   labelled bars with the raw numbers written on them.
    Reads:   token and minute spend against ceiling, findings by rung, gates
             passed of total.
    Level:   one and two.

Chat form, which must be as informative as the artifact form:

    Gates      passed 4 of 7   [####----]
    Budget     18k of 40k tokens, 26 of 90 minutes
    Findings   needs you 1, at risk 3, for info 6

In the artifact this becomes bars with `role="progressbar"`,
`aria-valuetext="4 of 7 gates passed"`, and the number printed inside the bar so
the bar is decoration and the number is the content (section 3.5, FETCHED).

### Banned, with the reason

    sankey         experimental, and BrotherMode has no flow magnitude question
                   (section 1.3, FETCHED)
    gantt          implies dated commitments this product cannot honour, and
                   invites a founder to read a plan as a promise
    pie            part to whole of nothing anyone needs, and angle comparison
                   is the weakest visual encoding available
    mindmap,       shapes for authors, not for readers of state
    timeline
    class, ER,     they describe code and data models, which the founder
    sequence       explicitly does not read
    quadrant,      chart types with no store row behind them; any use would be
    xychart,       hand authored, violating L-V1
    radar
    fork/join,     UML machinery with no meaning to an untrained reader
    concurrency
    (section 1.2)

That is five allowed shapes against roughly twenty five available. Graphic
economy is the point, not a side effect.

## 5.2 The wording rules that go with the shapes

- Node labels are noun phrases plus a status word, never sentences and never
  identifiers. "Build, NOW", not "wr_8813 in_progress".
- Every label carries its status as a WORD. Never as colour alone (WCAG 1.4.1,
  level A) and never as a bare glyph.
- Labels go on the drawing, not in a separate key. CUD, verbatim, section 3.3.
- The chat text that introduces a diagram never says "the red one". It names the
  thing and its position. CUD, verbatim, section 3.3.
- Identifiers (record ids, hashes, paths) are permitted in the artifact's text,
  never inside a diagram node.

## 5.3 Size caps (JUDGEMENT, testable)

    nodes per diagram          9 maximum
    edges per diagram          12 maximum
    lanes in D3                4 maximum
    stages in D1               7 maximum
    outcomes in D4             3 maximum, one of which is the handback
    diagrams per chat message  1
    diagrams per artifact page 4

When the data exceeds the cap, the generator does not shrink the font, it
AGGREGATES and says so in the caption: "3 of 14 gates shown, the 3 that are not
passing". Mermaid's own ceilings (500 edges, 50000 characters, FETCHED section
1.1) are irrelevant at this scale and exist only as a backstop assertion in the
generator.

## 5.4 The severity ladder: four rungs, one interrupting

The ladder is defined by DELIVERY BEHAVIOUR first (per section 2.5), then by
name, then by appearance. Rung names are what a non engineer would say out loud.

| Rung | Means | Delivery | Where it may appear | ARIA | Cap |
| --- | --- | --- | --- | --- | --- |
| **NEEDS YOU** | Work is stopped until a human acts. Names one action and one actor. | Interrupts: emitted into chat the moment the row appears, and pinned at the top of the artifact | Chat and artifact | `role="alert"` | At most ONE on screen. A second one queues. |
| **AT RISK** | Nothing is stopped, but something is likely to stop or to be wrong. Names what would settle it. | Polite: appears in the next briefing and in the artifact | Chat (briefing only) and artifact | `role="status"` | At most 3 shown, rest counted |
| **FOR INFO** | True, worth knowing, requires nothing. | Silent: artifact only, plus the count line in chat | Artifact | none (plain region) | Counted, not listed, above 6 |
| **SETTLED** | A thing that was open is now closed, with the evidence that closed it. | Silent, and deliberately low contrast. | Artifact | none | No cap, collapsed by default |

Rules, each traceable to a citation:

1. **Only NEEDS YOU interrupts.** Directly from AHRQ: make only high level
   (severe) alerts interruptive. FETCHED, section 2.1.
2. **At most one NEEDS YOU at a time, and at most two rungs visible in any chat
   message.** From GitHub's one or two per article cap, FETCHED section 2.3, and
   MDN's several alerts at once create bad user experiences, FETCHED section 2.5.
3. **A rung is assigned by a rule over store rows, never by an author's feel.**
   From SRE: rules that generate alerts for humans should be simple to
   understand and represent a clear failure, and never alert because something
   seems a bit weird. FETCHED, section 2.2. Concretely: NEEDS YOU is exactly the
   set of rows that block progress and name a human actor (open decision window,
   failed hard gate, consent not yet given, fence held by a human, budget
   ceiling reached). If a condition cannot be expressed as such a query, it is
   not a NEEDS YOU.
4. **No promotion by age.** An AT RISK does not become a NEEDS YOU because it
   has been ignored. It becomes NEEDS YOU only when the blocking condition
   becomes true. Time based escalation is the classic manufacture of noise.
5. **SETTLED is deliberately quiet and uncoloured.** From GOV.UK's task list
   change: spend the colour on what still needs action. FETCHED, section 3.7.
6. **The ladder has no fifth rung, ever.** Adding one requires deleting one.

Note what is NOT on the ladder: there is no TIP and no CAUTION. MDN dropped
exactly those two plus IMPORTANT and runs fine (FETCHED, section 2.3). A tip is
documentation, and documentation belongs in the artifact's help panel, not in
the alert stream.

### The visual mark, and the ANSI structure borrowed

The action rungs (NEEDS YOU, AT RISK) and the knowledge rungs (FOR INFO,
SETTLED) get structurally different marks, copying the ANSI separation of hazard
signal words from NOTICE (PARTIAL, section 2.6):

    NEEDS YOU   solid left bar, 6px, plus the word, plus a filled triangle glyph
    AT RISK     solid left bar, 3px, plus the word, plus an open triangle glyph
    FOR INFO    dotted left bar, 3px, plus the word, no triangle
    SETTLED     no bar, plus the word, no triangle

Four discriminable states in monochrome, before a single colour is applied.
Bar weight, bar style, glyph presence and glyph fill are four independent
non colour channels. That is dual coding done properly rather than as a
disclaimer.

### The chat rendering, which must work with zero styling

    ▌NEEDS YOU  Setup consent not given. Nothing has been written yet.
    ▌           Say "go ahead" to create the project files, or "not yet".

    │AT RISK    The flaky test in test_store.py has failed 3 of 9 runs.
    │           A 20 run repeat would settle whether it is the race or the fixture.

    ┆FOR INFO   4 gates passed of 7. Budget 18k of 40k tokens.

No colour. No emoji. It reads correctly in a monochrome terminal, in a
screen reader, and pasted into an email. JUDGEMENT, satisfying L-V3 and L-V4.

Emoji are deliberately excluded as the primary mark: their screen reader
announcements are verbose and inconsistent, and the founder's own standing
instruction bans them in assistant output. UNVERIFIED as to the exact screen
reader behaviour, which I did not test; the house rule settles it either way.

## 5.5 Alerts are derived, never stored

JUDGEMENT, and the most consequential engineering claim here.

The insights table is append only and permanent, which is correct for insights
because an insight is a historical claim. An alert is the opposite: it is a
statement about NOW, and a stored alert is a lie the moment the condition
clears. So there is no `alerts` table. There is one function:

    alerts_now(store) -> [Alert]   pure, ordered, deduplicated, capped

built from queries over rows that already exist (gate results, decision windows,
fences, consent state, budget counters, work records). Consequences worth
stating because they are the payoff:

- An alert cannot go stale, so nobody has to write dismissal logic, and there is
  no "mark as read" state to get wrong.
- The chat and the artifact cannot disagree, because both call the same
  function.
- Testing an alert means inserting rows and asserting the returned list, with no
  UI in the loop.
- A stale alert becomes impossible rather than unlikely, which is the same
  reasoning the ledger design already uses to refuse a second source of truth.

## 5.6 Colour tokens, measured

MEASURED. Computed in this session with a standard library script implementing
the WCAG relative luminance and contrast ratio formulas, at
`scratchpad/contrast.py`, run with `python3 contrast.py`. The script's own
sanity checks returned 21.0:1 for black on white and 4.54:1 for #767676 on
white, which are the known reference values, so the implementation is confirmed
against something independent of my palette. All 40 pairs cleared their floor;
0 failures. These numbers describe the proposed tokens, not shipped code.

Light theme (page #FFFFFF):

| Token | Ink (text) | Rule (border, glyph) | Tint (fill) | Ink on tint | Rule on tint | Rule on page |
| --- | --- | --- | --- | --- | --- | --- |
| needs-you | #8C2D00 | #D55E00 | #FDEFE8 | 7.50:1 | 3.44:1 | 3.87:1 |
| at-risk | #6B4400 | #A06A00 | #FFF6E5 | 7.98:1 | 4.29:1 | 4.61:1 |
| for-info | #00436B | #0072B2 | #EAF3FA | 9.28:1 | 4.62:1 | 5.19:1 |
| settled | #00543A | #009E73 | #E8F6F0 | 8.10:1 | 3.07:1 | 3.42:1 |
| idle | #3F4650 | #767B84 | #F1F2F4 | 8.51:1 | n/a | 4.25:1 |
| body text | #1A1D21 | n/a | n/a | n/a | n/a | 16.91:1 |
| muted text | #575E68 | n/a | n/a | n/a | n/a | 6.55:1 |

Dark theme (page #12151A):

| Token | Ink | Rule | Tint | Ink on tint | Ink on page | Rule on page |
| --- | --- | --- | --- | --- | --- | --- |
| needs-you | #FFA582 | #FF7A47 | #2A1710 | 8.92:1 | 9.54:1 | 7.08:1 |
| at-risk | #F0B95A | #E69F00 | #2A2110 | 8.91:1 | 10.27:1 | 8.12:1 |
| for-info | #7FC4F5 | #56B4E9 | #0F1E2A | 8.97:1 | 9.68:1 | 7.93:1 |
| settled | #5FD3AE | #3FBF97 | #0E2018 | 9.22:1 | 9.94:1 | 7.94:1 |
| idle | #A7AEB9 | #767B84 | n/a | n/a | 8.19:1 | 4.30:1 |
| body text | #E9ECF1 | n/a | n/a | n/a | 15.45:1 | n/a |

Mermaid node tokens: light node text #1A1D21 on #EFF1F4 measures 14.95:1 and
light node stroke #5B6470 on white measures 6.00:1; dark node text #E9ECF1 on
#1E242C measures 13.20:1 and dark node stroke #8A93A0 on the dark page measures
5.89:1.

Notes on this table, stated rather than buried:

- The tightest number in the set is the light settled rule at 3.07:1 against its
  own tint, which clears 1.4.11's 3:1 by 0.07. WCAG says computed values must
  not be rounded (FETCHED, section 3.1), so it clears, but it has no margin. Any
  future tweak to that tint must re-run the script. This is exactly why the
  script belongs in CI rather than in a designer's head.
- Hue anchors are the CUD ones: vermilion for the stop rung rather than pure
  red, because dark red reads as black to protanopes (FETCHED, section 3.3);
  bluish green rather than green; blue and sky blue separated by brightness.
- The rungs alternate warm and cool going down the ladder (vermilion, orange,
  blue, green), following the CUD advice to alternate warm and cool, with
  distinct brightness between the two warm neighbours.
- Colour is still never the carrier. Removing this entire table must leave every
  rung distinguishable by word, bar weight, bar style and glyph.

## 5.7 The insight box: one shape, six slots

The box has exactly six slots, in this order, and no slot is optional. If a slot
has no content the row is not an insight and the write is refused, which is the
existing ledger design's own refusal rule applied to the rendering.

    1  CLAIM        one sentence, the thing now believed
    2  BECAUSE      the evidence, with its class shown as a word:
                    EXECUTED / MEASURED / READ / REASONED
    3  INSTEAD OF   the alternative that was considered, and why not
    4  CHANGES IF   the flip condition, in plain language
    5  CONFIDENCE   high / moderate / low, followed by its basis
    6  YOUR MOVE    the handback line, always present, always last

Slots 1 to 5 are the ledger columns already designed (`claim`, `evidence` plus
`evidence_class`, `alternatives`, `flip_condition`, `confidence`). Slot 6 is the
`control_offered` column made visible. So the box is a direct rendering of one
row, which is L-V1 satisfied without any new storage.

Chat rendering:

    ┆FOR INFO   INSIGHT · calibration · 14:22

      The retry test was decorative. It passed with the retry logic deleted.
      BECAUSE      I deleted the retry branch in a scratch copy and ran the
                   suite: 0 of 61 tests went red.   [EXECUTED]
      INSTEAD OF   Leaving it and adding a second test. Rejected: two tests
                   that both pass on broken code are worse than one.
      CHANGES IF   A test fails against that mutation. Then the coverage is
                   real and this insight is wrong.
      CONFIDENCE   High, because it is a measurement and it repeats.
      YOUR MOVE    Hand this back to me: I take this decision and the work
                   under it, and BrotherMode records where it stopped and
                   what it would have done.

Artifact rendering: same six slots, same order, as a `<section>` with a heading,
a definition list, the evidence class as a bordered token (whose border must
clear 3:1, per 1.4.11), and the handback as a real control.

Three hard rules on the box:

1. **REASONED never renders as settled.** An insight whose evidence class is
   REASONED gets the muted ink, no rung bar, and the literal words "not tested"
   next to the class token. This is the existing law L19 given a visual form
   rather than a policy document.
2. **The box never carries a rung above FOR INFO on its own.** An insight is not
   an alert (section 2.7). If the same fact needs action, an alert is emitted
   separately and links to the insight; the insight is not promoted.
3. **Six slots or it is not a box.** A five slot rendering is a test failure,
   not a shorter box, because the missing slot is always CHANGES IF and that is
   the slot that makes the claim falsifiable.

## 5.8 Where each thing renders

| Element | Terminal chat | Artifact page |
| --- | --- | --- |
| D1 pipeline | ASCII stage line | mermaid |
| D2 gate ladder | count line only | mermaid |
| D3 lane map | one sentence: who holds the pen | mermaid |
| D4 decision fork | the question and lettered options as text | mermaid plus real controls |
| D5 counts | text bars | HTML bars with progressbar semantics |
| NEEDS YOU | yes, immediately | pinned top, `role="alert"` |
| AT RISK | in the briefing only | listed, `role="status"` |
| FOR INFO / SETTLED | count only | listed, SETTLED collapsed |
| Insight box | in the briefing, six slots | full, with handback control |

The half hour briefing designed in DESIGN-insight-ledger-and-handback.md is the
chat column of this table, already specified at six lines. This vocabulary does
not change it; it says what the six lines are allowed to look like.

## 5.9 Artifact construction rules

    - Single file. Inline CSS and JS only. No CDN, no fonts, no images. Assets,
      if any, as data URIs.
    - Mermaid via <pre class="mermaid">, theme 'base' plus explicit
      themeVariables from section 5.6. Never theme 'default' or 'dark', because
      neither is contrast tested by us. (FETCHED, section 3.6.)
    - Every diagram: accTitle plus accDescr, inside a <figure> with a
      <figcaption> carrying the same information in prose.
      (FETCHED, section 3.4.)
    - No click handlers inside mermaid source. securityLevel is strict by
      default and disables them. (FETCHED, section 1.1.) Interactivity lives in
      surrounding HTML.
    - Both themes via prefers-color-scheme plus a data-theme override on the
      root, so the viewer's toggle wins in both directions.
    - Wide content (diagrams, tables) scrolls inside its own overflow-x
      container. The page body never scrolls sideways.
    - The page states the row count and the generation timestamp it was built
      from, so a stale tab is visibly stale.

## 5.10 The acceptance tests that would make this real

A vocabulary with no test is a style guide, and style guides rot. None of these
exist yet. Each is mechanical and standard library only:

    T1  contrast          re-run the section 5.6 computation over the shipped
                          token table; any pair below its floor fails the suite.
                          Includes the sanity assertions (21.0 and 4.54) so a
                          broken formula cannot pass silently.
    T2  colour is never   for every generated view, strip all colour and assert
        alone             every status is still recoverable from text.
                          Mechanically: every status-bearing element must carry a
                          status word from the fixed lexicon.
    T3  diagram caps      parse every generated mermaid block, assert node and
                          edge counts against section 5.3.
    T4  diagram type      assert the first keyword of every generated mermaid
        allowlist         block is one of flowchart or stateDiagram-v2. Any
                          other type fails, which is how the ban is enforced.
    T5  accessibility     every generated mermaid block has accTitle and
        pair              accDescr; every figure has a non empty figcaption.
    T6  one alert         alerts_now() never returns more than one NEEDS YOU,
                          and never more than two rungs for a single chat
                          message.
    T7  six slots         every rendered insight box has all six slots non
                          empty; a REASONED row renders the words "not tested".
    T8  handback present  every rendered decision fork contains a handback
                          outcome (this test already exists in the ledger
                          design's plan; it extends to the drawn form).
    T9  generated only    grep the generated artifact for any string not
                          traceable to a row, the same docs-truth check the
                          handover pack already specifies.
    T10 mermaid escaping  node labels containing `end`, or ids starting with o
                          or x, are sanitised. (FETCHED, section 1.1.)

T4 is the load bearing one. Bans enforced by prose get broken in month three by
someone who has a really good reason for a pie chart.

---

# PART SIX: what is not verified, and what I did not do

- **Which mermaid version renders inside a Claude Code artifact, and therefore
  whether `swimlane-beta` and the newer beta diagram types parse.** UNVERIFIED. I
  could not observe rendered output from this session. The proposal routes around
  it by using only flowchart and stateDiagram-v2. Someone should run a one page
  probe with the founder watching and record the answer.
- **The eight Okabe-Ito hex values.** PARTIAL. The CUD page publishes the palette
  as an image; I read the design principles verbatim but not the numbers. My
  proposed tokens do not depend on the list, because every proposed value is
  measured.
- **Moody's Physics of Notations.** PARTIAL. Summaries only.
- **ANSI Z535 signal word definitions.** PARTIAL. Paid standard, vendor
  summaries only.
- **Screen reader announcement behaviour for emoji and for mermaid SVG output
  in practice.** UNVERIFIED. Mermaid's documented mapping to `<title>`, `<desc>`,
  `aria-labelledby`, `aria-describedby` and `aria-roledescription` is FETCHED,
  but I ran no assistive technology against a rendered diagram.
- **Alert fatigue quantification.** I have AHRQ's qualitative statement that the
  vast majority of warnings are overridden, FETCHED. I attempted The Joint
  Commission Sentinel Event Alert 50 (403 Forbidden) and a PubMed Central article
  that turned out to be an unrelated oncology paper. No specific percentage is
  claimed anywhere in this document.
- **docs.github.com was blocked to my primary fetcher** and its Alerts section
  was retrieved through a second scraper against the same live URL. The quoted
  text is verbatim from that retrieval, not from memory.
- **Nothing in Part Five is implemented, tested, or wired to the store.** The
  only executed thing in this document is the contrast computation.
- **Not researched, out of lens:** onboarding sequence design, the shape of the
  live project view, how the artifact gets delivered and refreshed, and the
  consent gate's own wording. Those belong to the other lenses.

---

# Appendix A: sources actually opened in this session

    https://mermaid.js.org/intro/
    https://mermaid.js.org/syntax/flowchart.html
    https://mermaid.js.org/syntax/stateDiagram.html
    https://mermaid.js.org/syntax/sankey.html
    https://mermaid.js.org/syntax/swimlanes.html
    https://mermaid.js.org/config/accessibility.html
    https://mermaid.js.org/config/theming.html
    https://mermaid.js.org/config/schema-docs/config.html
    https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
    https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html
    https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html
    https://www.w3.org/WAI/tutorials/images/complex/
    https://developer.mozilla.org/en-US/docs/MDN/Writing_guidelines/Howto/Markdown_in_MDN
    https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/alert_role
    https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/progressbar_role
    https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-color-scheme
    https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax
    https://docusaurus.io/docs/markdown-features/admonitions
    https://design-system.service.gov.uk/components/notification-banner/
    https://design-system.service.gov.uk/components/task-list/
    https://sre.google/sre-book/monitoring-distributed-systems/
    https://psnet.ahrq.gov/primer/alert-fatigue
    https://jfly.uni-koeln.de/color/
    https://www.nngroup.com/articles/ten-usability-heuristics/
    https://www.nngroup.com/articles/progressive-disclosure/
    https://github.com/Financial-Times/chart-doctor/tree/main/visual-vocabulary

Partial or summary only:

    https://blog.ansi.org/ansi/ansi-z535-4-2023-product-safety-sign-or-label/
    https://www.safetysign.com/safety-header
    https://www.semanticscholar.org/paper/The-%22physics%22-of-notations%3A-a-scientific-approach-Moody/73f214edc7e36c1c9aeca212ed828116a2db5522

Failed to open:

    https://www.jointcommission.org/.../sea_50_alarms_4_5_13_final1.pdf  (403)

Local files read:

    /Users/khalil.maaouni/Documents/BrotherModeUp/docs/program/absolute-lead/DESIGN-insight-ledger-and-handback.md
    /Users/khalil.maaouni/Documents/BrotherModeUp/tools/bm_docs_export.py  (inspected, not read in full)
