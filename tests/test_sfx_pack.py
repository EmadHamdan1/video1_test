import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import sfx_pack


class SfxPackTests(unittest.TestCase):
    def _audio_file(self, root: Path, name: str) -> Path:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"RIFF" + (b"\x00" * 2048))
        return path

    def test_pack_discovery_honours_environment_override(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pack = root / "custom" / "Saoud_SFX_Pack"
            pack.mkdir(parents=True)
            with patch.dict(os.environ, {"SAOUD_SFX_PACK": str(pack)}):
                found = sfx_pack.find_sfx_pack(root, root / "project", root / "source" / "voice.mp3")
            self.assertEqual(found, pack.resolve())

    def test_audio_discovery_filters_extensions_and_tiny_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            good = self._audio_file(root, "Paper_Whoosh.wav")
            self._audio_file(root, "readme.txt")
            tiny = root / "tiny.mp3"
            tiny.write_bytes(b"x")
            found = sfx_pack.discover_audio_files(root)
            self.assertEqual(found, [good.resolve()])

    def test_named_files_map_to_distinct_story_sound_roles(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            expected = {
                "whoosh": "paper_whoosh.wav",
                "pop": "cartoon_pop.wav",
                "scratch": "vinyl_scratch.wav",
                "bass_drop": "bass_drop.wav",
                "heartbeat": "heartbeat.wav",
                "air_gasp": "air_gasp.wav",
                "low_hit": "low_hit.wav",
                "rope_snap": "rope_snap.wav",
                "soft_click": "camera_shutter.wav",
                "concrete_thud": "concrete_thud.wav",
            }
            files = [self._audio_file(root, name) for name in expected.values()]
            selected = sfx_pack.select_sfx_sources(files)
            for kind, filename in expected.items():
                with self.subTest(kind=kind):
                    self.assertEqual(selected[kind].name, filename)
            self.assertEqual(len(set(selected.values())), len(selected))


if __name__ == "__main__":
    unittest.main()
