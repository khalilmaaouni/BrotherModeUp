# Generated Artifacts

BrotherMode creates human-readable files from project records. These files are outputs, not the authoritative store of project truth.

## Artifact Table

| Artifact | Created by | Purpose | Authority |
| --- | --- | --- | --- |
| `CANVAS.md` | Start/project flow | Readable project brief | Generated view |
| `PROJECT-VIEW.html` | `/brothermode:view` | Visual snapshot of project status | Generated snapshot |
| `DELIVERY-PACKET.md` | `/brothermode:deliver` | Delivery summary and evidence | Generated delivery view |
| Handoff packet | `brothermode continue` | Session-to-session continuity | Generated from records |

## `CANVAS.md`

Use it to read the agreed goal and project shape.

Do not manually edit it to change the project. If the goal or scope changes, record the change through BrotherMode and regenerate the canvas.

## `PROJECT-VIEW.html`

Use it as a shareable local snapshot.

Important properties:

- generated from recorded project state;
- self-contained file;
- does not act on the project;
- does not update itself while open;
- can become stale after project records change.

Regenerate with:

```text
/brothermode:view
```

## `DELIVERY-PACKET.md`

Use it as the handoff artifact after verification.

It should state:

- what was delivered;
- verification evidence;
- what remains intentionally out of scope;
- relevant limitations.

Do not create or edit this file by hand to bypass the delivery gate.

## Handoff Packet

The continuity path generates a packet from rows so a successor session receives recorded state rather than a narrative reconstructed from chat memory.

Test without launching:

```bash
brothermode continue --dry-run
```

## Rule for All Generated Artifacts

If an artifact disagrees with the underlying BrotherMode records, fix the records or the generator. Do not patch the artifact as if it were the source of truth.
