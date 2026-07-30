#!/usr/bin/env python3
"""Run a test suite and republish its failures as GitHub Actions annotations.

WHY THIS EXISTS, 2026-07-31 (Loop 6). The Windows legs of the `store` job had
been failing on every run for days while the local gate was green, and nobody
could say WHICH test failed without downloading the run log. That download needs
an authenticated `gh`, and credentials here are founder-only, so in practice the
failure was undiagnosable by the machine that could have fixed it: a red CI with
an unreadable reason is barely better than no CI.

Annotations are the one failure channel a PUBLIC repository exposes without
authentication (`/repos/OWNER/REPO/commits/SHA/check-runs` returns them to an
anonymous caller). A `::error::` workflow command becomes such an annotation. So
this wrapper runs the suite unchanged, and on failure re-emits the unittest FAIL
and ERROR header lines as annotations. The next red Windows run names its own
failing tests to anyone with a browser and no login at all.

It changes NOTHING about pass/fail: the child's exit code is returned verbatim,
the child's output is streamed through untouched, and a green run emits nothing.
This is an observability wrapper, never a gate.

Deliberately not a shell pipeline: `tee` plus `${PIPESTATUS[0]}` behaves
differently under PowerShell, and this project has already shipped one red commit
because an exit code was read through a pipe. Python is the one interpreter every
leg of this matrix is guaranteed to have.

Usage, from the repository root:
    python .github/run_with_annotations.py tools/test_bm_store.py
"""
import re
import subprocess
import sys

# unittest prints "FAIL: test_name (module.Class)" / "ERROR: test_name (...)".
# Anchored at line start so a test whose own output mentions the word FAIL in
# prose cannot manufacture an annotation.
_FAILURE_LINE = re.compile(r"^(FAIL|ERROR): (\S+)\s*\((\S+)\)")


def main(argv):
    if len(argv) < 2:
        sys.stderr.write("usage: run_with_annotations.py <script> [args...]\n")
        return 2
    target = argv[1]
    proc = subprocess.run([sys.executable] + argv[1:],
                          capture_output=True, text=True)
    # Stream the child's own output through first and unchanged, so the log a
    # human reads is exactly what it would have been without this wrapper.
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)

    if proc.returncode == 0:
        return 0

    seen = []
    for line in (proc.stdout + "\n" + proc.stderr).splitlines():
        m = _FAILURE_LINE.match(line.strip())
        if m and m.group(0) not in seen:
            seen.append(m.group(0))

    if seen:
        # One annotation per failing test, capped: annotations are a summary
        # channel, and a suite failing in fifty places needs the first few plus
        # the count, not fifty lines nobody reads.
        for entry in seen[:10]:
            print("::error title=%s failed::%s" % (target, entry))
        if len(seen) > 10:
            print("::error title=%s failed::and %d more failing test(s); "
                  "download the run log for the full list"
                  % (target, len(seen) - 10))
    else:
        # Nonzero with no recognisable unittest failure header: a crash, an
        # import error, or a nonzero exit from something that is not unittest.
        # Say so rather than silently emitting nothing, because "red with no
        # annotation" is the exact state this wrapper exists to end.
        tail = (proc.stdout + proc.stderr).strip().splitlines()[-3:]
        print("::error title=%s failed::exit %d with no unittest FAIL/ERROR "
              "header. Last lines: %s"
              % (target, proc.returncode, " | ".join(tail)))
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv))
