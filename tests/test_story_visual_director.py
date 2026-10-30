import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import story_visual_director as director


class StoryVisualDirectorTests(unittest.TestCase):
    def test_supplied_art_is_full_frame_at_opening_and_story_cadence(self):
        settings = {"local_full_bleed_every": 4, "local_full_bleed_min_shock": 3}
        opening = director.plan_hero_composition(0, 0, settings)
        cadence = director.plan_hero_composition(3, 0, settings)
        self.assertTrue(opening["full_bleed"])
        self.assertTrue(cadence["full_bleed"])
        self.assertEqual(opening["scale"], 1.0)
        self.assertEqual(cadence["side"], "full_bleed")

    def test_high_impact_beat_uses_full_frame_even_between_cadence_points(self):
        settings = {"local_full_bleed_every": 5, "local_full_bleed_min_shock": 3}
        plan = director.plan_hero_composition(1, 3, settings)
        self.assertTrue(plan["full_bleed"])
        self.assertEqual(plan["reason"], "high-impact beat")

    def test_regular_beats_keep_varied_large_compositions(self):
        settings = {
            "local_full_bleed_every": 0,
            "local_full_bleed_min_shock": 4,
            "card_scene_scale": 0.74,
            "scene_image_x": -0.24,
        }
        plans = [director.plan_hero_composition(i, 0, settings) for i in range(1, 4)]
        self.assertEqual([p["side"] for p in plans], ["right", "center", "left"])
        self.assertTrue(all(not p["full_bleed"] for p in plans))
        self.assertTrue(all(p["scale"] >= 0.74 for p in plans))

    def test_secondary_visuals_follow_impact_and_spacing_not_randomness(self):
        settings = {
            "secondary_image_inserts": True,
            "secondary_min_shock": 3,
            "insert_every": 4,
        }
        self.assertFalse(director.should_add_supporting_visual(0, 3, settings))
        self.assertFalse(director.should_add_supporting_visual(1, 0, settings))
        self.assertTrue(director.should_add_supporting_visual(2, 3, settings))
        self.assertTrue(director.should_add_supporting_visual(3, 0, settings))
        self.assertFalse(director.should_add_supporting_visual(4, 0, settings))

    def test_supporting_visuals_can_be_disabled(self):
        settings = {"secondary_image_inserts": False, "secondary_min_shock": 0, "insert_every": 1}
        self.assertFalse(director.should_add_supporting_visual(2, 3, settings))


if __name__ == "__main__":
    unittest.main()
