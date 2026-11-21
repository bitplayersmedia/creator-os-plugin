---
name: burn-captions
description: "Creator OS job skill: burns TikTok/Reels-style captions and the on-screen hook into a finished vertical (9:16) video, timed by whisper and spelled from the job's script; use it only when a Creator OS job brief names it."
user-invocable: false
---

# Burn captions

`burn_captions.py` (this folder, stdlib Python) turns a finished video plus the job's script into a captioned MP4. It never touches the input video: it writes a new file. Run it as `python3 "${CLAUDE_SKILL_DIR}/burn_captions.py"` (`${CLAUDE_SKILL_DIR}` is this skill's folder, shown as its base directory when it loads).

## When

In a finish job, captions go on last, after `zoom-moves`, so zooms never crop or scale them. One run per clip.

## Inputs

- `--video`: the clip to caption (9:16; the captions are laid out at 1080x1920 and scale to the real size). Spoken mode needs an audio track.
- `--script`: the job's script. In a finish job write `input.script` to a file (`script.json`) and pass that. The spoken text is its `lines` joined, the hook is its `hook`. A script card (`.md`, spoken text in `> ` lines under `**Script:**`) or plain text also works.
- `--style`: the look. In a finish job write `input.captionStyle` to a file (`style.json`) and pass that: `font`, `size`, `primary`, `outline` (the outline colour), `highlight`, `box` (`""` for no box, else a band colour behind the captions), `positionY`, `hookSeconds` (how long the hook shows), `uppercase`, `maxWords`. Colours are hex (`#F2C230`) or ASS (`&H0030C2F2&`). Without `--style` the defaults apply.
- `--hook "TEXT"`: the hook shown at the top for the first `hookSeconds`. Pass `input.hook`; it overrides the script's own `hook`. `--no-hook` drops it.
- `--mode spoken` (anything with a voice: 1 to 3 word captions timed by whisper) or `--mode beats` (a silent clip: each script line is a text card spread over the clip).

## Example (a finish job)

Write `input.script` and `input.captionStyle` from the job's input to work files with the Write tool, then run:

```bash
python3 "${CLAUDE_SKILL_DIR}/burn_captions.py" --mode spoken --video take.mp4 \
  --script script.json --style style.json --hook "<input.hook>" --out captioned.mp4
```

`take.mp4` is the clip after zooms (the raw take when the job has none), `script.json` holds `input.script`, `style.json` holds `input.captionStyle`. Other flags: `--model` picks another whisper model (default `small.en`), `--beats-y 640` puts the beats cards in the top third, `--keep-work` keeps the temporary work folder (`audio.wav`, whisper's `audio.json`, `captions.ass`) and prints where it is. Otherwise the folder is removed when the run ends.

## The caption-match figure (qc.captionMatch)

The run prints a report. Its `caption match: 0.93` line is the share of the script's words that whisper heard exactly: the value for `qc.captionMatch` in the job's `result.json`. The lines above it say how the rest went: `fuzzy` words were heard differently (for example `flat-share` heard as two words) and still got times, `unmatched/interpolated` words whisper missed got times from their neighbours, and `heard but not in script` counts words in the audio that the script lacks.

- At least 0.6: use the figure as it is.
- Under 0.6 the run also prints a WARNING: the script and the voice track differ. Do not ship that clip. Check that the script is the one the take was made from. If it is, write the brief's error shape (`{ "error": { "what", "why", "todo" }, "retry": true }`) with the figure in `why`; the brief says a match under 0.6 is a failure, never a result.
- Beats mode prints no figure (there is no audio to match). A finish job has a voice, so it uses spoken mode.

## What it does

1. **Spoken:** extracts 16 kHz mono audio, runs whisper with word timestamps, then aligns whisper's words to the script with `difflib`. The script's spelling, punctuation and CAPS win; whisper supplies the times.
2. Chunks of 1 to `maxWords` words, at most about 14 characters, broken at punctuation and at pauses over 0.6 s. Each chunk shows from its first word until the next chunk starts, or 0.6 s after its last word, whichever is sooner.
3. One ASS event per spoken word: that word in the highlight colour, the rest in the main colour. A word written in CAPS in the script pops (scales to about 121% then settles at 115%) while it is spoken.
4. **Hook:** the hook at the top for `hookSeconds`, at most two balanced lines, on a semi-transparent black box. In beats mode it is skipped when the first beat already says it.
5. **Beats:** each beat is a boxed card, centred, spread evenly over the clip. CAPS words show in the highlight colour.
6. Burns with `libx264 -crf 18 -preset medium`, audio copied, `-map_metadata 0 -metadata major_brand= -metadata minor_version= -metadata compatible_brands= -movflags +faststart+use_metadata_tags`, so the AIGC label and other metadata survive (the three empty brand tags stop `isom;isom` piling up over passes, which Instagram rejects as "Invalid video container brand").

## Tools

- **ffmpeg built with libass** (it has the `ass` filter). The script uses `FFMPEG_FULL` when set, then checks the `ffmpeg` on PATH. If the PATH build lacks libass or is missing, it looks for Homebrew’s `ffmpeg-full`. On macOS install it with `brew install ffmpeg-full`.
- **`whisper`** (the openai-whisper CLI) on PATH for spoken mode: `pip install openai-whisper`, or your package manager. The first run downloads the model (about 460 MB).
- A missing tool is an error with `retry: false` that names the tool and how to get it (the brief's error shape).

## Style rules

| Rule | Default |
|---|---|
| Font | Arial Black (falls back to Impact) |
| Size / outline / shadow | 78 / 7 px black / 2 px (at 1080x1920) |
| Highlight | `#F2C230` warm yellow, or `highlight` from the style |
| Caption position | centre line y = 1350, inside x 120 to 900: above the platform caption bar and clear of the right-hand buttons |
| Hook | top, y = 380, first 2.2 s, two lines max, box |
| Beats | box card at y = 960 (`--beats-y 640` for the top third) |
| Words per caption | 1 to 3, about 14 characters a line |

Other keys the script accepts in a style file (its own names): `fallback_font`, `bold`, `shadow`, `pop`, `spacing`, `caption_box` (AABBGGRR), `caption_box_pad`, `hook_y`, `hook_size`, `hook_primary`, `hook_box`, `hook_spacing`, `hook_uppercase`, `beats_size`, `max_chars`.

## Rules

- **Never show a word that is not in the audio.** The script supplies spelling only. If the report says under 60% of the script matched, or several words were "heard but not in script", the script and the voice track differ: see the caption-match section above.
- Keep the AI label: the metadata of the input is kept; do not strip it.
- Do not caption over a face: if the face sits low in frame, raise `positionY` in the style file rather than covering the mouth.

## Verify

Look at the result before writing `result.json`. Pull frames at the hook, a CAPS word and the middle (use the same ffmpeg as above):

```bash
ffmpeg -y -ss 0.5 -i captioned.mp4 -frames:v 1 -vf scale=540:-2 cap-0.5.png
ffmpeg -y -ss 6 -i captioned.mp4 -frames:v 1 -vf scale=540:-2 cap-6.png
```

Read the PNGs and check: the hook is in its box at the top while it shows; the caption sits in the lower middle, readable, not over the mouth, not cut off at either side; the highlighted word matches what is being said at that moment; nothing sits in the bottom ~420 px or the right-hand ~180 px.

© Bit Players Media LLC. Licensed for use with Creator OS only.
