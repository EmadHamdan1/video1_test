"""Structural QA for a generated CapCut project spec (no render required)."""
from __future__ import annotations

from typing import Any

BACKGROUND_NAMES = {"Whiteboard Background"}


def audit_spec(spec: dict[str, Any], max_gap: float = 4.5,
               text_size: tuple[int, int] = (14, 30), safe: float = 0.88,
               duration: float | None = None) -> list[str]:
    issues: list[str] = []
    tracks = spec.get("tracks", [])
    ends = [float(item.get("start", 0)) + float(item.get("duration", 0))
            for track in tracks for item in track.get("items", [])]
    total = float(duration) if duration is not None else max(ends, default=0.0)
    starts: list[float] = []
    texts: list[dict[str, Any]] = []
    clip_lengths: dict[str, float] = {}
    for track in tracks:
        track_type = track.get("type")
        track_name = track.get("name")
        for item in track.get("items", []):
            start, length = float(item.get("start", 0)), float(item.get("duration", 0))
            end = start + length
            ref = str(item.get("ref", "unnamed"))
            if item.get("ref"):
                clip_lengths[str(item["ref"])] = length
            if start < -0.001 or length <= 0:
                issues.append("INVALID_TIMING %s start=%.3f duration=%.3f" % (ref, start, length))
            if end > total + 0.05:
                issues.append("PAST_END %s ends at %.2fs > %.2fs" % (ref, end, total))
            if track_type == "video" and track_name not in BACKGROUND_NAMES:
                starts.append(start)
            if track_type == "text":
                starts.append(start)
                texts.append(item)
                size = float(item.get("fontSize", 0))
                if not (text_size[0] <= size <= text_size[1]):
                    issues.append("TEXT_SIZE %s fontSize=%s outside %s" % (ref, item.get("fontSize"), text_size))
                if abs(float(item.get("x", 0))) > safe or abs(float(item.get("y", 0))) > safe:
                    issues.append("TEXT_OFF_SAFE_AREA %s at (%.2f, %.2f)" % (ref, item.get("x", 0), item.get("y", 0)))
    for index, first in enumerate(texts):
        for second in texts[index + 1:]:
            overlaps = (float(first["start"]) < float(second["start"]) + float(second["duration"])
                        and float(second["start"]) < float(first["start"]) + float(first["duration"]))
            same_zone = abs(float(first.get("x", 0)) - float(second.get("x", 0))) < 0.5 and abs(float(first.get("y", 0)) - float(second.get("y", 0))) < 0.1
            if overlaps and same_zone:
                issues.append("TEXT_OVERLAP %s vs %s" % (first.get("ref"), second.get("ref")))
    for operation in spec.get("operations", []):
        if operation.get("op") == "keyframe":
            target = str(operation.get("target", ""))
            if target in clip_lengths and float(operation.get("time", 0)) > clip_lengths[target] + 0.001:
                issues.append("KEYFRAME_PAST_CLIP %s t=%.2f > %.2f" % (target, operation.get("time", 0), clip_lengths[target]))
    events = sorted(set([0.0, total] + [round(value, 3) for value in starts if 0 <= value <= total]))
    for left, right in zip(events, events[1:]):
        if right - left > max_gap:
            issues.append("STATIC_GAP %.1fs-%.1fs (%.1fs without a new visual/text start)" % (left, right, right-left))
    return issues
