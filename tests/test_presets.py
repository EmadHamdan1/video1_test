import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PresetIntegrityTests(unittest.TestCase):
    def test_all_preset_json_files_parse(self):
        for relative in (
            "presets/motion_presets.json",
            "presets/text_animation_presets.json",
            "presets/asset_sources.json",
        ):
            with self.subTest(path=relative):
                payload = json.loads((ROOT / relative).read_text(encoding="utf-8"))
                self.assertIsInstance(payload, dict)
                self.assertEqual(payload.get("version"), 1)

    def test_motion_presets_reference_existing_text_presets(self):
        motion = json.loads((ROOT / "presets/motion_presets.json").read_text(encoding="utf-8"))
        text = json.loads((ROOT / "presets/text_animation_presets.json").read_text(encoding="utf-8"))
        text_names = set(text["presets"])
        self.assertIn("whiteboard_smooth", motion["presets"])
        for name, preset in motion["presets"].items():
            with self.subTest(preset=name):
                self.assertIn(preset["text_preset"], text_names)
                self.assertGreater(preset["target_shot_seconds"], preset["minimum_shot_seconds"])
                transitions = preset["transitions"]
                self.assertEqual(transitions["default"]["slug"], "dissolve")
                self.assertGreater(transitions["default"]["duration"], 0)
                self.assertLessEqual(transitions["default"]["duration"], 0.5)
                for accent in transitions["accents"]:
                    self.assertGreaterEqual(accent["every"], 2)
                    self.assertGreater(accent["duration"], 0)
                    self.assertLessEqual(accent["duration"], 0.5)

    def test_asset_sources_keep_credentials_local(self):
        sources = json.loads((ROOT / "presets/asset_sources.json").read_text(encoding="utf-8"))
        self.assertIn("openverse", {item["id"] for item in sources["search_providers"]})
        self.assertIn("lucide", {item["id"] for item in sources["search_providers"]})
        self.assertIn("huggingface-inference", {item["id"] for item in sources["search_providers"]})
        self.assertTrue(any("never commit" in item.lower() or "never upload" in item.lower() for item in sources["policy"]))


if __name__ == "__main__":
    unittest.main()
