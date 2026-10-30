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


def build_production_plan(config: dict[str, Any], scenes: list[dict[str, Any]],
                          duration: float, toolchain: dict[str, Any] | None = None) -> dict[str, Any]:
    beats = config.get("story_beats", [])
    beats = beats if isinstance(beats, list) else []
    planned: list[dict[str, Any]] = []
    recent_motion: list[str] = []

    for index, scene in enumerate(scenes):
        beat = _beat_for_scene(scene, beats, duration)
        beat_id = str(beat.get("scene_id") or f"beat_{index + 1:03d}")
        scene_id = str(scene.get("scene_ref") or f"scene_{index + 1:03d}")
        emotion = str(beat.get("emotion", scene.get("emotion", "neutral")))
        shock = max(0, min(3, int(beat.get("shock_level", scene.get("shock_level", 0)) or 0))
        primary = str(scene.get("source_image") or scene.get("image") or "")
        stock = str(scene.get("stock_source_path") or "")
        planned_entrance_id = str(scene.get("motion_recipe_id", "")).strip()
        enter = (
            motion_library.get_recipe(planned_entrance_id)
            if planned_entrance_id in motion_library.CATALOG
            else motion_library.choose_recipe("entrance", emotion, shock, scene_id, recent_motion)
        )
        # The selected recipe contains its paired exit choreography. Do not choose
        # a second unrelated exit and let the report disagree with the CapCut timeline.
        exit_recipe = enter
        camera = motion_library.choose_recipe("camera", emotion, shock, scene_id + ":camera", recent_motion)
        recent_motion.extend([enter["id"], camera["id"]])
        recent_motion = recent_motion[-15:]

        supporting: list[dict[str, Any]] = []
        if stock:
            supporting.append({
                "asset": stock,
                "role": "licensed_stock_support",
                "provenance_required": True,
            })

        planned.append({
            "scene_id": scene_id,
            "beat_id": beat_id,
            "start": round(float(scene.get("start", 0.0)), 3),
            "end": round(float(scene.get("end", duration)), 3),
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
            "composition": {
                "layout": str(scene.get("layout", "full-frame")),
                "focal_region": scene.get("focal_region"),
                "focal_region_confidence": scene.get("focal_region_confidence", 0.0),
                "requires_visual_review": not bool(scene.get("focal_region")),
            },
            "motion": {
                "entrance": enter["id"],
                "hold": camera["id"],
                "exit": exit_recipe["id"],
                "transition_out": motion_library.choose_recipe(
                    "transition", emotion, shock, scene_id + ":transition", recent_motion
                )["id"],
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
