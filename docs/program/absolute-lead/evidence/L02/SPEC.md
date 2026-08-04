# L02 SPEC pointer

Status: CURRENT as of 2026-08-05.

The decision-complete specification for this loop was authored by an
independent architect against the real store schema before any code was
written: six tables with exact CREATE statements, the schema 13 to 14 bump
following the house migration pattern, the fourteen commands with exit codes
and refusal texts, the sixteen invariants each mapped to an enforcing site
and a test name, the adversarial test list, the U1 to U2 boundary, and two
rejected alternatives with flip conditions (a contract as a JSON file in
.brothermode, and a separate autonomy database, both rejected for breaking
the single-store law). The full specification and the seven implementation
deltas that refined it are retained with this program's working records. The
one load-bearing design call: immutability is a revision chain with
UNIQUE(project_id, revision), insert only, which makes two live contracts
unrepresentable rather than merely constrained.
