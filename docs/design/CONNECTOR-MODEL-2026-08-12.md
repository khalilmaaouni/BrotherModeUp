# The connector model and its release gate: design, not build

Status: CURRENT

Q3 of `docs/plan/REPLAN-2026-08-12.md`. The horizon says R2 is where "the
release stops being one repository," because connectors are separately
versioned surfaces with their own auth failure modes. This designs the model
and the per-connector gate. **Nothing here is implemented.**

---

## 1. The problem, from what was observed this session

1. **Roughly twenty connected services required authentication that could not
   be granted.** This session opened with a list of servers whose tools were
   unusable because the session was non-interactive and the sign-in flow needs
   a person. The capability was *listed as present* and was *not usable*. That
   gap is the whole problem in one line.
2. **Interactively-authenticated connectors are absent in unattended runs.**
   Stated in the harness's own documentation. So a workflow that works while
   the founder watches silently loses capability at 03:00, which is exactly
   when nobody is there to notice.
3. **A connector's version drifted three ways on one machine** and the copy on
   the PATH was two majors behind, surfacing as a missing command reported as
   a product defect.
4. **A scheduled task starts with no memory and no granted approvals.** Tonight
   one was armed, and the tooling itself warned that approvals granted during a
   run are stored on the task, so a first run may pause on prompts nobody is
   there to answer.

The pattern: **a connector's availability is not a property of the connector.
It is a property of the session, and nothing carries that distinction.** A
release process that only proves "the code is green" cannot see any of this.

## 2. Criteria

1. **Availability is reported per session kind**, not globally. "Works" must
   mean "works interactive" or "works unattended", never both by assumption.
2. **A degraded connector is a stated state, never silence.** Failure 2 is a
   silent downgrade.
3. **A connector's version is part of its identity**, so drift is detectable.
4. **The gate must be per connector.** One green tree cannot vouch for twenty
   independently versioned surfaces.
5. **A connector that cannot be exercised in a gate is reported as
   unexercised**, never as passing. This is the existing house rule that a
   check which cannot tell must never read as a pass.

## 3. Alternative A, REJECTED: one integration suite covering all connectors

Add connector tests to the existing battery.

**Why it is attractive:** one gate, one verdict, nothing new to run.

**Why it is rejected:** it fails criterion 4 and, worse, it makes the main
battery depend on credentials and third-party availability. The battery's
value comes from being deterministic and offline; tonight it ran twice and
both verdicts were trustworthy precisely because nothing external could move
under it. Coupling twenty auth surfaces to it would convert the project's one
reliable gate into a flaky one, and a flaky gate gets ignored, which costs
more than the connectors are worth.

**What would flip it:** if connectors could be faked completely. Then they are
not connectors, they are fixtures, and this is fine.

## 4. Alternative B, REJECTED: trust the connector's own health check

Each connector reports whether it is up; the release reads that.

**Why it is attractive:** near zero cost, and connectors often ship one.

**Why it is rejected:** it fails criteria 1 and 2 together, and failure 1
above is the proof. A server that answers "healthy" while its tools are
unusable because nobody signed in is *reporting truthfully about the wrong
thing*. Health is not availability. The distinction is exactly what this
model exists to record, so delegating it to the thing that cannot see it is
circular.

## 5. The design, RECOMMENDED: a connector record with a per-connector gate and an honest matrix

**Each connector gets a record** carrying: its name and version; what it
reaches; its authentication mode, which is the load-bearing field
(`none`, `token-from-env`, `interactive-only`); and its last exercised result
per session kind.

**The authentication mode decides unattended availability mechanically.**
`interactive-only` means unavailable unattended, always, by definition rather
than by discovery at 03:00. That single field turns failure 2 from a surprise
into a lookup.

**The gate is per connector and has exactly three outcomes**, mirroring the
vocabulary already used elsewhere here:

- `exercised`: a real call was made and returned what was expected. Names the
  call.
- `unexercised`: no call was made, and why. **This is not a failure and it is
  not a pass.** A connector needing a credential the gate does not hold is
  `unexercised`, and a release ships with that stated rather than hidden.
- `broken`: a call was made and failed. Blocks the connector, not the release.

**A connector does not block the product's release.** It blocks its own. This
is what "the release stops being one repository" means concretely: the main
tag ships on the main battery, and each connector carries its own verdict, so
one broken integration cannot hold the product hostage and cannot silently
ride along either.

**The output is a matrix, published with the release**: connector, version,
auth mode, interactive verdict, unattended verdict. Five columns. A person can
read it in ten seconds and see that twelve of twenty are `interactive-only`
and therefore absent from every overnight run. Nobody can read that today.

### Consequences

- **The honest matrix will look bad at first.** Most connectors will read
  `unexercised`, because most need credentials a gate should not hold. That is
  an accurate picture replacing no picture, and the temptation to make it look
  better by relaxing the vocabulary is the thing to refuse.
- **Someone must maintain records for connectors they did not write.** Version
  drift (failure 3) means these go stale, which is the same staleness problem
  the memory design addresses, and both should use the same sweep rather than
  two.
- **`unexercised` can hide rot indefinitely.** A connector never exercised is
  never known to be broken. Mitigation: the matrix counts how long since each
  was last exercised, so "never" is visible rather than blank.

### Flip condition

**If after a quarter the matrix is still almost entirely `unexercised`, the
per-connector gate is theatre** and the honest move is to publish the auth
matrix alone, drop the gate, and say plainly that connectors are unverified.

## 6. What needs the founder

1. **Do connectors ship in this repository at all, or as separate
   distributions?** The horizon says R2 is where one repository stops being
   enough, and this design assumes separate but does not decide it.
2. **Which credentials, if any, may a gate hold?** The strict answer is none,
   which makes almost everything `unexercised`. Any other answer puts secrets
   in a runner and needs its own decision.
3. **Is an `interactive-only` connector allowed in an unattended workflow at
   all**, or refused at declaration time?

## 7. Done-check

Complete when a reader can state the two rejected designs and why, the three
gate outcomes and that the middle one is neither pass nor fail, what would
flip the recommendation, and what needs a founder decision. All four present.
