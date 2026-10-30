import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import asset_director
import stock_fetcher


class GeneratedAssetRoutingTests(unittest.TestCase):
    def test_generation_queue_is_linked_to_exact_story_segment_and_requires_cost_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets" / "stock").mkdir(parents=True)
            (root / "build").mkdir()
            with (root / "scene_plan.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=[
                    "segment_id", "sentence", "visual_prompt", "search_query"
                ])
                writer.writeheader()
                writer.writerow({
                    "segment_id": "scene_003",
                    "sentence": "The rescue team arrives.",
                    "visual_prompt": "A rescue team entering a narrow cave.",
                    "search_query": "cave rescue team",
                })
            config = {
                "project_name": "Test",
                "asset_style_guide": "consistent flat 2D cartoon illustration",
                "scene_images": ["main.png"],
                "story_beats": [{
                    "scene_id": "story_003", "start_s": 0, "end_s": 4,
                    "stock_query": "cave rescue team",
                }],
            }
            scenes = [{
                "scene_ref": "scene_003", "start": 0, "end": 4,
                "image": "main.png", "source_image": "main.png",
            }]
            report = asset_director.build_asset_report(
                config, scenes, {"tracks": []}, root,
                toolchain={"python_modules": {
                    "huggingface_hub": {"installed": True},
                    "rembg": {"installed": False},
                }},
            )
            queue = report["asset_generation_queue"]
            self.assertEqual(len(queue), 1)
            self.assertEqual(queue[0]["segment_id"], "scene_003")
            self.assertIn("consistent flat 2D cartoon illustration", queue[0]["prompt"])
            self.assertTrue(queue[0]["generation_requires_explicit_cost_confirmation"])
            self.assertTrue(queue[0]["use_requires_selection_and_license_review"])
            self.assertFalse(queue[0]["background_removal_available"])

    def test_only_selected_and_license_reviewed_ai_images_enter_beat_pool(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            generated = root / "assets" / "generated"
            generated.mkdir(parents=True)
            unreviewed_path = generated / "unreviewed.png"
            reviewed_path = generated / "reviewed-cutout.png"
            Image.new("RGBA", (640, 640), (0, 0, 0, 0)).save(reviewed_path)
            Image.new("RGB", (640, 640), (80, 80, 80)).save(unreviewed_path)
            fields = [
                "id", "kind", "segment_id", "query", "creator", "source",
                "license", "source_page", "selected", "downloaded_path", "license_reviewed",
            ]
            with (root / "media_candidates.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow({
                    "id": "C0001", "kind": "image", "segment_id": "scene_003",
                    "query": "rope and pulley", "creator": "AI-generated",
                    "source": "Hugging Face", "license": "Reviewed model terms",
                    "source_page": "https://huggingface.co/model", "selected": "yes",
                    "downloaded_path": str(unreviewed_path), "license_reviewed": "no",
                })
                writer.writerow({
                    "id": "C0002", "kind": "image", "segment_id": "scene_003",
                    "query": "rescue pulley cutout", "creator": "AI-generated",
                    "source": "Hugging Face", "license": "Reviewed model terms",
                    "source_page": "https://huggingface.co/model", "selected": "yes",
                    "downloaded_path": str(reviewed_path), "license_reviewed": "yes",
                })
            with patch.object(stock_fetcher, "fetch_stock", return_value=[]):
                pool = stock_fetcher.load_stock_pool_entries(
                    {"settings": {"stock_media": {"enabled": False}}}, root, lambda *_: None
                )
            self.assertEqual(len(pool), 1)
            self.assertEqual(pool[0]["id"], "C0002")
            self.assertEqual(pool[0]["beat"], 2)
            self.assertTrue(pool[0]["alpha_channel"])
            self.assertEqual(pool[0]["asset_origin"], "ai_generated_and_license_reviewed")


if __name__ == "__main__":
    unittest.main()
