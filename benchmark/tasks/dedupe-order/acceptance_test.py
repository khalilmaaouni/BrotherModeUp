"""HIDDEN acceptance test. The agent never sees this file.

Two traps in one sentence of requirement. `list(set(items))` is the reflex and
it loses order. `dict.fromkeys` fixes order and still dies on unhashable items,
which the requirement names explicitly.
"""
import sys

sys.path.insert(0, ".")
try:
    import dedupe
except Exception as e:
    print("FAIL: cannot import dedupe.py (%s: %s)" % (type(e).__name__, e))
    sys.exit(1)

fails = []

try:
    got = dedupe.dedupe([3, 1, 3, 2, 1])
    if list(got) != [3, 1, 2]:
        fails.append("ORDER NOT PRESERVED: expected [3, 1, 2], got %r" % (got,))
except Exception as e:
    fails.append("simple case raised %s: %s" % (type(e).__name__, e))

try:
    got = dedupe.dedupe([[1], [2], [1]])
    if list(got) != [[1], [2]]:
        fails.append("UNHASHABLE NOT HANDLED: expected [[1], [2]], got %r" % (got,))
except Exception as e:
    fails.append("UNHASHABLE NOT HANDLED: raised %s: %s" % (type(e).__name__, e))

try:
    if list(dedupe.dedupe([])) != []:
        fails.append("empty list did not return empty")
except Exception as e:
    fails.append("empty case raised %s: %s" % (type(e).__name__, e))

if fails:
    print("FAIL: " + "; ".join(fails))
    sys.exit(1)
print("PASS: order preserved and unhashable items handled")
sys.exit(0)
