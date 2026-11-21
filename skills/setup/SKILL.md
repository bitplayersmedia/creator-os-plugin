---
name: setup
description: Link to your Creator OS studio and find, test and save how you make pictures, videos and voices.
argument-hint: "[images|video|voice]"
disable-model-invocation: true
---

# Creator OS setup

Arguments: `$ARGUMENTS`. With no argument, do images, video and voice in that order. With `images`, `video` or `voice`,
do only that kind (`voices` is an alias for `voice`). For any other argument, show the valid choices and stop.

Use the Creator OS MCP tools `status`, `pair`, `save_setup`, `save_recipe` and `check_tools`
(named `mcp__plugin_creator-os_creator-os__<tool>`).

1. Call `status`. If unlinked, explain that Creator OS uses this session's permissions, and ask for the pairing code
   from Settings, Connect Claude. Ask for a site address only if the user says they use another site. Call `pair`.
   If pairing fails, show the refusal and ask for a new code. Never sign in for the user or ask for their token.
   Call `save_setup`, passing `jobsDir` only if the user names a location. Get the exact jobs folder from `status`.
   If the link was revoked or setup was refused, report that and stop before generating samples.
2. Ask the selected questions one at a time. Finish the current kind before asking the next.
   - Images: “How do you want to make pictures?”
   - Video: “How do you want to make videos?”
   - Voice: “How do you want to make voices?”
   Accept any route the user chooses. Offer connected tools as examples when available and mention costs.
3. Try the user's route in this session. Before any paid call, explain the estimated cost and wait for a yes.
   Make one picture, one short 9:16 image-to-video clip with speech, or one spoken line, as appropriate.
   Save the sample in a new test subfolder under the jobs folder. Inspect it for the expected format and show the
   actual image, clip or audio to the user. If the route fails, explain the failure, try a fix or another route with
   the user, and repeat until it works or the user stops. Keep the previous recipe if a replacement was never proved.
4. During voice setup, ask: “For one consistent voice across shots, Higgsfield offers voice change at about
   1–2 credits per shot. Do you want to use it? Yes or no?” Record the choice in the voice recipe. On a no, keep the
   takes' own speech. On a yes, record the voice-change route and prerequisites separately from voice sample generation.
5. After each successful test, call `save_recipe` with its `kind` and Markdown `text`. Record the working route,
   exact steps or commands, input and output formats, sizes and limits, cost in credits (0 for free), tools or accounts
   the user must already have open or signed into, and the date proved. For pictures, also record Soul ID training
   capability if known. Leave out credentials. If saving fails, show the error and fix it before reporting readiness.
   Then call `check_tools` with the proved kind's `tool` and `answers: true`. Include `balance` only for a paid service
   when a verified balance is available. Use the MCP tool for recipe writes. Sample files can be written by the chosen route.
6. If a route uses credits, including optional voice change, ask how many credits each `/creator-os:work` run may use
   and pass that cap to `check_tools`. Free routes need no cap. Change a previously saved cap only when the user chooses.
7. Report what was proved, the sample and recipe paths, and any remaining kind. Repeat any site error from
   `save_setup` or `check_tools` verbatim so the user knows why the website may still show setup as missing.
