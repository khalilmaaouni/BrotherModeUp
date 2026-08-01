# Help artifact, update command, and explainer v2

Status: CURRENT (founder-ratified 2026-08-01: seven decisions through question
windows, design gate approved the same day; implemented the same day in the
rc.11 cut). Base: main at 8aa6dd1, the rc.10 release-cut commit.

## 1. What the founder asked for, in their words compressed

A simple way to update the skill. A detailed help artifact from
/brotherme-help: where each element stands, process diagrams, data model,
code review and reading capability, so developers can co-participate. The
explainer is not detailed enough: concrete examples, an end-to-end project,
loop advice, more exciting text, good-at and not-good-at stated, use cases
with tutorials. Plan on the strongest model, execute with a fleet.

## 2. Ratified decisions

1. Explainer audience: non-technical founder first; developer section later
   in the page, never first.
2. Anchor example: a small-business website, idea to delivered, plus three
   short sketches of other uses inside the use-case cards.
3. Format: conversation replay (chat bubbles: what you type, what BrotherME
   answers) with a clickable stage stepper (Idea, Brief, Build, Check,
   Deliver). One honesty label: an illustration with real command shapes,
   not a recording.
4. Tone: energetic and honest. Excitement from specifics, never adjectives.
   The not-good-at list gets equal design weight to the good-at list.
5. Help deep tour: reuse tools/bm_docs.py. No new renderer tool.
6. Update path: a seventh command, /brotherme-update, plus docs in the same
   change.
7. Explainer home: replace docs/brotherme-explained.html in place; the
   published artifact updates at the same URL.

## 3. Part A: explainer v2 (docs/brotherme-explained.html)

Page order, replacing the current page's middle while keeping its design
system (palette, Georgia display, token-based themes, no em or en dashes):

1. Hero: current thesis, sharpened.
2. Watch a real project happen: the website walkthrough as a conversation
   replay. Stage stepper with five stages; clicking a stage scrolls to that
   part of the story. Bubbles alternate: the founder types plain words,
   BrotherME answers in its real register (outcome first, one recommended
   action, ranges with confidence). The Build stage shows the guided loop in
   action: a helper builds, a separate checker refutes, one check fails, the
   fix happens, the re-run passes. Labeled illustration, command shapes real.
3. Using the loops well: three practical advices (let the cheap helper do
   the labor and judge by the check, not the prose; escalate after two
   failed checks, the system does it for you; your job is decisions, its
   job is proof).
4. Good at / Not good at: two equal columns, concrete entries only. Not
   good at includes: judgments of pure taste, work with no possible check,
   anything requiring your accounts or credentials (it will hand those
   moments back to you), and week-long unattended runs (unproven; the
   honest state is in NOT-FINALIZED).
5. Use cases, six cards, each a mini tutorial (what you type first, what it
   asks, what delivered looks like): website, research report, data
   cleanup, app prototype, content and translations, ops automation.
6. Install and update together: the two install lines, then updating
   (/brotherme-update, or the two lines it wraps), then uninstall.
7. The six (now seven) commands; honest limits panel (kept, updated); links.

Interactivity: vanilla JS only, no external assets, stage stepper plus
collapsible tutorial cards, both themes, reduced-motion respected.

## 4. Part B: the deep tour behind /brotherme-help

commands/brotherme-help.md keeps its plain-words help as the default and
gains: an offer of the deep tour as its one recommended next action when the
user wants more. On yes, the session runs `python3 tools/bm_docs.py
generate`, reads the generated Documentation/ folder, and builds ONE HTML
artifact: project state (where you are), process diagrams and data model
(mermaid fences, which artifacts render natively), decisions taken, code
map, and a co-build section for developers: the repo's own conventions
(mirror the sibling, explicit failure paths, tests beside code), where each
kind of code lives, and how to add an element cleanly.

skills/brotherme/SKILL.md gains the matching flow paragraph (the conductor
must name every flow a command enters; the rc.10 audit proved what happens
otherwise).

Honest limit, stated in the command and on the artifact: a project with no
BrotherME record gets the static product tour and says so plainly; the
live where-you-are view requires the project record the store keeps.

## 5. Part C: /brotherme-update

New commands/brotherme-update.md. The session, on this command: reads the
installed VERSION file; checks the newest release tag (git ls-remote --tags
on the public repository, network permitting; on failure says plainly it
could not check); then tells the user, in plain words, current version,
newest version, and the exact lines for their install path:

- Plugin install: `/plugin marketplace update brotherme-marketplace`, then
  `/plugin update brotherme`, then restart Claude Code. Both subcommands
  verified against `claude plugin --help` output on 2026-08-01.
- Pinned clone: `git fetch --tags` then `git checkout <newest tag>` inside
  the skill folder, per docs/RELEASE.md.

Docs in the same change: README gains an Updating paragraph beside the
install lines; docs/QUICKSTART.md Path 1 gains the update lines; the
explainer's install section shows the update ritual. Every live "six
guided commands" claim becomes seven (CHANGELOG history stays as written).

## 6. What this deliberately does not do

No auto-update, no version nag at session start, no new Python renderer,
no second explainer page, no fake typeable terminal, no recorded-session
claim anywhere.

## 7. Implementation plan (the plan the fleet executes)

Guided loop throughout: the orchestrator (strongest model) writes briefs and
judges; sonnet builders execute; the orchestrator re-runs every done-check
and holds all test files.

Fences (registered in STATE.md before dispatch):
- B1-explainer: docs/brotherme-explained.html ONLY. Input: the orchestrator
  writes the full walkthrough conversation and the good-at/not-good-at
  copy into the brief; B1 builds the page around it, keeping the existing
  design system. Done-check: page opens, zero em or en dashes, stepper
  jumps, both themes readable.
- B2-update: commands/brotherme-update.md (new), README.md,
  docs/QUICKSTART.md. Done-check: every named CLI line exists verbatim in
  `claude plugin --help` output or docs/RELEASE.md; grep finds no live
  "six guided commands" claim left.
- B3-helptour: commands/brotherme-help.md, skills/brotherme/SKILL.md.
  Done-check: every flow the command names exists as a conductor heading;
  `python3 tools/bm_docs.py generate` runs green in a scratch project.
- Orchestrator lands drift tests in tools/test_bm.py (command count, update
  command names the verified lines, help command's deep tour named by the
  conductor), reviews all three returns as a refuter, rebuilds the artifact
  from the final page, regenerates checksums, runs test_all, commits, and
  pushes through GitHub Desktop (founder gate G3dad1a78).

Wave order: B1, B2, B3 dispatch as ONE wave (disjoint fences, no suite
runs inside agents). Orchestrator work proceeds in parallel on the tests.

Estimate: 2 to 4 hours of session work. Confidence high on B2 and B3,
medium on B1 (walkthrough copy takes drafts).

## 8. Done means

python3 tools/test_all.py exits 0 after the last edit; the artifact URL
serves the new page; /brotherme-update exists with verified lines; the
deep tour is reachable from /brotherme-help; every claim on the page
survives the refute pass (each named command exists verbatim).

## 9. Amendment, 2026-08-01, second founder review (session 4cf1d535)

Ratified in-session through a question window after wave 8 closed at 54cb898.
The founder's ask, compressed: the page must show ambitious work, a big
project against the small one and why this product fits it; list the key
features that make it unique with practical use cases; personas for the
beginner and for the ambitious data engineer, backend engineer,
infrastructure engineer, solo founder and other relevant people, each taken
deep; and the features section permanently states what each does, how to use
it, and when to use it (already bound by the same-change rule and its drift
test, test_the_explainer_features_section_declares_its_update_rule).

Delivered as: the small-versus-big section rebuilt around two concrete
timelines plus the what-wakes-up contrast; an eighth mechanism card (risky
moments come back to you); seven personas (first-time founder, solo founder,
seasoned builder, data engineer, backend engineer, infrastructure engineer,
engineering lead). One wave, orchestrator as sole inline writer, no
builders. Done means: python3 tools/test_all.py exits 0 after the last edit,
zero em or en dashes on the page, artifact republished at the same URL.
