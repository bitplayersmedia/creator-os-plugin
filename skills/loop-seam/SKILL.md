---
name: loop-seam
description: "Creator OS job skill: make a finished clip loop without a jump (trim the head, dissolve the tail into it, crossfade the room tone, check the end pose and the silence); use it only when a Creator OS job brief names it."
user-invocable: false
---

# Loop seam

Every short gets looped by the platform. A clip whose last frame flows into its first keeps getting replayed, and replays count as watch time. A clip that ends on another pose shows a jump at the wrap and the viewer swipes. Engine: `loop_seam.py` in this folder (`ffmpeg` and `ffprobe` on PATH; the openai-whisper CLI `whisper` only for the word timings). `${CLAUDE_SKILL_DIR}` is this skill's folder, shown as its base directory when the skill loads.

This skill runs first in the finish job, before `zoom-moves` and `burn-captions`. If `ffmpeg`, `ffprobe` or `python3` is missing from PATH, write the brief's error shape with `retry: false`, naming the tool and how to get it (a package manager is fine, never a fixed path).

## What it does

With overlap `x` (default 0.42 s, 10 frames at 24 fps):

1. The first `x` seconds come off the head.
2. The last `x` seconds dissolve into those head frames (`xfade=fade`), so the output's final frame is the clip's own frame `x`, one step before the output's first frame. The wrap is a normal frame step.
3. The audio gets an equal-power crossfade (`acrossfade`, `qsin`) over the same `x`, so the room tone wraps too.
4. Metadata is kept (`-map_metadata 0 -metadata major_brand= -metadata minor_version= -metadata compatible_brands= -movflags +faststart+use_metadata_tags`): the AIGC tag survives (the three empty brand tags stop `isom;isom` piling up over passes, which Instagram rejects as "Invalid video container brand").

Before it renders it checks three things and prints them:

| Check | Pass | Fail |
|---|---|---|
| Silence at both ends (whisper words with `--whisper`, else `silencedetect`) | the dissolve fits before the first word and after the last, with 0.08 s to spare | "no room for a seam": the first word starts at 0.0 s or the tail has no stillness |
| Seam SSIM (new first frame against the last frame) | 0.90 or more is invisible, 0.80 or more is a soft dissolve | 0.65 to 0.80 is a visible morph, below 0.65 the pose or framing is different (the clip ends on another pose than it starts) |
| Room tone | tail and head within 6 dB | the audio wrap will be heard (a tail that went dead silent) |

A failed check exits with code 2 and renders nothing. `--force` renders anyway and is for looking at the damage, never for a master.

## In a finish job: a failed seam means no seam

A finish job has no video tool budget, so it cannot regenerate the take. When the check fails on a 10 to 15 s take (exit code 2, or any PROBLEM line), do not regenerate and do not use `--force`: skip the dissolve, carry the plain take on to the next phase, and write the result with `qc.loop` false. A clip that gets a seam gets `qc.loop` true; `qc.seamSsim` is the seam SSIM the script printed (optional). A failed seam never fails the job by itself.

## Steps

1. Clip with a voice (talking, narrated after the voice track is on):
   `python3 "${CLAUDE_SKILL_DIR}/loop_seam.py" IN.mp4 OUT.mp4 --whisper`
   Silent clip: the same without `--whisper` (whisper would hallucinate words from the ambience). A whisper json you already have: `--words <path to its audio.json>`.
2. Read the report. On a PROBLEM line, follow "a failed seam means no seam" above. `--check-only` reports without rendering.
3. Look at `OUT.mp4.seam.png` (the last four frames, a white bar, then the first four frames: it must read as one motion) and, when you can, the clip three times in `OUT.loop3.mp4`.
4. Then `zoom-moves` with `"loop": true` in the map when the seam was made, then `burn-captions`.

Flags: `--overlap 0.42` (clamped to the free silence; 4 frames minimum, 1 s maximum), `--crf 12`, `--model small.en`. Whisper missing and no `--words`: the script exits with a hint to install the openai-whisper CLI (`pip install openai-whisper`, or your package manager); either install it, pass `--words`, or run without `--whisper` for a clip with no voice.

## Why the head is trimmed

A dissolve needs the two ends to meet on the same picture. Blending the tail into the untouched first frame would still leave `x` seconds of motion between the blend's end and frame 0. Trimming the head by `x` makes the blend end exactly one frame before the new first frame. The trim costs 0.42 s of the opening, which is why a take should have half a second of stillness before the first word.

© Bit Players Media LLC. Licensed for use with Creator OS only.
