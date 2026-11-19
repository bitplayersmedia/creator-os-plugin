---
name: setup
description: Set up Creator OS on this computer (link it to your studio with the code from Settings, Connect Claude).
disable-model-invocation: true
---

# Creator OS setup

Link this computer to the user's Creator OS studio. The tools are `mcp__plugin_creator-os_creator-os__pair`,
`mcp__plugin_creator-os_creator-os__save_setup`, `mcp__plugin_creator-os_creator-os__check_tools`, `mcp__plugin_creator-os_creator-os__status` and
`mcp__plugin_creator-os_creator-os__disconnect`.

1. Ask the user for the code shown in Creator OS, Settings, Connect Claude. Ask for a site address only if they say they
   use a site other than the default one.
2. Call `pair` with the code (and the site address, if they gave one). If the answer is not "Linked to <studio>.", tell
   the user what it said (for example the code is wrong or has run out) and ask for a new code. Do not retry by yourself.
3. Call `save_setup` (with `jobsDir` only if the user names a folder for job files).
4. Picture, video and voice tool (one path for now: Higgsfield, the user's own account). Offer the tools this session
   already has connected first; if Higgsfield is not connected, recommend it (its hosted MCP, or its CLI after
   `higgsfield auth login`) and say a paid plan is needed. Any other route (for example Google Flow through the
   browser) is an opt-in the user must ask for, with a warning that it is slower and may break. Never sign in for the user.
5. Prove the tool answers: make one real call to it, and a balance (credits) call where it has one. Then call
   `check_tools` with `tools: [{ kind, tool, answers, balance }]` for `images`, `video` and `voice` (`answers` true only
   if the call worked). If it says `missing`, tell the user which and how to fix it; do not guess.
6. Ask the spend cap in plain words: "How many credits may Creator OS use each time you run /creator-os:work? Say 0
   (the default) and it will never spend." Call `check_tools` with `spendCap` (0 when they do not answer).
7. Tell the user, in a few plain sentences: this computer is linked to <studio>; full-quality files stay on this
   computer; Google Drive comes later; what is ready or missing; the spend cap. If an answer from `save_setup` or
   `check_tools` ended with a line about the site (it could not be reached, the link was revoked, or the site refused
   the setup), repeat that line word for word: until it is fixed, Creator OS still shows setup as missing.

Also tell the user, one line each: `status` shows whether this computer is linked (with `waiting` it also counts the jobs
waiting), and `disconnect` ends the link.

Never ask for, show or repeat the token: it is saved by the tools and no tool result contains it. Never write files by
hand and never run other commands to set anything up.
