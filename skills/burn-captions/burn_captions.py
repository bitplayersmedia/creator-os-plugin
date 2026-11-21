#!/usr/bin/env python3
"""Burn TikTok/Reels-style captions into a vertical (9:16) video.

spoken mode: whisper word timings + the script card's text (the script's
spelling wins), 1-3 word chunks, karaoke highlight, CAPS words pop.
beats mode: the script's caption beats as cards spread over the video.

Stdlib only. Needs an ffmpeg built with libass (the `ass` filter) and, for
spoken mode, the whisper CLI on PATH. See SKILL.md.
"""
import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PLAY_W, PLAY_H = 1080, 1920
FONT_DIRS = ["/System/Library/Fonts/Supplemental", "/System/Library/Fonts", "/Library/Fonts",
             str(Path.home() / "Library/Fonts"), "/usr/share/fonts", str(Path.home() / ".fonts")]

DEFAULT_STYLE = {
    "font": "Arial Black",
    "fallback_font": "Impact",
    "highlight": "F2C230",   # warm yellow, RRGGBB
    "outline": 7,
    "shadow": 2,
    "size": 78,
    "position_y": 1350,      # caption centre line (lower middle, above the platform caption bar)
    "safe_left": 120,        # keep text within x 120..900 (right-side buttons)
    "safe_right": 900,
    "max_chars": 14,         # per caption line
    "max_words": 3,
    "hook_y": 380,
    "hook_size": 92,
    "hook_seconds": 2.2,
    "hook_box": "30000000",  # AABBGGRR box colour (alpha 30 = mostly opaque black)
    "primary": "FFFFFF",     # caption text colour, RRGGBB
    "outline_color": "000000",  # caption outline colour, RRGGBB
    "bold": 0,               # 1 = use the font's bold face (serif display fonts need it)
    "spacing": 0,            # letter spacing for captions (px at 1080x1920)
    "hook_primary": "FFFFFF",  # hook and beat text colour, RRGGBB
    "hook_spacing": 0,       # letter spacing for the hook and beats
    "hook_uppercase": False, # set the hook in capitals
    "caption_box": "",       # AABBGGRR: draw captions on a solid band (BorderStyle 4) instead of an outline
    "caption_box_pad": 16,   # band padding when caption_box is set
    "beats_y": 960,
    "beats_size": 80,
    "beats_chars": 18,
    "pop": 115,              # % scale for CAPS (stressed) words
    "uppercase": False,
}

PUNCT_BREAK = tuple(".,!?;:…—–")
GAP_CAP = 0.6


# ---------- script parsing ----------

def _field(md, label):
    m = re.search(r"\*\*" + label + r"[^*]*\*\*\s*(.*)", md, re.I)
    return m


def _unquote(s):
    s = s.strip()
    if len(s) >= 2 and s[0] in "\"“'" and s[-1] in "\"”'":
        s = s[1:-1]
    return s.strip()


def parse_hook(md):
    m = _field(md, r"On-screen text \(hook caption\):")
    return _unquote(m.group(1)) if m and m.group(1).strip() else None


def _strip_directions(text):
    return re.sub(r"\s+", " ", re.sub(r"\[[^\]]*\]", " ", text)).strip()


def parse_spoken(md):
    """The spoken script: the `> ` lines under **Script:** (or all `>` lines, or the whole file)."""
    lines = md.splitlines()
    out, started = [], False
    for line in lines:
        if not started:
            m = re.search(r"\*\*Script:?\*\*:?\s*(.*)", line)
            if m:
                started = True
                if m.group(1).strip():
                    out.append(_unquote(m.group(1)))
            continue
        s = line.strip()
        if s.startswith(">"):
            out.append(s.lstrip(">").strip())
        elif re.match(r"^(- \*\*|\*\*|#)", s):
            break
    if not out:
        quoted = [l.strip().lstrip(">").strip() for l in lines if l.strip().startswith(">")]
        out = quoted if quoted else [l for l in lines if not l.lstrip().startswith("#")]
    return _strip_directions(" ".join(x for x in out if x))


def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?…])\s+", text) if s.strip()]


def parse_beats(md):
    """Caption beats from a 'Caption beats' / 'Text beats' / 'Shots and captions' / 'Text cards' list;
    else the spoken script split into sentences."""
    lines = md.splitlines()
    beats, started, para = [], False, []
    head = re.compile(r"\*\*(Caption beats|Text beats|Shots and captions|Text cards)[^*]*\*\*", re.I)
    for line in lines:
        s = line.strip()
        if not started:
            if head.search(s):
                started = True
            continue
        if s.startswith(">"):
            body = s.lstrip(">").strip()
            if body:
                para.append(body)
            elif para:
                beats.append(" ".join(para)); para = []
            continue
        if para:
            beats.append(" ".join(para)); para = []
        if re.match(r"^(- \*\*|\*\*|#)", s):
            break
        m = re.match(r"^(\d+[.)]|[-*])\s+(.*)", s)
        if m:
            item = m.group(2)
            q = re.findall(r"\"([^\"]+)\"|“([^”]+)”", item)
            beats.append(_unquote(q[-1][0] or q[-1][1]) if q else item.strip())
    if para:
        beats.append(" ".join(para))
    beats = [_strip_directions(_unquote(b)) for b in beats if b.strip()]
    return beats or split_sentences(parse_spoken(md))


def script_from_json(data):
    """A Creator OS script object ({hook, lines: [...], ...}) -> spoken text, hook, beats.
    The spoken text is the lines joined; each line is one caption beat."""
    if not isinstance(data, dict) or not isinstance(data.get("lines"), list):
        raise ValueError("a script .json needs a `lines` list (the job's script object)")
    lines = [_strip_directions(str(x)) for x in data["lines"]]
    lines = [x for x in lines if x]
    hook = data.get("hook")
    hook = _strip_directions(str(hook)) if hook else None
    return {"spoken": " ".join(lines), "hook": hook or None, "beats": lines}


def script_from_text(md):
    return {"spoken": parse_spoken(md), "hook": parse_hook(md), "beats": parse_beats(md)}


def load_script(path):
    """Read --script: a .json script object, or a script card (.md) / plain text."""
    text = Path(path).read_text()
    if Path(path).suffix.lower() == ".json":
        return script_from_json(json.loads(text))
    return script_from_text(text)


# ---------- words and alignment ----------

def norm(word):
    return re.sub(r"[^a-z0-9]", "", word.lower())


def tokenize(text):
    """Script text -> display tokens; punctuation-only tokens stick to the previous word."""
    raw = []
    for t in text.split():
        raw.extend(p for p in re.split(r"(?<=[—–])(?=\w)", t) if p)
    toks = []
    for t in raw:
        if not norm(t) and toks:
            toks[-1] += t
        elif norm(t):
            toks.append(t)
    return toks


def is_stressed(word):
    letters = re.sub(r"[^A-Za-z]", "", word)
    return len(letters) >= 2 and letters.isupper()


def whisper_words(data):
    out = []
    for seg in data.get("segments", []):
        for w in seg.get("words", []) or []:
            if norm(w.get("word", "")):
                out.append({"word": w["word"].strip(), "start": float(w["start"]), "end": float(w["end"])})
    return out


def align(script_tokens, wwords, duration=None):
    """Give each script token whisper times. Returns (words, stats).
    words: [{text, start, end, how}] where how is matched|fuzzy|interpolated."""
    a = [norm(t) for t in script_tokens]
    b = [norm(w["word"]) for w in wwords]
    words = [{"text": t, "start": None, "end": None, "how": None} for t in script_tokens]
    extra = 0
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            for k in range(i2 - i1):
                w = wwords[j1 + k]
                words[i1 + k].update(start=w["start"], end=w["end"], how="matched")
        elif op == "replace":
            # script words heard differently: spread the heard span over them by length
            s, e = wwords[j1]["start"], wwords[j2 - 1]["end"]
            lens = [max(1, len(a[i])) for i in range(i1, i2)]
            tot, acc = sum(lens), 0
            for k, i in enumerate(range(i1, i2)):
                ws = s + (e - s) * acc / tot
                acc += lens[k]
                words[i].update(start=ws, end=s + (e - s) * acc / tot, how="fuzzy")
        elif op == "insert":
            extra += j2 - j1
    # interpolate script words whisper did not hear
    n = len(words)
    i = 0
    while i < n:
        if words[i]["start"] is not None:
            i += 1
            continue
        j = i
        while j < n and words[j]["start"] is None:
            j += 1
        prev_end = words[i - 1]["end"] if i > 0 else None
        next_start = words[j]["start"] if j < n else None
        if prev_end is None and next_start is None:
            prev_end, next_start = 0.0, 0.4 * (j - i)
        elif prev_end is None:
            prev_end = max(0.0, next_start - 0.3 * (j - i))
        elif next_start is None:
            next_start = prev_end + 0.3 * (j - i)
            if duration:
                next_start = min(next_start, max(prev_end, duration))
        step = (next_start - prev_end) / (j - i)
        for k in range(i, j):
            words[k].update(start=prev_end + step * (k - i), end=prev_end + step * (k - i + 1), how="interpolated")
        i = j
    stats = {h: sum(1 for w in words if w["how"] == h) for h in ("matched", "fuzzy", "interpolated")}
    stats["script_words"] = n
    stats["whisper_words"] = len(wwords)
    stats["whisper_extra"] = extra
    return words, stats


def caption_match(stats):
    """0 to 1: the share of script words whisper heard exactly (the figure for qc.captionMatch)."""
    return stats["matched"] / stats["script_words"] if stats["script_words"] else 0.0


# ---------- chunking ----------

def chunk_words(words, max_words=3, max_chars=14, gap=GAP_CAP):
    chunks, cur = [], []
    for w in words:
        if cur:
            text = " ".join(x["text"] for x in cur + [w])
            if len(cur) >= max_words or len(text) > max_chars or w["start"] - cur[-1]["end"] > gap:
                chunks.append(cur); cur = []
        cur.append(w)
        if w["text"].endswith(PUNCT_BREAK) or w["text"].rstrip("\"”'’)").endswith(PUNCT_BREAK):
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    out = []
    for k, c in enumerate(chunks):
        start = c[0]["start"]
        last_end = max(w["end"] for w in c)
        end = last_end + gap
        if k + 1 < len(chunks):
            end = min(end, chunks[k + 1][0]["start"])
        end = max(end, start + 0.12)
        out.append({"words": c, "start": start, "end": end})
    return out


# ---------- ASS ----------

def ass_time(t):
    cs = int(round(max(0.0, t) * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def ass_color(hexrgb, alpha="00"):
    h = hexrgb.lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        raise ValueError(f"colour must be RRGGBB, got {hexrgb!r}")
    return f"&H{alpha}{h[4:6]}{h[2:4]}{h[0:2]}&".upper()


def ass_text(s):
    return s.replace("\\", "/").replace("{", "(").replace("}", ")")


def est_width(text, size):
    """Rough rendered width for Arial Black / Impact. libass sizes a font by its line height
    (about 1.4 em for Arial Black), so per-char em widths are scaled by 0.75."""
    w = 0.0
    for ch in text:
        if ch == " ":
            w += 0.3
        elif ch.isupper():
            w += 0.8
        elif ch.isdigit():
            w += 0.68
        elif ch.isalpha():
            w += 0.64
        else:
            w += 0.34
    return w * size * 0.75


def fit_size(lines, size, width):
    widest = max(est_width(l, 1) for l in lines) if lines else 1
    return max(28, min(size, int(width / widest))) if widest else size


def wrap(text, max_chars):
    lines, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > max_chars:
            lines.append(cur); cur = word
        else:
            cur = f"{cur} {word}".strip()
    if cur:
        lines.append(cur)
    return lines


def wrap_two(text, one_line_max=18):
    """Hook: one line if short, else the most balanced two-line split."""
    words = text.split()
    if len(text) <= one_line_max or len(words) < 2:
        return [text]
    best = min(range(1, len(words)),
               key=lambda k: max(len(" ".join(words[:k])), len(" ".join(words[k:]))))
    return [" ".join(words[:best]), " ".join(words[best:])]


def find_font(name):
    if not name:
        return False
    target = name.lower().replace(" ", "")
    for d in FONT_DIRS:
        if os.path.isdir(d):
            for f in os.listdir(d):
                if Path(f).stem.lower().replace(" ", "") == target:
                    return True
    return False


def resolve_font(style):
    for name in (style.get("font"), style.get("fallback_font")):
        if find_font(name):
            return name
    return style.get("font") or "Arial Black"


def ass_header(style, font):
    hl = ass_color(style["highlight"])
    box = "&H" + style["hook_box"].upper() + "&"
    prim = ass_color(style["primary"])
    oc = ass_color(style["outline_color"])
    hprim = ass_color(style["hook_primary"])
    bold = -1 if style.get("bold") else 0
    if style.get("caption_box"):
        cb_style, cb_outline = 4, style["caption_box_pad"]
        cb_back = "&H" + style["caption_box"].upper() + "&"
    else:
        cb_style, cb_outline, cb_back = 1, style["outline"], "&H80000000&"
    return "\n".join([
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {PLAY_W}",
        f"PlayResY: {PLAY_H}",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: TV.709",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Caption,{font},{style['size']},{prim},{hl},{oc},{cb_back},"
        f"{bold},0,0,0,100,100,{style['spacing']},0,{cb_style},{cb_outline},{style['shadow']},5,"
        f"{style['safe_left']},{PLAY_W - style['safe_right']},0,1",
        # BorderStyle 4 (libass >= 0.17): one box behind the whole event, in BackColour
        f"Style: Hook,{font},{style['hook_size']},{hprim},{hl},&HFF000000&,{box},"
        f"{bold},0,0,0,100,100,{style['hook_spacing']},0,4,18,0,5,70,70,0,1",
        f"Style: Beat,{font},{style['beats_size']},{hprim},{hl},&HFF000000&,{box},"
        f"{bold},0,0,0,100,100,{style['hook_spacing']},0,4,18,0,5,"
        f"{style['safe_left']},{PLAY_W - style['safe_right']},0,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ])


def _event(layer, start, end, style_name, text):
    return f"Dialogue: {layer},{ass_time(start)},{ass_time(end)},{style_name},,0,0,0,,{text}"


def caption_events(chunks, style):
    """One event per (chunk, active word): the spoken word in the highlight colour, CAPS words pop."""
    hl = ass_color(style["highlight"])
    white = ass_color(style["primary"])
    x = (style["safe_left"] + style["safe_right"]) // 2
    y = style["position_y"]
    width = style["safe_right"] - style["safe_left"]
    pop = style["pop"]
    events = []
    for ch in chunks:
        ws = ch["words"]
        texts = [w["text"].upper() if style.get("uppercase") else w["text"] for w in ws]
        stressed = [is_stressed(w["text"]) for w in ws]
        # fit the line, allowing for the pop on stressed words
        line_w = sum(est_width(t, 1) * (pop / 100 if s else 1) for t, s in zip(texts, stressed))
        line_w += est_width(" ", 1) * (len(texts) - 1)
        size = max(28, min(style["size"], int(width / line_w))) if line_w else style["size"]
        for i, w in enumerate(ws):
            start = ch["start"] if i == 0 else max(ch["start"], w["start"])
            end = ws[i + 1]["start"] if i + 1 < len(ws) else ch["end"]
            end = min(max(end, start), ch["end"])
            if int(round(end * 100)) <= int(round(start * 100)):
                continue
            parts = []
            for k, t in enumerate(texts):
                if k == i:
                    tag = f"\\c{hl}"
                    if stressed[k]:
                        tag += f"\\fscx100\\fscy100\\t(0,90,\\fscx{pop + 6}\\fscy{pop + 6})\\t(90,200,\\fscx{pop}\\fscy{pop})"
                    parts.append("{" + tag + "}" + ass_text(t) + "{\\c" + white + "\\fscx100\\fscy100}")
                else:
                    parts.append(ass_text(t))
            prefix = f"{{\\an5\\pos({x},{y})" + (f"\\fs{size}" if size != style["size"] else "") + "}"
            events.append(_event(1, start, end, "Caption", prefix + " ".join(parts)))
    return events


def hook_event(hook, style, start=0.0):
    lines = wrap_two(hook.upper() if style.get("hook_uppercase") else hook)
    size = fit_size(lines, style["hook_size"], PLAY_W - 140)
    text = "\\N".join(ass_text(l) for l in lines)
    return _event(2, start, start + style["hook_seconds"], "Hook",
                  f"{{\\an5\\pos({PLAY_W // 2},{style['hook_y']})\\fs{size}\\fad(120,200)}}{text}")


def beat_events(beats, duration, style, y=None):
    y = style["beats_y"] if y is None else y
    x = (style["safe_left"] + style["safe_right"]) // 2
    width = style["safe_right"] - style["safe_left"]
    hl = ass_color(style["highlight"])
    events = []
    n = len(beats)
    for i, b in enumerate(beats):
        lines = wrap(b, style["beats_chars"])
        size = fit_size(lines, style["beats_size"], width)
        out = []
        for line in lines:
            ws = [("{\\c" + hl + "}" + ass_text(w) + "{\\c&H00FFFFFF&}") if is_stressed(w) else ass_text(w)
                  for w in line.split()]
            out.append(" ".join(ws))
        start, end = duration * i / n, duration * (i + 1) / n
        events.append(_event(1, start, end, "Beat",
                             f"{{\\an5\\pos({x},{y})\\fs{size}\\fad(150,150)}}" + "\\N".join(out)))
    return events


def build_ass(style, font, events):
    return ass_header(style, font) + "\n" + "\n".join(events) + "\n"


# ---------- tools ----------

def die(msg):
    print(f"burn-captions: {msg}", file=sys.stderr)
    sys.exit(1)


LIBASS_HINT = ("An ffmpeg built with libass (it has the `ass` filter) is needed. Some packages ship ffmpeg "
               "without it. Point FFMPEG_FULL at one that has it; on macOS with Homebrew: "
               "`brew install ffmpeg-full`, then "
               "FFMPEG_FULL=\"$(brew --prefix ffmpeg-full)/bin/ffmpeg\".")


def resolve_ffmpeg(env=None, which=shutil.which):
    """Which ffmpeg to use: FFMPEG_FULL when set, else `ffmpeg` on PATH. Returns (path or None, source)."""
    env = os.environ if env is None else env
    chosen = env.get("FFMPEG_FULL")
    if chosen:
        return chosen, "FFMPEG_FULL"
    return which("ffmpeg"), "PATH"


def has_ass_filter(filters_output):
    return bool(re.search(r"^\s*\S+\s+ass\s", filters_output, re.M))


def supports_ass(path):
    if not path or not (os.path.isfile(path) and os.access(path, os.X_OK)):
        return False
    try:
        filters = subprocess.run([path, "-hide_banner", "-filters"], capture_output=True, text=True)
    except OSError:
        return False
    return filters.returncode == 0 and has_ass_filter(filters.stdout)


def homebrew_ffmpeg():
    if sys.platform != "darwin" or not shutil.which("brew"):
        return None
    try:
        prefix = subprocess.run(["brew", "--prefix", "ffmpeg-full"], capture_output=True, text=True)
    except OSError:
        return None
    if prefix.returncode == 0 and prefix.stdout.strip():
        return str(Path(prefix.stdout.strip()) / "bin" / "ffmpeg")
    return None


def ffmpeg_full():
    path, source = resolve_ffmpeg()
    if supports_ass(path):
        return path
    if source == "PATH":
        candidate = homebrew_ffmpeg()
        if supports_ass(candidate):
            return candidate
    problem = f"{path} (from {source}) has no usable ass filter or is not executable." if path else "ffmpeg was not found."
    die(problem + " " + LIBASS_HINT)


def ffprobe_for(ffmpeg):
    p = Path(ffmpeg).with_name("ffprobe")
    return str(p) if p.exists() else (shutil.which("ffprobe") or die("ffprobe not found"))


def probe(ffprobe, video):
    r = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height",
                        "-of", "json", str(video)], capture_output=True, text=True)
    if r.returncode:
        die(f"ffprobe failed on {video}: {r.stderr.strip()}")
    d = json.loads(r.stdout)
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), None)
    if not v:
        die(f"{video} has no video stream")
    return {"duration": float(d["format"]["duration"]), "width": v["width"], "height": v["height"],
            "audio": any(s.get("codec_type") == "audio" for s in d["streams"])}


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        die(f"command failed: {' '.join(map(str, cmd))}\n{r.stderr[-2000:]}")
    return r


def transcribe(ffmpeg, video, work, model):
    wav = work / "audio.wav"
    js = work / "audio.json"
    if js.exists() and js.stat().st_mtime > Path(video).stat().st_mtime:
        print(f"  reusing whisper transcript {js}")
        return json.loads(js.read_text())
    whisper = shutil.which("whisper") or die(
        "whisper CLI not found on PATH. Install the openai-whisper CLI (pip install openai-whisper, "
        "or your package manager) and make sure `whisper` runs.")
    run([ffmpeg, "-y", "-hide_banner", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(wav)])
    print(f"  whisper {model} (the first run downloads the model)")
    run([whisper, str(wav), "--model", model, "--language", "en", "--word_timestamps", "True",
         "--output_format", "json", "--output_dir", str(work), "--fp16", "False", "--verbose", "False"])
    return json.loads(js.read_text())


def to_rrggbb(value):
    """A colour as hex (#RGB, #RRGGBB, RRGGBB, CSS #RRGGBBAA) or ASS (&HBBGGRR& / &HAABBGGRR&) -> RRGGBB."""
    s = str(value).strip()
    m = re.fullmatch(r"&H([0-9a-fA-F]{6}|[0-9a-fA-F]{8})&?", s, re.I)
    if m:
        bgr = m.group(1)[-6:]
        return (bgr[4:6] + bgr[2:4] + bgr[0:2]).upper()
    h = s.lstrip("#")
    if re.fullmatch(r"[0-9a-fA-F]{3}", h):
        h = "".join(c * 2 for c in h)
    if re.fullmatch(r"[0-9a-fA-F]{8}", h):
        h = h[:6]
    if not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        raise ValueError(f"colour must be hex or ASS, got {value!r}")
    return h.upper()


def to_aabbggrr(value):
    """A caption box colour (CaptionStyle `box`; '' means no box) -> AABBGGRR for ASS. Opaque enough to read on."""
    s = str(value).strip()
    if not s:
        return ""
    m = re.fullmatch(r"&H([0-9a-fA-F]{8})&?", s, re.I)
    if m:
        return m.group(1).upper()
    h = s.lstrip("#")
    alpha = "30"
    if re.fullmatch(r"[0-9a-fA-F]{8}", h) and not s.upper().startswith("&H"):
        alpha = f"{255 - int(h[6:8], 16):02X}"  # CSS #RRGGBBAA: AA is opacity, ASS alpha is transparency
    rgb = to_rrggbb(s)
    return alpha + rgb[4:6] + rgb[2:4] + rgb[0:2]


# CaptionStyle (src/shared/kit.ts) key -> this script's style key, for the names that differ
CAPTION_STYLE_KEYS = {"positionY": "position_y", "hookSeconds": "hook_seconds", "maxWords": "max_words"}


def style_overrides(data):
    """Style keys from a style JSON: a Creator OS CaptionStyle ({font, size, primary, outline (a colour),
    highlight, box, positionY, hookSeconds, uppercase, maxWords}), a kit with a `captions` block, or
    this script's own keys."""
    if "captions" in data:
        data = data["captions"]
    elif "persona" in data:
        return {}  # a persona kit without a captions block: defaults
    out = {k: v for k, v in data.items() if k in DEFAULT_STYLE}
    for src, dst in CAPTION_STYLE_KEYS.items():
        if src in data:
            out[dst] = data[src]
    if isinstance(data.get("outline"), str):  # CaptionStyle: outline is the outline colour
        out["outline_color"] = data["outline"]
        del out["outline"]
    if "box" in data:
        out["caption_box"] = to_aabbggrr(data["box"])
    return out


def load_style(path):
    style = dict(DEFAULT_STYLE)
    if path:
        data = json.loads(Path(path).read_text())
        if not isinstance(data, dict):
            raise ValueError("a style .json must hold one object")
        style.update(style_overrides(data))
    for key in ("highlight", "primary", "outline_color", "hook_primary"):
        style[key] = to_rrggbb(style[key])
    for key in ("size", "position_y", "max_words"):
        style[key] = int(round(float(style[key])))
    style["hook_seconds"] = float(style["hook_seconds"])
    style["uppercase"] = bool(style["uppercase"])
    return style


def main(argv=None):
    ap = argparse.ArgumentParser(description="Burn TikTok/Reels-style captions into a 9:16 video.")
    ap.add_argument("--video", required=True)
    ap.add_argument("--script", required=True,
                    help="the job's script object (.json with `hook` and `lines`), or a script card (.md) / plain text")
    ap.add_argument("--out", required=True)
    ap.add_argument("--style", help="a CaptionStyle .json (the job's captionStyle), or a kit with a `captions` key")
    ap.add_argument("--hook", help="hook title text (default: the script's hook)")
    ap.add_argument("--no-hook", action="store_true", help="no hook title even if the card has one")
    ap.add_argument("--mode", choices=["spoken", "beats"], default="spoken")
    ap.add_argument("--beats-y", type=int, help="beats card centre y (960 middle, 640 top third)")
    ap.add_argument("--model", default="small.en", help="whisper model (default small.en)")
    ap.add_argument("--keep-work", action="store_true", help="keep the temp work folder and print where it is")
    args = ap.parse_args(argv)

    video, out = Path(args.video).resolve(), Path(args.out).resolve()
    if not video.exists():
        die(f"no such video: {video}")
    try:
        script = load_script(args.script)
        style = load_style(args.style)
    except (ValueError, OSError) as e:
        die(f"cannot read --script / --style: {e}")
    font = resolve_font(style)
    ffmpeg = ffmpeg_full()
    info = probe(ffprobe_for(ffmpeg), video)
    if abs(info["width"] / info["height"] - 9 / 16) > 0.02:
        print(f"  warning: {info['width']}x{info['height']} is not 9:16; captions are laid out for 9:16")
    work = Path(tempfile.mkdtemp(prefix="burn-captions-"))
    try:
        render(args, script, style, font, ffmpeg, info, video, out, work)
    finally:
        if args.keep_work:
            print(f"  work files: {work}")
        else:
            shutil.rmtree(work, ignore_errors=True)


def render(args, script, style, font, ffmpeg, info, video, out, work):
    hook = None if args.no_hook else (args.hook or script["hook"])
    events, report = [], []
    if args.mode == "spoken":
        if not info["audio"]:
            die("video has no audio track; use --mode beats for silent clips")
        tokens = tokenize(script["spoken"])
        if not tokens:
            die("no spoken script found (a .json script needs `lines`; a card needs `> ` lines under **Script:**)")
        words, st = align(tokens, whisper_words(transcribe(ffmpeg, video, work, args.model)), info["duration"])
        chunks = chunk_words(words, style["max_words"], style["max_chars"])
        chunks[-1]["end"] = max(chunks[-1]["start"] + 0.12, min(chunks[-1]["end"], info["duration"]))
        events += caption_events(chunks, style)
        report += [f"script words: {st['script_words']}, whisper words: {st['whisper_words']}",
                   f"matched: {st['matched']}, fuzzy (heard differently): {st['fuzzy']}, "
                   f"unmatched/interpolated: {st['interpolated']}, heard but not in script: {st['whisper_extra']}",
                   f"chunks: {len(chunks)}"]
        report.append(f"caption match: {caption_match(st):.2f} (matched / script words; the job's qc.captionMatch)")
        if caption_match(st) < 0.6:
            report.append("WARNING: under 60% of the script matched the audio. Is this the right script? "
                          "Captions must not show words that are not in the audio; check before posting.")
    else:
        beats = script["beats"]
        if not beats:
            die("no caption beats found in the script")
        if hook and norm(hook) == norm(beats[0]):
            hook = None  # the first beat already is the hook
        events += beat_events(beats, info["duration"], style, args.beats_y)
        report.append(f"beats: {len(beats)} over {info['duration']:.1f}s ({info['duration'] / len(beats):.1f}s each)")
    if hook and style["hook_seconds"] > 0:
        events.append(hook_event(hook, style))
        report.append(f"hook: {hook!r} for {style['hook_seconds']}s")

    ass = work / "captions.ass"
    ass.write_text(build_ass(style, font, events))
    # libass finds system fonts through CoreText; the work dir is cwd so the filter path needs no escaping
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(video), "-vf", "ass=captions.ass",
           "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
           "-c:a", "copy", "-map_metadata", "0", "-metadata", "major_brand=", "-metadata", "minor_version=", "-metadata", "compatible_brands=", "-movflags", "+faststart+use_metadata_tags", str(out)]
    out.parent.mkdir(parents=True, exist_ok=True)
    run(cmd, cwd=work)

    print(f"burn-captions ({args.mode}, font {font}, {info['width']}x{info['height']})")
    for line in report:
        print("  " + line)
    print(f"  output: {out}")


if __name__ == "__main__":
    main()
