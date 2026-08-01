---
description: Package the finished work into one delivery summary with the evidence that it works
---

Outcome to produce: one delivery packet the user can read, share, and act on, proving what was built and how it was checked.

Enter the delivery flow of the brotherme skill. Run the mechanical command `python3 tools/bm_project.py deliver` to generate the delivery packet from the store's own rows; never fill DELIVERY-PACKET.md by hand and never answer from memory of this conversation about what is done. That path is relative to the BrotherME install folder, not the user's project folder: a plugin install runs it from the plugin's own root, a clone install runs it from `~/.claude/skills/brothermode`; prefix that install path onto the command, and still run it from the user's project folder so it reads and writes that project's own records. Do not say "ready to deliver" unless a verifying check ran after the last edit and passed; if any check is missing or failing, say so plainly and list what remains instead of delivering.
