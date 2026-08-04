# L02 REFUTATION: the independent security verdict

Status: CURRENT as of 2026-08-05.

An independent security refuter, given the diff and the shipped code but not
the implementers' reasoning, was told to disprove the claim that the
autonomy contract is safe to land. It ran 95 concrete exploit attempts
across eight attack angles against fresh temporary stores.

VERDICT: STANDS. No bypass found.

- Authorization bypass: revoked contracts refuse, paused contracts refuse a
  new unit while status still works, path traversal and absolute, symlink,
  Unicode NFC versus NFD, trailing slash and case folding all refused,
  floors smuggled through custom or misspelled risk classes refused.
- Immutability holds: no UPDATE path, the UNIQUE constraint makes two live
  contracts unrepresentable, revoke plus re-sign cannot resurrect revoked
  authority.
- Signer check catches the accidental case and is honest about its limits.
- Ceilings and spend correct: negative and non-numeric refused, missing
  ceilings are NO-DATA, thresholds compute correctly.
- Migration robust: rows survive, an interrupted migration refuses or
  recovers and never half-migrates, future and past schema get the right
  refusal, genuine corruption still says CORRUPT.
- Injection contained, purge complete with no orphans, every transition
  audited.

The strongest thing the refuter produced was a LOW, non-security overflow
nit (a spend or ceiling at or beyond the signed 64 bit maximum raised a raw
error instead of a clean refusal). It was fixed here before landing, with
two tests, and re-verified. The two design boundaries the refuter named
(gate-check answers rather than blocks, and the post-signing symlink TOCTOU)
are correct for U1 and are recorded as obligations on the L03 controller.
