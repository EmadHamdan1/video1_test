"""Route selected motion compositions to their specialised renderers."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import hyperframes_bridge
import remotion_bridge


def render_selected_graphics(config: dict[str, Any], build_dir: Path, duration: float,
                             project_root: Path) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    hyperframes = config.get("hyperframes", {})
    if isinstance(hyperframes, dict) and hyperframes.get("enabled", False) and hyperframes.get("elements"):
        rendered = hyperframes_bridge.render_hyperframes_overlay(
            hyperframes,
            build_dir,
            duration,
            project_template=project_root / "hyperframes-engine",
        )
        if rendered:
            outputs.append({
                **rendered,
                "renderer": "hyperframes",
                "track_name": "HyperFrames Motion Graphics",
                "start": 0.0,
                "duration": round(float(duration), 3),
            })

    remotion = config.get("remotion", {})
    project_fps = int((config.get("canvas") or {}).get("fps", 30))
    if isinstance(remotion, dict) and remotion.get("enabled", False):
        compositions = remotion.get("compositions", [])
        if not isinstance(compositions, list):
            raise ValueError("remotion.compositions must be a list.")
        for index, item in enumerate(compositions, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"Remotion composition {index} must be an object.")
            start = max(0.0, float(item.get("start", 0.0)))
            requested_duration = float(item.get("duration", 5.0))
            if requested_duration <= 0:
                raise ValueError(f"Remotion composition {index} duration must be positive.")
            if start >= duration:
                continue
            clip_duration = min(requested_duration, duration - start)
            render_spec = {**item, "duration": clip_duration, "fps": int(item.get("fps", project_fps))}
            rendered = remotion_bridge.render_alpha_composition(
                render_spec,
                build_dir,
                project_root / "motion-lab",
            )
            if rendered:
                outputs.append({
                    **rendered,
                    "renderer": "remotion",
                    "track_name": str(item.get("track_name") or f"Remotion Graphics {index:02d}"),
                    "start": start,
                    "duration": clip_duration,
                })
    return outputs


def attach_graphics_tracks(spec: dict[str, Any], outputs: list[dict[str, Any]],
                           total_duration: float | None = None) -> None:
    tracks = spec.setdefault("tracks", [])
    if not isinstance(tracks, list):
        raise ValueError("CapCut compile spec tracks must be a list.")
    for index, output in enumerate(outputs, start=1):
        start = max(0.0, float(output.get("start", 0.0)))
        requested = max(0.0, float(output.get("duration", 0.0)))
        if total_duration is not None:
            if start >= float(total_duration):
                continue
            requested = min(requested, float(total_duration) - start)
        duration = requested
        if duration < 0.1:
            continue
        tracks.append({
            "type": "video",
            "name": str(output.get("track_name") or f"Motion Graphics {index:02d}"),
            "items": [{
                "type": "video",
                "path": str(output["path"]),
                "start": round(start, 3),
                "duration": round(duration, 3),
                "ref": f"{output.get('renderer', 'graphics')}_graphics_{index:03d}",
                "scale": 1.0,
                "x": 0.0,
                "y": 0.0,
                "rotation": 0,
            }],
        })
