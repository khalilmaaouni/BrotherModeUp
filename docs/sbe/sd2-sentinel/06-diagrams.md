# 06. Diagrams as code

One diagram, the evidence flow across the three layers of 02-process.md.
Every node traces to an entity in 05-data-model.md or a component below.

## Components
- AC: the allow-listed auto-clear, layer 3 of 02-process.md, producing one ClearanceReceipt per action.
- BD: the board strip on the command center, where every finding lands.
- CL: the Claim entity as the sweep reads it, carrying stall_threshold_seconds.
- GR: the gate receipt writer inside tools/test_all.py (RF-5, live at 943c59a).
- LJ: the SentinelJob's launchd runner, com.brothermode.sentinel.
- MN: the macOS notification channel for HIGH findings.
- PP: the phone push channel for CRITICAL findings.
- PR: the provisional records the sweep reads from the store.
- PT: the PostToolUse touch that refreshes a heartbeat at most once per minute.
- RC: the gate-receipt.json file the gate writes into the store's private directory.
- S1: signal 1, dead owner detection.
- S2: signal 2, in-flight stall detection.
- S3: signal 3, spend without progress detection.
- S4: signal 4, hung gate detection.
- S5: signal 5, dead provisional detection.
- SP: the spend ledger the machine spend guard maintains.
- SS: the SessionStart hook that writes the heartbeat.
- detector: layer 2 as one unit, the bm_stall sweep the SentinelJob runs each interval.

```mermaid
flowchart TD
    subgraph writers [Layer 1: evidence writers]
        SS[SessionStart hook] -->|writes| HB[Heartbeat]
        PT[PostToolUse touch] -->|refreshes| HB
        GR[Gate receipt writer] --> RC[gate-receipt.json]
        CL[Claim with stall_threshold_seconds]
    end
    subgraph detector [Layer 2: bm_stall sweep, pure read]
        HB --> S1[S1 dead owner]
        CL --> S2[S2 in-flight stall]
        SP[Spend ledger] --> S3[S3 spend without progress]
        RC --> S4[S4 hung gate]
        PR[Provisional records] --> S5[S5 dead provisional]
    end
    subgraph response [Layer 3: response]
        S1 --> F[Finding]
        S2 --> F
        S3 --> F
        S4 --> F
        S5 --> F
        F -->|always| BD[Board strip]
        F -->|high| MN[macOS notification]
        F -->|critical| PP[Phone push]
        F -->|dead owner or dead provisional, all signals dead| AC[Allow-listed auto-clear]
        AC --> CR[ClearanceReceipt]
    end
    LJ[SentinelJob, launchd 5 min] -->|runs| detector
    detector -->|missing job finding| F
```
