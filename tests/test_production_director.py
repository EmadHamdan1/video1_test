import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import production_director


class ProductionDirectorTests(unittest.TestCase):
    def test_plan_covers_scenes_and_keeps_narration_off_screen(self):
        config = {
            "project_name": "Test documentary",
            "canvas": {"width": 1920, "height": 1080, "fps": 30},
            "story_beats": [
                {"scene_id": "b1", "start_s": 0, "end_s": 3, "text": "A person enters a cave", "emotion": "tense", "shock_level": 1},
                {"scene_id": "b2", "start_s": 3, "end_s": 6, "text": "The rope snaps", "emotion": "shocking", "shock_level": 3},
            ],
        }
        scenes = [
            {"scene_ref": "s1", "start": 0, "end": 3, "duration": 3, "image": "a.jpg"},
            {"scene_ref": "s2", "start": 3, "end": 6, "duration": 3, "image": "b.jpg"},
        ]
        plan = production_director.build_production_plan(config, scenes, 6)
        self.assertEqual(len(plan["scenes"]), 2)
        self.assertFalse(plan["text_policy"]["narration_subtitles"])
        self.assertEqual(plan["scenes"][0]["screen_text"], [])
        self.assertEqual(plan["scenes"][1]["beat_id"], "b2")
        self.assertTrue(plan["scenes"][0]["motion"]["entrance"])


    def test_production_plan_uses_the_same_enter_hold_and_transition_recipes(self):
        enter = motion_library.choose_recipe("entrance", "tense", 1, "scene-1")
        camera = motion_library.choose_recipe("camera", "tense", 1, "scene-1:camera")
        transition = motion_library.choose_recipe("transition", "tense", 1, "scene-1:transition")
        config = {"story_beats": [
            {"scene_id": "beat-1", "start_s": 0, "end_s": 5,
             "emotion": "tense", "shock_level": 1, "stock_query": "cave"}
        ]}
        scenes = [{
            "scene_ref": "scene-1", "start": 0, "end": 5, "duration": 5,
            "image": "user-art.png",
            "motion_recipe_id": enter["id"],
            "camera_recipe_id": camera["id"],
            "transition_recipe_id": transition["id"],
        }]
        plan = production_director.build_production_plan(config, scenes, 5)
        motion = plan["scenes"][0]["motion"]
        self.assertEqual(motion["entrance"], enter["id"])
        self.assertEqual(motion["hold"], camera["id"])
        self.assertEqual(motion["transition_out"], transition["id"])
        self.assertEqual(motion["exit"], transition["id"])

    def test_supplied_asset_remains_primary_and_stock_is_supporting(self):
        config = {"story_beats": [{"scene_id": "b", "start_s": 0, "end_s": 5, "stock_query": "cave rescue"}]}
        scenes = [{
            "scene_ref": "s", "start": 0, "end": 5, "duration": 5,
            "source_image": "user-art.png", "stock_source_path": "stock-rescue.jpg",
        }]
        plan = production_director.build_production_plan(config, scenes, 5)
        shot = plan["scenes"][0]
        self.assertEqual(shot["primary_asset"], "user-art.png")
        self.assertEqual(shot["supporting_assets"][0]["asset"], "stock-rescue.jpg")


if __name__ == "__main__":
    unittest.main()
