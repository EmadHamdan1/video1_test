import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import asset_director


class AssetDirectorTests(unittest.TestCase):
    def test_reports_visual_gap_without_inventing_semantic_match(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "build").mkdir()
            (root / "assets" / "stock").mkdir(parents=True)
            (root / "build" / "MISSING_ASSETS.json").write_text(
                json.dumps({"items": [{"asset": "rescue pulley", "status": "review"}]}),
                encoding="utf-8",
            )
            config = {
                "project_name": "Test",
                "scene_images": ["supplied.png"],
                "story_beats": [{"scene_id": "beat-1", "start_s": 0, "end_s": 4, "stock_query": "cave rescue pulley"}],
            }
            scenes = [{"scene_ref": "scene-1", "start": 0, "end": 4, "source_image": "supplied.png"}]
            spec = {"tracks": []}
            report = asset_director.build_asset_report(config, scenes, spec, root)
            self.assertEqual(report["summary"]["visual_gaps"], 1)
            self.assertEqual(report["scenes"][0]["semantic_match_status"], "requires_visual_review")
            self.assertEqual(report["missing_asset_requests"][0]["asset"], "rescue pulley")


    def test_does_not_queue_ai_generation_when_a_matching_stock_candidate_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stock_dir = root / "assets" / "stock"
            stock_dir.mkdir(parents=True)
            (root / "build").mkdir()
            image_path = stock_dir / "cave-rescue.jpg"
            image_path.write_bytes(b"reviewed mock image")
            (stock_dir / "stock_manifest.json").write_text(
                json.dumps([{
                    "path": str(image_path),
                    "provider": "Wikimedia Commons",
                    "license": "CC BY 4.0",
                    "credit": "Photographer",
                    "query": "cave rescue",
                    "beat": 0,
                    "alpha_channel": False,
                }]),
                encoding="utf-8",
            )
            config = {
                "project_name": "Test",
                "story_beats": [{
                    "scene_id": "beat-1", "start_s": 0, "end_s": 5,
                    "stock_query": "cave rescue",
                }],
            }
            scenes = [{"scene_ref": "scene-1", "start": 0, "end": 5, "image": "primary.png"}]
            report = asset_director.build_asset_report(config, scenes, {"tracks": []}, root)
            self.assertEqual(report["summary"]["visual_gaps"], 1)
            self.assertEqual(report["visual_gaps"][0]["available_candidates"], 1)
            self.assertEqual(report["asset_generation_queue"], [])

    def test_marks_supporting_layer_when_selected_on_timeline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = {"story_beats": [{"scene_id": "beat-1", "start_s": 0, "end_s": 5, "stock_query": "cave rescue"}]}
            scenes = [{"scene_ref": "scene-1", "start": 0, "end": 5, "image": "primary.png"}]
            spec = {"tracks": [{
                "name": "Fast Secondary Image Inserts",
                "items": [{"path": "support.png", "start": 1.0, "duration": 1.5}],
            }]}
            report = asset_director.build_asset_report(config, scenes, spec, root)
            self.assertEqual(report["summary"]["scenes_with_supporting_layers"], 1)
            self.assertEqual(report["visual_gaps"], [])


if __name__ == "__main__":
    unittest.main()
