# L02 VERIFY: commands and output

Status: CURRENT as of 2026-08-05.

Every command below was run after the last edit of the loop, by the
orchestrator, not trusted from an implementer's paste.

    $ python3 tools/test_bm_store.py
    Ran 756 tests ... OK              (was 703; 53 new autonomy and migration tests)

    $ python3 tools/test_bm_autonomy.py
    Ran 58 tests ... OK              (56 behavioral plus 2 overflow-refusal)

    $ python3 tools/test_bm_schema.py
    Ran 20 tests ... OK

    $ python3 tools/test_bm_sentinel.py
    Ran 87 tests ... OK              (version pins rerooted to the constant)

    $ python3 tools/test_bm_docs.py
    Ran 199 tests ... OK             (schema-claim check now exempts verbatim quotations)

    $ python3 tools/test_bm.py TestPreWriteGate
    Ran 2 tests ... OK

    $ python3 tools/test_bm_store.py TestP17InstructionTextMatchesTheInstalledLayout
    Ran 8 tests ... OK

The full serial gate result and the verify-install PASSED line are recorded
in the commit that regenerates CHECKSUMS.sha256, run after this file lands.
