"""Asset department: inventory sources, map support layers, and queue visual gaps."""
from __future__ import annotations

import csv
import json
import re
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
        return json.loads(path.read_text(encoding="utf-8-sig"),)
    except (OSError, json.JSONDecodeError):
        return fallback


def _load_selected_reviewed_assets(project_dir: Path) -> list[dict[str, Any]]:
    """Return only local image files a person selected and explicitly source/license-reviewed."""
    manifest = project_dir / "media_candidates.csv"
    if not manifest.is_file():
        return []
    try:
        with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except OSError:
        return []
    assets: list[dict[str, Any]] = []
    for item in rows:
        if str(item.get("kind", "")).lower() not in {"image", "photo"}:
            continue
        if str(item.get("selected", "")).strip().lower() not in {"yes", "true", "1"}:
            continue
        if str(item.get("license_reviewed", "")).strip().lower() not in {"yes", "true", "1"}:
            continue
        path = Path(str(item.get("downloaded_path", "")).strip()).expanduser()
        match = re.fullmatch(r"scene_(\d{1,4})", str(item.get("segment_id", "")).strip())
        if not path.is_file() or not match:
            continue
        assets.append({
            "path": str(path.resolve()),
            "provider": str(item.get("source", "reviewed local asset")),
            "license": str(item.get("license", "")),
            "credit": str(item.get("creator", "")),
            "query": str(item.get("query", "")),
            "beat": int(match.group(1)) - 1,
            "alpha_channel": inspect_asset(str(path))["alpha_channel"],
            "asset_origin": "selected_and_license_reviewed_local_asset",
        })
    return assets


def _load_scene_prompts(project_dir: Path) -> dict[str, dict[str, str]]:
    path = project_dir / "scene_plan.csv"
    if not path.is_file():
        return {}
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return {
                str(row.get("segment_id", "")).strip(): {
                    "sentence": str(row.get("sentence", "")).strip(),
                    "visual_prompt": str(row.get("visual_prompt", "")).strip(),
                    "search_query": str(row.get("search_query", "")).strip(),
                }
                for row in csv.DictReader(handle)
                if row.get("segment_id")
            }
    except OSError:
        return {}


def _generation_prompt(query: str, style_guide: str, sentence: str) -> str:
    event = query.strip() or sentence.strip()
    return (
        "Create one 16:9 supporting documentary illustration showing this visual requirement: "
        + event + ". Match this project's existing visual identity: " + style_guide.strip()
        + ". Use one clear focal subject, a readable silhouette, coherent object proportions, "
        "cinematic but restrained lighting, and enough negative space for independent composition. "
        "Do not add subtitles, transcript text, decorative captions, watermarks, logos, or UI. "
        "Do not invent factual details; treat uncertain reconstructions as illustrative."
    )


def build_asset_report(config: dict[str, Any], scenes: list[dict[str, Any]],
                       spec: dict[str, Any], project_dir: Path,
                       toolchain: dict[str, Any] | None = None,
                       production_plan: dict[str, Any] | None = None) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    manifest_path = project_dir / "assets" / "stock" / "stock_manifest.json"
    stock_manifest = _load_json(manifest_path, [])
    if not isinstance(stock_manifest, list):
        stock_manifest = []
    reviewed_local_assets = _load_selected_reviewed_assets(project_dir)
    scene_prompts = _load_scene_prompts(project_dir)

    missing_doc = _load_json(project_dir / "build" / "MISSING_ASSETS.json", {"items": []})
    requested = missing_doc.get("items", []) if isinstance(missing_doc, dict) else []
    if not isinstance(requested, list):
        requested = []

    secondary = [
        {**item, "_track_name": str(track.get("name", "supporting_layer"))}
        for track in spec.get("tracks", [])
        if track.get("name") in {
            "Fast Secondary Image Inserts", "Story Fact Callouts", "Icon Overlays"
        }
        for item in track.get("items", [])
    ]
    beats = config.get("story_beats", [])
    beats = beats if isinstance(beats, list) else []
    style_guide = str(config.get(
        "asset_style_guide",
        "a consistent flat 2D cartoon editorial illustration style, bold clean outlines, "
        "controlled palette, readable expressions and props, clean shapes, no photorealistic inserts",
    ))
    python_caps = (toolchain or {}).get("python_modules", {})
    hf_available = bool(python_caps.get("huggingface_hub", {}).get("installed", False))
    rembg_available = bool(python_caps.get("rembg", {}).get("installed", False))

    planned: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    plan_by_scene = {
        str(item.get("scene_id", "")): item
        for item in (production_plan or {}).get("scenes", [])
    }
    generation_queue: list[dict[str, Any]] = []

    for scene_index, scene in enumerate(scenes):
        start, end = float(scene.get("start", 0.0)), float(scene.get("end", 0.0))
        midpoint = (start + end) / 2
        beat_index = next(
            (i for i, beat in enumerate(beats)
             if float(beat.get("start_s", 0.0)) <= midpoint <= float(beat.get("end_s", 0.0))),
            min(scene_index, max(0, len(beats) - 1)),
        )
        beat = beats[beat_index] if beats else {}
        primary_source = str(scene.get("source_image") or scene.get("image") or "")
        displayed_asset = str(scene.get("image") or primary_source)
        support_used = [
            {
                "path": str(item.get("path", "")),
                "start": float(item.get("start", 0.0)),
                "duration": float(item.get("duration", 0.0)),
                "track": str(item.get("_track_name", "supporting_layer")),
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
                "origin": "licensed_stock",
            }
            for item in stock_manifest
            if abs(int(item.get("beat", -1)) - beat_index) <= 1
            and Path(str(item.get("path", ""))).is_file()
        ]
        stock_candidates.extend([
            {**item, "origin": "selected_reviewed_local_asset"}
            for item in reviewed_local_assets
            if abs(int(item.get("beat", -1)) - beat_index) <= 1
            and Path(str(item.get("path", ""))).is_file()
        ])
        scene_id = str(scene.get("scene_ref", f"scene_{scene_index + 1:03d}"))
        beat_id = str(beat.get("scene_id", f"beat_{beat_index + 1:03d}"))
        visual_query = str(beat.get("stock_query") or beat.get("visual_purpose") or "")
        planned_scene = plan_by_scene.get(scene_id, {})
        graphics_layers = planned_scene.get("graphics_layers", [])
        planned_support_layers = planned_scene.get("supporting_assets", [])
        row = {
            "scene_id": scene_id,
            "beat_id": beat_id,
            "start": round(start, 3),
            "end": round(end, 3),
            "visual_query": visual_query,
            "primary_source_asset": inspect_asset(primary_source),
            "displayed_asset": inspect_asset(displayed_asset),
            "full_bleed_stock_source": str(scene.get("stock_source_path") or ""),
            "supporting_layers_used": support_used,
            "planned_supporting_assets": planned_support_layers,
            "graphics_layers": graphics_layers,
            "matching_stock_candidates": stock_candidates,
            "semantic_match_status": "requires_visual_review",
        }
        planned.append(row)

        if not support_used and not planned_support_layers and not graphics_layers and not scene.get("stock_source_path") and visual_query:
            gap = {
                "scene_id": scene_id,
                "beat_id": beat_id,
                "start": row["start"],
                "visual_query": visual_query,
                "status": "no_supporting_layer_selected",
                "available_candidates": len(stock_candidates),
                "action": (
                    "review and select a matching candidate"
                    if stock_candidates else
                    "create or source a consistent-style supporting visual"
                ),
            }
            gaps.append(gap)
            prompt_row = scene_prompts.get(f"scene_{beat_index + 1:03d}", {})
            prompt_seed = (
                prompt_row.get("visual_prompt")
                or "Create a clear, literal supporting visual of: " + visual_query
            )
            prompt = _generation_prompt(visual_query, style_guide, prompt_row.get("sentence", prompt_seed))
            generation_queue.append({
                "scene_id": scene_id,
                "segment_id": f"scene_{beat_index + 1:03d}",
                "beat_id": beat_id,
                "start": row["start"],
                "purpose": visual_query,
                "prompt": prompt,
                "generator": "scripts/prepare_assets.py generate-image",
                "generation_requires_explicit_cost_confirmation": True,
                "use_requires_selection_and_license_review": True,
                "alpha_policy": (
                    "Accept only a verified real alpha channel for a cutout layer. "
                    "If the selected file is opaque, use it only as an opaque image layer; "
                    "never simulate transparency with a white or black matte."
                ),
                "background_removal_available": rembg_available,
            })

    return {
        "schema_version": 2,
        "project": str(config.get("project_name", "Video1 Production")),
        "asset_policy": {
            "supplied_media_is_primary": True,
            "supporting_media_requires_beat_match": True,
            "transparent_cutouts_require_real_alpha": True,
            "automatic_semantic_recognition": False,
            "manual_review_required": True,
            "ai_generation_requires_explicit_cost_confirmation": True,
            "local_assets_are_not_used_until_selected_and_source_license_reviewed": True,
        },
        "generation_tools": {
            "huggingface_hub_installed": hf_available,
            "background_removal_package_installed": rembg_available,
            "generation_command": "python scripts/prepare_assets.py generate-image",
            "review_command": "python scripts/prepare_assets.py review-license",
            "generation_cost_confirmation_required": True,
        },
        "source_image_count": len(config.get("scene_images", [])),
        "stock_manifest": str(manifest_path),
        "stock_asset_count": len(stock_manifest),
        "reviewed_local_asset_count": len(reviewed_local_assets),
        "scenes": planned,
        "visual_gaps": gaps,
        "asset_generation_queue": generation_queue,
        "missing_asset_requests": requested,
        "summary": {
            "scene_count": len(planned),
            "scenes_with_supporting_layers": sum(bool(row["supporting_layers_used"]) for row in planned),
            "visual_gaps": len(gaps),
            "stock_assets": len(stock_manifest),
            "reviewed_local_assets": len(reviewed_local_assets),
            "generation_queue_items": len(generation_queue),
        },
    }


def render_asset_report(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    tools = report.get("generation_tools", {})
    lines = [
        "# Asset department report",
        "",
        "- Supplied imagery remains the primary visual source.",
        "- Supporting media is accepted only when its query belongs to the scene beat or an adjacent beat.",
        "- Image metadata does not prove semantic relevance; visual review is required.",
        "- AI generation is queued, never triggered automatically; each generation needs explicit cost acknowledgement.",
        "- Locally selected assets are excluded until a human selects them and records a licence/source or model-terms review.",
        "",
        "## Summary",
        "",
        f"- Scenes: {summary.get('scene_count', 0)}",
        f"- Scenes with supporting layers: {summary.get('scenes_with_supporting_layers', 0)}",
        f"- Visual gaps: {summary.get('visual_gaps', 0)}",
        f"- Licensed stock assets cached: {summary.get('stock_assets', 0)}",
        f"- Selected and reviewed local assets ready for beat matching: {summary.get('reviewed_local_assets', 0)}",
        f"- Suggested AI asset prompts: {summary.get('generation_queue_items', 0)}",
        "",
        "## Generation capability",
        "",
        f"- Hugging Face package installed: {'yes' if tools.get('huggingface_hub_installed') else 'no'}",
        f"- Background removal package detected: {'yes' if tools.get('background_removal_package_installed') else 'no'}",
        "- Generation remains manual and cost-gated.",
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
    lines.extend(["", "## Asset generation queue", ""])
    queue = report.get("asset_generation_queue", [])
    if not queue:
        lines.append("No new asset-generation prompt is currently queued.")
    else:
        for item in queue:
            lines.append(
                f"- {item['segment_id']}: {item['purpose']} — prompt is stored in ASSET_GENERATION_QUEUE.json."
            )
    lines.extend(["", "## Missing asset requests", ""])
    requests = report.get("missing_asset_requests", [])
    if not requests:
        lines.append("No explicit missing-asset request list was provided.")
    else:
        for item in requests:
            lines.append(f"- {item.get('asset', 'Unnamed asset')}: {item.get('status', 'review required')}")
    lines.extend(["", "## Review rule", "", "Approve image-to-beat relevance, style consistency, crop safety, actual alpha transparency, and model/source terms before publication."])
    return "\n".join(lines) + "\n"
