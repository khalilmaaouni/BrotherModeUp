# L02 RED: the gap before the fix

Status: CURRENT as of 2026-08-05.

The claim to disprove was that BrotherMode already had a mechanical autonomy
contract. It did not: the Phase 2 design document described one and said in
its own words it was not implemented and that the loop consulting it was
later work (finding P0-01). The reproduction is the absence itself, shown two
ways on the pre-L02 tree at HEAD d7cf044:

    $ cd /Users/khalil.maaouni/Documents/BrotherModeUp && python3 -c "import tools.bm_autonomy" 2>&1 | tail -1
    ModuleNotFoundError: No module named 'tools.bm_autonomy'

    $ cd /Users/khalil.maaouni/Documents/BrotherModeUp && grep -c "autonomy_contract" tools/bm_store.py
    0

Writer B additionally ran its 56 new behavioral tests against the tree with
tools/bm_autonomy.py absent and recorded 56 failures and 2 errors, the honest
red state, before the module existed. The store-side tests were shown failing
the same way before schema 14 existed. Every fix below was shown failing for
the intended reason first.
