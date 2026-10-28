import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_nutty_putty.py"
SPEC = importlib.util.spec_from_file_location("prepare_nutty_putty", SCRIPT)
BUILDER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BUILDER)


class NuttyPuttyPreparationTests(unittest.TestCase):
    def test_fixed_asset_inventory_matches_user_material_count(self):
        self.assertEqual(len(BUILDER.IMAGE_SOURCES), 28)
        self.assertEqual(len(BUILDER.PRESENTER_SOURCES), 4)
        self.assertEqual(len(BUILDER.STORY_EN), 26)
        self.assertEqual(len(BUILDER.STORY_AR), 26)

    def test_script_word_alignment_uses_reference_text_and_keeps_monotonic_time(self):
        tokens = BUILDER.tokenise_story(BUILDER.STORY_EN[:2])
        heard = []
        for index, token in enumerate(tokens):
            heard.append({
                "text": token["text"],
                "norm": token["norm"],
                "start_s": index * 0.22,
                "end_s": index * 0.22 + 0.18,
            })
        duration = len(heard) * 0.22 + 0.5
        ratio = BUILDER.align_tokens(tokens, heard, duration)
        self.assertAlmostEqual(ratio, 1.0)
        self.assertTrue(all(token["end_s"] > token["start_s"] for token in tokens))
        self.assertTrue(all(
            right["start_s"] >= left["start_s"]
            for left, right in zip(tokens, tokens[1:])
        ))
        self.assertTrue(all(token["end_s"] <= duration for token in tokens))

    def test_missing_asr_uses_explicit_estimated_timing(self):
        tokens = BUILDER.tokenise_story(BUILDER.STORY_EN[:1])
        ratio = BUILDER.align_tokens(tokens, [], 6.0)
        self.assertEqual(ratio, 0.0)
        self.assertTrue(all(token["timing_estimated"] for token in tokens))
        self.assertAlmostEqual(tokens[0]["start_s"], 0.0)
        self.assertGreater(tokens[-1]["end_s"], tokens[-1]["start_s"])

    def test_hyphenated_focus_phrase_matches_split_script_tokens(self):
        tokens = BUILDER.tokenise_story(["Twenty-seven hours upside down."])
        for index, token in enumerate(tokens):
            token["start_s"] = index * 0.4
            token["end_s"] = index * 0.4 + 0.3
        found = BUILDER.find_phrase(tokens, "TWENTY-SEVEN HOURS")
        self.assertIsNotNone(found)
        self.assertAlmostEqual(found[0], 0.0)

    def test_storyboard_boundaries_cover_all_images_and_duration(self):
        rows = [
            {"line_index": index, "start_s": round(index * 3.8, 3), "end_s": round(index * 3.8 + 3.0, 3)}
            for index in range(10)
        ]
        tokens = BUILDER.tokenise_story(BUILDER.STORY_EN[:10])
        for index, token in enumerate(tokens):
            token["start_s"] = index * 0.15
            token["end_s"] = index * 0.15 + 0.1
        boundaries = BUILDER.fit_storyboard_boundaries(rows, tokens, 39.0, 13, 2.0)
        self.assertEqual(len(boundaries), 14)
        self.assertAlmostEqual(boundaries[0], 0.0)
        self.assertAlmostEqual(boundaries[-1], 39.0)
        self.assertTrue(all(right > left for left, right in zip(boundaries, boundaries[1:])))

    def test_fact_callout_is_generated_only_for_a_matched_script_phrase(self):
        tokens = BUILDER.tokenise_story(["John was twenty-six years old."])
        for index, token in enumerate(tokens):
            token["start_s"] = index * 0.25
            token["end_s"] = index * 0.25 + 0.2
        old_project = BUILDER.PROJECT
        try:
            import tempfile
            with tempfile.TemporaryDirectory() as temporary:
                BUILDER.PROJECT = Path(temporary)
                overlays = BUILDER.make_fact_callouts(tokens, 5.0)
                self.assertEqual(len(overlays), 1)
                self.assertEqual(overlays[0]["label"], "26 YEARS OLD")
                image_path = Path(overlays[0]["path"])
                self.assertTrue(image_path.is_file())
                from PIL import Image
                with Image.open(image_path) as image:
                    self.assertEqual(image.size, (1920, 1080))
                    self.assertEqual(image.mode, "RGBA")
        finally:
            BUILDER.PROJECT = old_project

    def test_arabic_subtitles_use_sentence_timing_and_write_srt(self):
        rows = [
            {"start_s": index * 3.0, "end_s": index * 3.0 + 2.8}
            for index in range(len(BUILDER.STORY_AR))
        ]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "captions_ar.srt"
            cues = BUILDER.write_arabic_subtitles(path, rows)
            contents = path.read_text(encoding="utf-8-sig")
        self.assertTrue(path.is_file())
        self.assertGreater(len(cues), len(BUILDER.STORY_AR))
        self.assertIn("جون", contents)
        self.assertIn(" --> ", contents)
        self.assertTrue(all(item["end"] > item["start"] for item in cues))
        self.assertTrue(all(
            right["start"] >= left["end"] - 0.001
            for left, right in zip(cues, cues[1:])
        ))
        self.assertEqual(cues[0]["text"], "كهف نوتي بوتي —")

    def test_caption_chunks_never_exceed_three_words(self):
        tokens = BUILDER.tokenise_story(["One two three four five six seven."])
        for index, token in enumerate(tokens):
            token["start_s"] = index * 0.4
            token["end_s"] = index * 0.4 + 0.32
        # Use a temporary project root so the unit test never writes into the repository.
        old_project = BUILDER.PROJECT
        try:
            import tempfile
            with tempfile.TemporaryDirectory() as temporary:
                BUILDER.PROJECT = Path(temporary)
                cues = BUILDER.write_captions(tokens, ["One two three four five six seven."])
                self.assertGreaterEqual(len(cues), 2)
                self.assertTrue(all(len(cue["text"].split()) <= 3 for cue in cues))
        finally:
            BUILDER.PROJECT = old_project


if __name__ == "__main__":
    unittest.main()
