import io
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prepare_assets


def png_bytes(with_alpha: bool) -> bytes:
    output = io.BytesIO()
    if with_alpha:
        image = Image.new("RGBA", (64, 64), (20, 30, 40, 0))
        for x in range(16, 48):
            for y in range(16, 48):
                image.putpixel((x, y), (20, 30, 40, 255))
    else:
        image = Image.new("RGB", (64, 64), (20, 30, 40))
    image.save(output, format="PNG")
    return output.getvalue()


class BackgroundRemovalTests(unittest.TestCase):
    def make_project(self, directory: str, selected: str = "yes",
                     reviewed: str = "yes") -> tuple[dict[str, Path], Path]:
        root = Path(directory)
        paths = prepare_assets.project_paths(str(root))
        paths["generated"].mkdir(parents=True, exist_ok=True)
        source = paths["images"] / "rescue-pulley.jpg"
        source.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (64, 64), (120, 90, 70)).save(source, format="JPEG")
        prepare_assets.write_csv(paths["manifest"], [{
            "id": "C0001",
            "kind": "image",
            "segment_id": "scene_003",
            "title": "Rescue pulley",
            "creator": "Photographer",
            "source": "Test stock provider",
            "license": "Reviewed test license",
            "license_url": "https://example.com/license",
            "source_page": "https://example.com/source",
            "selected": selected,
            "downloaded_path": str(source.resolve()),
            "license_reviewed": reviewed,
            "review_notes": "Reviewed test terms.",
        }])
        return paths, source

    def test_requires_explicit_model_download_acknowledgement(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "may download a local model"):
                prepare_assets.remove_background(directory, "C0001", False)

    def test_rejects_unselected_or_unreviewed_source_before_loading_rembg(self):
        fake = types.ModuleType("rembg")
        fake.remove = lambda data: png_bytes(True)
        with tempfile.TemporaryDirectory() as directory:
            self.make_project(directory, selected="yes", reviewed="no")
            with patch.dict(sys.modules, {"rembg": fake}):
                with self.assertRaisesRegex(ValueError, "Review the source/model terms"):
                    prepare_assets.remove_background(directory, "C0001", True)

    def test_creates_a_real_alpha_cutout_and_keeps_provenance(self):
        fake = types.ModuleType("rembg")
        fake.remove = lambda data: png_bytes(True)
        with tempfile.TemporaryDirectory() as directory:
            paths, _ = self.make_project(directory)
            with patch.dict(sys.modules, {"rembg": fake}):
                target = prepare_assets.remove_background(directory, "C0001", True)
            self.assertTrue(target.is_file())
            with Image.open(target) as image:
                self.assertEqual(image.mode, "RGBA")
                self.assertEqual(image.getchannel("A").getextrema(), (0, 255))
            rows = prepare_assets.read_csv(paths["manifest"])
            source = next(row for row in rows if row["id"] == "C0001")
            derivative = next(row for row in rows if row["id"] == "C0002")
            self.assertEqual(source["selected"], "no")
            self.assertEqual(derivative["selected"], "yes")
            self.assertEqual(derivative["license_reviewed"], "yes")
            self.assertIn("source licence/model terms remain applicable", derivative["review_notes"])
            self.assertTrue(target.with_suffix(".png.source.txt").is_file())

    def test_rejects_opaque_output_instead_of_claiming_alpha(self):
        fake = types.ModuleType("rembg")
        fake.remove = lambda data: png_bytes(False)
        with tempfile.TemporaryDirectory() as directory:
            self.make_project(directory)
            with patch.dict(sys.modules, {"rembg": fake}):
                with self.assertRaisesRegex(ValueError, "did not produce visible transparent pixels"):
                    prepare_assets.remove_background(directory, "C0001", True)
            generated = list((Path(directory) / "assets" / "generated").glob("*.png"))
            self.assertEqual(generated, [])


if __name__ == "__main__":
    unittest.main()
