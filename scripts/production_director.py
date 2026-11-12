"""Build a renderer-neutral documentary shot plan from timed story beats."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import motion_library


def _beat_for_scene(scene: dict[str, Any], beats: list[dict[str, Any]], duration: float) -> dict[str, Any]:
    midpoint = (float(scene.get("start", 0.0)) + float(scene.get("end", duration))) / 2
    for beat in beats:
        start = float(beat.get("start_s", 0.0))
        end = float(beat.get("end_s", duration))
        if start <= midpoint <= end:
            return beat
    if not beats:
        return {}
    return min(
        beats,
        key=lambda item: abs(
            (float(item.get("start_s", 0.0)) + float(item.get("end_s", duration))) / 2 - midpoint
        ),
    )


def _intersects(start: float, end: float, item_start: float, item_duration: float) -> bool:
    return item_start < end and item_start + item_duration > start


def _layers_for_scene(config: dict[str, Any], spec: dict[str, Any] | None,
                      start: float, end: float) -> dict[str, list[dict[str, Any]]]:
    graphics: list[dict[str, Any]] = []
    supporting: list[dict[str, Any]] = []

    for renderer_name, key in (("hyperframes", "elements"), ("remotion", "compositions")):
        renderer = config.get(renderer_name, {})
        if not isinstance(renderer, dict) or not renderer.get("enabled", False):
            continue
        values = renderer.get(key, [])
        if not isinstance(values, list):
            continue
        for item in values:
            if not isinstance(item, dict):
                continue
            item_start = max(0.0, float(item.get("start", 0.0)))
            item_duration = max(0.0, float(item.get("duration", 0.0)))
            if item_duration <= 0 or not _intersects(start, end, item_start, item_duration):
                continue
            graphics.append({
                "renderer": renderer_name,
                "id": str(item.get("id", item.get("ref", ""))),
                "type": str(item.get("type", item.get("id", "composition"))),
                "start": item_start,
                "duration": item_duration,
                "purpose": str(item.get("visual_purpose", item.get("title", item.get("text", "")))),
                "asset": str(item.get("path", item.get("src", ""))),
                "independent_layer": True,
            })

    if spec:
        for track in spec.get("tracks", []):
            name = str(track.get("name", ""))
            if name not in {"Fast Secondary Image Inserts", "Story Fact Callouts", "Icon Overlays"}:
                continue
            for item in track.get("items", []):
                item_start = max(0.0, float(item.get("start", 0.0)))
                item_duration = max(0.0, float(item.get("duration", 0.0)))
                if item_duration <= 0 or not _intersects(start, end, item_start, item_duration):
                    continue
                supporting.append({
                    "track": name,
                    "ref": str(item.get("ref", "")),
                    "asset": str(item.get("path", item.get("text", ""))),
                    "start": item_start,
                    "duration": item_duration,
                    "media_type": str(item.get("type", track.get("type", ""))),
                    "independent_layer": True,
                })
    return {"supporting": supporting, "graphics": graphics}


def build_production_plan(config: dict[str, Any], scenes: list[dict[str, Any]],
                          duration: float, toolchain: dict[str, Any] | None = None,
                          spec: dict[str, Any] | None = None) -> dict[str, Any]:
    beats = config.get("story_beats", [])
    beats = beats if isinstance(beats, list) else []
    planned: list[dict[str, Any]] = []
    recent_motion: list[str] = []

    for index, scene in enumerate(scenes):
        beat = _beat_for_scene(scene, beats, duration)
        beat_id = str(beat.get("scene_id") or f"beat_{index + 1:03d}")
        scene_id = str(scene.get("scene_ref") or f"scene_{index + 1:03d}")
        emotion = str(beat.get("emotion", scene.get("emotion", "neutral")))
        shock = max(0, min(3, int(beat.get("shock_level", scene.get("shock_level", 0)) or 0)))
        primary = str(scene.get("source_image") or scene.get("image") or "")
        stock = str(scene.get("stock_source_path") or "")
        planned_entrance_id = str(scene.get("motion_recipe_id", "")).strip()
        enter = (
            motion_library.get_recipe(planned_entrance_id)
            if planned_entrance_id in motion_library.CATALOG
            else motion_library.choose_recipe("entrance", emotion, shock, scene_id, recent_motion)
        )
        camera_id = str(scene.get("camera_recipe_id", "")).strip()
        camera = (
            motion_library.get_recipe(camera_id)
            if camera_id in motion_library.CATALOG
            else motion_library.choose_recipe("camera", emotion, shock, scene_id + ":camera", recent_motion)
        )
        transition_id = str(scene.get("transition_recipe_id", "")).strip()
        transition = (
            motion_library.get_recipe(transition_id)
            if transition_id in motion_library.CATALOG
            else motion_library.choose_recipe("transition", emotion, shock, scene_id + ":transition", recent_motion)
        )
        recent_motion.extend([enter["id"], camera["id"], transition["id"]])
        recent_motion = recent_motion[-15:]

        scene_start = round(float(scene.get("start", 0.0)), 3)
        scene_end = round(float(scene.get("end", duration)), 3)
        layers = _layers_for_scene(config, spec, scene_start, scene_end)
        supporting: list[dict[str, Any]] = list(layers["supporting"])
        if stock:
            supporting.append({
                "asset": stock,
                "role": "licensed_stock_support",
                "provenance_required": True,
            })

        planned.append({
            "scene_id": scene_id,
            "beat_id": beat_id,
            "start": scene_start,
            "end": scene_end,
            "duration": round(float(scene.get("duration", 0.0)), 3),
            "narration_reference": {
                "text": str(beat.get("text", scene.get("caption_context", ""))),
                "start": beat.get("start_s"),
                "end": beat.get("end_s"),
            },
            "emotion": emotion,
            "shock_level": shock,
            "visual_purpose": str(beat.get("visual_purpose", beat.get("stock_query", ""))),
            "primary_asset": primary,
            "supporting_assets": supporting,
            "graphics_layers": layers["graphics"],
            "composition": {
                "layout": str(scene.get("layout", "full-frame")),
                "focal_region": scene.get("focal_region"),
                "focal_region_confidence": scene.get("focal_region_confidence", 0.0),
                "requires_visual_review": not bool(scene.get("focal_region")),
            },
            "motion": {
                "entrance": enter["id"],
                "hold": camera["id"],
                "exit": transition["id"],
                "transition_out": transition["id"],
                "capcut_entrance_style": motion_library.hero_entrance_style(enter),
                "capcut_exit_style": str(scene.get("capcut_transition_style") or motion_library.capcut_transition_exit(transition)),
                "capcut_hold_profile": motion_library.capcut_hold_profile(camera),
            },
            "screen_text": [],
            "renderer_roles": {
                "source_media": "capcut",
                "complex_graphics": "hyperframes",
                "reusable_react_graphics": "remotion",
            },
        })

    return {
        "schema_version": 1,
        "project": str(config.get("project_name", "Video1 Production")),
        "duration": round(float(duration), 3),
        "fps": int((config.get("canvas") or {}).get("fps", 30)),
        "canvas": config.get("canvas", {"width": 1920, "height": 1080, "fps": 30}),
        "text_policy": {
            "narration_subtitles": False,
            "spoken_transcript_on_screen": False,
            "allow_story_labels": True,
            "rule": "Only reviewed functional labels, dates, measurements, and chapter markers may be visible.",
        },
        "motion_catalogue": motion_library.catalogue_summary(),
        "toolchain": toolchain or {},
        "scenes": planned,
    }


def write_production_plan(plan: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
