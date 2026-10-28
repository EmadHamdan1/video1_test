import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prepare_assets.py"
SPEC = importlib.util.spec_from_file_location("prepare_assets", SCRIPT)
ASSETS = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(ASSETS)


class AssetPipelineTests(unittest.TestCase):
    def test_story_splits_english_and_arabic_punctuation(self):
        beats = ASSETS.split_story(
            "A shadow moved through the hall. Then the lights went out!\n"
            "وفي النهاية اكتشفوا السر؟"
        )
        self.assertEqual(len(beats), 3)
        self.assertIn("lights went out", beats[1])
        self.assertTrue(beats[2].endswith("؟"))

    def test_search_query_removes_common_english_stopwords(self):
        query = ASSETS.make_search_query(
            "The mysterious abandoned hospital with flickering lights and dark corridors"
        )
        self.assertNotIn("the", query.split())
        self.assertNotIn("with", query.split())
        self.assertIn("hospital", query)
        self.assertIn("lights", query)

    def test_safe_extensions_are_limited_to_media_types(self):
        self.assertEqual(ASSETS.safe_ext("https://cdn.example.test/image.jpg", "image/jpeg"), ".jpg")
        self.assertEqual(ASSETS.safe_ext("https://cdn.example.test/file", "audio/mpeg", "audio"), ".mp3")
        self.assertEqual(ASSETS.safe_ext("https://cdn.example.test/file.exe", "application/octet-stream"), ".jpg")

    def test_new_project_and_scene_plan_are_project_local(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "story-project"
            created = ASSETS.new_project("My Test Story", str(target))
            self.assertEqual(created, target.resolve())
            config = target / "project.json"
            self.assertTrue(config.is_file())
            self.assertTrue((target / "assets" / "images").is_dir())
            story = target / "story.txt"
            story.write_text(
                "A lost astronaut discovers an ocean under the ice.\n"
                "A strange blue light leads her toward a hidden machine.",
                encoding="utf-8",
            )
            plan_path = ASSETS.make_scene_plan(str(target))
            self.assertTrue(plan_path.is_file())
            plan = ASSETS.read_csv(plan_path)
            self.assertEqual(len(plan), 2)
            self.assertEqual(plan[0]["segment_id"], "scene_001")
            self.assertTrue(plan[0]["search_query"])
            self.assertEqual(plan[1]["segment_id"], "scene_002")

    def test_manifest_ids_are_stable_and_gallery_is_written(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = ASSETS.new_project("Gallery", str(Path(temporary) / "gallery"))
            candidates = [
                ASSETS.normalize_candidate({
                    "provider": "Openverse",
                    "title": "A <b>forest</b>",
                    "creator": "Creator",
                    "license": "CC BY 4.0",
                    "license_url": "https://creativecommons.org/licenses/by/4.0/",
                    "source_page": "https://example.test/item/1",
                    "preview_url": "https://example.test/image.jpg",
                    "download_url": "https://example.test/image.jpg",
                }, "image", "forest", "scene_001"),
            ]
            added = ASSETS.append_candidates(str(project), candidates)
            self.assertEqual(added[0]["id"], "C0001")
            gallery = project / "media_gallery.html"
            self.assertTrue(gallery.is_file())
            html_content = gallery.read_text(encoding="utf-8")
            self.assertIn("C0001", html_content)
            self.assertIn("Source page", html_content)
            self.assertNotIn("<b>forest</b>", html_content)

    def test_download_rejects_non_http_url(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = ASSETS.new_project("Unsafe", str(Path(temporary) / "unsafe"))
            row = {
                "id": "C0001", "kind": "image", "segment_id": "scene_001",
                "query": "bad", "title": "bad", "creator": "", "source": "test",
                "license": "unknown", "license_url": "", "source_page": "",
                "preview_url": "", "download_url": "file:///C:/Windows/win.ini",
                "selected": "no", "downloaded_path": "", "start_seconds": "",
                "volume": "", "notes": "",
            }
            ASSETS.write_csv(project / "media_candidates.csv", [row])
            with self.assertRaises(ValueError):
                ASSETS.download_candidate(str(project), "C0001")

    def test_huggingface_generation_requires_explicit_cost_acknowledgement(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = ASSETS.new_project("AI", str(Path(temporary) / "ai"))
            story = project / "story.txt"
            story.write_text("A weathered lighthouse shines over a stormy sea.", encoding="utf-8")
            ASSETS.make_scene_plan(str(project))
            with patch.object(ASSETS, "load_env_file", return_value=None):
                with patch.dict(os.environ, {"HF_TOKEN": "test-token"}):
                    with self.assertRaisesRegex(ValueError, "may consume paid provider credits"):
                        ASSETS.generate_hf_image(
                            str(project), "scene_001", None,
                            "black-forest-labs/FLUX.1-dev", False
                        )

    def test_generation_requires_token_before_any_api_import_or_call(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = ASSETS.new_project("AI no token", str(Path(temporary) / "no-token"))
            (project / "story.txt").write_text("A fox sits under a tree.", encoding="utf-8")
            ASSETS.make_scene_plan(str(project))
            with patch.object(ASSETS, "load_env_file", return_value=None):
                with patch.dict(os.environ, {"HF_TOKEN": ""}):
                    with self.assertRaisesRegex(ValueError, "HF_TOKEN is missing"):
                        ASSETS.generate_hf_image(
                            str(project), "scene_001", None,
                            "black-forest-labs/FLUX.1-dev", True
                        )


if __name__ == "__main__":
    unittest.main()
