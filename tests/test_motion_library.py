import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import motion_library


class MotionLibraryTests(unittest.TestCase):
    def test_catalogue_contains_more_than_two_hundred_distinct_ids(self):
        summary = motion_library.catalogue_summary()
        self.assertGreaterEqual(summary["recipe_count"], 200)
        self.assertEqual(len(motion_library.CATALOG), summary["recipe_count"])
        self.assertEqual(len(set(motion_library.CATALOG)), summary["recipe_count"])

    def test_catalogue_has_multiple_behavior_families_and_renderer_categories(self):
        summary = motion_library.catalogue_summary()
        self.assertGreaterEqual(summary["family_count"], 14)
        self.assertTrue({"image_entrance", "transition", "element", "camera"}.issubset(set(summary["categories"])))

    def test_recipe_has_separate_enter_and_exit_states(self):
        recipe = motion_library.get_recipe(next(iter(motion_library.CATALOG)))
        self.assertIn("from", recipe["enter"])
        self.assertIn("to", recipe["enter"])
        self.assertIn("to", recipe["exit"])
        self.assertNotEqual(recipe["enter"]["from"], recipe["enter"]["to"])

    def test_selection_is_deterministic_and_solemn_beats_are_restrained(self):
        first = motion_library.choose_recipe("entrance", "solemn", 3, "beat-27")
        second = motion_library.choose_recipe("entrance", "solemn", 3, "beat-27")
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(first["energy"], "subtle")

    def test_recent_recipe_ids_are_avoided_when_alternatives_exist(self):
        first = motion_library.choose_recipe("entrance", "tense", 1, "beat-A")
        second = motion_library.choose_recipe("entrance", "tense", 1, "beat-B", [first["id"]])
        self.assertNotEqual(first["id"], second["id"])


if __name__ == "__main__":
    unittest.main()
