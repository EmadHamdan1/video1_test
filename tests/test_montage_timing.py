import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_montage.py"
SPEC = importlib.util.spec_from_file_location("build_montage", SCRIPT)
BUILDER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BUILDER)


class MontageTimingTests(unittest.TestCase):
    def test_timestamp_parser(self):
        self.assertAlmostEqual(BUILDER.parse_timestamp("00:01:02,500"), 62.5)

    def test_srt_parser(self):
        text = (
            "1\n00:00:00,000 --> 00:00:01,200\nHello there.\n\n"
            "2\n00:00:01,200 --> 00:00:02,500\nA second line.\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "test.srt"
            path.write_text(text, encoding="utf-8")
            cues = BUILDER.read_srt(path)
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[0]["text"], "Hello there.")
        self.assertAlmostEqual(cues[1]["end"], 2.5)

    def test_boundaries_are_monotonic_and_cover_duration(self):
        boundaries = BUILDER.scene_boundaries(40.0, 8, 4.2, 1.6, [])
        self.assertEqual(boundaries[0], 0.0)
        self.assertEqual(boundaries[-1], 40.0)
        self.assertEqual(len(boundaries), 9)
        self.assertTrue(all(right > left for left, right in zip(boundaries, boundaries[1:])))
        self.assertTrue(all(right - left >= 1.59 for left, right in zip(boundaries, boundaries[1:])))

    def test_boundary_can_snap_to_nearby_caption_end(self):
        cues = [{"start": 8.0, "end": 9.6, "text": "caption end"}]
        boundaries = BUILDER.scene_boundaries(40.0, 4, 10.0, 1.6, cues)
        self.assertAlmostEqual(boundaries[1], 9.6)

    def test_scene_indices_cover_range_or_loop_when_needed(self):
        self.assertEqual(BUILDER.choose_scene_indices(10, 4), [0, 3, 6, 9])
        self.assertEqual(BUILDER.choose_scene_indices(2, 5), [0, 1, 0, 1, 0])


if __name__ == "__main__":
    unittest.main()
