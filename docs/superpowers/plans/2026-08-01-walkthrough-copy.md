# Walkthrough conversation copy (orchestrator-authored, for B1 brief)

Status: CURRENT (source copy for the walkthrough shipped in
docs/brotherme-explained.html; supersede this file only by editing the page
and this file together)

Honesty label to render above the replay, verbatim:
"This conversation is an illustration. The command shapes, the questions,
the checks, and the register are real; these exact bubbles were composed
for this page, not recorded from a session."

## Stage 1: Idea

YOU: /brotherme-start
YOU: I run a small bakery. I want a website: our story, photos, opening
hours, and a way for people to order birthday cakes ahead of time.

BROTHERME: A bakery site with a story page, photos, hours, and cake
pre-orders is a clear goal, and the pre-orders part is the one decision
that changes everything else. Question one of three: when someone orders a
cake, what should actually happen? A) You get an email with the details
(recommended: simplest, works day one), B) They pick a pickup slot in a
calendar, C) They pay online now. B and C are real features I can build
toward, but both add moving parts and days of work. Which fits how you
actually take orders today?

YOU: Email is fine honestly. We confirm by phone anyway.

BROTHERME: Email it is, and that keeps the whole build in the simple lane.
Question two: do you already have photos and your story text, or is
writing and choosing part of my job?

YOU: I have photos on my phone. No text written.

BROTHERME: Then I draft the story and you approve it; photos come from you
when we get there, and the site launches with placeholders if yours are
late. Last question: any deadline?

YOU: My niece's wedding expo is in three weeks.

## Stage 2: Brief

BROTHERME: Here is the one-page brief I will build against. The outcome: a
bakery website with four pages (home, our story, gallery, cake orders),
where a cake order form sends you an email. Included: mobile-friendly,
your colors once you share a photo of the shop, hours on every page.
Excluded, on purpose: online payment, pickup calendars, user accounts.
Success check: the site loads, every link works, and a test order lands in
your inbox. Risks: photos arriving late (site launches with placeholders),
and the three-week deadline, which this plan is scoped to fit.
Forecast: 4 to 7 working sessions. That is a range, not a promise, and
email delivery is the assumption most likely to move it. Shall I start?

YOU: Yes. Go.

## Stage 3: Build

BROTHERME: The four pages are underway. A fast helper is laying them out
from the approved brief while I hold the plan and check everything
it produces. You decide nothing until something needs your taste.

BROTHERME: First decision for you, with my recommendation: two looks for
the home page, warm cream with your bread photos leading (recommended,
matches the shop photo you sent), or a cleaner white gallery look. Both
open in the preview. One click and I continue.

YOU: The warm one.

BROTHERME: Warm it is. The story draft is on the story page in the
preview; mark anything that does not sound like you and I rewrite it.

## Stage 4: Check

BROTHERME: Bad news first: one check failed. The order form sent its test
email and the pages load on a phone, but the checker found the gallery's
third photo links to nothing when tapped. It was caught by a helper whose
whole job is to try to break what was built. Fixing now; the fix re-runs
the same check.

BROTHERME: The re-run passed. Every link works, the phone layout was
checked at several widths, and the order form's test message was confirmed
delivered. Nothing else failed.

## Stage 5: Deliver

BROTHERME: Delivered, with proof attached. The site is built and checked,
and the last step is yours: publishing needs your hosting login, so the
exact steps are ready and you press the button. The delivery packet lists
what was built, every check that ran
after the last change, the one defect found and its fix, and what I left
out on purpose (payments, calendars) with what adding each later would
take. One recommended next step: send yourself a real cake order from your
phone, today, so the first real order in your inbox is one you sent.

## Post-replay caption

Every stage above is a real command or a real gate in the product: the
questions come from the kickoff flow, the brief is the Project Canvas, the
build ran the guided loop (a cheap helper built, a separate checker tried
to break it, the failure escalated a fix), and delivery required a check
that ran after the last change. The project, the checks and their results
are composed for this page. What is real is the commands, the gates and
the shape of the questions.

# Good at / Not good at copy (verbatim for B1)

GOOD AT
- Turning a plain-words idea into a checked, delivered result
- Scoped building: websites, reports, data cleanups, prototypes
- Catching its own failures: separate checkers try to break the work
- Surviving crashes: progress and decisions live on disk, not in memory
- Saying no: it is built to refuse calling unproven work done, with that
  refusal enforced on Claude Code only

NOT GOOD AT
- Pure taste calls: it recommends, but your eye decides
- Work with no possible check: if nothing can prove it, it says so
- Anything needing your accounts: payments, sign-ins, publishing
  credentials stay with you, and it hands those moments back
- Real work of any length: every result so far comes from test suites and
  simulated projects, not from a day of anyone's actual work. You may be
  the first.
- Unattended runs: nobody has left it working alone for long, and it is
  not claimed to survive that
- Being fast on tiny tasks: the checking adds minutes; for a one-line
  answer, ask plain Claude
