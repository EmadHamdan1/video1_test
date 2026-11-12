"""Consistent, restrained title styling and text-motion helpers for the CapCut spec."""
from __future__ import annotations

import re
from typing import Any

PALETTE = {"ink": "#15191E", "paper": "#FFFFFF", "alert": "#E02424", "gold": "#F6CF45"}
SAFE = 0.88
TIERS = {"keyword": 1.0, "stat": 1.18, "chapter": 0.82}


def classify(word: str, shock: int) -> str:
    if shock >= 2:
        return "alert"
    if re.search(r"\d", word):
        return "stat"
    return "keyword"


def style_for(kind: str) -> tuple[str, dict[str, Any]]:
    if kind == "alert":
        return PALETTE["alert"], {"borderWidth": 3.0, "borderColor": PALETTE["paper"], "borderAlpha": 1.0}
    if kind == "stat":
        return PALETTE["gold"], {"borderWidth": 4.0, "borderColor": PALETTE["ink"], "borderAlpha": 1.0}
    if kind == "chapter":
        return PALETTE["ink"], {"borderWidth": 2.0, "borderColor": PALETTE["paper"], "borderAlpha": 1.0}
    return PALETTE["ink"], {"borderWidth": 2.5, "borderColor": PALETTE["paper"], "borderAlpha": 1.0}


def size_for(kind: str, base: int, text: str, lo: int = 16, hi: int = 30) -> int:
    """Three semantic size tiers; long labels shrink rather than taking over the frame."""
    size = float(base) * TIERS.get(kind, 1.0)
    length = len(re.sub(r"\s+", " ", text).strip())
    if length > 12:
        size *= max(0.68, 12 / length)
    return int(max(lo, min(hi, round(size))))


def safe_xy(x: float, y: float) -> tuple[float, float]:
    return round(max(-SAFE, min(SAFE, float(x))), 3), round(max(-SAFE, min(SAFE, float(y))), 3)


def avoid_collisions(items: list[dict[str, Any]], gap_y: float = 0.12) -> None:
    """Nudge simultaneously visible text away from collisions; coordinates are normalized."""
    placed: list[dict[str, Any]] = []
    for item in sorted(items, key=lambda value: float(value["start"])):
        for other in placed:
            overlaps = (float(item["start"]) < float(other["start"]) + float(other["duration"])
                        and float(other["start"]) < float(item["start"]) + float(item["duration"]))
            if overlaps and abs(float(item["x"]) - float(other["x"])) < 0.5 and abs(float(item["y"]) - float(other["y"])) < gap_y:
                item["y"] = round(min(SAFE, float(other["y"]) + gap_y), 3)
        item["x"], item["y"] = safe_xy(item["x"], item["y"])
        placed.append(item)


TEXT_RECIPES = {
    "alert": ("slam", "tilt_pop", "zoom"),
    "stat": ("pop", "zoom", "slide_left"),
    "keyword": ("rise", "slide_left", "slide_right", "tilt_pop", "pop"),
    "chapter": ("slide_left", "rise", "pop"),
}


def choose_text_recipe(kind: str, index: int = 0) -> str:
    """Assign deterministic, semantically appropriate text movement without random flicker."""
    choices = TEXT_RECIPES.get(kind, TEXT_RECIPES["keyword"])
    return choices[index % len(choices)]


def text_motion(timeline: Any, ref: str, duration: float, y: float,
                caps: dict[str, Any] | None = None, enter: float = 0.18,
                leave: float = 0.14, rise: float = 0.04, recipe: str = "rise",
                x: float = 0.0, direction: float = 1.0) -> None:
    """Animate text with a deterministic entry/settle/exit recipe using known transform properties."""
    caps = caps or {}
    if duration <= 0:
        return
    duration = float(duration)
    enter = min(max(0.04, enter), duration * 0.4)
    leave = min(max(0.04, leave), duration * 0.3)
    hold_end = max(enter + 0.01, duration - leave)
    direction = -1.0 if direction < 0 else 1.0

    start_x, start_y, start_scale, start_rotation = x, y + rise, 0.90, 0.0
    peak_scale = 1.04
    if recipe == "slide_left":
        start_x, start_y, start_scale = x - 0.085, y, 0.92
        peak_scale = 1.025
    elif recipe == "slide_right":
        start_x, start_y, start_scale = x + 0.085, y, 0.92
        peak_scale = 1.025
    elif recipe == "slam":
        start_x, start_y, start_scale, start_rotation = x, y - 0.12, 0.70, -4.5 * direction
        peak_scale = 1.12
    elif recipe == "tilt_pop":
        start_x, start_y, start_scale, start_rotation = x + 0.04 * direction, y + rise * 0.5, 0.68, -9.0 * direction
        peak_scale = 1.10
    elif recipe == "zoom":
        start_x, start_y, start_scale = x, y, 1.24
        peak_scale = 0.94
    elif recipe == "pop":
        start_x, start_y, start_scale = x, y + rise * 0.6, 0.72
        peak_scale = 1.10
    else:  # rise
        recipe = "rise"

    timeline.key(ref, "position_x", 0.0, start_x)
    timeline.key(ref, "position_y", 0.0, start_y)
    timeline.key(ref, "rotation", 0.0, start_rotation)
    timeline.key(ref, "uniform_scale", 0.0, start_scale)
    timeline.key(ref, "uniform_scale", enter * 0.68, peak_scale, "ease-out")
    timeline.key(ref, "position_x", enter * 0.70, x, "ease-out")
    timeline.key(ref, "position_y", enter * 0.70, y - 0.006, "ease-out")
    timeline.key(ref, "rotation", enter * 0.70, start_rotation * 0.12, "ease-out")
    timeline.key(ref, "uniform_scale", enter, 1.0, "ease-out")
    timeline.key(ref, "position_x", enter, x, "ease-out")
    timeline.key(ref, "position_y", enter, y, "ease-out")
    timeline.key(ref, "rotation", enter, 0.0, "ease-out")

    timeline.key(ref, "position_x", hold_end, x, "ease-in-out")
    timeline.key(ref, "position_y", hold_end, y, "ease-in-out")
    timeline.key(ref, "uniform_scale", hold_end, 1.0, "ease-in-out")

    opacity_property = caps.get("opacity_property")
    if opacity_property:
        timeline.key(ref, str(opacity_property), 0.0, 0.0)
        timeline.key(ref, str(opacity_property), enter, 1.0, "ease-out")
        timeline.key(ref, str(opacity_property), hold_end, 1.0)
        timeline.key(ref, str(opacity_property), duration, 0.0, "ease-in")

    if caps.get("scale", True):
        timeline.key(ref, "uniform_scale", duration, 0.84 if recipe not in {"slam", "tilt_pop"} else 0.76, "ease-in")
    if recipe == "slide_left":
        timeline.key(ref, "position_x", duration, x - 0.055, "ease-in")
    elif recipe == "slide_right":
        timeline.key(ref, "position_x", duration, x + 0.055, "ease-in")
    elif recipe in {"slam", "tilt_pop"}:
        timeline.key(ref, "position_y", duration, y + rise * 0.35, "ease-in")
        timeline.key(ref, "rotation", duration, 4.0 * direction, "ease-in")
    else:
        timeline.key(ref, "position_y", duration, y + rise * 0.6, "ease-in")
