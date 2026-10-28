import csv
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

    def test_scene_csv_includes_scene_ref_column(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "scene_timing.csv"
            scenes = [{
                "start": 0.0,
                "end": 2.0,
                "duration": 2.0,
                "image": "scene.jpeg",
                "caption_context": "",
                "scene_ref": "scene_001",
                "frame_ref": "frame_001",
                "layout": "whiteboard-card-left / presenter-right",
            }]
            BUILDER.write_scene_csv(path, scenes, [])
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual(rows[0]["scene_ref"], "scene_001")
        self.assertEqual(rows[0]["frame_ref"], "frame_001")
        self.assertEqual(rows[0]["layout"], "whiteboard-card-left / presenter-right")
        self.assertEqual(rows[0]["presenter_ref"], "")


    def test_whiteboard_spec_uses_framed_images_and_persistent_presenter(self):
        with tempfile.TemporaryDirectory() as temporary:
            previous_build_dir = BUILDER.BUILD_DIR
            BUILDER.BUILD_DIR = Path(temporary) / "build"
            try:
                config = {
                    "project_name": "Whiteboard test",
                    "canvas": {"width": 1920, "height": 1080, "fps": 30, "ratio": "16:9"},
                    "settings": {
                        "target_shot_seconds": 3.9,
                        "minimum_shot_seconds": 1.8,
                        "presenter_overlay": True,
                        "presenter_pose_seconds": 9.5,
                        "scene_image_scale": 0.50,
                        "scene_image_x": -0.25,
                        "scene_image_y": -0.02,
                        "presenter_scale": 0.42,
                        "presenter_x": 0.72,
                        "presenter_y": 0.18,
                    },
                }
                spec, scenes, presenters = BUILDER.make_spec(
                    config,
                    Path("voiceover.mp3"),
                    [Path("scene_a.jpeg"), Path("scene_clip.mp4"), Path("scene_c.jpeg")],
                    [Path("pose_1.jpeg"), Path("pose_2.jpeg"), Path("pose_3.jpeg")],
                    24.0,
                    [],
                    None,
                )
                tracks = {track["name"]: track for track in spec["tracks"]}
                self.assertIn("Whiteboard Background", tracks)
                self.assertIn("Whiteboard Scene Frames", tracks)
                self.assertIn("Presenter Explainer", tracks)
                self.assertEqual(len(tracks["Scene Artwork"]["items"]), len(scenes))
                self.assertTrue(all(item["scale"] < 0.7 for item in tracks["Scene Artwork"]["items"]))
                self.assertTrue(all(item["x"] < 0 for item in tracks["Scene Artwork"]["items"]))
                self.assertIn("video", {item["type"] for item in tracks["Scene Artwork"]["items"]})
                board = Path(tracks["Whiteboard Background"]["items"][0]["path"])
                first_card = Path(tracks["Whiteboard Scene Frames"]["items"][0]["path"])
                self.assertTrue(board.is_file())
                self.assertTrue(first_card.is_file())
                self.assertEqual(len(presenters), 3)
                self.assertAlmostEqual(presenters[0]["start"], 0.0)
                self.assertAlmostEqual(presenters[-1]["end"], 24.0)
                self.assertTrue(all(row["side"] == "right" for row in presenters))
                self.assertTrue(all(row["layout"] == "whiteboard-card-left / presenter-right" for row in scenes))
                for left, right in zip(presenters, presenters[1:]):
                    self.assertAlmostEqual(left["end"], right["start"], places=2)
                slugs = {
                    operation["slug"] for operation in spec["operations"]
                    if operation.get("op") == "transition"
                }
                self.assertTrue(slugs.issubset({"dissolve", "horizontal-blur", "radial-blur"}))
            finally:
                BUILDER.BUILD_DIR = previous_build_dir


    def test_timed_text_splits_long_cues_and_keeps_time(self):
        chunks = BUILDER.split_timed_text(
            2.0, 5.0, "The old machine began to glow", max_words=3, min_hold=0.8
        )
        self.assertEqual(len(chunks), 2)
        self.assertAlmostEqual(chunks[0]["start"], 2.0)
        self.assertAlmostEqual(chunks[-1]["end"], 5.0)
        self.assertTrue(all(chunk["end"] > chunk["start"] for chunk in chunks))
        self.assertEqual(chunks[0]["text"], "The old machine")

    def test_transcript_creates_editable_animated_caption_track(self):
        with tempfile.TemporaryDirectory() as temporary:
            previous_build_dir = BUILDER.BUILD_DIR
            BUILDER.BUILD_DIR = Path(temporary) / "build"
            try:
                config = {
                    "project_name": "Caption test",
                    "canvas": {"width": 1920, "height": 1080, "fps": 30, "ratio": "16:9"},
                    "settings": {
                        "target_shot_seconds": 3.0,
                        "minimum_shot_seconds": 1.0,
                        "presenter_overlay": False,
                        "add_captions_when_transcribed": True,
                        "caption_words_per_chunk": 4,
                    },
                }
                spec, _, _ = BUILDER.make_spec(
                    config, Path("voice.mp3"), [Path("image.jpeg")], [], 4.0,
                    [{"start": 0.0, "end": 3.0, "text": "The old machine began to glow"}],
                    Path("captions.srt"),
                )
                tracks = {track["name"]: track for track in spec["tracks"]}
                self.assertIn("Animated Captions", tracks)
                text_items = tracks["Animated Captions"]["items"]
                self.assertGreaterEqual(len(text_items), 2)
                self.assertTrue(all(item["ref"].startswith("caption_") for item in text_items))
                operations = spec["operations"]
                self.assertTrue(any(op.get("op") == "text-style" for op in operations))
                self.assertTrue(any(op.get("op") == "keyframe" and op.get("property") == "position_y" for op in operations))
                self.assertFalse(any(op.get("op") == "keyframe" and op.get("property") == "opacity" for op in operations))
                self.assertFalse(any(op.get("op") == "captions" for op in operations))
            finally:
                BUILDER.BUILD_DIR = previous_build_dir

    def test_scene_text_creates_callouts_without_whisper(self):
        with tempfile.TemporaryDirectory() as temporary:
            previous_build_dir = BUILDER.BUILD_DIR
            BUILDER.BUILD_DIR = Path(temporary) / "build"
            try:
                config = {
                    "project_name": "Callout test",
                    "scene_texts": ["A strange machine appeared in the forest"],
                    "canvas": {"width": 1920, "height": 1080, "fps": 30, "ratio": "16:9"},
                    "settings": {
                        "target_shot_seconds": 4.0,
                        "minimum_shot_seconds": 1.0,
                        "presenter_overlay": False,
                        "show_scene_text_without_transcript": True,
                    },
                }
                spec, _, _ = BUILDER.make_spec(
                    config, Path("voice.mp3"), [Path("image.jpeg")], [], 4.0, [], None
                )
                tracks = {track["name"]: track for track in spec["tracks"]}
                self.assertIn("Animated Scene Callouts", tracks)
                self.assertGreaterEqual(len(tracks["Animated Scene Callouts"]["items"]), 1)
            finally:
                BUILDER.BUILD_DIR = previous_build_dir

    def test_full_frame_storyboard_uses_exact_boundaries_without_whiteboard_cards(self):
        with tempfile.TemporaryDirectory() as temporary:
            previous_build_dir = BUILDER.BUILD_DIR
            BUILDER.BUILD_DIR = Path(temporary) / "build"
            try:
                flash = Path(temporary) / "flash.png"
                flash.write_bytes(b"test fixture placeholder")
                config = {
                    "project_name": "Full-frame horror test",
                    "story_beats": [
                        {"start_s": 0.0, "end_s": 2.0, "text": "NUTTY PUTTY CAVE", "emotion": "tense", "shock_level": 1, "trigger_word": "CAVE"},
                        {"start_s": 2.0, "end_s": 4.5, "text": "John went deeper", "emotion": "scary", "shock_level": 2, "trigger_word": "DEEPER"},
                    ],
                    "storyboard_boundaries": [0.0, 2.0, 4.5, 7.0],
                    "background_music": {"path": str(Path(temporary) / "music.wav"), "start": 0.0, "duration": 7.0, "volume": 0.3},
                    "canvas": {"width": 1920, "height": 1080, "fps": 30, "ratio": "16:9"},
                    "settings": {
                        "layout_mode": "full_frame",
                        "use_storyboard_boundaries": True,
                        "scene_zoom_start": 1.0,
                        "scene_zoom_end": 1.065,
                        "target_shot_seconds": 2.5,
                        "minimum_shot_seconds": 1.2,
                        "presenter_overlay": False,
                        "show_scene_text_without_transcript": False,
                        "flash_overlay_path": str(flash),
                        "flash_times": [4.5],
                    },
                }
                spec, scenes, _ = BUILDER.make_spec(
                    config,
                    Path("voice.mp3"),
                    [Path("intro.mp4"), Path("scene_a.jpg"), Path("scene_b.jpg")],
                    [],
                    7.0,
                    [],
                    None,
                )
                tracks = {track["name"]: track for track in spec["tracks"]}
                self.assertIn("Scene Artwork", tracks)
                self.assertNotIn("Whiteboard Background", tracks)
                self.assertNotIn("Whiteboard Scene Frames", tracks)
                self.assertEqual(len(tracks["Scene Artwork"]["items"]), 3)
                self.assertAlmostEqual(scenes[0]["start"], 0.0)
                self.assertAlmostEqual(scenes[0]["end"], 2.0)
                self.assertAlmostEqual(scenes[1]["start"], 2.0)
                self.assertIn("Shock Flash Hits", tracks)
                self.assertTrue(any(
                    operation.get("op") == "keyframe" and operation.get("property") == "rotation"
                    for operation in spec["operations"]
                ))
            finally:
                BUILDER.BUILD_DIR = previous_build_dir


    def test_icon_overlay_uses_separate_track_and_scene_relative_timing(self):
        with tempfile.TemporaryDirectory() as temporary:
            previous_build_dir = BUILDER.BUILD_DIR
            BUILDER.BUILD_DIR = Path(temporary) / "build"
            try:
                icon = Path(temporary) / "test-icon.png"
                icon.write_bytes(b"fake png placeholder")
                config = {
                    "project_name": "Icon overlay test",
                    "canvas": {"width": 1920, "height": 1080, "fps": 30, "ratio": "16:9"},
                    "settings": {
                        "target_shot_seconds": 4.0,
                        "minimum_shot_seconds": 1.0,
                        "presenter_overlay": False,
                        "icon_overlays": [{
                            "candidate_id": "C0001",
                            "scene_id": "scene_001",
                            "path": str(icon),
                            "offset": 0.35,
                            "duration": 1.4,
                            "x": -0.56,
                            "y": -0.42,
                            "scale": 0.16,
                        }],
                    },
                }
                spec, scenes, _ = BUILDER.make_spec(
                    config, Path("voice.mp3"), [Path("image.jpeg")], [], 4.0, [], None
                )
                tracks = {track["name"]: track for track in spec["tracks"]}
                self.assertIn("Icon Overlays", tracks)
                icon_item = tracks["Icon Overlays"]["items"][0]
                self.assertEqual(icon_item["ref"], "icon_001")
                self.assertAlmostEqual(icon_item["start"], scenes[0]["start"] + 0.35, places=2)
                self.assertAlmostEqual(icon_item["duration"], 1.4, places=2)
                self.assertTrue(any(
                    operation.get("op") == "keyframe"
                    and operation.get("target") == "icon_001"
                    and operation.get("property") == "uniform_scale"
                    for operation in spec["operations"]
                ))
            finally:
                BUILDER.BUILD_DIR = previous_build_dir


if __name__ == "__main__":
    unittest.main()
