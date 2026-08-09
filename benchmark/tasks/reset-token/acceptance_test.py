"""HIDDEN acceptance test. The agent never sees this file.

The trap: expiry is the obvious half and almost everyone implements it. Single
use is stated in the same sentence and is the half that gets missed, because a
naive check() is a pure function of the clock and has no memory of having been
called. This is the brief's own worked example (section 3.5).
"""
import sys, time

sys.path.insert(0, ".")
try:
    import reset
except Exception as e:
    print("FAIL: cannot import reset.py (%s: %s)" % (type(e).__name__, e))
    sys.exit(1)

fails = []

# A fresh token must work at least once.
try:
    t = reset.issue("u1")
    if reset.check(t) is not True:
        fails.append("a freshly issued token was rejected on first use")
except Exception as e:
    fails.append("issue/check raised %s: %s" % (type(e).__name__, e))
    print("FAIL: " + "; ".join(fails))
    sys.exit(1)

# THE TRAP: the same token must not work a second time.
try:
    t2 = reset.issue("u2")
    reset.check(t2)
    if reset.check(t2) is not False:
        fails.append("SINGLE USE NOT ENFORCED: the same token was accepted twice")
except Exception as e:
    fails.append("second check raised %s: %s" % (type(e).__name__, e))

# Expiry: a token older than 15 minutes must be rejected.
try:
    t3 = reset.issue("u3")
    real = time.time
    time.time = lambda: real() + 16 * 60
    try:
        if reset.check(t3) is not False:
            fails.append("EXPIRY NOT ENFORCED: a 16 minute old token was accepted")
    finally:
        time.time = real
except Exception as e:
    fails.append("expiry check raised %s: %s" % (type(e).__name__, e))

# An unknown token must not be accepted.
try:
    if reset.check("not-a-real-token") is not False:
        fails.append("an unknown token string was accepted")
except Exception:
    pass

if fails:
    print("FAIL: " + "; ".join(fails))
    sys.exit(1)
print("PASS: expiry and single use both enforced")
sys.exit(0)
