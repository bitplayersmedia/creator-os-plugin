#!/usr/bin/env python3
"""Zoom moves for persona clips: smooth pushes, snap-in hits and combos that ease back out.

  python3 zoom_moves.py IN.mp4 OUT.mp4 MAP.json [--crf 12] [--dry-run]

MAP.json:
  {"cx": 0.5,
   "shots": [{"frame": 0, "cy": 0.20, "base": 1.0}, {"frame": 70, "cy": 0.10, "base": 1.15}],
   "moves": [
     {"type": "combo", "steps": [[1.58, 1.10], [2.18, 1.22]], "out": "cut"},
     {"type": "hit",   "t": 6.45, "peak": 1.12, "hold": 0.6, "out": 0.9},
     {"type": "push",  "t0": 20.4, "t1": 22.6, "peak": 1.10, "hold": 0.6, "out": 0.8}]}

shots: one entry per shot, keyed by its FIRST frame (from scene detection, checked by eye; "t"
  in seconds also works and is rounded to the nearest frame). cy = focal height (0 top, 1 bottom)
  so the face stays in frame; base = the shot's resting zoom (a constant reframe that changes only
  on the cut, e.g. 1.15 to crop a stray prop at the frame edge).
moves (peaks are relative to the shot's base; 1.12 = 12 % tighter):
  hit    one-frame snap in at t. Impact words only.
  combo  a snap up on each item of a 2-3 word combo ("never A, B or C").
  push   smooth zoom in from t0 to t1.
  out    how a move ends. "cut" (the default for hit and combo): stay in until the shot's last
         frame; the next shot starts at its own base on its first frame. A number: hold `hold`
         seconds, then a smooth ease back out over that many seconds (use rarely, only where it
         looks good and well before a cut). 0: snap back out after `hold`.
Moves are combined by taking the largest, so an overlap rises instead of snapping down.
The script warns about any move or ease that runs within 1 s of a cut (it looks jarring).

Zoom is computed per frame in Python and written into zoompan as a lookup, so any curve is exact.
The input is upscaled 2x before zoompan so slow eases don't wobble on whole-pixel crops. Audio is
copied and the metadata kept (-map_metadata 0, use_metadata_tags; brand tags blanked so they don't pile up), so an AIGC tag survives.
"""
import argparse, json, subprocess, sys

MAX_ZOOM = 1.32


def probe(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
        "stream=width,height,r_frame_rate:format=duration", "-of", "json", path])
    d = json.loads(out)
    s = d["streams"][0]
    num, den = (s["r_frame_rate"].split("/") + ["1"])[:2]
    return s["width"], s["height"], float(num) / float(den), float(d["format"]["duration"])


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def envelope(m, t, n, cut):
    """Relative zoom (1.0 = rest) of one move at time t (frame n); cut = first frame of the next shot."""
    kind, hold = m["type"], m.get("hold", 0.4)
    out = m.get("out", 0.8 if kind == "push" else "cut")
    if out == "cut":
        if n >= cut:
            return 1.0
        hold, out = 1e9, 0
    if kind == "push":
        t0, t1, p = m["t0"], m["t1"], m["peak"]
        if t < t0:
            return 1.0
        if t < t1:
            return 1 + (p - 1) * smooth((t - t0) / (t1 - t0))
        top_end = t1 + hold
    elif kind == "hit":
        p = m["peak"]
        if t < m["t"]:
            return 1.0
        top_end = m["t"] + hold
    elif kind == "combo":
        steps = sorted(m["steps"])
        if t < steps[0][0]:
            return 1.0
        p = max(z for s, z in steps if s <= t)
        if t < steps[-1][0]:
            return p
        p = steps[-1][1]
        top_end = steps[-1][0] + hold
    else:
        sys.exit(f"unknown move type {kind!r}")
    if t < top_end:
        return p
    return p - (p - 1) * smooth((t - top_end) / out) if out > 0 else 1.0


def start_of(m):
    return m.get("t", m.get("t0", min((s for s, _ in m.get("steps") or [[0, 1]]), default=0)))


def end_of(m):
    """Last moment the move changes the zoom, or None if it holds until the cut."""
    out = m.get("out", 0.8 if m["type"] == "push" else "cut")
    if out == "cut":
        return None
    top = m.get("t1", max([s for s, _ in m.get("steps") or []] + [m.get("t", 0)]))
    return top + m.get("hold", 0.4) + out


def frames(cfg, w, h, fps, dur):
    shots = sorted(cfg.get("shots") or [{"frame": 0}],
                   key=lambda s: s.get("frame", round(s.get("t", 0) * fps)))
    firsts = [s.get("frame", round(s.get("t", 0) * fps)) for s in shots]
    nframes = int(round(dur * fps)) + 1
    cuts = firsts[1:] + [nframes]
    moves = cfg.get("moves", [])
    for m in moves:
        n0 = round(start_of(m) * fps)
        cut = next((c for c in cuts if c > n0), nframes)
        m["_cut"] = cut
        end = end_of(m)
        if cut < nframes and (n0 > cut - fps or (end is not None and end * fps > cut - fps)):
            print(f"warning: {m['type']} at {start_of(m):.2f}s ({m.get('label', '')}) moves within 1 s "
                  f"of the cut at frame {cut}; hold it to the cut (\"out\": \"cut\") or drop it",
                  file=sys.stderr)
    cx = cfg.get("cx", 0.5)
    rows = []
    for n in range(nframes):
        t = n / fps
        i = max(k for k, f in enumerate(firsts) if f <= n)
        s = shots[i]
        base, cy = s.get("base", 1.0), s.get("cy", 0.42)
        env = max([1.0] + [envelope(m, t, n, m["_cut"]) for m in moves])
        z = base * env
        if z > MAX_ZOOM:
            print(f"warning: zoom {z:.3f} at {t:.2f}s capped to {MAX_ZOOM}", file=sys.stderr)
            z = MAX_ZOOM
        W, H = 2 * w, 2 * h  # zoompan works on the 2x upscale
        rows.append((n, round(z, 4), round(cx * (W - W / z)), round(cy * (H - H / z))))
    if cfg.get("loop"):
        # the clip wraps (loop-seam ran first): the end is not a cut, so it must be at rest and match the start
        first, last = shots[0], shots[-1]
        if (first.get("base", 1.0), first.get("cy", 0.42)) != (last.get("base", 1.0), last.get("cy", 0.42)):
            print("warning: loop clip: the first and last shots must share base and cy (the wrap would jump)", file=sys.stderr)
        rest_end = last.get("base", 1.0)
        if any(abs(z - rest_end) > 1e-3 for _, z, _, _ in rows[-int(fps):]):
            print("warning: loop clip: the zoom is not at rest in the last second (a held snap or a push running into the wrap)", file=sys.stderr)
        if any(abs(z - first.get("base", 1.0)) > 1e-3 for _, z, _, _ in rows[:int(0.3 * fps) + 1]):
            print("warning: loop clip: a move starts inside the first 0.3 s (the wrap would land on it)", file=sys.stderr)
    return rows


def tree(runs):
    """Balanced if(lt(on,k),a,b) lookup over [(first_frame, value)] runs."""
    if len(runs) == 1:
        return str(runs[0][1])
    mid = len(runs) // 2
    return f"if(lt(on\\,{runs[mid][0]})\\,{tree(runs[:mid])}\\,{tree(runs[mid:])})"


def runs_of(rows, col):
    out = []
    for r in rows:
        if not out or out[-1][1] != r[col]:
            out.append((r[0], r[col]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input"); ap.add_argument("output"); ap.add_argument("map")
    ap.add_argument("--crf", type=int, default=12)
    ap.add_argument("--dry-run", action="store_true", help="print the zoom curve, render nothing")
    a = ap.parse_args()
    w, h, fps, dur = probe(a.input)
    cfg = json.load(open(a.map))
    rows = frames(cfg, w, h, fps, dur)
    for m in cfg.get("moves", []):
        print(f"  {start_of(m):6.2f}s  {m['type']:5}  out={m.get('out', 0.8 if m['type'] == 'push' else 'cut')}  {m.get('label', '')}")
    if a.dry_run:
        for n, z, _, _ in rows[::max(1, round(fps / 4))]:
            print(f"{n / fps:6.2f}  {z:.3f}  " + "#" * round((z - 1) * 200))
        return
    filt = (f"[0:v]scale={2 * w}:{2 * h}:flags=lanczos,"
            f"zoompan=z='{tree(runs_of(rows, 1))}':x='{tree(runs_of(rows, 2))}':y='{tree(runs_of(rows, 3))}':"
            f"d=1:s={w}x{h}:fps={fps:.6f},format=yuv420p[v]")
    ftxt = a.output + ".filter.txt"
    open(ftxt, "w").write(filt)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", a.input, "-/filter_complex", ftxt,
                    "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-crf", str(a.crf),
                    "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "copy", "-map_metadata", "0",
                    "-metadata", "major_brand=", "-metadata", "minor_version=", "-metadata", "compatible_brands=", "-movflags", "+faststart+use_metadata_tags", a.output], check=True)
    print("wrote", a.output)


if __name__ == "__main__":
    main()
