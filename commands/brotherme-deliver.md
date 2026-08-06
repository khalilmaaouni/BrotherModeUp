---
description: Package the finished work into one delivery summary with the evidence that it works
---

Outcome to produce: one delivery packet the user can read, share, and act on, proving what was built and how it was checked.

Enter the delivery flow of the brotherme skill. Run the mechanical command `python3 "${CLAUDE_PLUGIN_ROOT}/tools/bm_project.py" deliver` to generate the delivery packet from that project's own records; never fill DELIVERY-PACKET.md by hand and never answer from memory of this conversation about what is done. A plugin install exports `${CLAUDE_PLUGIN_ROOT}` for skill and command content, so that path resolves on its own; on a clone install, where the variable is unset, run `python3 tools/bm_project.py deliver` instead, from the BrotherMode root (`~/.claude/skills/brothermode`). Either way, run it from the user's project folder so it reads and writes that project's own records. Do not say "ready to deliver" unless a verifying check ran after the last edit and passed; if any check is missing or failing, say so plainly and list what remains instead of delivering.
