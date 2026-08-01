# The documentation rebuild: from 1/5 to useful

Status: CURRENT. Written 2026-08-01 after the founder rated the summary page
and the book 1 of 5 (summary "extremely weak", book "extremely complicated
and unpractical") and ordered a green-versus-red process with real research.
Five agents ran: three researchers (fetch-confirmed sources), two red-team
attackers. Their findings agree with each other and with the founder.

## Why the 1/5 happened, in one sentence

Every gate this project ran checked whether the artifacts were TRUE and no
gate checked whether they were USEFUL, so both artifacts became accurate
walls of prose organized around the product instead of the reader.

## The evidence, compressed (full returns in the session transcript)

Red team, summary: 4,942 words; install command at 90 percent page depth;
zero shown evidence (no capture, no diagram; "mechanical gate" asserted
three times, never shown firing); eight ideas restated 31 times across four
sections; the longest section is admitted fiction (personas); nine scattered
disclaimers that assemble into "never been used".

Red team, book: 21,551 words; the beginner's actual product (the seven
guided commands) first appears at chapter thirteen; 4,100 words before
first proven success; contents titled after internals, not tasks; glossary
mid-book; two early exercises broken as printed (ch2's HOME trick breaks
its own tilde path; ch3 uses relative tool paths that cannot resolve from
the reader's project directory).

Research (all fetch-confirmed, sources in the agents' returns): Diátaxis:
one document, one mode; mixing tutorial, reference, and explanation is the
central documented failure of documentation; tutorials carry no explanation
and show a result after every step. NN/g (two articles, eye-tracking): 79
percent scan, concise plus scannable improves usability 124 percent. Top
tool pages (tailwind, linear, shadcn, fetched): under 100 words before the
first concrete proof. For Dummies formula (Wikipedia plus live titles):
parts, skimmable modules, The Part of Tens, a standalone cheat sheet.
Cookbook format: problem, solution, discussion. Practitioner consensus: a
reader abandons a book for good at the first example that fails when run.

## The redesign

### A. The summary page (docs/brotherme-explained.html), rebuilt small

Target: under 1,500 words. Structure, in order:

1. Hero: a falsifiable claim no competitor page can make, roughly: a plugin
   for Claude Code that blocks two writers on one file and refuses the word
   done until a check runs after the last change and passes. Then the
   two-line install, immediately, above the fold.
2. PROOF BLOCK: one real captured transcript (provided in the build brief;
   actually run, not composed) showing the gate refusing an overlapping
   claim, with one line of caption. This is the page's only long evidence.
3. One dated STATUS box consolidating every honesty statement: what is
   verified, what is not, one place, confident register. Delete the nine
   scattered disclaimers.
4. How it works: the eight mechanisms ONCE, one line each, no restatement
   sections. Delete the personas section and the six-kinds section
   entirely; delete the ten-laws list from this page (it lives in the
   book); keep at most five bakery bubbles as a taste, linked to the book
   for the full story.
5. Get it, update it, go deeper: install recap line, /brotherme-update,
   link to the book and repository. End of page.

Register: NN/g scanner rules: front-load every paragraph, bold lead words,
no paragraph over three sentences.

### B. The book, inverted from product-tour to task-first

Same file, docs/book/brothermode-for-dummies.html. The material survives;
the organization inverts. New shape:

- CHEAT SHEET first (For Dummies formula): one screen: the two install
  lines, the seven commands with one line each, the three commands of
  parallel safety, where things live on disk. Anchor id "cheatsheet".
- PART ONE: DO (tutorial mode, Diátaxis rules: no explanation, a visible
  result after every step, time and expected output labeled on every
  exercise):
  1. Install and see it alive (ONE default path: the plugin; clone moves
     to a sidebar "if the plugin path fails"), ending with /brotherme-help
     answering. Under 300 words to first success.
  2. One real project, start to delivered, through the seven guided
     commands only.
  3. The two how-tos everyone needs: run parallel work without losing
     anything; get everything back after a crash.
- PART TWO: SOLVE (how-to recipes, cookbook shape problem/solution/
  discussion): recast from current chapters three, five, six, eight, nine,
  thirteen: correcting it, reviewing a decision, working with a team,
  handing over, the deep tour, updating.
- PART THREE: UNDERSTAND (explanation, behind an explicit divider stating
  no first-time reader needs to cross it): philosophy and ten laws, the
  five questions, the vault and Obsidian, the two composed walkthroughs
  (ch15, ch16), runtimes, when it goes wrong.
- PART FOUR: LOOK UP (reference): the seven commands in full, the tool
  commands, the glossary (moved to the actual end), the task index ("I
  want to..." mapping questions to anchors).
- Contents: task-shaped titles, sub-anchors, the parts visible.
- Fix as part of the move: ch2 HOME-trick exercise (use a variable that
  preserves the real home), ch3 relative paths (absolute $BM form),
  standardize every try-box (time, prerequisite, expected output), and the
  markup inconsistency in ch13/14 exercises.

### C. The gate this project was missing (process change)

A usefulness gate joins the truth gates for founder-facing documents: a red
reader (rushed user trying to DO something) runs BEFORE the founder sees
any documentation artifact. Candidate rule 6133983f captures this and
awaits founder approval. The drift tests gain: summary word count under
1,600 (mechanical proxy for the wall-of-prose regression), install command
within the first 120 lines of the summary body, book carries the cheat
sheet anchor and the task index.

## Done means

Summary under 1,500 words with install and real proof above the fold; book
inverted into the four parts with first success under 300 words; both pass
a FRESH red-team read (different agent, same hostile personas) at 3/5 or
better before the founder is asked to look; test_all green after the last
edit; pushed via Desktop; both artifacts republished at their same URLs.
