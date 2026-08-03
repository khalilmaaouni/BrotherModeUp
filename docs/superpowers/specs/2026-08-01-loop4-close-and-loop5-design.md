# Loop 4 close-out and Loop 5 design

Status: CURRENT. Written 2026-08-01 by the orchestrator.

## Loop 4: task and delivery spine. GATE: lifecycle states travel only
## through the service layer. Verdict: MET BY CONSTRUCTION, evidence mapped.

The loop's substance landed inside Loops 1 and 2 rather than as its own
wave, which the program map permits (the source's atomic operations ARE
the schema-12 service methods). The gate maps to running tests:

- Ten states and legality live in one place, brotherme/core/schema.py
  transition(); the store's transition_task and review_task delegate to
  it (test: illegal transition refuses with schema's own text; the state
  named done refused by name; both in tools/test_bm_project.py and
  tools/test_bm_store.py).
- Every mutation is one transaction with its attribution row
  (TestLoop1Atomicity, eight forced-failure tests).
- Nothing reaches the tables around the service layer: bm_project.py
  carries no SQL (AST guard test, plus the sqlite3-import guard);
  bm_store.py is the single writer of store.sqlite3 (write-site
  inventory gate, tools/write_sites.json, enforced by
  test_no_unreviewed_write_sites); review is composite and atomic
  (review_task, orphan-evidence regression).
- Residual honesty: the store's OWN ownership tables (records, claims)
  predate the five shapes and stay governed by their own methods; no
  displayed surface mutates either raw.

Loop 4 closes with no new code. Anything that would have been Loop 4
work and is not covered above belongs to Loop 5's surface and is listed
there.

## Loop 5 design: forecasting, attribution, alerts, status from rows
## only. GATE: every displayed number traces to a row and its evidence.

D-1. bm_project.py gains: forecast add (wraps add_forecast; ranges plus
     confidence required, point estimates refused with the forecasting
     rule quoted), forecast show (latest per project plus history count),
     alert raise / alert resolve / alert list (wrap the existing service
     methods), and status grows two sections: the latest forecast
     (ranges and confidence, never a point) and unresolved alerts with
     severity. All reads through the accessors; no new SQL anywhere.
D-2. Attribution summary: status --history N prints the last N
     attribution events (event_type, actor, timestamp) from
     list_attribution. Deliver's packet already includes the summary.
D-3. The gate test, by construction: a test drives a full project, then
     parses every number out of status, next, forecast show, and the
     delivery packet, and asserts each one equals a value derivable from
     rows fetched via the accessors in the same test (counts, ranges,
     token figures). A displayed number with no row behind it fails the
     build.
D-4. Reforecast law (source doc): forecasts append, never edit; already
     enforced (test_add_forecast_never_edits_a_prior_forecast_row).
     forecast add records next_reforecast_event; status prints it so the
     founder sees when the number is due to move.

Work package: ONE builder (files: tools/bm_project.py,
tools/test_bm_project.py, and command file commands/brotherme-status.md
only if its wording must name the new sections), then the standard
refute pass folded into the Loop 3 refuter wave to save a round trip:
the Loop 3 refuters run after Loop 5's builder lands, covering both
loops' surfaces in one wave.

## Out of scope

Alert generation policy (what raises alerts automatically) is Loop 6
adjacent security work and the pulse reference's judgment call; Loop 5
ships the mechanical rails only.
