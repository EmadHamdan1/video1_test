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


def text_motion(timeline: Any, ref: str, duration: float, y: float,
                caps: dict[str, Any] | None = None, enter: float = 0.18,
                leave: float = 0.14, rise: float = 0.04) -> None:
    """Use verified position/scale keyframes; opacity remains opt-in until CLI probing."""
    caps = caps or {}
    if duration <= 0:
        return
    enter = min(max(0.04, enter), duration * 0.4)
    leave = min(max(0.04, leave), duration * 0.3)
    hold_end = max(enter + 0.01, duration - leave)
    timeline.key(ref, "position_y", 0.0, y + rise)
    timeline.key(ref, "position_y", enter, y, "ease-out")
    timeline.key(ref, "position_y", hold_end, y, "ease-in-out")
    timeline.key(ref, "position_y", duration, y + rise * 0.6, "ease-in")
    opacity_property = caps.get("opacity_property")
    if opacity_property:
        timeline.key(ref, str(opacity_property), 0.0, 0.0)
        timeline.key(ref, str(opacity_property), enter, 1.0, "ease-out")
        timeline.key(ref, str(opacity_property), hold_end, 1.0)
        timeline.key(ref, str(opacity_property), duration, 0.0, "ease-in")
    # Scale keyframes are already used by the image pipeline and create a restrained
    # text overshoot/settle plus a visible exit when no verified opacity property exists.
    if caps.get("scale", True):
        timeline.key(ref, "uniform_scale", 0.0, 0.82)
        timeline.key(ref, "uniform_scale", enter * 0.72, 1.075, "ease-out")
        timeline.key(ref, "uniform_scale", enter, 1.0, "ease-out")
        timeline.key(ref, "uniform_scale", hold_end, 1.0, "ease-in-out")
        timeline.key(ref, "uniform_scale", duration, 0.84, "ease-in")
