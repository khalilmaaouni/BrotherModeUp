Status: CURRENT. Written 2026-08-17. These two contracts were produced by a
design pass on the strongest tier and were NOT implemented. They are written
here because they existed only in a session transcript and would otherwise be
lost. Every file and line reference was cited by the design pass from files it
had opened; line numbers may have moved since.

NAMING: both repositories are PUBLIC. Roles only. No client name, no company, no
reviewer's personal name appears here or in anything built from it.

# Lane A part 2: the two remaining honesty-seam contracts

Lane A had three items plus one precondition. Part 1 landed the precondition
(A0, an owner and an expiry on both exemption parsers) and A1 (a green summary
that names the classes it did not examine). A2 and A3 are NOT started.

Target repository for both: `/Users/khalil.maaouni/Documents/BrotherSBE`.

## A2, receipt provenance: a receipt records where it came from

WHAT THE ADOPTER TEAM RAISED: the gate inspects that a result is a whole number
and the duration positive, so a hand-written file claiming success passes as well
as a real one. Their operating rule is to trust evidence produced by the build
system, not by somebody's laptop.

WHAT ALREADY EXISTS, and this is the part that makes A2 cheap. The producer field
is half shipped. `src/brothersbe/evidence.py:724` already writes
`"ciRunId": os.environ.get("SBE_CI_RUN_ID") or None` into every wrapper receipt,
and `tools/sbe_passport.py:117` to `:133` already reads the three states:
truthy means the build system, key present but null means local, key absent means
the origin was never established. Do NOT introduce a new literal `"local"`
spelling; the key-present-null shape on disk already carries that meaning and a
new spelling would relabel every existing receipt.

THE CHANGE:
- `src/brothersbe/evidence.py`, beside line 724: add the missing url half,
  `"ciRunUrl": os.environ.get("SBE_CI_RUN_URL") or None`.
- `tools/sbe_gate.py`, function `gate_ran` (about line 1432): per readable
  receipt, classify the producer. Under the new flag, any receipt without a
  truthy `ciRunId` appends to `problems`, which the existing path at about
  `:1501` to `:1502` already turns into a FAIL. Two distinct messages, because
  they are different situations: "produced off the build system" when the key is
  present and null, and "producer not established: no ciRunId field" when the key
  is absent.
- THE FLAG IS A THIRD FLAG, `--strict-producer`, not a mode of `--strict`.
  Reason: `--strict-waivers` already set the pattern of one opt-in flag per
  refusal class (about `:1588` to `:1594`), and folding this into `--strict`
  would re-verdict every estate's existing green runs. Load-bearing wiring that
  is easy to miss: add it to the argument filter tuple at about `:1587`, or the
  unknown-flag refusal at about `:1619` to `:1626` exits 2. Carry it to
  `gate_ran` through a module global set once in `main()`, because gate functions
  receive only `root` (about `:1719`).
- DEFAULT IS OFF, per the ratified amendment that this product reports rather
  than blocks. With the flag absent, `gate_ran` appends producer accounting to
  its evidence sentence ("N of M receipt(s) record no build-system producer") and
  the exit code stays 0.
- AN OLD RECEIPT WITH NO FIELD is classified "not established". Under the flag it
  FAILs by name. By default it only adds a note, so no existing local run breaks.

DONE-CHECK, and note it deliberately uses a hand-written receipt, which is the
exact artifact the item exists to catch:

    cd $(mktemp -d) && echo '{"checks":[{"name":"x","exit_code":0,"duration_ms":5}]}' > ran-receipt.json \
      && python3 /Users/khalil.maaouni/Documents/BrotherSBE/tools/sbe_gate.py ran . --strict --strict-producer; echo exit=$?

Expect a FAIL line and exit=1. Run the same command WITHOUT `--strict-producer`
and expect exit=0, which proves the default reports rather than blocks.

TEST, failing first: `tools/test_sbe_receipt_shapes.py`, function
`test_strict_producer_refuses_a_receipt_with_no_ci_run_id`. It fails today
because the flag does not exist, so the run exits 2 on an unrecognized flag.

THE CEILING, and it must ship as a comment rather than be discovered later.
`SBE_CI_RUN_ID` is an environment variable any local shell can export, and
`src/brothersbe/evidence.py:516` to `:521` already states that the seal "proves
nothing about who produced it". So a `--strict-producer` green means THE RECEIPT
CLAIMS a build system, not that a build system produced it. A forged id plus url
passes strict exactly as easily as a real one. Write that down in the code.

## A3, owed checks: every check the plan promised must appear in the evidence

WHAT THE ADOPTER TEAM RAISED: evidence containing one check passes exactly as
green as evidence containing all of them. The forward direction landed on
2026-08-15 (a verification plan citing a behaviour id that no longer exists now
FAILs). The reverse direction, every owed check appearing in the evidence, does
not exist.

SIZE CORRECTION: the plan's table sized this T1. It is T2. The gate must begin
reading artifact 08's Proof column, which is new reading rather than an edit.

THE CHANGE: a new function `gate_proof` in `tools/sbe_gate.py`, plus a fifth
`GATES` entry, `"proof"`.

REUSE, exactly, and do not write a second parser: `from sbe_design import
_behaviour_rows`. The path is already primed at about `tools/sbe_gate.py:101`.
`_behaviour_rows` (about `tools/sbe_design.py:2765`) returns rows keyed by the
lower-cased columns of the table whose header is exactly
`ID | Starting point | Trigger | Required outcome | Proof`
(`templates/dossier/08-behaviour.md:21`).

Check names cited in a Proof cell are backticked tokens. Match them against the
union of check names across every ran-receipt under root, gathered by the
existing `find(root, RAN_RECEIPT, "ran")` plus `_items` and
`_run_receipt_as_checks` (about `:1406` to `:1429`), which already normalize both
a hand-written `name` and a wrapper `checkId`.

VERDICTS, matched to `check_behaviour` exactly rather than invented, because this
codebase already distinguishes all three cases and the new gate must not disagree
with the old one:
- table ABSENT: NO-DATA, "no 08-behaviour.md", matching about
  `tools/sbe_design.py:2813` to `:2814`.
- table UNREADABLE: FAIL, matching about `:2808` to `:2811`, whose comment says
  an artifact that exists and cannot be read is a broken claim rather than an
  absent one.
- Proof cell present but EMPTY: FAIL naming the row, matching about `:2844` to
  `:2850` and `:2880` to `:2881`.
- Proof that is PROSE naming no backticked check: REPORTED in the evidence
  sentence, never FAILed. This is not a softening, it is a correctness
  requirement: the shipped template's own Proof cells (`08-behaviour.md:23` to
  `:25`) are prose, so enforcing the premise as originally written fails every
  existing dossier on day one.
- No row naming any check at all: NO-DATA.

FAIL MESSAGE SHAPE, ids first and the cited check in parentheses, capped at 8 as
the sibling message at about `:2850` already caps:

    N behaviour row(s) cite a check no ran-receipt records: B1 (reconcile),
    B4 (settle-drill); a Proof naming a check nobody ran is a claim, not a proof

REGISTRY RULE THAT WILL BITE: `evals/test_no_data_class.py` discovers the `GATES`
registry, so the new entry must declare a `full_fixture` whose files carry BOTH
an 08 table citing a backticked check AND a ran-receipt recording it. Open the
file that reads the registry before adding to it.

DONE-CHECK:

    cd $(mktemp -d) && printf '| ID | Starting point | Trigger | Required outcome | Proof |\n|---|---|---|---|---|\n| B1 | a | b | c | run `reconcile` |\n' > 08-behaviour.md \
      && echo '{"checks":[{"name":"other","exit_code":0,"duration_ms":5}]}' > ran-receipt.json \
      && python3 /Users/khalil.maaouni/Documents/BrotherSBE/tools/sbe_gate.py proof . --strict; echo exit=$?

Expect a FAIL naming B1 and exit=1.

TEST, failing first: `tools/test_sbe.py`, function
`test_a_proof_citing_a_check_no_receipt_ran_fails_by_row_id`. It fails today
because the gate name "proof" does not exist.

THE CEILING, again to be written as a comment. Name matching proves NAMING, not
execution. A hand-written receipt entry
`{"name": "reconcile", "exit_code": 0, "duration_ms": 1}` satisfies every row
citing `reconcile` with nothing having run, and the union-across-root rule lets
one directory's receipt vouch for another directory's behaviour table. Worse for
adoption: because prose Proofs only report, a team that never adopts backticks
keeps this gate permanently inert while it prints PASS.

## Constraints both inherit

D2, ratified: a refusal in this product ships behind an estate switch and
defaults to reporting. Paved road, not forced road.

D4, ratified: no new refusal ships without an exception path carrying an OWNER
and an EXPIRY. That path is A0, which landed in part 1 as two keys on the
`.sbe-exempt` file, parsed by both mirrored parsers. A2 and A3 use it rather than
inventing anything.

## What part 1's adversarial review said about the exception path they will use

Read this before relying on A0, because it bounds what A2 and A3 can promise.
The reviewer executed the attack and confirmed: an author refused for an expired
exemption can DELETE both keys and go green, exit 0, with the waiver printing
"no owner recorded, no expiry recorded". That is the ratified grandfather design,
not a defect, but it means the mechanism is a voluntary annotation rather than an
expiry. `owner:` is an unverified string, not an identity. Three defects the
reviewer found in part 1 were sent back for fixing before merge: prose inside
`reason:` being mined into a granted exception, a date contract that Python 3.11
and later silently widen, and missing tests for the design parser's grandfather
path.

## Order

A2 before A3, because A3 leans on A2's receipt reading. Only two files are
touched across both, so at most two writers, and `tools/sbe_gate.py` is taken
SERIALLY by one writer, never split.
