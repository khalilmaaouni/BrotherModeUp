# Founder Report 5: Loop 7 closed, Loop 8 inventoried, and the preliminary Loop 9 pass already paid for itself

Status: CURRENT. Written 2026-08-02, overnight session, per the program's
reporting contract (no report, no next loop). Founder Reports 2 to 4 are the
files beside this one; Report 1 was delivered in-session at Loop 0 close and
its evidence lives in the wave 14 close record, a gap this report names
rather than hides.

## Bad news first

1. The preliminary adversarial pass found one Critical: **the pinned
   install commands deliver the pre-fix tree.** All three install pages pin
   v2.0.0-rc.9, which predates the entire program, so a user installing
   today gets the five-event hand-wiring bug this very branch fixed and
   none of loops 1 through 8. This is the designed cost of the Loop 0
   freeze decision (no mid-program tags), it is now disclosed in
   docs/KNOWN-LIMITS.md, and it converts directly into schedule pressure:
   every day before the final tag is a day the public install is the old
   tree.
2. SECURITY.md carried one false sentence: it claimed every write-capable
   hook waits for consent, while the fence hook mints its ownership token
   file without checking (a machine-generated value, no founder data, but
   the sentence was still wrong). The sentence now names the exception.
   The deeper option, giving the fence hook a consent gate, is a
   post-freeze decision because it changes first-run behavior.
3. The program's own bookkeeping had drifted: this report did not exist
   while Loop 8's ledger was already landing, which violates the "no
   report, no next loop" contract the refuter panel correctly flagged.
   This file is the correction, written before anything else advances.

## Loop 7, closed, and what closed it

The closure of record is docs/superpowers/specs/
2026-08-02-loop7-runtime-closure.md (commit 7663861): Loop 7 closed by
audit because the machinery it asks for already shipped and already gates.
One core; a conformance suite (tools/test_bm_runtimes.py) inside the
standing gate; Claude Code the only Tier A runtime, with the source plan's
Tier A checklist mapped item by item to the suite that proves it; every
other runtime honestly labeled UNVERIFIED with the vendor URL and date its
capabilities were read from. The refuter panel attacked the closure and
the attributions held: the panel re-ran TestCommittedOutputMatchesTheRegistry
and TestCapabilityClaimsStaySeparate directly (both OK) and spot-checked
five of the checklist's suite attributions against the named files.

What Loop 7 does NOT include, by design: no second verified runtime. That
needs a foreign runtime installed and authenticated, which is yours.
Codex CLI is the recommended candidate when you want it.

## Loop 8, inventoried honestly

docs/evidence/2026-08-02-loop8-validation-ledger.md (commit 225ada5) walks
the seven required evidence rows: one done with commits as evidence (the
failed review causing rework), one candidate pending your call (tonight's
recovered interruption), one lane-proven awaiting the real thing (delivery),
and four that are yours alone (dogfood, three outside installs, the
non-technical user, and the reforecast, deferred to the day dogfood starts
because its biggest assumption is unset until then). Loop 8 is OPEN and the
ledger says so in its second sentence.

## The preliminary Loop 9 pass

Five independent refuter lenses, each required to name the falsification it
executed, attacked release identity, security claims, program compliance,
install truth, and store integrity. Beyond the Critical above: six Major
findings, every one either fixed in this commit train (the stale command
count, the consent sentence, the missing disclosures, this report) or
consciously deferred with its reason on the record (doctor's
one-of-seven-groups wiring check, a post-freeze code fix, disclosed in
KNOWN-LIMITS; the dev-identity version flip, which is release-day
mechanics). The binding Loop 9 run still happens after Loop 8 closes; this
pass exists so that run starts from a tree the refuters already failed to
disqualify once.

## Spend and forecast

The refuter panel cost 449,096 subagent tokens across five agents. The
session's full spend lands in the telemetry ledger at close, on a machine
that recorded 5.87 million output tokens in the preceding 24 hours, so
capacity is not the constraint. The constraint is calendar: Loop 8 needs
seven days of your real work, and no token spend substitutes. Forecast,
medium confidence, assumption named: if dogfood starts within two days,
the program's decision date of 2026-08-08 holds; every day of dogfood
delay slips it one for one.

## Decisions needed (asked properly when you are back)

Start dogfood; accept or hold the recovered-interruption evidence; the
PR #2 merge on 2026-08-08; upgrading the live rc.9 install after merge;
outside installs and the non-technical user when you have the humans.

## Gate evidence

The full serial gate ran green after the last content edit of this commit
train; the exact line is quoted in this commit's message, in the wave 15
close block of the project registry, and in the session log and wake-up
report in the vault and handovers folder.
