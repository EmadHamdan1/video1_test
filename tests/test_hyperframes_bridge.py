import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import hyperframes_bridge as bridge


class HyperFramesBridgeTests(unittest.TestCase):
    def test_seekable_composition_contains_title_arrow_and_timeline(self):
        html = bridge.build_composition_html(12.0, [
            {
                "id": "scene-title", "type": "title", "start": 1.5, "duration": 3.0,
                "kicker": "CASE FILE", "title": "THE CORKSCREW",
                "note": "Illustrative reconstruction", "font_size": 48,
            },
            {
                "id": "rope-arrow", "type": "arrow", "start": 4.0, "duration": 2.0,
                "x1": 0.2, "y1": 0.4, "x2": 0.7, "y2": 0.55,
            },
        ])
        self.assertIn('data-composition-id="main"', html)
        self.assertIn('data-duration="12.000"', html)
        self.assertIn('window.__timelines["main"]=tl', html.replace(" ", ""))
        self.assertIn("strokeDashoffset", html)
        self.assertIn("THE CORKSCREW", html)
        self.assertIn('data-start="4.000"', html)

    def test_text_is_escaped_before_html_render(self):
        html = bridge.build_composition_html(
            5.0,
            [{"type": "callout", "start": 0, "duration": 2,
              "text": '<script>alert("x")</script>'}],
        )
        self.assertNotIn("<script>alert", html)
        self.assertIn("&lt;script&gt;", html)

    def test_rejects_element_after_project_end(self):
        with self.assertRaises(ValueError):
            bridge.build_composition_html(
                4.0, [{"type": "title", "start": 3, "duration": 2, "title": "Too late"}]
            )

    def test_rejects_degenerate_arrow(self):
        with self.assertRaises(ValueError):
            bridge.build_composition_html(
                4.0,
                [{"type": "arrow", "start": 0, "duration": 2,
                  "x1": 0.4, "y1": 0.4, "x2": 0.405, "y2": 0.405}],
            )

    def test_capcut_overlay_is_a_separate_video_track(self):
        spec = {"tracks": []}
        bridge.add_overlay_track(spec, {"path": "overlay.mov"}, 9.25)
        item = spec["tracks"][0]["items"][0]
        self.assertEqual(spec["tracks"][0]["name"], "HyperFrames Motion Graphics")
        self.assertEqual(item["type"], "video")
        self.assertEqual(item["duration"], 9.25)
        self.assertEqual(item["path"], "overlay.mov")


    def test_image_element_is_registered_as_an_independent_clip(self):
        html = bridge.build_composition_html(
            8.0,
            [{"id": "rope-cutout", "type": "image", "path": "assets/rope.png",
              "start": 1.0, "duration": 3.0, "x": 0.2, "y": 0.3,
              "width": 0.4, "height": 0.5, "track_index": 3}],
            asset_map={"rope-cutout": "assets/rope-cutout.png"},
        )
        self.assertIn('class="clip hf-image"', html)
        self.assertIn('src="assets/rope-cutout.png"', html)
        self.assertIn('data-track-index="3"', html)
        self.assertIn("object-fit:contain", html)

    def test_vector_shapes_and_text_labels_are_supported(self):
        html = bridge.build_composition_html(
            5.0,
            [
                {"id": "cave-outline", "type": "shape", "shape": "path",
                 "path_d": "M0 80 C30 10 70 10 100 80", "start": 0.5, "duration": 3},
                {"id": "not-to-scale", "type": "text", "text": "NOT TO SCALE",
                 "start": 0.5, "duration": 3},
            ],
        )
        self.assertIn('class="clip hf-shape"', html)
        self.assertIn("M0 80 C30 10 70 10 100 80", html)
        self.assertIn("NOT TO SCALE", html)

    def test_motion_recipe_is_embedded_for_independent_layers(self):
        html = bridge.build_composition_html(
            5.0,
            [{"id": "object", "type": "shape", "shape": "circle",
              "start": 0.0, "duration": 3.0}],
        )
        self.assertIn("motionIn", html)
        self.assertIn("motionOut", html)
        self.assertIn("gsap.timeline", html)

 
    def test_each_image_uses_separate_entrance_camera_and_transition_recipes(self):
        item = bridge.normalize_elements(
            8.0,
            [{"id": "rope-cutout", "type": "image", "path": "rope.png",
              "start": 0, "duration": 5, "emotion": "tense", "shock_level": 2}],
        )[0]
        motion = item["motion"]
        self.assertEqual(
            bridge.motion_library.get_recipe(motion["id"])["category"],
            "image_entrance",
        )
        self.assertEqual(
            bridge.motion_library.get_recipe(motion["hold_id"])["category"],
            "camera",
        )
        self.assertEqual(
            bridge.motion_library.get_recipe(motion["transition_id"])["category"],
            "transition",
        )
        html = bridge.build_composition_html(
            8.0,
            [{"id": "rope-cutout", "type": "image", "path": "rope.png",
              "start": 0, "duration": 5, "emotion": "tense", "shock_level": 2}],
            asset_map={"rope-cutout": "assets/rope.png"},
        )
        self.assertIn('"hold"', html)
        self.assertIn('"transition"', html)
        self.assertIn("sine.inOut", html)

    def test_vector_shapes_default_to_element_motion_but_allow_reviewed_role_override(self):
        item = bridge.normalize_elements(
            6.0,
            [{"id": "diagram-node", "type": "shape", "shape": "circle",
              "start": 0, "duration": 4}],
        )[0]
        self.assertEqual(
            bridge.motion_library.get_recipe(item["motion"]["id"])["category"],
            "element",
        )
        image_item = bridge.normalize_elements(
            6.0,
            [{"id": "diagram-image", "type": "image", "path": "node.png",
              "motion_role": "element", "start": 0, "duration": 4}],
        )[0]
        self.assertEqual(
            bridge.motion_library.get_recipe(image_item["motion"]["id"])["category"],
            "element",
        )

    def test_rejects_unknown_motion_role(self):
        with self.assertRaisesRegex(ValueError, "motion_role"):
            bridge.normalize_elements(
                5.0,
                [{"id": "bad-role", "type": "image", "path": "x.png",
                  "motion_role": "random", "start": 0, "duration": 3}],
            )

    def test_rejects_unsafe_svg_path_commands(self):
        with self.assertRaises(ValueError):
            bridge.build_composition_html(
                4.0,
                [{"id": "unsafe", "type": "shape", "shape": "path",
                  "path_d": '<script>alert(1)</script>', "start": 0, "duration": 2}],
            )


    def test_verifies_hyperframes_prores_alpha_and_exact_duration(self):
        metadata = bridge.verify_render_metadata({
            "streams": [{
                "codec_name": "prores", "pix_fmt": "yuva444p12le",
                "width": 1920, "height": 1080, "duration": "6.000000",
            }]
        }, 6.0, fps=30)
        self.assertEqual(metadata["pixel_format"], "yuva444p12le")
        self.assertEqual(metadata["duration"], 6.0)
        self.assertEqual(metadata["fps"], 30)

    def test_rejects_hyperframes_overlay_with_wrong_duration(self):
        with self.assertRaisesRegex(RuntimeError, "duration verification failed"):
            bridge.verify_render_metadata({
                "streams": [{
                    "codec_name": "prores", "pix_fmt": "yuva444p10le",
                    "width": 1920, "height": 1080, "duration": "5.000000",
                }]
            }, 6.0, fps=30)

    def test_rejects_prores_output_without_alpha(self):
        with self.assertRaisesRegex(RuntimeError, "alpha verification failed"):
            bridge.verify_render_metadata({
                "streams": [{
                    "codec_name": "prores", "pix_fmt": "yuv444p10le",
                    "width": 1920, "height": 1080, "duration": "6.000000",
                }]
            }, 6.0, fps=30)


    def test_renders_with_fallback_config_when_no_local_template_exists(self):
        import json
        from types import SimpleNamespace
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source" / "object.png"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"synthetic transparent image bytes")
            build = root / "build"
            template = root / "no-template"
            calls = []

            def fake_which(name):
                return {"npx": "/tools/npx", "ffprobe": "/tools/ffprobe"}.get(name)

            def fake_run(command, **kwargs):
                calls.append(command)
                if command[0] == "/tools/npx":
                    output = Path(command[command.index("--output") + 1])
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_bytes(b"fake rendered mov")
                    return SimpleNamespace(returncode=0, stdout="", stderr="")
                return SimpleNamespace(
                    returncode=0,
                    stdout=json.dumps({"streams": [{
                        "codec_name": "prores",
                        "pix_fmt": "yuva444p10le",
                        "width": 1920,
                        "height": 1080,
                        "duration": "6.000000",
                    }]}),
                    stderr="",
                )

            config = {
                "enabled": True,
                "version": "0.8.221",
                "elements": [{
                    "id": "transparent-object", "type": "image", "path": str(source),
                    "start": 0.5, "duration": 4.0,
                }],
            }
            with patch.object(bridge.shutil, "which", side_effect=fake_which), \
                 patch.object(bridge.subprocess, "run", side_effect=fake_run):
                result = bridge.render_hyperframes_overlay(config, build, 6.0, template)

            generated = build / "hyperframes" / "render-project"
            project_config = json.loads((generated / "hyperframes.json").read_text(encoding="utf-8"))
            self.assertEqual(project_config["paths"]["assets"], "assets")
            self.assertTrue((generated / "assets" / "transparent-object.png").is_file())
            self.assertIn("gsap@3.15.0", (generated / "index.html").read_text(encoding="utf-8"))
            self.assertEqual(result["pixel_format"], "yuva444p10le")
            self.assertEqual(result["duration"], 6.0)
            self.assertTrue(any("hyperframes@0.8.221" in str(arg) for arg in calls[0]))


    def test_disabled_bridge_does_not_require_local_hyperframes_project(self):
        self.assertIsNone(
            bridge.render_hyperframes_overlay(
                {"enabled": False}, Path(tempfile.gettempdir()), 5.0
            )
        )


if __name__ == "__main__":
    unittest.main()
