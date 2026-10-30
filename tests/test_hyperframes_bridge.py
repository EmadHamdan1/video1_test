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

    def test_disabled_bridge_does_not_require_local_hyperframes_project(self):
        self.assertIsNone(
            bridge.render_hyperframes_overlay(
                {"enabled": False}, Path(tempfile.gettempdir()), 5.0
            )
        )


if __name__ == "__main__":
    unittest.main()
