import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import toolchain_doctor


class ToolchainDoctorTests(unittest.TestCase):
    def test_detects_tools_and_reusable_packages_without_installing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            node_modules = root / "motion-lab" / "node_modules"
            (node_modules / "gsap").mkdir(parents=True)
            (node_modules / "gsap" / "package.json").write_text(
                json.dumps({"name": "gsap", "version": "3.15.0"}), encoding="utf-8"
            )
            (root / "hyperframes-engine").mkdir()
            (root / "hyperframes-engine" / "hyperframes.json").write_text("{}", encoding="utf-8")
            with patch.object(toolchain_doctor.shutil, "which", side_effect=lambda name: f"/bin/{name}" if name in {"node", "npm", "npx", "ffmpeg", "ffprobe", "capcut"} else None):
                report = toolchain_doctor.inspect_toolchain(root)
            self.assertTrue(report["packages"]["gsap"]["installed"])
            self.assertEqual(report["packages"]["gsap"]["version"], "3.15.0")
            self.assertTrue(report["renderers"]["hyperframes"])
            self.assertTrue(report["renderers"]["capcut"])

    def test_missing_optional_libraries_are_reported_without_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            report = toolchain_doctor.inspect_toolchain(Path(directory))
            self.assertFalse(report["packages"]["pixi"]["installed"])
            self.assertFalse(report["packages"]["matter"]["installed"])


if __name__ == "__main__":
    unittest.main()
