import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import renderer_router


class RendererRouterTests(unittest.TestCase):
    def test_attaches_independent_named_graphics_tracks_and_clamps_duration(self):
        spec = {"tracks": []}
        outputs = [
            {"path": "overlay-a.mov", "renderer": "hyperframes", "track_name": "HyperFrames", "start": 0, "duration": 12},
            {"path": "overlay-b.mov", "renderer": "remotion", "track_name": "Remotion", "start": 8, "duration": 7},
            {"path": "ignored.mov", "renderer": "remotion", "track_name": "Late", "start": 12, "duration": 1},
        ]
        renderer_router.attach_graphics_tracks(spec, outputs, total_duration=12)
        self.assertEqual(len(spec["tracks"]), 2)
        self.assertEqual(spec["tracks"][0]["name"], "HyperFrames")
        self.assertEqual(spec["tracks"][1]["items"][0]["start"], 8)
        self.assertEqual(spec["tracks"][1]["items"][0]["duration"], 4)

    def test_remotion_router_clamps_requested_duration_before_render(self):
        config = {
            "remotion": {
                "enabled": True,
                "compositions": [
                    {"id": "CaseFileOverlay", "start": 4, "duration": 9, "props": {}},
                    {"id": "CaseFileOverlay", "start": 10, "duration": 3, "props": {}},
                ],
            }
        }
        fake = {"path": "overlay.mov", "duration": 5, "codec": "prores", "pixel_format": "yuva444p10le"}
        with patch.object(renderer_router.remotion_bridge, "render_alpha_composition", return_value=fake) as render:
            outputs = renderer_router.render_selected_graphics(config, Path("build"), 10, Path("."))
        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0]["start"], 4)
        self.assertEqual(outputs[0]["duration"], 6)
        self.assertEqual(render.call_args.args[0]["duration"], 6)
        self.assertEqual(render.call_args.args[0]["fps"], 30)

    def test_invalid_remotion_composition_list_is_rejected(self):
        with self.assertRaises(ValueError):
            renderer_router.render_selected_graphics(
                {"remotion": {"enabled": True, "compositions": {}}},
                Path("build"), 10, Path(".")
            )


if __name__ == "__main__":
    unittest.main()
