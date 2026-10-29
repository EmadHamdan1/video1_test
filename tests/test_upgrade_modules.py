import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import qa_spec
import stock_fetcher
import text_system


class FakeTimeline:
    def __init__(self):
        self.keys = []

    def key(self, ref, prop, time, value, easing=None):
        self.keys.append((ref, prop, time, value, easing))


class MontageUpgradeTests(unittest.TestCase):
    def test_concrete_stock_queries_are_deduplicated(self):
        beats = [
            {"stock_query": "dark cave entrance", "trigger_word": "CAVE"},
            {"stock_query": "Dark Cave Entrance", "trigger_word": "CAVE"},
            {"trigger_word": "TWENTY SEVEN"},
        ]
        queries = stock_fetcher.build_queries(beats)
        self.assertEqual([item["query"] for item in queries], ["dark cave entrance"])
        self.assertEqual(queries[0]["beat"], 0)

    def test_wikimedia_licence_filter_rejects_nc_and_nd(self):
        self.assertTrue(stock_fetcher.license_ok("CC0"))
        self.assertTrue(stock_fetcher.license_ok("CC BY 4.0"))
        self.assertFalse(stock_fetcher.license_ok("CC BY-NC 4.0"))
        self.assertFalse(stock_fetcher.license_ok("CC BY-ND 4.0"))
        self.assertFalse(stock_fetcher.license_ok("CC BY-SA 4.0"))
        self.assertTrue(stock_fetcher.license_ok("CC BY-SA 4.0", allow_share_alike=True))

    def test_text_recipe_selection_varies_by_semantic_role(self):
        self.assertEqual(len({text_system.choose_text_recipe("alert", i) for i in range(3)}), 3)
        self.assertEqual(len({text_system.choose_text_recipe("stat", i) for i in range(3)}), 3)
        self.assertEqual(len({text_system.choose_text_recipe("chapter", i) for i in range(3)}), 3)
        for recipe_index in range(5):
            timeline = FakeTimeline()
            recipe = text_system.choose_text_recipe("keyword", recipe_index)
            text_system.text_motion(timeline, "label", 1.2, -0.2, recipe=recipe, x=0.25)
            self.assertTrue(any(key[1] == "uniform_scale" for key in timeline.keys))
            self.assertTrue(any(key[1] == "rotation" for key in timeline.keys))
            self.assertLessEqual(max(key[2] for key in timeline.keys), 1.2)

    def test_transparent_png_is_detected_for_cutout_overlays(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rgba_path = root / "transparent.png"
            rgb_path = root / "opaque.jpg"
            Image.new("RGBA", (32, 32), (255, 0, 0, 0)).save(rgba_path)
            Image.new("RGB", (32, 32), (255, 0, 0)).save(rgb_path, "JPEG")
            self.assertTrue(stock_fetcher._image_has_transparency(rgba_path))
            self.assertFalse(stock_fetcher._image_has_transparency(rgb_path))

    def test_text_size_and_safe_area(self):
        self.assertEqual(text_system.classify("RUN", 3), "alert")
        self.assertEqual(text_system.classify("27 HOURS", 0), "stat")
        self.assertGreaterEqual(text_system.size_for("keyword", 22, "A VERY LONG CALLOUT"), 16)
        x, y = text_system.safe_xy(2.0, -3.0)
        self.assertEqual((x, y), (0.88, -0.88))

    def test_overlapping_texts_are_separated(self):
        items = [
            {"start": 0, "duration": 1.0, "x": 0, "y": 0.5},
            {"start": 0.2, "duration": 1.0, "x": 0.1, "y": 0.52},
        ]
        text_system.avoid_collisions(items)
        self.assertGreaterEqual(abs(items[1]["y"] - items[0]["y"]), 0.1)

    def test_text_motion_has_sorted_safe_keyframes_and_caps_are_opt_in(self):
        timeline = FakeTimeline()
        text_system.text_motion(timeline, "kw", 1.0, 0.4)
        position_times = [key[2] for key in timeline.keys if key[1] == "position_y"]
        self.assertEqual(position_times, sorted(position_times))
        self.assertGreaterEqual(sum(key[1] == "uniform_scale" for key in timeline.keys), 4)
        self.assertFalse(any(key[1] in {"alpha", "opacity"} for key in timeline.keys))

        timeline = FakeTimeline()
        text_system.text_motion(timeline, "kw", 1.0, 0.4, {"opacity_property": "alpha"})
        self.assertTrue(any(key[1] == "alpha" for key in timeline.keys))
        self.assertLessEqual(max(key[2] for key in timeline.keys), 1.0)

    def test_qa_flags_large_text_overlap_and_static_gap(self):
        spec = {"tracks": [
            {"type": "video", "name": "Scene Artwork", "items": [
                {"ref": "first", "start": 0, "duration": 2},
                {"ref": "next", "start": 9, "duration": 2},
            ]},
            {"type": "text", "name": "Keyword Callouts", "items": [
                {"ref": "big", "start": 0, "duration": 1, "fontSize": 60, "x": 0, "y": 0.5},
                {"ref": "overlap", "start": 0.4, "duration": 1, "fontSize": 20, "x": 0.1, "y": 0.52},
            ]},
        ]}
        issues = " ".join(qa_spec.audit_spec(spec))
        for expected in ("TEXT_SIZE big", "TEXT_OVERLAP", "STATIC_GAP"):
            self.assertIn(expected, issues)

    def test_lower_resolution_transparent_cutout_is_kept_but_not_as_full_bleed_stock(self):
        from PIL import Image, ImageDraw

        candidate = {
            "provider": "pexels", "id": "transparent-1", "kind": "photo",
            "url": "https://images.example.test/cutout.png", "width": 900, "height": 900,
            "license": "Pexels License", "page_url": "https://www.pexels.com/photo/cutout/",
            "credit": "Photo by Test on Pexels (https://www.pexels.com/photo/cutout/)",
        }
        original_search = stock_fetcher.pexels_search
        original_key = os.environ.get("PEXELS_API_KEY")
        stock_fetcher.pexels_search = lambda *_args, **_kwargs: [candidate]
        os.environ["PEXELS_API_KEY"] = "test-key"
        try:
            buffer = io.BytesIO()
            image = Image.new("RGBA", (900, 900), (0, 0, 0, 0))
            ImageDraw.Draw(image).ellipse((80, 80, 820, 820), fill=(220, 40, 40, 255))
            image.save(buffer, "PNG")
            with tempfile.TemporaryDirectory() as temporary:
                config = {
                    "settings": {"stock_media": {
                        "enabled": True, "providers": ["pexels"], "per_query": 1, "max_total": 2,
                        "min_width": 1280, "min_cutout_width": 640,
                    }},
                    "story_beats": [{"stock_query": "transparent cave rescue cutout"}],
                }
                assets = stock_fetcher.fetch_stock(
                    config, Path(temporary), log=lambda _message: None,
                    http_get=lambda _url: buffer.getvalue(),
                )
            self.assertEqual(len(assets), 1)
            self.assertTrue(assets[0]["alpha_channel"])
            self.assertLess(assets[0]["width"], 1280)
        finally:
            stock_fetcher.pexels_search = original_search
            if original_key is None:
                os.environ.pop("PEXELS_API_KEY", None)
            else:
                os.environ["PEXELS_API_KEY"] = original_key

    def test_stock_fetch_is_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = stock_fetcher.fetch_stock({"settings": {"stock_media": {"enabled": False}}}, Path(temporary))
            self.assertEqual(result, [])

    def test_fetch_stock_is_cached_and_credits_are_written(self):
        from PIL import Image
        candidate = {
            "provider": "pexels", "id": "1", "kind": "photo",
            "url": "https://images.example.test/a.jpg", "width": 1920, "height": 1080,
            "license": "Pexels License", "page_url": "https://www.pexels.com/photo/example/",
            "credit": "Photo by Test on Pexels (https://www.pexels.com/photo/example/)",
        }
        original_search = stock_fetcher.pexels_search
        original_key = os.environ.get("PEXELS_API_KEY")
        search_count = 0

        def search(*args, **kwargs):
            nonlocal search_count
            search_count += 1
            return [candidate]

        stock_fetcher.pexels_search = search
        os.environ["PEXELS_API_KEY"] = "test-key"
        try:
            with tempfile.TemporaryDirectory() as temporary:
                buffer = io.BytesIO()
                Image.new("RGB", (512, 512), "red").save(buffer, "JPEG")
                config = {
                    "settings": {"stock_media": {
                        "enabled": True, "providers": ["pexels"], "per_query": 1, "max_total": 10,
                    }},
                    "story_beats": [{"stock_query": "dark cave entrance"}],
                }
                def download(_url):
                    return buffer.getvalue()
                first = stock_fetcher.fetch_stock(config, Path(temporary), log=lambda _message: None, http_get=download)
                second = stock_fetcher.fetch_stock(config, Path(temporary), log=lambda _message: None, http_get=download)
                credits = (Path(temporary) / "assets" / "stock" / "CREDITS.txt").read_text(encoding="utf-8")
                contact_sheet_created = (Path(temporary) / "build" / "ASSET_STOCK_CONTACT_SHEET.jpg").is_file()
            self.assertEqual(len(first), 1)
            self.assertEqual(len(second), 1)
            self.assertEqual(search_count, 1)
            self.assertIn("Pexels", credits)
            self.assertTrue(contact_sheet_created)
        finally:
            stock_fetcher.pexels_search = original_search
            if original_key is None:
                os.environ.pop("PEXELS_API_KEY", None)
            else:
                os.environ["PEXELS_API_KEY"] = original_key


if __name__ == "__main__":
    unittest.main()
