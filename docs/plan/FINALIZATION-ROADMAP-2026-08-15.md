Status: CURRENT.

# Finalization roadmap, 2026-08-15

One page: where BrotherMode stands against its real competitors, and the
shortest honest path to a version the founder can call finished. Written from
the 2026-08-15 research pass (three researchers, every claim cited to a page
actually opened) and the repository's own records. North star, unchanged: a
non-engineer founder runs multi-session AI work safely, sees progress without
asking, and no work is closed without a verifying command quoted after the
last edit.

## Where we stand

v3.3.0 was cut on 2026-08-15 on the founder's recorded decision, taken the
same day this page was written; it carries the Bitbucket lane and this
page, on an unchanged engine. The prior release: v3.2.1, whose tag was
re-checked this session and dereferences to 2002bc84 both locally and on
the remote. The full battery verdict recorded at that commit by the closing
session: 3136 tests across 35 suites, exit 0, doctor 11 of 11 (historical
record bound to 2002bc84, quoted from the 2026-08-12 close report, not re-run
here; this session runs its own gate before it pushes). Toolkit wave 1 landed
(TK1 inventory, TK5a receipts). Queue depth 29, TK2 on top. Zero recorded
installs outside this machine; the tester pack exists to change that and has
never been executed by an outsider. That last number is the honest headline:
the product is green, deep, and unproven in other hands.

## The fair comparison, orchestration layer against orchestration layer

The existing docs/ECOSYSTEM.md compares BrotherMode against coding agents
(Cursor, Copilot, Codex CLI, Cline, superpowers) and stays authoritative for
that set. This section covers the closer category it did not: multi-agent
orchestration and process layers. All numbers read live on 2026-08-15 from
the GitHub API or the project's own pages by this session's researchers;
each researcher's return names its URLs, and the session log carries them.

| Project | Scale (2026-08-15) | What it does well | Enforced file ownership | Session handover | Forecasts from history | Non-engineer progress view |
|---|---|---|---|---|---|---|
| Ruflo, ex claude-flow (ruvnet/ruflo) | 67,852 stars, v3.38.9, near daily releases | Swarm topologies, vector memory, 35 plugins, cost tracker plugin, multi-provider routing | Not documented | Memory persistence, no ceremony | No | No |
| superpowers (obra/superpowers) | 272,120 stars, v6.3.0 | TDD and review discipline as skills, 14+ agent runtimes, huge community | No, worktree isolation by convention | No | No | No |
| BMAD-METHOD (bmad-code-org) | 51,907 stars, v6.11.0 | Full lifecycle roles, durable context, non-technical people join planning via web bundles | No, human mediated | Context passing, not transactional | No | Participatory, not a status page |
| spec-kit (github/spec-kit) | 128,294 stars, v0.16.4 | Executable specs, whole-org roles, official GitHub backing | Not documented | Not documented | No | No |
| claude-task-master | 27,992 stars, last release 2026-03-31, stale | PRD to dependency-tracked tasks | No | No | No | No |
| claude-swarm (affaan-m) | 319 stars, dormant since 2026-02 | Hard dollar budget ceiling, per-file locks | Pessimistic locks, weaker than fences | Replay only | No | No |
| metaswarm (dsifry) | 392 stars, v0.12.0 | 9-phase TDD-gated workflow across 3 CLIs | Not documented | State survives compaction | No | No |
| BrotherMode | ~0 external installs | Transactional ownership store, hook-refused cross-fence writes, baton ceremony whose close half refuses hollow packs, forecast calibration that refuses to guess, founder progress pages | Yes, a hook refuses the write; its suite runs in CI | Yes, a ceremony with a refusing close check | Yes, NO-DATA below 3 usable pairs | Yes, delivered pages |

What the table says, fairly, in both directions:

- Nobody else ships what the last four columns describe. The ownership
  store, the write-refusing fence, the handover ceremony with a close check
  that refuses hollow packs, and forecast calibration that prints NO-DATA
  rather than a guess are unique in this category as of this research pass.
  That is the moat, and it is real.
- Everybody else beats us on reach and adoption. superpowers runs on 14+
  runtimes, metaswarm on 3, Ruflo ships plugins daily to 67k stars.
  BrotherMode's enforcement holds on Claude Code only, and its external
  install count is zero. A moat nobody has crossed into is
  indistinguishable from a product nobody has tried.
- Ruflo's own release notes admitted mislabeled internals (a search
  labeled HNSW that was brute force for an unspecified period) and config
  that was silently discarded; our evidence culture is the counter
  position and worth stating publicly.
- claude-task-master and affaan-m/claude-swarm are stale or dormant;
  treating them as active competitors would overstate the field.

## The roadmap, in order, each step with files and its done-check

Phase 0, housekeeping, this session. Commit the stranded board stamp a dead
session left (docs/plan/COMMAND-CENTER.html plus CHECKSUMS.sha256), land
this page, docs/BITBUCKET.md, bitbucket-pipelines.yml, the README pointer.
Done-check: full gate exit 0 after the last edit, quoted; tree clean;
pushed.

Phase 1, the Toolkit program to completion. Already ratified, 35 recorded
decisions, no re-litigation: TK2 conflict detection, then TK10, TK11, TK3,
TK4, TK6 in queue order (docs/plan/QUEUE.json is the machine truth; run
python3 tools/bm_idle.py next). Done-check per item already recorded in the
queue; program closes on TK6, the five-step pipeline on real cargo with one
evidence packet.

Phase 2, proof in other hands. The largest unmeasured number, named in the
tester pack itself: nobody has ever run the two-command install on a machine
that never had these products. Execute docs/team/TESTER-PACK.md with at
least one outside tester and one non-technical user; file the quoted
transcripts under docs/evidence/tester-pack/. Done-check: recorded install
count moves off zero with transcripts on disk. Founder-gated: recruiting the
testers is his call.

Phase 3, Bitbucket to proven. The code and docs land in Phase 0
(docs/BITBUCKET.md states exactly what was executed and what is labeled
UNVERIFIED). Founder creates the workspace and mirror and enables Pipelines,
one session then pushes the release, runs both install commands against the
mirror, and quotes one green Pipelines URL into docs/BITBUCKET.md.
Done-check: the UNVERIFIED labels on that page close with quoted output.

Phase 4, tell the market the truth. Extend docs/ECOSYSTEM.md with the
orchestration-layer section above through its own weekly-refresh procedure
(docs/ECOSYSTEM-REFRESH.md), so the comparison this roadmap carries becomes
the public page's seventh section rather than a private note. Done-check:
python3 tools/test_bm_docs.py green after the edit; the page's Last checked
line moves only through the documented pass.

Phase 5, the finalization cut. When phases 1 to 3 hold: cut the next minor
version, re-pin marketplace.json and every install command through the
documented release steps (docs/RELEASE.md), and update the one-pager.
Done-check: release-truth suite green, tag dereferences identically local
and remote, scripts/release-smoke-install.sh PASS.

## Founder decisions, answered 2026-08-15 through the question windows

1. Bitbucket workspace and mirror: the founder creates it now. The moment
   it exists, Phase 3's verification loop runs and the UNVERIFIED labels
   on docs/BITBUCKET.md close with quoted output.
2. Testers: the analyst lead and the engineering lead, from the founder's own team. The tester pack
   and install card are ready to hand them as they stand.
3. The cut: v3.3.0, cut 2026-08-15, the same day, per the standing Friday
   decision on the board. Phases 1 and 2 may run as the two parallel lanes
   the law allows.

## What this roadmap deliberately does not do

No new engine features outside the ratified Toolkit program. No multi-runtime
enforcement expansion (superpowers' 14 runtimes are its game; ours is depth
on one). No re-opening of released tags. Each of these is a recorded
decision with a flip condition: revisit multi-runtime only if an outside
tester asks for it in writing; revisit new features only when the queue
above TK6 is empty.
