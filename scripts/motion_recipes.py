"""Reusable, deterministic keyframe recipes for layered CapCut still-image motion.

Only uses properties already emitted by the current CapCut CLI pipeline:
uniform_scale, position_x, position_y and rotation. It intentionally avoids
unverified alpha/opacity, masks, blur, and native transition slugs.
"""
from __future__ import annotations

from typing import Any

RECIPES = (
    "from_left", "from_right", "from_top", "from_bottom",
    "scale_pop", "tilt_swing", "diagonal_sweep", "zoom_through",
    "rise_overshoot", "drop_bounce",
)
EXIT_RECIPES = ("shrink_away", "slide_away", "drop_away", "tilt_away", "zoom_away")


def overlay_layout(index: int, hero_x: float, shock: int = 0) -> dict[str, Any]:
    """Pick a visually varied overlay layout. Returns one or two non-overlapping slots."""
    side = 1.0 if hero_x < -0.08 else (-1.0 if hero_x > 0.08 else (1.0 if index % 2 == 0 else -1.0))
    # High-impact beats and selected odd/even rhythm points briefly create a two-insert collage.
    if shock >= 3 or index % 5 == 3:
        return {
            "name": "paired_top_cards",
            "slots": [
                {"x": -0.48, "y": -0.36, "scale": 0.18, "recipe": "from_left"},
                {"x": 0.48, "y": -0.36, "scale": 0.18, "recipe": "from_right"},
            ],
        }
    patterns = (
        {"name": "opposite_side", "x": side * 0.66, "y": 0.18, "scale": 0.235, "recipe": "from_left" if side > 0 else "from_right"},
        {"name": "upper_corner", "x": side * 0.65, "y": -0.34, "scale": 0.19, "recipe": "drop_bounce"},
        {"name": "lower_corner", "x": side * 0.62, "y": 0.39, "scale": 0.20, "recipe": "rise_overshoot"},
        {"name": "floating_detail", "x": side * 0.70, "y": -0.02, "scale": 0.22, "recipe": "tilt_swing"},
        {"name": "centre_pop", "x": 0.0, "y": 0.34, "scale": 0.225, "recipe": "scale_pop"},
        {"name": "diagonal_detail", "x": side * 0.58, "y": -0.29, "scale": 0.205, "recipe": "diagonal_sweep"},
        {"name": "zoom_detail", "x": side * 0.64, "y": 0.14, "scale": 0.24, "recipe": "zoom_through"},
    )
    slot = dict(patterns[index % len(patterns)])
    name = slot.pop("name")
    return {"name": name, "slots": [slot]}


def apply_layer_motion(tl: Any, ref: str, duration: float, scale: float, x: float, y: float,
                       recipe: str, index: int = 0) -> None:
    """Animate one layered image through entrance, restrained hold and a different exit."""
    D = max(0.25, float(duration))
    S = max(0.035, float(scale))
    enter = min(0.32, max(0.14, D * 0.22))
    exit_len = min(0.22, max(0.12, D * 0.16))
    exit_at = max(enter + 0.06, D - exit_len)
    direction = -1.0 if index % 2 else 1.0
    rotation = 0.0
    start_x, start_y, start_scale = x, y, 0.72 * S
    peak_scale = 1.06 * S

    if recipe == "from_left":
        start_x, start_scale = x - 1.18, 0.82 * S
        rotation = -4.0
    elif recipe == "from_right":
        start_x, start_scale = x + 1.18, 0.82 * S
        rotation = 4.0
    elif recipe == "from_top":
        start_y, start_scale = y - 1.12, 0.82 * S
        rotation = -2.5 * direction
    elif recipe == "from_bottom":
        start_y, start_scale = y + 1.12, 0.82 * S
        rotation = 2.5 * direction
    elif recipe == "scale_pop":
        start_scale, peak_scale = 0.035 * S, 1.12 * S
        start_y = y + 0.10
        rotation = -3.0 * direction
    elif recipe == "tilt_swing":
        start_x, start_y, start_scale = x + 0.18 * direction, y - 0.20, 0.035 * S
        rotation = -16.0 * direction
        peak_scale = 1.08 * S
    elif recipe == "diagonal_sweep":
        start_x, start_y, start_scale = x - 0.90 * direction, y + 0.72, 0.76 * S
        rotation = 5.0 * direction
    elif recipe == "zoom_through":
        start_scale, peak_scale = 1.42 * S, 0.92 * S
        start_x, start_y = x + 0.06 * direction, y
    elif recipe == "rise_overshoot":
        start_y, start_scale = y + 1.02, 0.78 * S
        peak_scale = 1.07 * S
    elif recipe == "drop_bounce":
        start_y, start_scale = y - 1.02, 0.78 * S
        peak_scale = 1.08 * S
        rotation = 3.0 * direction
    else:
        # Safe predictable fallback rather than emitting arbitrary keyframe operations.
        recipe = "from_left"
        start_x, start_scale, rotation = x - 1.18, 0.82 * S, -4.0

    # Enter, slight settle, then an understated drift; values are all bounded in time.
    tl.key(ref, "position_x", 0.0, start_x)
    tl.key(ref, "position_y", 0.0, start_y)
    tl.key(ref, "uniform_scale", 0.0, start_scale)
    tl.key(ref, "rotation", 0.0, rotation)
    tl.key(ref, "uniform_scale", enter * 0.68, peak_scale, "ease-out")
    tl.key(ref, "position_x", enter * 0.72, x + (0.012 * direction), "ease-out")
    tl.key(ref, "position_y", enter * 0.72, y - 0.008, "ease-out")
    tl.key(ref, "rotation", enter * 0.72, rotation * 0.16, "ease-out")
    tl.key(ref, "uniform_scale", enter, S, "ease-out")
    tl.key(ref, "position_x", enter, x, "ease-out")
    tl.key(ref, "position_y", enter, y, "ease-out")
    tl.key(ref, "rotation", enter, 0.0, "ease-out")

    hold_span = max(0.02, exit_at - enter)
    idle_t = enter + hold_span * 0.52
    tl.key(ref, "position_x", idle_t, x - 0.008 * direction, "ease-in-out")
    tl.key(ref, "position_y", idle_t, y + 0.010, "ease-in-out")
    tl.key(ref, "uniform_scale", idle_t, S * 1.012, "ease-in-out")
    tl.key(ref, "position_x", exit_at, x, "ease-in-out")
    tl.key(ref, "position_y", exit_at, y, "ease-in-out")

    exit_recipe = EXIT_RECIPES[index % len(EXIT_RECIPES)]
    if exit_recipe == "shrink_away":
        tl.key(ref, "uniform_scale", D, 0.035 * S, "ease-in")
        tl.key(ref, "rotation", D, 6.0 * direction, "ease-in")
    elif exit_recipe == "slide_away":
        tl.key(ref, "position_x", D, x + 1.16 * direction, "ease-in")
        tl.key(ref, "uniform_scale", D, 0.82 * S, "ease-in")
        tl.key(ref, "rotation", D, 4.0 * direction, "ease-in")
    elif exit_recipe == "drop_away":
        tl.key(ref, "position_y", D, y + 1.02, "ease-in")
        tl.key(ref, "uniform_scale", D, 0.78 * S, "ease-in")
    elif exit_recipe == "tilt_away":
        tl.key(ref, "position_x", D, x + 0.42 * direction, "ease-in")
        tl.key(ref, "rotation", D, 15.0 * direction, "ease-in")
        tl.key(ref, "uniform_scale", D, 0.82 * S, "ease-in")
    else:  # zoom_away
        tl.key(ref, "uniform_scale", D, 1.28 * S, "ease-in")
        tl.key(ref, "position_y", D, y - 0.06, "ease-in")


def staggered_pair_offsets(index: int) -> tuple[float, float]:
    """Small timing offset between two cards, deterministic per scene."""
    return (0.0, 0.08 if index % 2 == 0 else 0.12)
