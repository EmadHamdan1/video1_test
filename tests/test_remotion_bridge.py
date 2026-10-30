import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import remotion_bridge


class RemotionBridgeTests(unittest.TestCase):
    def test_render_passes_exact_fps_and_duration_frames_and_checks_alpha(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            motion_lab = root / "motion-lab"
            binary = motion_lab / "node_modules" / ".bin"
            binary.mkdir(parents=True)
            cli = binary / "remotion"
            cli.write_text("test cli", encoding="utf-8")
            build = root / "build"
            calls = []

            def fake_run(command, **kwargs):
                calls.append(command)
                if command[0] == str(cli):
                    output = Path(command[4])
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_bytes(b"fake mov")
                    return SimpleNamespace(returncode=0, stdout="", stderr="")
                return SimpleNamespace(
                    returncode=0,
                    stdout=json.dumps({"streams": [{
                        "codec_name": "prores",
                        "pix_fmt": "yuva444p10le",
                        "width": 1920,
                        "height": 1080,
                        "duration": "4.500000",
                    }]}),
                    stderr="",
                )

            with patch.object(remotion_bridge.subprocess, "run", side_effect=fake_run), \
                 patch.object(remotion_bridge.shutil, "which", return_value="/usr/bin/ffprobe"):
                output = remotion_bridge.render_alpha_composition(
                    {"id": "CaseFileOverlay", "duration": 4.5, "fps": 30, "props": {}},
                    build,
                    motion_lab,
                )

            render_command = calls[0]
            self.assertIn("--fps", render_command)
            self.assertEqual(render_command[render_command.index("--fps") + 1], "30")
            self.assertIn("--duration", render_command)
            self.assertEqual(render_command[render_command.index("--duration") + 1], "135")
            self.assertEqual(output["duration_frames"], 135)
            self.assertEqual(output["duration"], 4.5)
            self.assertEqual(output["pixel_format"], "yuva444p10le")

    def test_render_rejects_duration_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            motion_lab = root / "motion-lab"
            binary = motion_lab / "node_modules" / ".bin"
            binary.mkdir(parents=True)
            cli = binary / "remotion"
            cli.write_text("test cli", encoding="utf-8")

            def fake_run(command, **kwargs):
                if command[0] == str(cli):
                    Path(command[4]).write_bytes(b"fake mov")
                    return SimpleNamespace(returncode=0, stdout="", stderr="")
                return SimpleNamespace(
                    returncode=0,
                    stdout=json.dumps({"streams": [{
                        "codec_name": "prores", "pix_fmt": "yuva444p10le",
                        "width": 1920, "height": 1080, "duration": "5.000000",
                    }]}),
                    stderr="",
                )

            with patch.object(remotion_bridge.subprocess, "run", side_effect=fake_run), \
                 patch.object(remotion_bridge.shutil, "which", return_value="/usr/bin/ffprobe"):
                with self.assertRaisesRegex(RuntimeError, "duration verification failed"):
                    remotion_bridge.render_alpha_composition(
                        {"id": "CaseFileOverlay", "duration": 4.5, "fps": 30, "props": {}},
                        root / "build",
                        motion_lab,
                    )


if __name__ == "__main__":
    unittest.main()
