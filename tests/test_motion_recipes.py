import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import motion_recipes as motion


class FakeTimeline:
    def __init__(self):
        self.keys = []

    def key(self, ref, prop, time, value, easing=None):
        self.keys.append({"target": ref, "property": prop, "time": float(time),
                          "value": float(value), "easing": easing})


class MotionRecipeTests(unittest.TestCase):
    def test_hero_motion_is_selected_from_story_emotion_and_trigger(self):
        self.assertEqual(motion.choose_hero_entrance(4, 3, "shocking", "ROPE SNAPPED"), "punch")
        self.assertEqual(motion.choose_hero_entrance(0, 3, "sad", "27 HOURS"), "slide_left")
        self.assertEqual(motion.choose_hero_entrance(0, 2, "scary", "CORKSCREW"), "diagonal_sweep")
        self.assertEqual(motion.choose_hero_entrance(0, 2, "scary", "WHAT IF"), "zoom_through")
        self.assertNotEqual(
            motion.choose_hero_entrance(0, 3, "sad", "DECLARED DEAD"),
            motion.choose_hero_entrance(0, 3, "shocking", "HEAD FIRST"),
        )

    def test_high_impact_layout_creates_a_two_card_collage(self):
        layout = motion.overlay_layout(index=2, hero_x=-0.24, shock=3)
        self.assertEqual(layout["name"], "paired_top_cards")
        self.assertEqual(len(layout["slots"]), 2)
        self.assertLess(layout["slots"][0]["x"], 0)
        self.assertGreater(layout["slots"][1]["x"], 0)
        self.assertNotEqual(layout["slots"][0]["recipe"], layout["slots"][1]["recipe"])

    def test_layout_cycle_varies_positions_and_motion(self):
        layouts = [motion.overlay_layout(index=i, hero_x=-0.24, shock=0) for i in range(7)]
        names = [layout["name"] for layout in layouts]
        recipes = [layout["slots"][0]["recipe"] for layout in layouts]
        self.assertGreaterEqual(len(set(names)), 6)
        self.assertGreaterEqual(len(set(recipes)), 6)
        self.assertTrue(all(-0.88 <= slot["x"] <= 0.88 and -0.88 <= slot["y"] <= 0.88
                            for layout in layouts for slot in layout["slots"]))

    def test_all_recipes_emit_supported_keyframes_inside_clip(self):
        for index, recipe in enumerate(motion.RECIPES):
            with self.subTest(recipe=recipe):
                timeline = FakeTimeline()
                motion.apply_layer_motion(timeline, "layer", 1.35, 0.21, 0.62, -0.34, recipe, index)
                self.assertTrue(timeline.keys)
                self.assertTrue(all(
                    key["property"] in {"uniform_scale", "position_x", "position_y", "rotation"}
                    for key in timeline.keys
                ))
                self.assertTrue(all(0 <= key["time"] <= 1.35 for key in timeline.keys))
                for prop in ("uniform_scale", "position_x", "position_y", "rotation"):
                    times = [key["time"] for key in timeline.keys if key["property"] == prop]
                    self.assertTrue(times, "missing keyframes for " + prop)
                    self.assertEqual(times, sorted(times))

    def test_different_exit_recipes_are_selected(self):
        exits = set()
        for index in range(len(motion.EXIT_RECIPES)):
            timeline = FakeTimeline()
            motion.apply_layer_motion(timeline, "layer", 1.7, 0.2, -0.62, 0.2, "from_left", index)
            exits.add(tuple(
                key["property"] for key in timeline.keys
                if abs(key["time"] - 1.7) < 1e-6
            ))
        self.assertGreaterEqual(len(exits), 4)

    def test_paired_images_get_a_small_stagger(self):
        self.assertEqual(motion.staggered_pair_offsets(0), (0.0, 0.08))
        self.assertEqual(motion.staggered_pair_offsets(1), (0.0, 0.12))


if __name__ == "__main__":
    unittest.main()
