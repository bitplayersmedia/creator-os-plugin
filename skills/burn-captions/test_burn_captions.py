"""Run: python3 plugin/skills/burn-captions/test_burn_captions.py"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import burn_captions as bc  # noqa: E402

CARD = """# Joint and several

- **Format:** Off-camera interview.
- **On-screen text (hook caption):** "Moving into a flat-share? Find out who pays."
- **Script:**
  > Moving into a flat-share? Find out who pays. Not your share. ALL of it.
- **Gesture:** sets two fingers down.
"""

BEATS_CARD = """# Dirt

- **On-screen text (hook caption):** "One hour of dirt."
- **Shots and captions:**
  1. Wide: a gardener bent over a raised bed. "One hour of dirt."
  2. Medium: the gardener by the "cane" wigwams. "No notifications out here."
- **Length:** 2 captions.
"""

CARDS = """**Text cards (in order):**

> Things nobody tells you at 25.
>
> Boring is not the same as poor.

- **Length:** ~55 words
"""


def W(word, s, e):
    return {"word": word, "start": s, "end": e}


class Parse(unittest.TestCase):
    def test_spoken_and_hook(self):
        self.assertEqual(bc.parse_spoken(CARD), "Moving into a flat-share? Find out who pays. Not your share. ALL of it.")
        self.assertEqual(bc.parse_hook(CARD), "Moving into a flat-share? Find out who pays.")

    def test_beats_from_shots(self):
        self.assertEqual(bc.parse_beats(BEATS_CARD), ["One hour of dirt.", "No notifications out here."])

    def test_beats_from_blockquote_cards(self):
        self.assertEqual(bc.parse_beats(CARDS), ["Things nobody tells you at 25.", "Boring is not the same as poor."])

    def test_beats_fallback_sentences(self):
        self.assertEqual(bc.parse_beats(CARD)[:2], ["Moving into a flat-share?", "Find out who pays."])

    def test_tokenize_keeps_punctuation(self):
        self.assertEqual(bc.tokenize("Wait — what? ALL of it."), ["Wait—", "what?", "ALL", "of", "it."])


class Align(unittest.TestCase):
    def test_script_spelling_wins_and_gaps_interpolate(self):
        toks = bc.tokenize("Not your share. ALL of it.")
        heard = [W(" not", 0.0, 0.2), W(" your", 0.2, 0.4), W(" share.", 0.4, 0.8),
                 W(" all", 1.0, 1.2), W(" it", 1.6, 1.8)]
        words, st = bc.align(toks, heard)
        self.assertEqual([w["text"] for w in words], toks)
        self.assertEqual(st["matched"], 5)
        self.assertEqual(st["interpolated"], 1)
        of = words[4]
        self.assertEqual(of["how"], "interpolated")
        self.assertAlmostEqual(of["start"], 1.2)
        self.assertAlmostEqual(of["end"], 1.6)

    def test_fuzzy_split_word(self):
        words, st = bc.align(["flat-share?"], [W("flat", 0.0, 0.3), W("chair", 0.3, 0.6)])
        self.assertEqual(st["fuzzy"], 1)
        self.assertEqual((words[0]["start"], words[0]["end"]), (0.0, 0.6))


class Chunk(unittest.TestCase):
    def words(self, text, step=0.3):
        return [{"text": t, "start": i * step, "end": i * step + step, "how": "matched"}
                for i, t in enumerate(text.split())]

    def test_breaks_at_punctuation_and_limits(self):
        chunks = bc.chunk_words(self.words("Say it's the cellist. Lovely girl, gone by March."))
        texts = [" ".join(w["text"] for w in c["words"]) for c in chunks]
        self.assertEqual(texts, ["Say it's the", "cellist.", "Lovely girl,", "gone by March."])
        for t in texts:
            self.assertLessEqual(len(t.split()), 3)

    def test_chunk_end_caps_gap(self):
        ws = self.words("Slowly. Quite")
        ws[1]["start"], ws[1]["end"] = 5.0, 5.3
        chunks = bc.chunk_words(ws)
        self.assertAlmostEqual(chunks[0]["end"], 0.3 + 0.6)
        self.assertAlmostEqual(chunks[0]["start"], 0.0)


class Ass(unittest.TestCase):
    def test_time_and_colour(self):
        self.assertEqual(bc.ass_time(3725.456), "1:02:05.46")
        self.assertEqual(bc.ass_color("#F2C230"), "&H0030C2F2&")

    def test_caption_events_highlight_and_pop(self):
        style = dict(bc.DEFAULT_STYLE)
        ws = [{"text": "ALL", "start": 0.0, "end": 0.4, "how": "matched"},
              {"text": "of", "start": 0.4, "end": 0.6, "how": "matched"},
              {"text": "it.", "start": 0.6, "end": 1.0, "how": "matched"}]
        ev = bc.caption_events(bc.chunk_words(ws), style)
        self.assertEqual(len(ev), 3)
        self.assertIn("Dialogue: 1,0:00:00.00,0:00:00.40,Caption", ev[0])
        self.assertIn("{\\c&H0030C2F2&\\fscx100\\fscy100\\t(", ev[0])  # active CAPS word pops
        self.assertIn("\\fscx115", ev[0])
        self.assertIn("{\\c&H0030C2F2&}of", ev[1])
        self.assertIn("\\pos(510,1350)", ev[0])
        self.assertTrue(ev[2].split(",")[2] == "0:00:01.60")  # last word holds 0.6 s

    def test_build_ass_and_hook(self):
        style = dict(bc.DEFAULT_STYLE)
        doc = bc.build_ass(style, "Arial Black", [bc.hook_event("Moving into a flat-share? Find out who pays.", style)])
        self.assertIn("PlayResX: 1080", doc)
        self.assertIn("PlayResY: 1920", doc)
        self.assertIn("Style: Hook,Arial Black", doc)
        self.assertIn(",4,18,0,5,", doc)  # one box behind the hook
        self.assertIn("Dialogue: 2,0:00:00.00,0:00:02.20,Hook", doc)
        self.assertEqual(doc.count("\\N"), 1)  # two lines

    def test_beats_spread_evenly(self):
        ev = bc.beat_events(["One.", "Two.", "Three."], 9.0, dict(bc.DEFAULT_STYLE))
        self.assertIn("0:00:03.00,0:00:06.00,Beat", ev[1])


SCRIPT_JSON = {
    "hook": "Moving into a flat-share? Find out who pays.",
    "setting": "a kitchen",
    "lines": ["Moving into a flat-share?", "Find out who pays. [beat]", "Not your share. ALL of it."],
    "guardrail": "no legal advice",
}

CAPTION_STYLE = {
    "font": "Impact", "size": 90, "primary": "#FFFFFF", "outline": "#101010", "highlight": "#00FF88",
    "box": "", "positionY": 1400, "hookSeconds": 3, "uppercase": True, "maxWords": 2,
}


class JsonInputs(unittest.TestCase):
    def test_script_json_lines_and_hook(self):
        s = bc.script_from_json(SCRIPT_JSON)
        self.assertEqual(s["spoken"], "Moving into a flat-share? Find out who pays. Not your share. ALL of it.")
        self.assertEqual(s["hook"], SCRIPT_JSON["hook"])
        self.assertEqual(s["beats"], ["Moving into a flat-share?", "Find out who pays.", "Not your share. ALL of it."])

    def test_script_json_needs_lines(self):
        with self.assertRaises(ValueError):
            bc.script_from_json({"hook": "x"})

    def test_load_script_by_extension(self):
        with tempfile.TemporaryDirectory() as d:
            j, m = Path(d, "script.json"), Path(d, "card.md")
            j.write_text(json.dumps(SCRIPT_JSON))
            m.write_text(CARD)
            self.assertEqual(bc.load_script(j)["hook"], SCRIPT_JSON["hook"])
            self.assertEqual(bc.load_script(m)["spoken"], bc.parse_spoken(CARD))
            self.assertEqual(bc.load_script(m)["hook"], bc.parse_hook(CARD))

    def test_caption_style_maps_onto_script_style(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d, "style.json")
            p.write_text(json.dumps(CAPTION_STYLE))
            st = bc.load_style(p)
        self.assertEqual(st["font"], "Impact")
        self.assertEqual(st["size"], 90)
        self.assertEqual(st["primary"], "FFFFFF")
        self.assertEqual(st["outline_color"], "101010")
        self.assertEqual(st["outline"], bc.DEFAULT_STYLE["outline"])  # the width is untouched
        self.assertEqual(st["highlight"], "00FF88")
        self.assertEqual(st["caption_box"], "")
        self.assertEqual(st["position_y"], 1400)
        self.assertEqual(st["hook_seconds"], 3.0)
        self.assertTrue(st["uppercase"])
        self.assertEqual(st["max_words"], 2)

    def test_caption_style_box_and_ass_colours(self):
        data = dict(CAPTION_STYLE, box="#112233", highlight="&H0030C2F2&")
        st = bc.style_overrides(data)
        self.assertEqual(st["caption_box"], "30332211")  # AABBGGRR
        self.assertEqual(bc.to_rrggbb(st["highlight"]), "F2C230")
        self.assertEqual(bc.to_rrggbb("#fc0"), "FFCC00")
        with self.assertRaises(ValueError):
            bc.to_rrggbb("gold")

    def test_old_formats_still_load(self):
        kit = {"persona": "x", "captions": {"highlight": "#F2C230", "outline": 5, "position_y": 1300}}
        st = bc.style_overrides(kit)
        self.assertEqual(st, {"highlight": "#F2C230", "outline": 5, "position_y": 1300})
        self.assertEqual(bc.style_overrides({"persona": "x"}), {})
        self.assertEqual(bc.style_overrides({"size": 60, "max_words": 2}), {"size": 60, "max_words": 2})

    def test_hook_seconds_and_max_words_reach_the_events(self):
        st = dict(bc.DEFAULT_STYLE, hook_seconds=3.0)
        self.assertIn("0:00:03.00,Hook", bc.hook_event("Hi there", st))


class FfmpegLookup(unittest.TestCase):
    def test_ffmpeg_full_wins(self):
        which = lambda name: "/usr/bin/ffmpeg"
        self.assertEqual(bc.resolve_ffmpeg({"FFMPEG_FULL": "/opt/x/ffmpeg"}, which), ("/opt/x/ffmpeg", "FFMPEG_FULL"))

    def test_path_when_unset_or_empty(self):
        which = lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else None
        self.assertEqual(bc.resolve_ffmpeg({}, which), ("/usr/bin/ffmpeg", "PATH"))
        self.assertEqual(bc.resolve_ffmpeg({"FFMPEG_FULL": ""}, which), ("/usr/bin/ffmpeg", "PATH"))

    def test_none_when_missing(self):
        self.assertEqual(bc.resolve_ffmpeg({}, lambda name: None), (None, "PATH"))

    def test_ass_filter_detection(self):
        self.assertTrue(bc.has_ass_filter(" T.. ass               V->V       Render ASS subtitles\n"))
        self.assertFalse(bc.has_ass_filter(" T.. assume            V->V       something else\n"))

    def test_caption_match_figure(self):
        self.assertAlmostEqual(bc.caption_match({"matched": 9, "script_words": 10}), 0.9)
        self.assertEqual(bc.caption_match({"matched": 0, "script_words": 0}), 0.0)


if __name__ == "__main__":
    unittest.main()
