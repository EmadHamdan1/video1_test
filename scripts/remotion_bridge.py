"""Render a selected Remotion composition as a verified transparent overlay."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _find_remotion(motion_lab: Path) -> str | None:
    local = motion_lab / "node_modules" / ".bin"
    candidates = (
        local / "remotion.cmd",
        local / "remotion.exe",
        local / "remotion",
    )
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return shutil.which("remotion")


def render_alpha_composition(spec: dict[str, Any], build_dir: Path,
                             motion_lab: Path) -> dict[str, Any] | None:
    if not motion_lab.is_dir():
        raise FileNotFoundError(f"Remotion project was not found: {motion_lab}")
    renderer = _find_remotion(motion_lab)
    if not renderer:
        raise RuntimeError(
            "Remotion is enabled in project config, but its local CLI was not found. "
            "Run npm install inside motion-lab after reviewing package.json."
        )

    composition = str(spec.get("id", "")).strip()
    if not composition:
        raise ValueError("Each remotion.compositions entry needs an id.")
    start = float(spec.get("start", 0.0))
    duration = float(spec.get("duration", 5.0))
    if start < 0 or duration <= 0:
        raise ValueError(f"Invalid Remotion start/duration for {composition}.")
    props = spec.get("props", {})
    if not isinstance(props, dict):
        raise ValueError(f"Remotion props for {composition} must be a JSON object.")

    output_dir = build_dir / "remotion"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{composition.lower()}_{len(list(output_dir.glob('*.mov'))) + 1:03d}.mov"
    props_path = output_dir / f"{composition.lower()}_props.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")
    command = [
        renderer, "render", "src/index.ts", composition, str(output),
        "--props=" + str(props_path),
        "--codec", "prores",
        "--prores-profile", "4444",
        "--pixel-format", "yuva444p10le",
        "--image-format", "png",
    ]
    # Windows cannot launch .cmd shims through CreateProcess directly with shell=False.
    # Use cmd.exe explicitly while keeping every argument separately quoted by subprocess.
    if os.name == "nt" and renderer.lower().endswith((".cmd", ".bat")):
        command = ["cmd.exe", "/d", "/s", "/c", subprocess.list2cmdline(command)]
    result = subprocess.run(
        command, cwd=str(motion_lab), env=os.environ.copy(),
        text=True, capture_output=True, check=False,
        timeout=int(spec.get("timeout_seconds", 1800)),
    )
    if result.returncode != 0 or not output.is_file():
        detail = (result.stderr or result.stdout or "No Remotion output.").strip()
        raise RuntimeError(f"Remotion render failed for {composition}:\n{detail[-4000:]}")

    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("FFprobe is required to verify Remotion alpha output.")
    probe = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name,pix_fmt,width,height,duration",
         "-of", "json", str(output)],
        text=True, capture_output=True, check=False,
    )
    if probe.returncode != 0:
        raise RuntimeError("FFprobe failed on Remotion output: " + probe.stderr[-1500:])
    stream = (json.loads(probe.stdout).get("streams") or [{}])[0]
    codec, pixel_format = str(stream.get("codec_name", "")), str(stream.get("pix_fmt", ""))
    if codec != "prores" or "a" not in pixel_format:
        raise RuntimeError(
            f"Remotion alpha verification failed for {composition}: codec={codec}, pix_fmt={pixel_format}."
        )
    return {
        "path": str(output.resolve()),
        "composition": composition,
        "codec": codec,
        "pixel_format": pixel_format,
        "width": int(stream.get("width", 1920)),
        "height": int(stream.get("height", 1080)),
        "duration": float(duration),
        "source_duration": float(stream.get("duration") or duration),
    }
