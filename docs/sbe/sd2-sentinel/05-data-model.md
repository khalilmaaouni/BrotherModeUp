# 05. Data model

## Conceptual: entities and meanings
- Session: one Claude session identified by its hook label; system of record: the fence token directory (.brothermode/fence).
- Heartbeat: the newest liveness evidence for one session (pid, timestamp); system of record: the store's private directory, hook-written.
- Claim: a fence over files held by a session, optionally carrying a stall threshold; system of record: the store (claims and records tables).
- Finding: one detected problem (kind, severity, evidence, clearing command); system of record: bm_stall sweep output, mirrored to the alerts table when raised.
- ClearanceReceipt: the record that an allow-listed auto-clear ran, naming its finding and the verbs executed; system of record: the store (attribution and state-change receipts).
- SentinelJob: the launchd LaunchAgent and its schedule; system of record: the plist under the user's LaunchAgents plus launchctl state.

## Relationships
- Session to Heartbeat: one-to-one, mandatory once SD2 lands. Every live session has exactly one current heartbeat; a session without one is judged only by store activity age.
- Session to Claim: one-to-many, optional. A session may hold many claims; every claim names exactly one owner session.
- Claim to Finding: one-to-many, optional. A claim may accumulate findings; every finding names exactly one subject record or claim.
- Finding to ClearanceReceipt: one-to-one, optional. Only a dead-owner or dead-provisional finding may gain a receipt, and a receipt names exactly one finding.
- SentinelJob to Finding: one-to-many, optional. The job produces findings each interval, including the finding that the job itself is missing.

## Attribute roles
| Attribute | Entity | Role |
|---|---|---|
| session_label | Session | identifier |
| pid | Heartbeat | descriptor |
| beat_at | Heartbeat | temporal |
| lifecycle_uuid | Claim | identifier |
| stall_threshold_seconds | Claim | measure |
| kind | Finding | status |
| severity | Finding | status |
| cleared_finding | ClearanceReceipt | foreign key |
| verbs_run | ClearanceReceipt | descriptor |
| interval_seconds | SentinelJob | measure |

## Physical notes
Heartbeat rows live as small files under the store's private gitignored
directory, never the tracked tree (the M20 law). The stall threshold is a
new nullable column on claims, guarded ADD COLUMN, defaults applied in
code so absent means default, never zero.
