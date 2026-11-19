---
name: short-form-director
description: Creator OS job skill: direct a 10 to 30 second vertical video as a two-column A/V beat sheet. Use it only when a Creator OS job brief names it.
user-invocable: false
---

# Short-form director

A persona video loses the viewer when the character sits still and talks. A professional short is **directed**: every few seconds something changes on screen, every important word lands on the face or in the hands, and the first second is a physical event, not a sentence. This skill turns a script into a **beat sheet** that the video prompt can follow shot by shot.

It runs unattended. It never asks a question and never waits for a pick: the job's brief and its `input` carry every choice (`input.script`, `input.format`, `input.bible`), and anything missing gets a sensible default. The `beats` job writes the sheet into the brief's `result.json` shape (rows with `start`, `end`, `shot`, `action`, `line`, `face`, plus `sound`, `loopPose` and `agentChecks`), never as a chat reply. If the job cannot be done, write the brief's error shape (`{ "error": { "what", "why", "todo" }, "retry": true|false }`).

It sits between the `content-engine` skill (ideas and spoken words) and the video prompt, which follows the beat sheet. Captions are burned in afterwards with `burn-captions`, and zooms added with `zoom-moves`.

## The rules (check every beat sheet against them)

1. **Hook = an action in the first second,** paired with the on-screen hook caption. A hand slaps down, a file hits the desk, she walks into frame, something is torn, poured, dropped. Never open on a still face saying hello. **Row timing:** the first row is the hook beat and its `end` is at most 1.0 s (write it `0-1 s`, then the next row starts at 1 s); the app checks exactly this ("Physical hook": first row ends by 1.0 s and has an action). The hook row carries the action and usually no spoken line; the first line starts in row 2. The hook row is a shot like any other and counts in rule 3's 2 to 4.
2. **Something visibly changes every 3 to 4 seconds:** a new action, a prop, a new angle (cut), the character standing up or leaning into the lens. Count it: a 28 s clip needs at least 7 changes.
3. **2 shots per 10 to 15 s clip, 2 to 4 per 30 s,** each with its own framing (close on hands, medium seated, wider standing, close-up lean-in). The video model makes them in one multi-shot generation; cut on action. A clip where two or more people talk is not a good fit: keep one speaker and show others only as hands or blurred edges.
4. **Every stressed word is physical.** Write stressed words in CAPS in the line, and give each one a face or hand beat (a brow, a jab of the pen, a lean, a look over the sunglasses). The script's own CAPITALS are the stressed words: keep them as they are.
5. **Words leave room for action:** 25 to 40 spoken words for a 10 to 15 s clip, 40 to 75 for a 30 s card. If the action needs the time, cut words, not action. Each row's `line` is a script line unchanged; never reword the script to fit.
6. **One signature gesture per clip, on the key beat** (the persona's `bible.gesture`: folding sunglasses shut, nudging spectacles). Everyday gestures are not rationed.
7. **Payoff visual, then the loop pose.** The last shot resolves the hook physically (the pen goes in the drawer, the hive lid closes), and its last half-second returns to shot 1's framing and body position: same seat, hands in the same place, mouth closed, eyes where they were, still. The platform loops the clip and the `loop-seam` skill dissolves this pose into the opening frame. No sign-off unless it is the punchline.
8. **Sound you can see.** Name 1 to 3 diegetic sounds that sell the action (paper slap, drawer thud, jar lid). In talking clips the model generates them with the voice.
9. **Stillness at both ends.** About half a second with no words before the first line and after the last, room tone running, mouth closed. That is where the loop seam lives: a clip whose first word starts at 0.0 s, or whose tail goes dead silent, cannot loop.

## What AI video can and can't do (producibility)

- **Fine:** one character; large hand and body actions (slap, flick pages, stand, walk two steps, lean in, hold a prop to the lens, pour, plant, lift a lid); props that exist from the first frame; other people as hands or blurred edges only.
- **Not fine:** counting on fingers or any finger choreography (the model miscounts), readable text on props or screens, brands, crowds, fast spins, a prop that appears from nowhere, two characters talking to each other.
- **Risky (have a fallback):** paper or cloth doing something complex (a long strip unfolding), liquids splashing, animals. Write the fallback into the beat sheet.
- Keep the anchors from `input.bible.anchors` visible in the action text of every close-up, word for word.

## Format notes

- **Talking (on camera):** the character speaks the lines; the video model generates the voice itself, so the lips follow it. 2 to 4 shots, the face visible in most of them.
- **Narrated:** the character does something active the whole time and never speaks on camera; the voice track plays over it. Mouth closed or turned away; this is where bigger actions go.

## Output: the beat sheet

Fill the brief's rows from this table shape (one row per shot, time order, no gap or overlap):

```
Beat sheet (talking | narrated; N shots; ~S s)
| Time | Shot | Action (what we see) | Line (CAPS = stressed) | Face / performance |
|---|---|---|---|---|
| 0-1 s | Close on the desk (hook beat) | ... | | ... |
| 1-4 s | ... | ... | "..." | ... |
...
Sound: ...
Loop pose: ... (what shot 1 opens on and the last half-second returns to)
Props from frame one: ...
Fallback: ... (for any risky beat)
```

Map it onto the result: `start` and `end` are the Time column in seconds (row 1 starts at 0 and ends at 1 or earlier; each row is one shot, and the app counts rows as shots, so keep the total at 2 to 4 rows and never split a beat inside one shot into its own row: put it in that row's `action`), `shot` the framing, `action` what we see (with the props from frame one named in the first row and the fallback noted beside any risky beat), `line` the spoken line, `face` the performance. `sound` and `loopPose` are the Sound and Loop pose lines.

## Check before you write the result

Put each of these in the brief's `agentChecks` and fix any that fails; never report a failed check as ok:

- Hook action in the first second, and does row 1 end at 1.0 s or earlier?
- A change every 3 to 4 seconds?
- Every CAPS word has a beat?
- Words within the band (at most 40 for 15 s, at most 75 for 30 s), and timing fits `wpm`?
- Every spoken line of the script in exactly one row, unchanged?
- Loop pose named, equal to the opening pose, with stillness at both ends?
- A fallback for every risky beat?
- The persona's guardrail still met (no claim it forbids)?

## References

For the craft behind the beats (scene formula, Murch's rule of six, blocking, the 14-field shot card) read the `video-prompting` skill's `references/dramaturgy.md`. For how the video model reads a prompt (shots, audio, what it follows and ignores) read the `video-prompting` skill's `references/seedance-25.md`. Both are in that skill's folder; load the skill by name to find them.

## Worked example: "Put the pen down" (talking, 4 rows = 4 shots, about 27 s)

The app counts one shot per row, so the sheet has 2 to 4 rows in all, the hook row included. A move inside a shot (a tilt, a drag, a jab) goes inside that row's Action; it never gets a row of its own.

**On-screen text (hook caption):** "PUT. THE PEN. DOWN."
**Setting:** a sitting room, at the writing desk; a thick stapled contract lies open with a red pen beside it. The character is in her base outfit (a green coat over a black roll-neck, a spiral brooch below the right collarbone, hair swept up, cherry-red lipstick); cat-eye sunglasses folded on the desk.

| Time | Shot | Action | Line (CAPS = stressed) | Face |
|---|---|---|---|---|
| 0-1 s | Close on the desk (hook beat) | A young hand (sleeve only, edge of frame) brings a pen to the signature line. Her hand, gold watch on the wrist, SLAPS flat on the page at once; the paper jumps. | | Hand only; room tone, no words yet. |
| 1-11 s | Camera tilts up to a medium, seated | The camera tilts up from the page to her face as the hand stays pressed on the paper (about 3 s). She drags the contract across to herself, flicks pages fast, stops, jabs one line with the red pen. | "Ah-ah. Pen. DOWN." (about 1 s in) then "Three words I'd never sign past. AUTOMATICALLY renews. Lovely for THEM. You forget, it keeps going, and the reminder goes to a flat you left YEARS ago." | One eyebrow raised, lips pressed on "down"; dry half-smile on "Lovely for them"; eyes roll up on "years ago". |
| 11-19 s | Medium-wide, she stands | She tears the page out and holds it up to the lens; it unfolds into a long strip that drops past the desk to the floor. | "Including but NOT limited to. That's a list with no END." | Deadpan, watching it fall; a tiny shake of the head. |
| 19-27 s | Close-up, she leans into the lens | She picks up the sunglasses and folds them shut with one hand (signature gesture, key beat), then slides the red pen into the desk drawer and shuts it with a soft thud. | "And the WORST. At our DISCRETION. Theirs. Not yours. If they won't explain it, don't sign it." | Narrowed eyes on "discretion"; a warm, knowing smile on the last line. |

**Sound:** her voice (generated with the take), the paper slap, pages flicking, the drawer thud.
**Props from frame one:** the contract, the red pen, the young hand's pen, the folded sunglasses, the drawer closed.
**Fallback:** if the long strip glitches, she holds one page up to the lens and lets it slide off the desk.
**Guardrail:** reading principles only; no company named, no figures, nothing said about what the phrases mean in law.

*(This example is at a 30 s length. As a 15 s card the same hook (still a 0-1 s first row) is rows 1 and 4 only (2 shots), the sign-off cut, the last line "Theirs. Not yours.", and the drawer thud lands with her back in shot 1's seat and framing as the loop pose.)*

© Bit Players Media LLC. Licensed for use with Creator OS only.
