#!/usr/bin/env python3
"""Seamless loop seam for a finished persona clip (runs before zoom-moves and burn-captions).

The platforms loop every short. A clip that ends on one pose and restarts on another shows a
jump at the wrap; a clip whose last frame flows into its first keeps getting replayed, and
replays count as watch time. This script makes the wrap a normal frame step:

  trim x seconds off the head, then dissolve the clip's last x seconds into that trimmed head.

    out(t) = clip(t + x)                                       0 <= t < L - x      (L = D - x)
    out(t) = blend( clip(t + x) -> clip(t - (L - x)) )         L - x <= t < L

  so out(L) == clip(x) == out(0): the wrap lands one frame after the clip's own frame x.

Audio gets the same treatment: an equal-power crossfade of the room tone over the same x
seconds. x must sit inside the silence before the first word and after the last word, so pass
whisper's word timings (`--words`, or `--whisper` to run it here) for every clip with a voice.

Usage:
  loop_seam.py IN.mp4 OUT.mp4 [--overlap 0.42] [--whisper | --words audio.json]
               [--check-only] [--crf 12] [--force]

Writes next to OUT: OUT.seam.png (last 4 frames | first 4 frames of OUT) and OUT.loop3.mp4
(OUT three times, to watch the wrap). Metadata is kept (-map_metadata 0, use_metadata_tags; brand tags blanked so they don't pile up), so
the AIGC tag survives. Exit code 2 when the seam would cut speech or the poses do not match;
`--force` renders anyway.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

MARGIN = 0.08          # seconds kept between the dissolve and the nearest word
MIN_OVERLAP = 0.167    # 4 frames at 24 fps: anything shorter reads as a cut
MAX_OVERLAP = 1.0
SSIM_GOOD, SSIM_SOFT, SSIM_BAD = 0.90, 0.80, 0.65


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def probe(path):
    out = run(["ffprobe", "-v", "error", "-show_entries",
               "stream=codec_type,width,height,r_frame_rate,nb_frames:format=duration", "-of", "json", path]).stdout
    d = json.loads(out)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    has_audio = any(s["codec_type"] == "audio" for s in d["streams"])
    num, den = (v["r_frame_rate"].split("/") + ["1"])[:2]
    fps = float(num) / float(den)
    nb = int(v.get("nb_frames") or round(float(d["format"]["duration"]) * fps))
    dur = nb / fps  # the video's own length; the audio track can run a few ms longer
    return v["width"], v["height"], fps, dur, nb, has_audio


def whisper_words(js):
    words = []
    for seg in json.load(open(js)).get("segments", []):
        for w in seg.get("words", []):
            words.append((float(w["start"]), float(w["end"]), w["word"].strip()))
    return words


def transcribe(video, work, model="small.en"):
    if not shutil.which("whisper"):
        sys.exit("whisper not found: install the openai-whisper CLI (pip install openai-whisper, or your package manager); or pass --words <audio.json>")
    wav = work / "audio.wav"
    run(["ffmpeg", "-y", "-v", "error", "-i", video, "-vn", "-ac", "1", "-ar", "16000", str(wav)])
    run(["whisper", str(wav), "--model", model, "--language", "en", "--word_timestamps", "True",
         "--output_format", "json", "--output_dir", str(work), "--fp16", "False", "--verbose", "False"])
    return work / "audio.json"


def silence_edges(video, dur):
    """(first sound, last sound) from silencedetect; None when the clip is never silent (ambient bed)."""
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", video, "-af", "silencedetect=n=-30dB:d=0.08",
                        "-f", "null", "-"], capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", r.stderr)]
    first = ends[0] if starts and starts[0] < 0.05 and ends else 0.0
    last = starts[-1] if starts and (not ends or starts[-1] > ends[-1]) else dur
    return first, last


def frame_png(video, t, out, width=540):
    """The frame shown at time t (seek a hair early so the last frame is still found)."""
    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{max(t - 0.002, 0):.4f}", "-i", video, "-frames:v", "1",
         "-vf", f"scale={width}:-2", "-update", "1", str(out)])
    if not Path(out).exists():
        sys.exit(f"no frame at {t:.3f}s in {video}")


def ssim(a, b):
    r = run(["ffmpeg", "-v", "info", "-i", str(a), "-i", str(b), "-filter_complex", "ssim", "-f", "null", "-"])
    m = re.search(r"All:([0-9.]+)", r.stderr)
    return float(m.group(1)) if m else float("nan")


def rms_db(video, start, length):
    r = run(["ffmpeg", "-v", "info", "-ss", f"{start:.4f}", "-t", f"{length:.4f}", "-i", video,
             "-af", "astats=measure_perchannel=none:measure_overall=RMS_level", "-f", "null", "-"])
    m = re.findall(r"RMS level dB: (-?[0-9.]+|-inf)", r.stderr)
    return float(m[-1]) if m and m[-1] != "-inf" else -99.0


def grade(s):
    if s >= SSIM_GOOD:
        return "invisible"
    if s >= SSIM_SOFT:
        return "soft dissolve, fine"
    if s >= SSIM_BAD:
        return "visible morph: the end pose is not quite the opening pose"
    return "no loop: the end pose or framing is not the opening one"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input"); ap.add_argument("output")
    ap.add_argument("--overlap", type=float, default=0.42, help="dissolve length in seconds (default 0.42, clamped to the silence at both ends)")
    ap.add_argument("--whisper", action="store_true", help="run whisper here to keep the dissolve off the words (talking and narrated clips)")
    ap.add_argument("--words", help="whisper word json (the audio.json whisper wrote, e.g. in a temp work folder) instead of --whisper")
    ap.add_argument("--model", default="small.en")
    ap.add_argument("--check-only", action="store_true", help="report the seam, render nothing")
    ap.add_argument("--crf", type=int, default=12)
    ap.add_argument("--force", action="store_true", help="render even when the seam would cut speech or the poses differ")
    a = ap.parse_args()

    src = str(Path(a.input).resolve())
    out = Path(a.output).resolve()
    w, h, fps, dur, nb, has_audio = probe(src)
    work = Path(tempfile.mkdtemp(prefix="loop-seam-"))
    problems = []

    # 1. how much silence is there at each end?
    if a.words or a.whisper:
        js = a.words or transcribe(src, work, a.model)
        words = whisper_words(js)
        if words:
            first, last = words[0][0], words[-1][1]
            print(f"words: first {words[0][2]!r} at {first:.2f}s, last {words[-1][2]!r} ends {last:.2f}s")
        else:
            first, last = dur, 0.0
            print("whisper heard no words")
    elif has_audio:
        first, last = silence_edges(src, dur)
        print(f"silencedetect: sound from {first:.2f}s to {last:.2f}s (pass --whisper for a clip with a voice)")
    else:
        first, last = dur, 0.0
    head_free, tail_free = first, dur - last

    # 2. pick the overlap in whole frames
    want = min(max(a.overlap, MIN_OVERLAP), MAX_OVERLAP)
    x = min(want, head_free - MARGIN, tail_free - MARGIN)
    k = int(x * fps)                       # whole frames
    x = k / fps
    if x < MIN_OVERLAP:
        problems.append(f"no room for a seam: {head_free:.2f}s free before the first sound, {tail_free:.2f}s after the last; "
                        f"the dissolve would cut speech. The take needs a beat of stillness at both ends, or --force.")
        k = max(int(MIN_OVERLAP * fps), 1); x = k / fps
    L = dur - x
    print(f"clip {dur:.2f}s @ {fps:g} fps ({nb} frames); overlap {x:.3f}s ({k} frames); output {L:.2f}s")

    # 3. do the poses match? SSIM of the new first frame (clip x) against the last frame
    f_new_first, f_last = work / "new-first.png", work / "last.png"
    f_tail_in, f_head_out = work / "tail-in.png", work / "head-out.png"
    frame_png(src, x, f_new_first); frame_png(src, dur - 1 / fps, f_last)
    frame_png(src, dur - x, f_tail_in); frame_png(src, 2 * x, f_head_out)
    s_seam = ssim(f_new_first, f_last)
    s_tail = ssim(f_tail_in, f_last)      # motion inside the dissolve window at the tail
    s_head = ssim(f_new_first, f_head_out)  # motion inside the window at the head
    print(f"seam SSIM {s_seam:.3f}: {grade(s_seam)}")
    print(f"motion inside the dissolve: tail {s_tail:.3f}, head {s_head:.3f} (below {SSIM_SOFT} = still moving; ghosting likely)")
    if s_seam < SSIM_SOFT:
        problems.append(f"seam SSIM {s_seam:.3f} ({grade(s_seam)})")
    if has_audio:
        tail_db, head_db = rms_db(src, dur - x, x), rms_db(src, 0, x)
        print(f"room tone: tail {tail_db:.1f} dB, head {head_db:.1f} dB" +
              ("  (more than 6 dB apart: the audio wrap will be heard)" if abs(tail_db - head_db) > 6 else ""))

    if problems:
        for p in problems:
            print("PROBLEM:", p)
        if not a.force:
            shutil.rmtree(work, ignore_errors=True)
            sys.exit(2)
    if a.check_only:
        shutil.rmtree(work, ignore_errors=True)
        return

    # 4. render: main = clip[x..D], head = clip[0..x]; dissolve main's last x seconds into head
    off = (nb - 2 * k) / fps
    fc = (f"[0:v]fps={fps:.6f},split[v0][v1];"
          f"[v0]trim=start_frame={k},setpts=PTS-STARTPTS[main];"
          f"[v1]trim=end_frame={k},setpts=PTS-STARTPTS[head];"
          f"[main][head]xfade=transition=fade:duration={x:.6f}:offset={off:.6f},format=yuv420p[v]")
    maps = ["-map", "[v]"]
    if has_audio:
        fc += (f";[0:a]asplit[a0][a1];[a0]atrim=start={x:.6f},asetpts=PTS-STARTPTS[amain];"
               f"[a1]atrim=end={x:.6f},asetpts=PTS-STARTPTS[ahead];"
               f"[amain][ahead]acrossfade=d={x:.6f}:c1=qsin:c2=qsin[a]")
        maps += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
    run(["ffmpeg", "-y", "-v", "error", "-i", src, "-filter_complex", fc, *maps,
         "-c:v", "libx264", "-crf", str(a.crf), "-preset", "medium", "-pix_fmt", "yuv420p",
         "-map_metadata", "0", "-metadata", "major_brand=", "-metadata", "minor_version=", "-metadata", "compatible_brands=", "-movflags", "+faststart+use_metadata_tags", str(out)])
    _, _, _, odur, onb, _ = probe(str(out))
    print(f"wrote {out} ({odur:.2f}s, {onb} frames)")

    # 5. proof: the frames either side of the wrap, and the clip looped three times
    strip = out.with_suffix(out.suffix + ".seam.png")
    tail, head = work / "tail.png", work / "head.png"
    run(["ffmpeg", "-y", "-v", "error", "-i", str(out), "-vf", f"select='gte(n,{onb - 4})',scale=270:-2,tile=4x1",
         "-fps_mode", "passthrough", "-frames:v", "1", "-update", "1", str(tail)])
    run(["ffmpeg", "-y", "-v", "error", "-i", str(out), "-vf", "select='lt(n,4)',scale=270:-2,tile=4x1",
         "-fps_mode", "passthrough", "-frames:v", "1", "-update", "1", str(head)])
    run(["ffmpeg", "-y", "-v", "error", "-i", str(tail), "-i", str(head), "-filter_complex",
         "[0]pad=iw+12:ih:0:0:white[t];[t][1]hstack", str(strip)])
    loop3 = out.with_suffix(".loop3.mp4")
    run(["ffmpeg", "-y", "-v", "error", "-stream_loop", "2", "-i", str(out), "-c", "copy", str(loop3)])
    print(f"look at {strip} (last 4 frames | first 4 frames) and watch {loop3}")
    shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
