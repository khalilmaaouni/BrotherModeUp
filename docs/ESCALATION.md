# Knowing when to stop and ask

Founder ask, 2026-08-15: the system should recognise when it is stuck and has
tried every method possible, then ask for help, ask for guidance, give a
recommendation, or hand over to a human.

The tool is `tools/bm_escalate.py`. This page is what it does, what it
refuses, what enforces it, and the one part that is not wired yet.

## Why it exists, given three things already existed

- `tools/bm_controller.py` escalates a unit that failed twice, and only inside
  a running Full-Auto controller. An ordinary interactive session has none of
  it.
- BrotherSBE's worker brief carries `maxAttemptsPerApproach: 2` as a sentence
  in a brief. This product's own first law says an instruction to a model is
  not a control.
- `tools/bm_stall.py` and BrotherSBE's stall detector watch dead workers,
  stale fences, disk floor and owed handovers. They detect a stuck MACHINE.
  Nothing detected a stuck LINE OF REASONING.

So the gap was one counter and one rule, which is all this file is.

## The six verbs

    python3 tools/bm_escalate.py attempt --objective "the import" \
        --approach "retry with backoff" --root-cause "the API returns 403" \
        --verdict failed [--evidence "..."] [--budget-attempts 4]

    python3 tools/bm_escalate.py forcing --objective "the migration" \
        --condition irreversible-and-ambiguous [--detail "..."]

    python3 tools/bm_escalate.py check   --objective "the import"
    python3 tools/bm_escalate.py packet  --objective "the import" \
        --owner "the BA" --recommendation "..." --risk "..." \
        --decision "..." --default "..."
    python3 tools/bm_escalate.py resolve --objective "the import" \
        --outcome answered|abandoned|handed-over --note "..."
    python3 tools/bm_escalate.py open

`attempt` prints the verdict after recording, so the ordinary loop needs one
command, not two. `check` and `open` are pure reads.

## The four triggers, any one is enough

| Trigger | Fires when | What it means |
|---|---|---|
| `forcing_condition` | a named condition is recorded, at zero attempts | guessing is the danger, so no number of tries changes the answer |
| `approaches_exhausted` | 3 or more DISTINCT approaches have failed | the objective has beaten the methods this session can name |
| `no_new_information` | 2 attempts failed with the same observed root cause | the second attempt bought nothing, which is the real signal |
| `budget_spent` | a declared attempt budget is spent with nothing passing | the work was sized and the size was wrong |

The forcing conditions are the ones BrotherSBE's L6 already carries as prose
and the 2026-08-15 architecture review listed as "escalate immediately": an
irreversible action with ambiguous intent, no owner, credentials unavailable,
authoritative sources in conflict, judgment that will not reduce to a rule,
the tool approving its own exception, and a waiver touching money, security,
privacy or customer-visible behaviour. An unlisted condition is accepted too,
because refusing to escalate a danger nobody enumerated is the wrong direction
to fail in.

Never on a single failure, with ONE exception: an attempt recorded with
`--truth-affecting` escalates on the first one. A wrong status, or a PASS with
a known counterexample, is a defect in what this product sells, and a second
attempt only means the wrong answer stands longer. The suite proves the flag
is what moves that verdict, by running the same failure without it and
requiring CONTINUE.

Silence has to mean healthy, so a passing attempt clears everything before it,
a `resolve` clears an open escalation, and a failure after a resolve re-opens
it. All three are covered by tests.

## What it refuses, which is the part that makes it worth having

- A failed attempt with no root cause is REFUSED at the door. A ledger of
  failures with no causes can never fire the repeat trigger, so accepting one
  would make the tool fail toward "keep going", the exact direction the
  founder asked it not to fail in.
- A packet with no recommendation, no decision, or no default action is
  REFUSED. Handing a person a problem with no proposal moves the work without
  reducing it, and an escalation with no default stalls the moment nobody
  answers.
- An unreadable ledger line is REPORTED, never silently skipped, for the same
  direction-of-failure reason.

## What it never does

It never answers the question, never retries anything, and never decides on
behalf of the human. Like the stall sweep beside it, it reports and a person
or the session acts. A monitor wired to a control is a control defect.

## The packet shape

The checkpoint shape both products already define, plus the two fields the
architecture review added because they change what the human does:

    who I am asking            <- new: an unaddressed question waits longest
    what I found
    my recommendation
    the alternatives I have not tried
    the risk if I guess        <- new: this is what decides how fast they answer
    the one decision I need
    what I do if you say nothing

In a Claude Code session the packet is delivered through the client's question
window (one decision, the recommended option first), and the written packet is
what survives the session.

## What is enforced, and the one thing that is not

ENFORCED by `tools/test_bm_escalate.py` (26 tests, green): every trigger fires
on its own and is asserted by NAME, the floor holds, clearing works in all
three directions, and both refusals hold end to end through the real command
line in a throwaway project.

NOT ENFORCED: that a session records its attempts at all, and that a session
holding an open escalation does not simply stop. The second one is closable by
a Stop hook, and this is the snippet, deliberately fail-open so a broken hook
never blocks a session:

    {
      "Stop": [
        {
          "hooks": [
            {
              "type": "command",
              "command": "python3 tools/bm_escalate.py open || true"
            }
          ]
        }
      ]
    }

It is not in `hooks/hooks.json` yet because that file belongs to another lane.
Until it is wired, this section is discipline and the tool is only its
instrument, which is this product's own rule about writing UNENFORCED where
it is true.

## Registration deltas, NOT applied

`tools/bm_escalate.py` and `tools/test_bm_escalate.py` were written while
another session held live work across seven files in this tree, so the shared
registries were left untouched rather than fought over. These are the exact
edits the next session applies, and none of them is optional:

1. `tools/write_sites.json`, `reviewed`: add `"tools/bm_escalate.py": 3`.
   The three sites are `os.makedirs`, `os.open` and `os.write`, all inside
   `append()`, which writes only the JSON record it was handed, at mode 0600.
2. `tools/bm_effects.py`, `REGISTRY`: add
   `"bm_escalate.py": {"attempt": LEDGER_WRITE, "resolve": LEDGER_WRITE,
   "check": PURE_READ, "packet": PURE_READ, "open": PURE_READ}` with the
   class names this file actually uses, confirmed by reading it first.
3. `pyproject.toml`, the module list: add `"bm_escalate"`.
4. `.github/workflows/tests.yml`: add
   `run: python3 tools/test_bm_escalate.py`.
5. `tools/test_all.py`, `SUITES`: add `"test_bm_escalate.py"`.
6. LAST, after `git add`: `sh scripts/checksums.sh CHECKSUMS.sha256`.

One finding to carry with them, found while checking site 1 and NOT caused by
this work: `tools/test_bm.py`'s write-site inventory is RED on this tree.
`scripts/install.py` has 17 write sites and 15 are reviewed. That belongs to
whoever is editing `scripts/install.py` right now, and the fix is a review of
the two new sites, not a number bump.

## The port

BrotherSBE takes the same tool under the existing porting rule (PARITY.md),
where it replaces the prose in the worker brief with the counter the parent
uses, so a worker and its orchestrator agree on what stuck means.
