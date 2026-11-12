"""Deterministic, story-aware composition decisions for the hybrid montage.

The supplied story image remains the primary visual. This module only decides
how prominently to stage it and when a supporting visual may be considered.
"""
from __future__ import annotations

from typing import Any

LAYOUT_CYCLE = ("left", "right", "center", "left", "center", "right")


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def plan_hero_composition(index: int, shock_level: int, settings: dict[str, Any]) -> dict[str, Any]:
    """Alternate full-frame supplied art with larger side/centre compositions.

    Full-frame is used for the opening, selected cadence points, and high-impact
    beats. Other shots retain the original whiteboard composition. All choices
    are deterministic and can be overridden through project settings.
    """
    index = max(0, int(index))
    shock = max(0, min(3, int(shock_level)))
    every = max(0, _safe_int(settings.get("local_full_bleed_every", 4), 4))
    threshold = _safe_int(settings.get("local_full_bleed_min_shock", 3), 3)

    is_full_frame = (
        index == 0
        or (threshold >= 0 and shock >= threshold)
        or (every > 0 and index > 0 and (index + 1) % every == 0)
    )
    if is_full_frame:
        reason = "opening" if index == 0 else (
            "high-impact beat" if threshold >= 0 and shock >= threshold else "planned cadence"
        )
        return {
            "side": "full_bleed",
            "x": 0.0,
            "y": 0.0,
            "scale": 1.0,
            "full_bleed": True,
            "reason": reason,
        }

    scene_x = float(settings.get("scene_image_x", -0.24))
    scene_y = float(settings.get("scene_image_y", -0.02))
    card_scale = float(settings.get("card_scene_scale", 0.74))
    card_scale = max(0.35, min(0.95, card_scale))
    side = LAYOUT_CYCLE[index % len(LAYOUT_CYCLE)]
    x = scene_x if side == "left" else (-scene_x if side == "right" else 0.0)
    scale = card_scale * (1.06 if side == "center" else 1.0)
    return {
        "side": side,
        "x": round(x, 4),
        "y": scene_y,
        "scale": round(scale, 4),
        "full_bleed": False,
        "reason": "supporting composition",
    }


def should_add_supporting_visual(index: int, shock_level: int, settings: dict[str, Any]) -> bool:
    """Gate extra imagery by beat importance and a restrained cadence."""
    if index <= 0 or not bool(settings.get("secondary_image_inserts", True)):
        return False

    threshold = _safe_int(settings.get("secondary_min_shock", 2), 2)
    every = max(0, _safe_int(settings.get("insert_every", 1), 1))
    if threshold >= 0 and int(shock_level) >= threshold:
        return True
    return every > 0 and (index + 1) % every == 0
