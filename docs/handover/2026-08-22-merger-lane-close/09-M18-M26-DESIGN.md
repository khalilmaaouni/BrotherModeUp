# M18 plus M26: one job, not two (design, written while the M22 gate ran)

## Why they are one job
M18's implementation ALREADY EXISTS in scripts/migrate_install.py as
`_schema_gap_message`, and its two tests pass. M26 is the finding that those
green tests do not cover the property they claim: they compare SOURCE
CONSTANTS, so they would stay green against an implementation that never
touches a real store. M26's done_check is explicit: "each test drives a real
store the wired copy genuinely cannot open, and fails when the code is changed
to compare source constants only."

A test cannot satisfy that against an implementation that only compares
constants. So M26 forces the implementation change M18 only half made, and the
two rows close together or neither does.

## The defect in the current implementation
`_schema_gap_message` reads this project's SCHEMA_VERSION, reads the wired
copy's SCHEMA_VERSION, and compares the two integers. That answers "does the
source say it is behind", not "can this copy reach a verdict against a real
store". The difference matters in both directions:
- a copy whose constant is behind but which can still open the store (schema
  compatible in practice) is reported as a gap that is not one;
- a copy whose constant matches but which cannot open the store for any other
  reason (a corrupt module, a missing dependency, an interpreter it cannot run
  under) is reported as fine.
M22 already removed the worst version of the first failure, where the constant
itself was not even the effective one.

## The shape that satisfies both rows
Replace the constant comparison with a REAL PROBE, and keep the constants only
for the wording of the message.

1. Cheap disqualifiers first, unchanged, all NO-DATA:
   - the wired store resolves to the same real path as this project's own
     (a copy cannot be compared against itself);
   - the wired copy has no tools/bm_store.py.
2. Build a throwaway project directory and let THIS PROJECT'S OWN current
   tools/bm_store.py init a real store in it. That store is at the current
   schema by construction, exactly the technique
   TestM17FenceLivenessAgainstRealStore._old_install_one_schema_behind and
   test_real_store_ahead_of_wired_hook_fails_not_passes already use in
   tools/test_bm.py, so this is reuse rather than a new pattern.
3. Invoke the WIRED copy's own bm_store.py against that real store as a
   subprocess (a read-only command, so nothing is mutated), with the
   environment pointed at the throwaway project.
4. Read the verdict from the probe, never from the constants:
   - exit 0: the wired copy CAN reach a verdict; return None.
   - non-zero with a schema refusal in its output: SCHEMA GAP, and the message
     names both version numbers, which is what the constants are still for.
   - non-zero for any other reason, or the subprocess could not be started at
     all: NO-DATA naming what happened, never a pass and never a block.
5. Clean up the throwaway directory in a finally block.

## Constraints this must respect
- Python 3.9, standard library only, which the probe satisfies (subprocess,
  tempfile).
- Use sys.executable, never a bare "python3": the M17 family already recorded
  a defect where the wired interpreter and sys.executable diverged, so which
  one is correct here has to be decided deliberately and stated in a comment
  rather than defaulted.
- Every boundary call gets an explicit failure path; a subprocess that cannot
  start is NO-DATA, not an exception.
- A dry run must not write anywhere except its own temporary directory. Assert
  that in the test the same way TestM1 asserts no .pyc lands beside the
  installed hook.

## The tests M26 demands
- Rewrite the two existing M18 tests so the fixture builds a REAL store the
  wired copy genuinely cannot open, rather than patching a literal and trusting
  the comparison.
- Add the mutation proof M26 asks for by name: a test that FAILS when the
  implementation is reduced to a source-constant comparison. The honest way to
  write that without shipping mutation machinery is a fixture whose constants
  AGREE while the real store is unopenable, so a constant comparison returns
  None (nothing to do) and only a real probe reports the gap.
- Keep the M22 tests untouched; they cover a different property.

## Order of work
M22 closes first: gate green, manifest last, push. Only then this lane opens,
because FINISH FIRST means one task per lane and the gate verdict binds to one
sha.
