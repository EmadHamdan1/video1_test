from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_bendia_cut as edit


class BendiaCutTests(unittest.TestCase):
    def test_uses_only_original_story_sources(self) -> None:
        self.assertEqual(len(edit.IMAGE_NAMES), 28)
        self.assertEqual(len(edit.STORY), 26)
        self.assertEqual(len(edit.HEADLINES), len(edit.STORY))
        source = Path(edit.__file__).read_text(encoding="utf-8")
        self.assertNotIn("hybrid_engine", source)
        self.assertNotIn("build_montage.py", source)
        self.assertNotIn("prepare_nutty_putty.py", source)

    def test_new_cut_starts_immediately_and_has_fast_visual_rhythm(self) -> None:
        duration = 104.15
        rows = edit.scene_plan(duration)
        self.assertGreaterEqual(len(rows), 40)
        self.assertLessEqual(len(rows), 48)
        self.assertEqual(rows[0]["start"], 0.0)
        self.assertAlmostEqual(rows[-1]["end"], duration, places=4)
        for row in rows:
            self.assertGreater(row["duration"], 1.3)
            self.assertLess(row["duration"], 3.0)
            self.assertIn(row["headline"], edit.HEADLINES[row["line_index"]])

    def test_first_scene_is_not_an_intro_card(self) -> None:
        rows = edit.scene_plan(104.15)
        self.assertEqual(rows[0]["index"], 0)
        self.assertEqual(rows[0]["start"], 0.0)
        self.assertEqual(rows[0]["image_index"], 0)
        self.assertEqual(edit.SFX_EVENTS[0][0], 0)


if __name__ == "__main__":
    unittest.main()
