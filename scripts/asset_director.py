"""Asset department: inventory sources, map support layers, and report visual gaps."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def inspect_asset(path_value: str) -> dict[str, Any]:
    path = Path(path_value).expanduser()
    result: dict[str, Any] = {
        "path": str(path),
        "exists": path.is_file(),
        "size_bytes": path.stat().st_size if path.is_file() else None,
        "width": None,
        "height": None,
        "aspect_ratio": None,
        "alpha_channel": False,
        "metadata_only": True,
    }
    if not path.is_file():
        return result
    if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
        try:
            from PIL import Image, ImageOps
            with Image.open(path) as opened:
                image = ImageOps.exif_transpose(opened)
                result["width"], result["height"] = image.size
                result["aspect_ratio"] = round(image.width / image.height, 4) if image.height else None
                result["alpha_channel"] = (
                    image.getchannel("A").getextrema()[0] < 255
                    if "A" in image.getbands()
                    else "transparency" in image.info
                )
        except Exception as exc:
            result["inspection_error"] = str(exc)
    return result


def _load_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return fallback


def build_asset_report(config: dict[str, Any], scenes: list[dict[str, Any]],
                       spec: dict[str, Any], project_dir: Path) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    manifest_path = project_dir / "assets" / "stock" / "stock_manifest.json"
    stock_manifest = _load_json(manifest_path, [])
    if not isinstance(stock_manifest, list):
        stock_manifest = []

    missing_doc = _load_json(project_dir / "build" / "MISSING_ASSETS.json", {"items": []})
    requested = missing_doc.get("items", []) if isinstance(missing_doc, dict) else []
    if not isinstance(requested, list):
        requested = []

    secondary = [
        item
        for track in spec.get("tracks", [])
        if track.get("name") in {"Fast Secondary Image Inserts", "HyperFrames Motion Graphics", "Story Fact Callouts"}
        for item in track.get("items", [])
    ]
    beats = config.get("story_beats", [])
    beats = beats if isinstance(beats, list) else []
    planned: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []

    for scene_index, scene in enumerate(scenes):
        start, end = float(scene.get("start", 0.0)), float(scene.get("end", 0.0))
        midpoint = (start + end) / 2
        beat_index = next(
            (i for i, beat in enumerate(beats)
             if float(beat.get("start_s", 0.0)) <= midpoint <= float(beat.get("end_s", 0.0))),
            min(scene_index, max(0, len(beats) - 1)),
        )
        beat = beats[beat_index] if beats else {}
        primary = str(scene.get("source_image") or scene.get("image") or "")
        support_used = [
            {
                "path": str(item.get("path", "")),
                "start": float(item.get("start", 0.0)),
                "duration": float(item.get("duration", 0.0)),
                "track": str(item.get("track_name", "supporting_layer")),
            }
            for item in secondary
            if float(item.get("start", 0.0)) < end
            and float(item.get("start", 0.0)) + float(item.get("duration", 0.0)) > start
        ]
        stock_candidates = [
            {
                "path": str(item.get("path", "")),
                "provider": str(item.get("provider", "")),
                "license": str(item.get("license", "")),
                "credit": str(item.get("credit", "")),
                "query": str(item.get("query", "")),
                "beat": int(item.get("beat", -1)),
                "alpha_channel": bool(item.get("alpha_channel", False)),
            }
            for item in stock_manifest
            if abs(int(item.get("beat", -1)) - beat_index) <= 1
            and Path(str(item.get("path", ""))).is_file()
        ]
        row = {
            "scene_id": str(scene.get("scene_ref", f"scene_{scene_index + 1:03d}")),
            "beat_id": str(beat.get("scene_id", f"beat_{beat_index + 1:03d}")),
            "start": round(start, 3),
            "end": round(end, 3),
            "visual_query": str(beat.get("stock_query") or beat.get("visual_purpose") or ""),
            "primary_asset": inspect_asset(primary),
            "supporting_layers_used": support_used,
            "matching_stock_candidates": stock_candidates,
            "semantic_match_status": "requires_visual_review",
        }
        planned.append(row)

        if not support_used and row["visual_query"]:
            gaps.append({
                "scene_id": row["scene_id"],
                "beat_id": row["beat_id"],
                "start": row["start"],
                "visual_query": row["visual_query"],
                "status": "no_supporting_layer_selected",
                "available_candidates": len(stock_candidates),
                "action": (
                    "review matching licensed candidates"
                    if stock_candidates else
                    "create or source one consistent-style supporting asset"
                ),
            })

    return {
        "schema_version": 1,
        "project": str(config.get("project_name", "Video1 Production")),
        "asset_policy": {
            "supplied_media_is_primary": True,
            "supporting_media_requires_beat_match": True,
            "transparent_cutouts_require_real_alpha": True,
            "automatic_semantic_recognition": False,
            "manual_review_required": True,
        },
        "source_image_count": len(config.get("scene_images", [])),
        "stock_manifest": str(manifest_path),
        "stock_asset_count": len(stock_manifest),
        "scenes": planned,
        "visual_gaps": gaps,
        "missing_asset_requests": requested,
        "summary": {
            "scene_count": len(planned),
            "scenes_with_supporting_layers": sum(bool(row["supporting_layers_used"]) for row in planned),
            "visual_gaps": len(gaps),
            "stock_assets": len(stock_manifest),
        },
    }


def render_asset_report(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        "# Asset department report",
        "",
        "- Supplied imagery remains the primary visual source.",
        "- Supporting media is accepted only when its query belongs to the scene beat or an adjacent beat.",
        "- Image metadata does not prove semantic relevance; visual review is required.",
        "",
        "## Summary",
        "",
        f"- Scenes: {summary.get('scene_count', 0)}",
        f"- Scenes with supporting layers: {summary.get('scenes_with_supporting_layers', 0)}",
        f"- Visual gaps: {summary.get('visual_gaps', 0)}",
        f"- Licensed stock assets cached: {summary.get('stock_assets', 0)}",
        "",
        "## Visual gaps",
        "",
    ]
    gaps = report.get("visual_gaps", [])
    if not gaps:
        lines.append("No unfilled supporting-visual gaps were detected by the structural planner.")
    else:
        for gap in gaps:
            lines.append(
                f"- {gap['scene_id']} ({gap['start']:.2f}s): {gap['visual_query']} — {gap['action']}."
            )
    lines.extend(["", "## Missing asset requests", ""])
    requests = report.get("missing_asset_requests", [])
    if not requests:
        lines.append("No explicit missing-asset request list was provided.")
    else:
        for item in requests:
            lines.append(f"- {item.get('asset', 'Unnamed asset')}: {item.get('status', 'review required')}")
    lines.extend(["", "## Review rule", "", "Approve image-to-beat relevance, style consistency, crop safety, and licence before publication."])
    return "\n".join(lines) + "\n"
