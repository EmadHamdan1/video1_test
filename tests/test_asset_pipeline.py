import importlib.util
import json
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
        self.assertEqual(ASSETS.safe_ext("https://cdn.example.test/file", "image/svg+xml", "image"), ".svg")
        self.assertEqual(ASSETS.safe_ext("https://cdn.example.test/file.svg", "image/svg+xml", "icon"), ".svg")
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

    def test_license_review_is_explicit_and_persisted(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = ASSETS.new_project("Review", str(Path(temporary) / "review"))
            row = {
                "id": "C0001", "kind": "image", "segment_id": "scene_001",
                "query": "forest", "title": "Forest", "creator": "Artist", "source": "Openverse",
                "license": "CC BY 4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/",
                "source_page": "https://example.test/forest", "preview_url": "",
                "download_url": "", "selected": "no", "downloaded_path": "",
                "downloaded_at": "", "license_reviewed": "no", "review_notes": "",
                "start_seconds": "", "volume": "", "notes": "",
            }
            ASSETS.write_csv(project / "media_candidates.csv", [row])
            with self.assertRaisesRegex(ValueError, "Provide a short review note"):
                ASSETS.review_license(str(project), "C0001", "")
            ASSETS.review_license(
                str(project), "C0001",
                "Verified the CC BY 4.0 terms and recorded attribution requirements."
            )
            updated = ASSETS.read_csv(project / "media_candidates.csv")
            self.assertEqual(updated[0]["license_reviewed"], "yes")
            self.assertIn("attribution", updated[0]["review_notes"].lower())

    def test_gallery_rejects_javascript_urls(self):
        self.assertEqual(ASSETS.safe_web_url("javascript:alert(1)"), "")
        self.assertEqual(ASSETS.safe_web_url("data:text/html,evil"), "")
        self.assertEqual(ASSETS.safe_web_url("https://example.test/image.jpg"), "https://example.test/image.jpg")
        self.assertEqual(ASSETS.safe_web_url("file:///C:/private/image.jpg"), "")
        self.assertEqual(
            ASSETS.safe_web_url("file:///C:/project/assets/image.jpg", allow_file=True),
            "file:///C:/project/assets/image.jpg",
        )
        with tempfile.TemporaryDirectory() as temporary:
            project = ASSETS.new_project("Safe Gallery", str(Path(temporary) / "safe-gallery"))
            row = ASSETS.normalize_candidate({
                "provider": "Test",
                "title": "No unsafe link",
                "license": "Unknown",
                "source_page": "javascript:alert(1)",
                "preview_url": "javascript:alert(2)",
                "download_url": "https://example.test/image.jpg",
            }, "image", "safe gallery", "")
            ASSETS.append_candidates(str(project), [row])
            page = (project / "media_gallery.html").read_text(encoding="utf-8")
            self.assertNotIn('href="javascript:', page)
            self.assertNotIn('src="javascript:', page)

    def test_scene_plan_includes_visual_prompts_and_sound_cue_queries(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = ASSETS.new_project("Prompt plan", str(Path(temporary) / "prompt-plan"))
            (project / "story.txt").write_text(
                "A creepy shadow appeared in the corridor. Then everyone laughed at the silly robot.",
                encoding="utf-8",
            )
            ASSETS.make_scene_plan(str(project))
            plan = ASSETS.read_csv(project / "scene_plan.csv")
            self.assertEqual(len(plan), 2)
            self.assertIn("Create a clear, literal visual of", plan[0]["visual_prompt"])
            self.assertIn("horror", plan[0]["sfx_search_query"])
            self.assertIn("cartoon", plan[1]["sfx_search_query"])

    def test_preflight_passes_only_when_audio_and_scene_media_exist(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = ASSETS.new_project("Preflight", str(Path(temporary) / "preflight"))
            report = ASSETS.preflight_project(str(project))
            self.assertFalse(report["ok"])
            self.assertTrue((project / "build" / "preflight_report.json").is_file())

            audio = project / "assets" / "audio" / "voice.wav"
            image = project / "assets" / "images" / "scene.jpg"
            audio.write_bytes(b"fake audio test file")
            image.write_bytes(b"fake image test file")
            config_path = project / "project.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["audio"] = str(audio)
            config["scene_images"] = [str(image)]
            config_path.write_text(json.dumps(config), encoding="utf-8")
            report = ASSETS.preflight_project(str(project))
            self.assertTrue(report["ok"])
            self.assertEqual(report["asset_counts"]["scene_media_available"], 1)

    def test_apply_assigns_default_sfx_timing_from_story_beat(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = ASSETS.new_project("Auto SFX", str(Path(temporary) / "auto-sfx"))
            (project / "story.txt").write_text(
                "A strange shadow appears. A loud crash shakes the room.",
                encoding="utf-8",
            )
            ASSETS.make_scene_plan(str(project))
            scene_image = project / "assets" / "images" / "scene2.jpg"
            sound_file = project / "assets" / "audio" / "impact.mp3"
            scene_image.write_bytes(b"fake image")
            sound_file.write_bytes(b"fake audio")
            rows = [
                {
                    "id": "C0001", "kind": "image", "segment_id": "scene_002",
                    "query": "crash", "title": "Crash image", "creator": "", "source": "test",
                    "license": "CC0", "license_url": "", "source_page": "https://example.test/image",
                    "preview_url": "", "download_url": "", "selected": "yes",
                    "downloaded_path": str(scene_image), "downloaded_at": "",
                    "license_reviewed": "yes", "review_notes": "Test asset",
                    "start_seconds": "", "volume": "", "notes": "",
                },
                {
                    "id": "C0002", "kind": "audio", "segment_id": "scene_002",
                    "query": "impact", "title": "Impact sound", "creator": "", "source": "test",
                    "license": "CC0", "license_url": "", "source_page": "https://example.test/sound",
                    "preview_url": "", "download_url": "", "selected": "yes",
                    "downloaded_path": str(sound_file), "downloaded_at": "",
                    "license_reviewed": "yes", "review_notes": "Test asset",
                    "start_seconds": "", "volume": "0.08", "notes": "",
                },
            ]
            ASSETS.write_csv(project / "media_candidates.csv", rows)
            ASSETS.apply_project(str(project), include_sfx=True)
            config = json.loads((project / "project.json").read_text(encoding="utf-8"))
            effects = config["settings"]["sound_effects"]
            self.assertEqual(len(effects), 1)
            self.assertAlmostEqual(effects[0]["start"], 3.98, places=2)
            self.assertAlmostEqual(effects[0]["volume"], 0.08, places=2)
            manifest = ASSETS.read_csv(project / "media_candidates.csv")
            sound_row = next(row for row in manifest if row["id"] == "C0002")
            self.assertEqual(sound_row["start_seconds"], "3.98")

    def test_choose_candidate_deselects_other_visuals_but_keeps_audio(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = ASSETS.new_project("Choose media", str(Path(temporary) / "choose-media"))
            def row(cid, kind, segment, selected="yes"):
                return {
                    "id": cid, "kind": kind, "segment_id": segment, "query": "",
                    "title": cid, "creator": "", "source": "test", "license": "CC0",
                    "license_url": "", "source_page": "https://example.test/" + cid,
                    "preview_url": "", "download_url": "", "selected": selected,
                    "downloaded_path": "", "downloaded_at": "", "license_reviewed": "yes",
                    "review_notes": "", "start_seconds": "", "volume": "", "notes": "",
                }
            rows = [
                row("C0001", "image", "scene_001"),
                row("C0002", "image", "scene_001"),
                row("C0003", "video", "scene_001"),
                row("C0004", "audio", "scene_001"),
            ]
            ASSETS.write_csv(project / "media_candidates.csv", rows)
            ASSETS.choose_candidate(str(project), "C0002")
            updated = {row["id"]: row for row in ASSETS.read_csv(project / "media_candidates.csv")}
            self.assertEqual(updated["C0001"]["selected"], "no")
            self.assertEqual(updated["C0002"]["selected"], "yes")
            self.assertEqual(updated["C0003"]["selected"], "no")
            self.assertEqual(updated["C0004"]["selected"], "yes")

    def test_set_project_preset_validates_and_saves_choice(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = ASSETS.new_project("Choose style", str(Path(temporary) / "choose-style"))
            with self.assertRaisesRegex(ValueError, "Unknown motion preset"):
                ASSETS.set_project_preset(str(project), "nonexistent_style")
            ASSETS.set_project_preset(str(project), "horror_comedy")
            config = json.loads((project / "project.json").read_text(encoding="utf-8"))
            self.assertEqual(config["settings"]["motion_preset"], "horror_comedy")

    def test_place_icon_converts_and_records_scene_overlay(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp_root = Path(temporary)
            project = ASSETS.new_project("Place icon", str(temp_root / "project"))
            (project / "story.txt").write_text("A strange light appears in the forest.", encoding="utf-8")
            ASSETS.make_scene_plan(str(project))
            svg = project / "assets" / "icons" / "lightbulb.svg"
            svg.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M12 2v4"/></svg>',
                encoding="utf-8",
            )
            candidate = {
                "id": "C0001", "kind": "icon", "segment_id": "",
                "query": "lightbulb", "title": "lightbulb", "creator": "Lucide contributors",
                "source": "Lucide", "license": "ISC", "license_url": "https://example.test/license",
                "source_page": "https://example.test/lightbulb", "preview_url": "",
                "download_url": "https://example.test/lightbulb.svg", "selected": "yes",
                "downloaded_path": str(svg), "downloaded_at": "", "license_reviewed": "yes",
                "review_notes": "Lucide license included", "start_seconds": "", "volume": "", "notes": "",
            }
            ASSETS.write_csv(project / "media_candidates.csv", [candidate])

            mock_root = temp_root / "repo"
            renderer = mock_root / "motion-lab" / "scripts" / "render-svg.mjs"
            module_dir = mock_root / "motion-lab" / "node_modules" / "@resvg" / "resvg-js"
            renderer.parent.mkdir(parents=True)
            renderer.write_text("// mocked renderer path", encoding="utf-8")
            module_dir.mkdir(parents=True)

            def fake_run(command, **kwargs):
                output_path = Path(command[3])
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"mock-png-data")
                return ASSETS.subprocess.CompletedProcess(command, 0, stdout='{"ok":true}', stderr="")

            with patch.object(ASSETS, "ROOT", mock_root):
                with patch.object(ASSETS.shutil, "which", return_value="node"):
                    with patch.object(ASSETS.subprocess, "run", side_effect=fake_run):
                        output = ASSETS.place_icon(
                            str(project), "C0001", "scene_001",
                            offset=0.4, duration=1.2, x=-0.5, y=-0.3, scale=0.15, color="#159A90"
                        )

            self.assertTrue(output.is_file())
            config = json.loads((project / "project.json").read_text(encoding="utf-8"))
            overlays = config["settings"]["icon_overlays"]
            self.assertEqual(len(overlays), 1)
            self.assertEqual(overlays[0]["scene_id"], "scene_001")
            self.assertAlmostEqual(overlays[0]["offset"], 0.4)
            self.assertEqual(overlays[0]["path"], str(output.resolve()))
            updated = ASSETS.read_csv(project / "media_candidates.csv")[0]
            self.assertEqual(updated["segment_id"], "scene_001")
            self.assertIn("rendered PNG", updated["notes"])


if __name__ == "__main__":
    unittest.main()
