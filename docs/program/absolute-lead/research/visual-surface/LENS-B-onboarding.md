Status: RESEARCH. Lens B of the visual surface program. Fable, 2026-08-05.
Input to design, not a design. Nothing here is built.

# Lens B: Onboarding and progressive disclosure for complex tools used by non experts

## What this document is

The founder's complaint is that BrotherMode's onboarding and handholding are
weak, that documentation and support are not visual, and that the user should
be kept engaged, fully understanding what is happening, with the option to take
over development. This lens answers five questions with cited evidence, then
proposes what the first fifteen minutes should actually look like.

Every product claim below comes from a page I opened and read. URLs are inline
and listed again at the end. Where I could not verify something, it is marked
UNVERIFIED and I did not build on it.

---

## Part 1: The evidence

### 1.1 The founding constraint: a first run cannot teach by telling

The oldest and best replicated result in this area is the paradox of the active
user, from Carroll and Rosson at IBM in the 1980s: new users do not read the
manual, they start using the product immediately, and they accept getting stuck
rather than spending time up front on learning. They are motivated by their own
immediate task, not by understanding the system. The paradox is that they would
save time by learning first, and they still will not do it. Nielsen Norman
Group's conclusion is that we must design for how users actually behave rather
than for an idealised rational user.
(https://www.nngroup.com/articles/paradox-of-the-active-user/)

This is not only theory. NN/G ran a quantitative usability test with 70
participants across 4 iOS apps, split between subjects: 35 read the tutorial,
35 skipped it. Results:

- Task success: 91 percent for tutorial readers, 94 percent for skippers. Not
  statistically significant.
- Task time: 93.49 seconds for tutorial readers, 85.17 seconds for skippers. No
  significant difference.
- Perceived ease: 4.92 for tutorial readers versus 5.49 for skippers, and that
  difference WAS statistically significant, in the wrong direction. Reading the
  tutorial made the tasks feel harder.

NN/G's recommendation is that the effort spent building tutorials would be
better spent making the interface easy enough not to need one.
(https://www.nngroup.com/articles/mobile-tutorials/)

The companion article adds the mechanism: tutorials interrupt users who are
trying to do something else, information presented out of context is hard to
recall when it is needed, and users forget multistep instructions without
reinforcement.
(https://www.nngroup.com/articles/onboarding-tutorials/)

**Consequence for BrotherMode.** The current `/brotherme-help` command is a
wall of chat prose containing five numbered facts and a list of seven commands.
The evidence says that adding more explanation, or turning that prose into a
prettier HTML page, will not move the founder's problem. The wall being visual
does not stop it being a wall.

### 1.2 What does work: give the beginner fewer features, not more words

The training wheels interface is the counterweight, and it is the single most
useful result for BrotherMode. Carroll's studies restricted novices to a small
subset of features and compared them against novices given the full system.
NN/G reports the results as: 26 percent and 21 percent faster on task across
two studies, 69 percent and 21 percent more facts learned, and a 28 percent
higher satisfaction rating in the first study. The benefit survived the removal
of the restriction: users who had started restricted were 52 percent faster on
advanced tasks afterwards and had learned 10 percent more facts. The stated
mechanism is that restriction focuses attention and lets the user build a
better structured mental model.
(https://www.nngroup.com/articles/training-wheels-user-interface/)

Caveat, stated plainly: these are NN/G's summary figures for Carroll's studies
on text editors from the 1980s. I did not read the original papers. The
direction of the effect is well established; treat the exact percentages as
NN/G's reporting rather than as something I verified at source.

### 1.3 Progressive disclosure has a hard numeric ceiling

NN/G defines progressive disclosure as deferring advanced or rarely used
features to a secondary screen so the primary options carry the attention. Two
rules matter here:

- Designs going beyond two disclosure levels typically have low usability,
  because users get lost moving between levels. Three or more levels means the
  design should be simplified instead.
- Everything users frequently need must be disclosed up front. Progressive
  disclosure is not permission to hide the common case.

(https://www.nngroup.com/articles/progressive-disclosure/)

### 1.4 The empty state is the real first-run teacher

This is where a tool that starts from nothing does its teaching, and it is the
part BrotherMode has no design for at all.

NN/G gives three guidelines for empty states in complex applications:

1. Communicate system status, so the user can tell the difference between
   loading, an error, and genuinely no data.
2. Provide learning cues, explaining what would populate the space and how it
   gets there. Their worked example is Datadog telling the user to star
   favourites in order to list them there.
3. Provide a direct pathway to the key task, an actual button or link that
   populates the space, not a description of one.

They note empty states are common during onboarding and initial usage of
complex applications, and that a totally blank state creates confusion and
decreases user confidence.
(https://www.nngroup.com/articles/empty-state-interface-design/)

IBM Carbon gives the anatomy and the content rules. Five elements: optional
image, title, body, primary action, optional secondary call to action linking
to documentation. Three types: no data (first use), user action (search or
filter returned nothing), and error management (permissions, system problem,
configuration required). Content rules that bite here:

- Write the title as a positive statement. Their example is to say to start by
  adding data assets rather than telling the user they have none.
- Keep words to a minimum so they are fast to read and act on.
- Use plain language, and specifically do not use product-specific terms the
  user does not yet understand.
- Do not cover multiple options in one empty state. If there are several things
  the user could do, pick the most important one and keep the focus there.
- Do not lead the user into a dead end.
- For errors, do not joke or use flippant language.

(https://v10.carbondesignsystem.com/patterns/empty-states-pattern/ , the v10
legacy page, because the current Carbon page did not render for my fetcher)

Shopify Polaris scopes the component: the empty state component is for when a
full page is empty, not for individual elements, and buttons should lead with a
strong verb in a verb plus noun form so the merchant can anticipate what
happens.
(https://polaris-react.shopify.com/components/layout-and-structure/empty-state)

Polaris content fundamentals add the editorial rule: only add content necessary
for clarity, keep it lean, do not overwhelm people with too many choices or too
much information up front, and focus on the one thing the person needs to know
or do next.
(https://polaris-react.shopify.com/foundations/patterns/help-content , which is
the fundamentals page after a redirect from polaris.shopify.com)

Atlassian's definition is the shortest and the most useful as a test: an empty
state appears when there is no data to display and describes what the user can
do next.
(https://atlassian.design/components/empty-state)

**Consequence for BrotherMode.** Carbon's rule against covering multiple
options in one empty state is a direct indictment of the current help command,
which presents seven commands at once. The rule against product-specific terms
the user does not yet understand indicts words like fence, gate, dispatch, and
work record appearing before the founder has met the thing they name.

### 1.5 Tours: a narrow legitimate use and hard numeric limits

NN/G's position is that instructional overlays and coach marks are dramatically
overused, that they are usually nice to have rather than need to have, and that
they are genuinely justified mainly for a novel interaction paradigm the user
has never encountered anywhere else. Where used, they must be brief, optional,
and cover only the minimum needed. Deck of cards tutorials are not recommended.
Interactive walkthroughs, where the user learns by doing in a low stakes
environment, are the format they endorse for genuinely unfamiliar workflows.
(https://www.nngroup.com/articles/mobile-app-onboarding/)

Atlassian's design system turns this into enforceable numbers. From the
spotlight usage guidance:

- Only show one spotlight at a time.
- Offer a dismiss option at every step. Do not force people to participate.
- Ideally a spotlight has a single step. Aim for three to four steps maximum.
  People only need enough to get started.
- Keep message copy to two lines at the app's minimum supported size.
- Use the heading to communicate the benefit, not to name the function. Their
  example contrasts a benefit phrasing against naming the object.
- If the message talks about an element or a location, that element must be
  visible on screen at the same time. Do not talk about things the viewer
  cannot see.
- Avoid sending people to another location for more information. If it cannot
  be avoided, link to support documentation.
- Limit the pulse animation, which is disruptive for some users, and skip it
  entirely when the spotlight opens on page entry.
- Explicitly: do not use these change-management patterns for new users signing
  up, because you do not want to overwhelm someone with content about
  experiences they have not seen.

The same page describes an inflection point pattern that is more valuable to
BrotherMode than the tour itself: after recognising that a user has repeated
the same manual action several times, offer a spotlight suggesting the shortcut
that automates it. The trigger is observed behaviour, not a timer and not first
launch.
(https://atlassian.design/components/onboarding/usage)

Note on source status: that Atlassian package is marked deprecated in favour of
@atlaskit/spotlight. The usage guidance is still published and is the most
specific numeric guidance I found anywhere, but it sits on a deprecated
component's page.

### 1.6 The alternative to a tour: guided interaction

Krystal Higgins, who wrote the book Better Onboarding, names the pattern that
replaces tours. Guided interaction is situated learning: scaffolding provided
while the person engages with the real product, tapering off as they acclimate.
Her rules: facilitate exploration in an authentic space, engage gradually,
provide clear next steps, avoid modal dialogs (a user cannot learn in context
while a pop-up keeps them out of that context), do not educate about obvious
interactions, and always allow escape.
(https://www.kryshiggins.com/guided-interaction/)

Her separate piece on the active user paradox makes the strategic point: the
answer is not more guidance earlier, it is guidance made accessible throughout
the experience and fitted to the context of use, so it helps whichever path the
user takes.
(https://www.kryshiggins.com/active-user-paradox/)

### 1.7 Help at the point of need, not in a manual

NN/G's tenth heuristic splits help into proactive (before the problem) and
reactive (after it), and then splits proactive help again into push revelations
that arrive regardless of context and pull revelations that are contextual tips
relevant to the user's current task. Their rule is to favour pull over push,
make help accessible without forcing users into it, keep proactive help short,
make push revelations easy to dismiss, and make reactive documentation
comprehensive, scannable, categorised, and optimised for search.
(https://www.nngroup.com/articles/help-and-documentation/)

The sixth heuristic, recognition rather than recall, adds the rule that matters
for a chat product: offer help in context instead of giving users a long
tutorial to memorise, and keep the information required to use the design
visible or easily retrievable when needed.
(https://www.nngroup.com/articles/ten-usability-heuristics/)

Diátaxis is the primary source for how the documentation itself should be cut.
Four modes on two axes: tutorials (learning, practical), how-to guides (work,
practical), reference (work, theoretical), explanation (learning, theoretical).
Its tutorial rules are the ones that govern a first fifteen minutes:

- Show the learner where they are going before they start.
- The tutorial must work for every user, every time, because confidence is
  built layer by layer and easily shaken.
- Every step should produce a comprehensible result, however small.
- Minimise choice: stay focused on what is required to reach the conclusion and
  leave everything else for another time.
- On explanation inside a tutorial, Diátaxis is blunt: "A tutorial is not the
  place for explanation." (https://diataxis.fr/tutorials/)

(https://diataxis.fr/ and https://diataxis.fr/tutorials/)

### 1.8 The stuck moment, specifically in a terminal

BrotherMode lives in a terminal and a chat, so the relevant craft literature is
about command line tools, and it is unusually concrete.

Command Line Interface Guidelines (clig.dev) prescribes:

- Display concise help by default. When the program or subcommand requires
  arguments and is run with none, print short help rather than an error.
- That concise help should carry a description of what the program does, one or
  two example invocations, flag descriptions, and an instruction to pass --help
  for more. Full help only on -h or --help. This is exactly NN/G's two-level
  progressive disclosure, applied to a terminal.
- Lead with examples, because users reach for examples over other forms of
  documentation.
- Suggest commands the user should run next, because when several commands form
  a workflow, suggesting the next one teaches the workflow and surfaces
  functionality.
- If the user did something wrong and you can guess what they meant, suggest
  it.
- Catch errors and rewrite them for humans, as a conversation in which the
  program guides the user in the right direction.
- Confirm before doing anything dangerous.

(https://clig.dev/)

Evan Czaplicki's account of rebuilding Elm's compiler errors is the best worked
example of a terminal error that teaches. The techniques:

- Show the offending code exactly as the user wrote it, with its line numbers,
  so the user can pattern match rather than decode a file:line:column
  coordinate and mentally re-render pretty-printed code.
- Give every message a specific hint that names the actual cause in the user's
  terms, rather than restating what went wrong for the compiler.
- Use colour with two distinct jobs: one colour to draw attention to the
  problem, another purely as a separator so a single message can be read alone.
- Layer the message: general context above the code snippet, more specific
  hints below it, so a reader who only needs the headline can stop early. That
  is progressive disclosure inside a single error.
- Emit the same information as structured JSON behind a flag, so editors can
  consume it.

(https://elm-lang.org/news/compiler-errors-for-humans)

NN/G's ninth heuristic is the same rule in general form: plain language, no
error codes, precisely indicate the problem, and constructively suggest a
solution, ideally a shortcut that resolves it immediately.
(https://www.nngroup.com/articles/ten-usability-heuristics/)

### 1.9 First runs that are documented and that work

**Stripe.** The first API request page is built so that the first success
happens inside the documentation page itself. The Stripe Shell executes real
Stripe CLI commands directly on the docs site, operating only in a sandbox,
which is defined on that page as an isolated test environment for exercising
functionality without affecting a live integration, so no real money moves. The
first success is one command creating a customer, and the reward is the actual
JSON object printed back. The next section then sends the user to the logs and
events pages to see the object they just created recorded in two places. So the
sequence is: one command, one visible object, then proof that the system
recorded it.
(https://docs.stripe.com/get-started/api-request ; note the fetcher returned
the Japanese localisation of this page, so I read a localised render of the
same content, with the English code samples and sandbox definition intact)

**GitHub.** The Hello World tutorial states its prerequisites as negatives,
telling the reader they do not need to know how to code, use the command line,
or install Git. It runs five sequential steps, defines each term inline
immediately before the step that uses it (a repository is introduced as a
folder containing related items), and ends with something that exists: a
repository with a changed README merged through a pull request.
(https://docs.github.com/en/get-started/start-your-journey/hello-world)

**Linear.** The start guide puts learning before configuration and offers three
parallel entry ramps: an intro video, a demo workspace where issues, projects
and workflows can be seen already populated, and a live onboarding session. The
first thing the user creates is a workspace, and only after those optional
ramps. The demo workspace matters most here: it solves the empty-state problem
by letting a new user see a full system before owning one.
(https://linear.app/docs/start-guide)

**Notion.** Templates are positioned as the way to avoid the blank page,
described as adding structure and content quickly and illustrating what
problems can be solved in the product.
(https://www.notion.com/help/guides/start-with-a-template)
UNVERIFIED: search results claimed Notion pre-selects templates in the sidebar
based on answers given during signup. The help page I opened does not describe
the signup experience, so I am not relying on that claim.

**Superhuman.** The most relevant precedent, because BrotherMode's runtime is
itself a conversational agent and can do what Superhuman paid humans to do.
From First Round Review's account with Rahul Vohra:

- The session started at 90 minutes and was optimised down to 30.
- The first 30 minutes were originally discovery about the customer's pain and
  workflow. That discovery was later replaced by a pre-session survey plus two
  minutes at the top of the call. The learning: gather context before the
  session, not during it.
- The specialist drives the customer through named activation states: signed
  up, setup moment, aha moment, and potentially habit moment, inside roughly
  thirty minutes.
- Over 65 percent of new customers fully transitioned their email after the
  human-led onboarding. Activation was close to 2x self-serve, and referrals
  per customer doubled.
- Mandatory onboarding got 100 percent attendance; optional onboarding got 15
  percent.
- Their decision rule is a 2x2 on price point against product complexity. High
  price and high complexity means keep humans in the loop potentially forever.
- The stated philosophy is that it is better to onboard manually and keep
  building core functionality than to automate onboarding into an incomplete
  product.

(https://review.firstround.com/superhuman-onboarding-playbook/)
Source status: this is a well sourced secondary account based on the founder's
own description, not Superhuman's product documentation.

**Shopify.** The new-store checklist is a written document organised into eight
phases containing roughly fifty individual tasks, each linking out to a
detailed guide. Notably, the checklist page itself carries no progress
tracking; it suggests printing it.
(https://help.shopify.com/en/manual/intro-to-shopify/initial-setup/new-to-shopify-checklists/general-checklist)
This is a useful negative example: a fifty-item list with no state is a manual,
not an onboarding.

**Endowed progress.** Nunes and Drèze, Journal of Consumer Research, 2006. The
abstract, read at source: people given artificial advancement toward a goal
show greater persistence toward reaching it. Converting an eight-step task into
a ten-step task with two steps already complete reframes it as undertaken and
incomplete rather than not yet begun, which increases the likelihood of
completion and decreases completion time. The effect depends on perceptions of
task completion rather than on a desire to avoid wasting the endowment.
(https://papers.ssrn.com/sol3/papers.cfm?abstract_id=991962)
UNVERIFIED: the widely repeated car wash figures (34 percent versus 19 percent
redemption) appear only in secondary write-ups I did not treat as sources. The
abstract's qualitative claim is what I rely on.

---

## Part 2: Answers to the five questions

### How does a first run teach without a wall of text

It does not teach by telling at all. It teaches by three mechanisms, in this
order of strength:

1. **Restriction.** Offer the beginner a small subset and nothing else. This is
   the only intervention in this research with double-digit measured gains in
   both speed and knowledge, and with gains that persist after the restriction
   lifts (1.2).
2. **A visible result per step.** Diátaxis requires every step to produce a
   comprehensible result. Stripe compresses this to one command and one
   returned object. GitHub ends with a real merged pull request (1.7, 1.9).
3. **Designed empty states carrying learning cues.** The place where nothing
   exists yet is the highest-traffic teaching surface in a tool that starts
   from zero, and it teaches by showing the shape of what will be there (1.4).

### What belongs in an empty state

Per Carbon, NN/G and Polaris combined, five things and no more: a title written
as a positive statement, one short body explaining why the space is empty and
what fills it, exactly one primary action in verb plus noun form, an optional
secondary link to documentation, and an optional image. Plain language only, no
product-specific vocabulary the user has not met. One option, not several. Never
a dead end. And for a system that is working rather than empty, the empty state
must distinguish loading from error from genuinely no data (1.4).

### When is a tour right and when is it noise

Right: for a genuinely novel interaction paradigm the user has met nowhere
else, and when triggered by observed behaviour rather than by first launch.
Atlassian's inflection point (three repetitions of a manual action, then offer
the shortcut) is the defensible trigger.

Noise: at first launch, for anything the user could work out, and any time it
covers a feature set rather than one benefit. Hard limits where one is used:
one at a time, dismissible at every step, ideally one step and never more than
three or four, two lines of copy, headings that state a benefit rather than
naming a function, and never a reference to something not currently on screen
(1.5).

### How do the best tools handle the moment a user is stuck

They rewrite the failure into a conversation. The pattern that recurs across
clig.dev, Elm and NN/G heuristic 9 is identical in structure:

1. Show the actual thing, exactly as the user produced it, not a coordinate or
   a code.
2. Name the cause in one hint, in the user's terms, not the system's.
3. Offer one concrete next action, and if the intent is guessable, guess it out
   loud.
4. Layer it: headline above, detail below, full detail only on request.
5. Confirm before anything dangerous.

(1.8)

### How is help surfaced at the point of need rather than in a separate manual

Pull, not push (NN/G heuristic 10). Contextual tips fired by what the user is
doing now, always dismissible, never a modal that blocks the thing being
explained (Higgins). Concise help as the default response to an under-specified
command, with full help one flag away (clig.dev). And the manual that does
still exist gets cut along Diátaxis lines so that the tutorial does not try to
be the reference (1.6, 1.7, 1.8).

---

## Part 3: What BrotherMode's first fifteen minutes should be

### The reframe the evidence forces

The founder asked for more visuals and more handholding. The evidence says the
binding constraint is not visual richness, it is quantity of offered choice at
minute zero, and the location of help relative to the moment of need. A
beautifully rendered HTML page listing fourteen commands would fail for the
same measured reason the current prose fails.

Three assets BrotherMode already has, which most tools do not, and which change
what is possible:

- **The runtime is a conversational agent.** Superhuman's 2x activation came
  from a human sitting with the user for thirty minutes. BrotherMode can run
  that session itself, at zero marginal cost, which is the highest-leverage
  move available and requires no GUI at all.
- **The store is the source of truth and views are generated.** Every empty
  state, every learning cue and every progress count can be derived from rows,
  so it cannot drift into decoration.
- **The insight ledger design already specifies a briefing and a handback.**
  The handback is, in onboarding terms, Higgins's allow-escape rule and
  Atlassian's dismiss-at-every-step rule, promoted to a first-class product
  feature. That is exactly the founder's stated requirement about giving the
  user the hand.

### Minute by minute

Times are targets for a founder who has never used the tool, working from an
empty folder in Claude Code.

**Minute 0 to 1. The doorway. Zero writes.**

The founder types `/brotherme-start "<goal>"` or `/brotherme-help`. Whatever
they type, one artifact opens and one question is asked in chat. Nothing is
written to disk, because consent has not been given, and the artifact says so
in one line.

The artifact is the product's front empty state and obeys Carbon's anatomy
exactly: a title written as a positive statement about what is about to happen,
one short body, ONE primary action, one secondary link. It answers only the
three questions a founder actually has at minute zero: what will happen, what
it will cost me in time and money, and what I will have to decide. It contains
no command list.

What is deliberately absent: the seven-command list, the words fence, gate,
dispatch, work record, store, and any mention of KNOWN-LIMITS. Those are
reference material and belong in the reference surface, not the tutorial
(Diátaxis).

**Minute 1 to 4. The goal, in the founder's own words, one question at a time.**

The existing kickoff rule (ask only the questions whose answers change scope,
one decision at a time, recommended option first) is already aligned with
minimise-choice and needs no change. Two additions:

- After the goal sentence is captured, render it back in the artifact
  immediately, not as chat prose. That satisfies the Diátaxis rule that every
  step produces a comprehensible result, and it is the moment the founder first
  sees the artifact update in response to something they said.
- Gather the scoping context here, before the working session, exactly as
  Superhuman moved discovery into a pre-session survey.

**Minute 4. Consent, and the first write.**

The store is initialised. One plain sentence about what it did, as
`brotherme-start.md` already prescribes. Two design points:

- The founder never sees `bm_project.py start` refuse for a missing store. The
  current command file already handles this and it is the right call: a correct
  engine refusal is a wrong first minute. This is clig.dev's rewrite-for-humans
  rule already applied once in this codebase, and it should become the general
  pattern rather than a one-off.
- The moment the store exists, the founder's progress does not read zero. It
  reads two of eight, because the goal is recorded and the project is set up,
  and both are real rows. This is the honest form of endowed progress: the
  advancement is genuine, and the reframing effect (undertaken and incomplete
  rather than not yet begun) is obtained without inventing anything.

**Minute 4 to 9. One real unit of work, end to end, with a visible object.**

This is the Stripe move. Not a description of what BrotherMode will do: the
smallest genuine piece of the founder's actual project, run to completion, with
the resulting artifact shown. The founder should be able to point at something
that exists and say that came from the thing I said five minutes ago.

Training wheels applies here and is the highest-value single change in this
whole document. The repository currently ships fourteen commands (brief, start,
status, stop, handback, decisions, update, auto-status, auto, next,
handover-pack, review, deliver, help). During the first fifteen minutes, three
exist for the founder: start, status, next. The other eleven are not disabled
and not hidden behind a flag. They are simply not offered, and each surfaces at
the moment its trigger occurs (review when there is work to review, deliver
when there is something to deliver, handback at the first key decision,
handover-pack when a second human is mentioned). This is a content and
sequencing change, not an engineering one.

**Minute 9 to 13. The live view replaces the wall of text.**

The generated artifact, regenerated from rows on every status request, becomes
the thing the founder reads instead of chat prose. Two rules make it teach
rather than merely report:

- Every section with no rows yet renders as a designed empty state carrying its
  own learning cue and its own single next action. The founder learns the shape
  of the product by seeing the outline of what will fill it, which is NN/G's
  guideline 2 and Datadog's worked example. A section that renders blank is a
  defect.
- The process flow renders as a mermaid diagram with the current node marked
  and unreached nodes visibly dimmed. This satisfies Atlassian's rule that you
  never reference something the viewer cannot see, and it answers the founder's
  stated wish for process flows without adding a separate diagram to maintain.

**Minute 13 to 15. The first briefing, and the first handback offer.**

The insight ledger design specifies a six-line briefing every thirty minutes of
active work. For a first run that is too late by construction, because
Superhuman's entire activation window is thirty minutes. Recommendation: the
first briefing fires at the first phase boundary regardless of the clock, and
the thirty-minute active-work rule governs from the second briefing onward.

The handback line appears at the first key decision, with the stable wording
the design already fixes. Its onboarding function is to make the escape hatch
visible early, which is precisely what makes a non-engineer willing to keep
going.

### The stuck moment, in BrotherMode terms

Triggers detectable from the store and the session, with no daemon and no new
dependency:

- A mechanical command refused.
- The same command failing twice with the same error.
- A decision window open with no founder input for N minutes.
- A gate red.
- The same manual action taken three times (Atlassian's inflection point).

On any trigger, do not print a log. The founder cannot read logs and should
never have to. Emit the Elm-shaped block instead:

1. One line of context above: what was being attempted, in the founder's words.
2. The actual thing, shown as it happened.
3. One hint naming the cause in plain language.
4. One suggested next action, phrased as a command the founder can say.
5. A single expander, "show me exactly what happened", which reveals the raw
   output only on request. That is the pull-not-push rule, and it is the only
   place a log is ever allowed to appear.

### Cutting the documentation along Diátaxis lines

Today the tutorial, the how-to, the reference and the explanation are mixed
together in the help command and the README. The split:

- **Tutorial**: the first fifteen minutes above. One path, no alternatives, and
  it must work every time.
- **How-to**: what `/brotherme-next` answers, task by task.
- **Reference**: the generated live view and the handover pack. Generated from
  rows, never hand written.
- **Explanation**: the deep tour artifact. Opt in, never on the first run.

The current help command's honesty content (what is verified, what is not, the
data-export and purge promises) is reference and explanation. It is important
and it must stay reachable, but placing it at minute zero is the single clearest
violation of both Carbon's one-option rule and Diátaxis's rule about
explanation in tutorials.

---

## Part 4: Rules that could be gated

Written as testable propositions, in the style this repository already uses for
its laws, so a design can adopt them and a suite can enforce them.

1. Any generated view section with zero rows renders a designed empty state
   carrying a title, one body line, and exactly one action. A section that
   renders blank fails.
2. No empty state offers more than one primary action.
3. No first-run surface uses a term from the internal vocabulary (fence, gate,
   dispatch, work record, store, ledger, sentinel) before that term has been
   introduced by a step the founder just completed.
4. At most three commands are offered to a founder before the first unit of
   work completes. A fourth in any first-run surface fails.
5. No disclosure path in a generated view exceeds two levels.
6. Every founder-facing failure carries: the attempted action in plain
   language, the actual output, one hint, one suggested next action, and one
   opt-in expander for the raw detail. A raw log rendered without the expander
   fails.
7. No mechanical refusal reaches the founder unrewritten. Every refusal string
   the engine can emit has a founder-facing counterpart.
8. Any guidance overlay or callout is dismissible, and no sequence exceeds
   four steps.
9. No callout references an element or artefact not currently visible to the
   founder.
10. The first briefing fires at the first phase boundary, not on the
    thirty-minute clock.
11. Progress counters count real rows only. A counter that can display a number
    with no row behind it fails.
12. The first fifteen minutes runs to completion from an empty folder with no
    branch, no optional path, and no founder question outside the scripted ones
    (the Diátaxis works-every-time requirement, expressed as a behavioural
    fixture).

---

## Part 5: What would falsify this

- If a founder trial shows the restricted three-command first run leaves people
  unable to find review or deliver later, the training-wheels transfer effect
  did not hold here and the surfacing triggers need rework rather than the
  restriction.
- If the generated live view is opened once and never again, the artifact is
  decoration and the briefing in chat is the real surface, which would move
  effort from the artifact to the briefing renderer.
- If the handback offer is never taken across several runs, it is functioning
  as reassurance rather than as an escape hatch. That is still a legitimate
  outcome (Atlassian's dismiss rule exists to reassure), but it changes how much
  engineering the handback path deserves.

---

## Part 6: Sources opened and read

Nielsen Norman Group
- https://www.nngroup.com/articles/progressive-disclosure/
- https://www.nngroup.com/articles/onboarding-tutorials/
- https://www.nngroup.com/articles/mobile-tutorials/
- https://www.nngroup.com/articles/mobile-app-onboarding/
- https://www.nngroup.com/articles/help-and-documentation/
- https://www.nngroup.com/articles/ten-usability-heuristics/
- https://www.nngroup.com/articles/empty-state-interface-design/
- https://www.nngroup.com/articles/training-wheels-user-interface/
- https://www.nngroup.com/articles/paradox-of-the-active-user/

Design systems
- https://v10.carbondesignsystem.com/patterns/empty-states-pattern/
- https://atlassian.design/components/onboarding/usage
- https://atlassian.design/components/onboarding/examples
- https://atlassian.design/components/empty-state
- https://polaris-react.shopify.com/components/layout-and-structure/empty-state
- https://polaris-react.shopify.com/foundations/patterns/help-content

Product documentation
- https://docs.stripe.com/get-started/api-request
- https://docs.github.com/en/get-started/start-your-journey/hello-world
- https://linear.app/docs/start-guide
- https://www.notion.com/help/guides/start-with-a-template
- https://help.shopify.com/en/manual/intro-to-shopify/initial-setup/new-to-shopify-checklists/general-checklist
- https://docs.retool.com/education/coe/phases/onboarding/building-apps

Craft and research
- https://clig.dev/
- https://elm-lang.org/news/compiler-errors-for-humans
- https://diataxis.fr/ and https://diataxis.fr/tutorials/
- https://www.kryshiggins.com/guided-interaction/
- https://www.kryshiggins.com/active-user-paradox/
- https://review.firstround.com/superhuman-onboarding-playbook/
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=991962

Repository files read for grounding
- /Users/khalil.maaouni/Documents/BrotherModeUp/docs/program/absolute-lead/DESIGN-insight-ledger-and-handback.md
- /Users/khalil.maaouni/Documents/BrotherModeUp/commands/brotherme-start.md
- /Users/khalil.maaouni/Documents/BrotherModeUp/commands/brotherme-help.md
- the fourteen files in /Users/khalil.maaouni/Documents/BrotherModeUp/commands/

---

## Part 7: Disclosure, what is unverified or incomplete

- **Apple Human Interface Guidelines**: the onboarding and launching pages did
  not render for my fetcher. I have search snippets only, so I made no Apple
  claims. UNVERIFIED.
- **Figma**: I found no primary documented onboarding or first-run guidance and
  opened no Figma page. Nothing about Figma appears above. NOT RESEARCHED.
- **Retool**: I opened their Center of Excellence onboarding page. It does not
  prescribe a first app, a duration, or milestones, so there is no Retool
  onboarding pattern to report. Their documented sequence is only: set up a
  resource, then build. Reported as a gap, not as guidance.
- **Carbon**: I read the v10 legacy empty-states page because the current page
  did not render. Content may have changed in the current version.
- **Atlassian spotlight**: the guidance I quoted numbers from sits on a
  component page marked deprecated in favour of @atlaskit/spotlight. I did not
  verify whether the replacement component carries the same numeric limits.
- **Stripe**: the fetch returned the Japanese localisation of the first API
  request page. Code samples and the sandbox definition were intact in English
  inside it, but I read a localised render.
- **Training wheels percentages**: NN/G's summary of Carroll's original studies.
  I did not read the original papers.
- **Superhuman**: First Round Review is a secondary account, though based
  directly on the founder's own description. Not product documentation.
- **Endowed progress**: I read the SSRN abstract at source. The frequently
  cited car wash percentages come from secondary write-ups only and are
  UNVERIFIED, so the argument above rests on the abstract's qualitative claim.
- **Notion signup personalisation**: search-snippet only, excluded.
- **No user research on BrotherMode itself**: every recommendation in Part 3 is
  an application of external evidence to this product's mechanics. None of it
  has been tested on a real founder using BrotherMode. Part 5 lists what would
  falsify it.
- **Not covered by this lens**: visual and information design of the artifact
  itself, mermaid rendering behaviour inside Claude Code artifacts, the alerting
  and insight-box cadence beyond its first occurrence, and accessibility of the
  generated views. Those belong to other lenses.
