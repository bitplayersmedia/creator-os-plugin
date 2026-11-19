---
name: zoom-moves
description: "Creator OS job skill: add zoom emphasis to a finished clip in the persona's soft or hard style (snap-in hits, combos, smooth pushes, never a move just before a cut); use it only when a Creator OS job brief names it."
user-invocable: false
---

# Zoom moves

Runs on every talking or narrated clip in the finish job, after `loop-seam` and before `burn-captions`. Engine: `zoom_moves.py` in this folder (ffmpeg zoompan, zoom computed per frame, 2x upscale so eases don't wobble, audio copied, metadata kept). `${CLAUDE_SKILL_DIR}` is this skill's folder, shown as its base directory when the skill loads.

If `ffmpeg`, `ffprobe` or `python3` is missing from PATH, write the brief's error shape with `retry: false`, naming the tool and how to get it (a package manager is fine, never a fixed path).

## The persona's style: `input.choices.zoom`

The job's input carries the style; never ask for one. `soft` and `hard` are the only values; if the field is missing, use `soft`.

| `input.choices.zoom` | Moves | Peak (relative to the shot's base) |
|---|---|---|
| `soft` | smooth `push` on a thesis or closing line; at most 2 `hit` or `combo` moves in the whole clip, only on real impact words | about 1.08 |
| `hard` | 3 to 5 moves in a 30 s clip: `hit` on impact words, `combo` on real combos, a `push` on the thesis; long stretches still at rest so the moves land | about 1.15 |

Scale the count to the clip: a 10 to 15 s take gets one or two moves in `soft` and two or three in `hard`. A clip with nothing worth emphasising gets no moves; copy it through with an empty `moves` list.

## The moves

| Move | What the viewer sees | Use for |
|---|---|---|
| `hit` | one-frame snap in, then stays in until the shot's last frame | an impact word only |
| `combo` | a snap up on each item of a 2 to 3 word combo, then stays in until the cut | only when the line is a real combo: "never do A, B or C", "Pen. DOWN.", "Theirs. Not yours." |
| `push` | smooth zoom in, then out | a thesis line, a closing line |

Rules:
- **Snaps stay in until the cut** (`"out": "cut"`, the default for hit and combo). The zoomed frame runs to the shot's last frame; the next shot starts at its own resting framing on its first frame. Get the cut frames exactly (scene detection, then look at the frames either side). A take with no cuts is one shot; a snap then holds until the end only if the clip is not a loop, so on a loop give each snap an `out` number.
- **Nothing moves just before a cut.** No snap, push or ease in the last second of a shot; the script warns. A snap that would land there is dropped (the cut is the emphasis).
- **Smooth ease-out rarely**, only where it looks good: a snap mid-way through a long shot, well clear of the next cut.
- **Never a two-step in and two-step out.** Steps up are only for combos.
- **Few moves.** Not every strong word needs one.
- **Loop clips** (`loop-seam` ran first and made a seam, so the input already wraps): the end of the clip is a wrap, not a cut. The last shot ends at rest: no snap held into the end, no move in the last second and none in the first 0.3 s; the first and last shots share `base` and `cy`. Put `"loop": true` in the map and the script checks all of it. When the seam was skipped (`qc.loop` false), leave `"loop"` out.
- Keep the absolute zoom at or below 1.30 (the script caps it at 1.32).

## Steps

1. Word timings: `whisper` on the clip's audio (the openai-whisper CLI on PATH, with `--word_timestamps True --output_format json`), or reuse the words from an earlier phase. If `whisper` is missing, work from `input.script` and the take's pacing instead of failing. Shot cuts: `ffmpeg -i IN -vf "scale=270:-1,select='gt(scene,0.25)',showinfo" -an -f null - 2>&1 | grep -oE "n: *[0-9]+|pts_time:[0-9.]+"`, then export the frames either side of each cut (`select=eq(n\,N)`) and confirm the first frame of every shot. Shots are keyed by that frame number.
2. Look at one frame per shot; set `cy` per shot so the face stays in frame when zoomed (0.10 to 0.30 for a face in the top third). Use a shot `base` above 1.0 only to crop a stray prop at the frame edge (it changes on the cut, so it reads as framing, not a zoom).
3. Write `moves.json` in the job's work folder (format in the script's docstring), with the moves for the persona's style from the table above. Snap moves 1 frame (about 0.04 s) before the word's start. Peaks are relative to the shot's base.
4. `python3 "${CLAUDE_SKILL_DIR}/zoom_moves.py" IN.mp4 OUT.mp4 moves.json --dry-run` prints the curve; check it, then run without `--dry-run`. The script also writes `OUT.mp4.filter.txt` next to the output; leave it out of `outputs/`.
5. Check frames at each peak (face in frame, nothing important cropped), then `burn-captions` on OUT.

## Example

A 12 s take, one shot, `soft` style, a seam made, impact word "never" at 4.20 s and a closing line from 9.0 s to 10.6 s:

```json
{"cx": 0.5, "loop": true,
 "shots": [{"frame": 0, "cy": 0.20, "base": 1.0}],
 "moves": [
   {"type": "hit", "t": 4.16, "peak": 1.08, "hold": 0.7, "out": 0.6, "label": "never"},
   {"type": "push", "t0": 8.6, "t1": 9.8, "peak": 1.06, "hold": 0.1, "out": 0.4, "label": "closing line"}]}
```

The push starts a little before the closing line and is back at rest by 10.3 s (`t1 + hold + out`), so no move touches the last second (11.0 s on) and the wrap lands on the shot's resting framing. Check that sum on any move in a looped clip. For `hard`, the same take could add a `combo` and raise the peaks to about 1.15.

© Bit Players Media LLC. Licensed for use with Creator OS only.
