Status: CURRENT. Written 2026-08-15.

# What worked, what failed, and what the difference was

Kept because the pattern is reusable and the failures are the useful half.

## What worked, and every one of these was a REFUSAL nobody had to remember

The value did not come from the products being clever. It came from them
saying no at moments when a person would have said yes.

- A WRITE WAS REFUSED ACROSS A LIVE CLAIM, by name, naming the session that
  held the file and the three ways to release it. The work became a patch on
  disk instead of a collision. (Correction that matters: on that machine the
  refusal came from BrotherSBE's hook, because BrotherMode's own is not
  registered. See document 11, finding M1.)
- A SECOND TEST RUN WAS REFUSED while another session's run held the lock,
  which is why two runs did not silently corrupt each other over one checkout.
- THE FULL BATTERY REFUSED TO REPORT GREEN on a tree that had been edited
  during the run. That refusal is the only reason a false failure was
  attributed to the measurement rather than to working code.
- THE CLOSE VERIFIER REFUSED THE SESSION THAT WROTE IT, correctly, because
  that session had dispatched seven agents without registering a claim in the
  store.
- THE COMMIT-TIME AND PUSH-TIME SCANS caught a forbidden attribution trailer
  in the oldest of 59 unpushed commits, in a public repository whose whole
  history had been rewritten to remove that exact string.
- THE DOCS SUITE caught the handover pack using a repository name where a
  product name belongs. Twice in one day, a control caught prose rather than
  code.

## What failed, and it was mostly judgement rather than tooling

- A FINDING WAS FILED FROM A SUMMARY AND NAMED THE WRONG FILE. The report said
  the delivery step certifies a project that did nothing. Reproducing it first
  showed the delivery step was correct and the hole was one file upstream, in
  task creation, where a task could be born past every gate it was meant to
  walk through. The fix is smaller because of the reproduction, and it would
  have been in the wrong place without it.
- A CLAIM WAS VERIFIED AGAINST THE WRONG COPY. "The north star now reaches
  every session" was proven by running the session-start script in the
  repository. Real sessions read an installed clone that did not have it.
  Verified, and about the wrong thing.
- A MEASUREMENT WAS TAKEN OVER A MOVING TREE, costing one full run.
- A WRITER LANE DUPLICATED WORK another session had already landed, for twenty
  minutes, because nothing checks whether the work already exists before a
  lane is dispatched.
- TWO DELIVERED CLAIMS WERE REFUTED by an adversarial pass: that shipping
  needed no push (the published tag carried the version string and neither of
  the two files it was supposed to carry), and that a new tool was sound (two
  real defects, found by executing attacks rather than by reading).

## The pattern, and it is the reusable part

BrotherMode makes it safe to run many things at once. BrotherSBE makes it
unsafe to believe any of them without proof.

The loop that follows: FAN OUT UNDER FENCES, THEN ATTACK WHAT COMES BACK.
Every serious finding came from that pairing. Every error came from doing the
first half and skipping the second.

Concretely, reviewers briefed to REFUTE rather than to confirm returned
`survives: false` on a design produced the same hour, and what they found
(nothing loads the product's own hooks; the closing gate certified an empty
project) was worth more than the design would have been.

## Three rules those failures earned

1. REPRODUCE BEFORE FIXING, even when a trusted reviewer names the file. A
   summary names a symptom; the reproduction names the cause.
2. NEVER MEASURE A TREE YOU ARE STILL EDITING, or one somebody else is
   editing. Commit, confirm clean, confirm HEAD has not moved, then run.
3. ASK THE CONTROL, DO NOT RE-DERIVE IT. A grep over the claim registry would
   have reported twenty live claims; asking the hook returned twenty refusals
   to enforce, the opposite conclusion, and became a filed finding.

## One measurement worth carrying

Of everything that protected this work, the parts that fired without being
remembered were mechanical: hooks, locks, scans, suites. The parts that failed
were the parts written as sentences. That is the products' own first law
holding up under its own use: a rule is not a control unless a file enforces
it.
