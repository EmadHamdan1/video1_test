from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.json"
BUILD_DIR = ROOT / "build"


def log(message: str) -> None:
    print("[montage] " + message, flush=True)


def load_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or CONFIG_PATH
    with config_path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def parse_timestamp(value: str) -> float:
    value = value.strip().replace(",", ".")
    parts = value.split(":")
    if len(parts) != 3:
        raise ValueError("Unexpected SRT timestamp: " + value)
    hours = float(parts[0])
    minutes = float(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds


def read_srt(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8-sig", errors="replace")
    blocks = re.split(r"\r?\n\s*\r?\n", content.strip())
    cues: list[dict[str, Any]] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        time_index = next((i for i, line in enumerate(lines) if "-->" in line), -1)
        if time_index < 0:
            continue
        try:
            left, right = [part.strip().split()[0] for part in lines[time_index].split("-->", 1)]
            start = parse_timestamp(left)
            end = parse_timestamp(right)
        except (ValueError, IndexError):
            continue
        text = " ".join(lines[time_index + 1:]).strip()
        text = re.sub(r"<[^>]+>", "", text)
        if text and end > start:
            cues.append({"start": start, "end": end, "text": text})
    return sorted(cues, key=lambda item: item["start"])


def audio_duration(path: Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            result = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                text=True, capture_output=True, timeout=30, check=False
            )
            if result.returncode == 0:
                value = float(result.stdout.strip())
                if math.isfinite(value) and value > 0:
                    return value
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass

    try:
        from mutagen import File as MutagenFile
        media = MutagenFile(str(path))
        duration = float(media.info.length) if media and media.info else 0.0
        if math.isfinite(duration) and duration > 0:
            return duration
    except Exception as exc:
        log("Mutagen could not read the audio duration: " + str(exc))

    raise RuntimeError(
        "Could not read the MP3 duration. Install requirements.txt and run this script again, "
        "or install FFmpeg so ffprobe is available."
    )


def find_whisper_command() -> str | None:
    """Find Whisper on PATH or inside this repository's virtual environment."""
    found = shutil.which("whisper")
    if found:
        return found

    if os.name == "nt":
        candidates = [
            ROOT / ".venv" / "Scripts" / "whisper.exe",
            ROOT / ".venv" / "Scripts" / "whisper",
        ]
    else:
        candidates = [ROOT / ".venv" / "bin" / "whisper"]

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def transcribe_if_available(audio: Path, settings: dict[str, Any]) -> tuple[list[dict[str, Any]], Path | None]:
    # A project-specific precomputed SRT (for example, generated from word-level alignment)
    # takes precedence over Whisper CLI. This keeps the core builder compatible with lighter
    # transcription pipelines and avoids replacing a verified transcript.
    captions_path = BUILD_DIR / "captions.srt"
    if settings.get("use_precomputed_captions", False) and captions_path.is_file():
        cues = read_srt(captions_path)
        if cues:
            log("Using " + str(len(cues)) + " precomputed caption cues from " + str(captions_path))
            return cues, captions_path
        log("Precomputed captions file was empty or unreadable; trying Whisper if available.")

    if not settings.get("transcribe_if_whisper_available", True):
        log("Whisper transcription is disabled in config.json.")
        return [], None

    whisper = find_whisper_command()
    if not whisper:
        log("Whisper was not found; using duration-based shot timing and no automatic captions.")
        return [], None

    output_dir = BUILD_DIR / "transcript"
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        whisper, str(audio),
        "--model", str(settings.get("whisper_model", "base")),
        "--output_format", "srt",
        "--output_dir", str(output_dir),
    ]
    log("Running local Whisper transcription. The first run may download its selected model.")
    try:
        result = subprocess.run(command, text=True, capture_output=True, timeout=None, check=False)
    except OSError as exc:
        log("Whisper could not start: " + str(exc))
        return [], None

    whisper_srt = output_dir / (audio.stem + ".srt")
    if result.returncode != 0 or not whisper_srt.exists():
        detail = (result.stderr or result.stdout or "No details returned").strip()
        log("Whisper failed; continuing without captions. " + detail[-900:])
        return [], None

    captions_path = BUILD_DIR / "captions.srt"
    shutil.copy2(whisper_srt, captions_path)
    cues = read_srt(captions_path)
    if cues:
        log("Whisper supplied " + str(len(cues)) + " timed text cues.")
    else:
        log("Whisper created an empty or unreadable SRT; continuing without captions.")
        captions_path.unlink(missing_ok=True)
        return [], None
    return cues, captions_path


def usable_paths(raw_paths: list[str], description: str) -> tuple[list[Path], list[str]]:
    good: list[Path] = []
    missing: list[str] = []
    for raw in raw_paths:
        path = Path(os.path.expandvars(raw)).expanduser()
        if not path.is_absolute():
            path = CONFIG_PATH.parent / path
        if path.is_file():
            good.append(path.resolve())
        else:
            missing.append(raw)
    if missing:
        log(str(len(missing)) + " " + description + " path(s) were not found; those entries will be skipped.")
        for item in missing[:5]:
            log("Missing: " + item)
        if len(missing) > 5:
            log("Plus " + str(len(missing) - 5) + " more missing path(s).")
    return good, missing


def discover_drafts_dir(configured: str | None) -> Path:
    if configured and configured.strip():
        return Path(os.path.expandvars(configured)).expanduser().resolve()

    env_dir = os.environ.get("CAPCUT_DRAFT_DIR", "").strip()
    if env_dir:
        return Path(os.path.expandvars(env_dir)).expanduser().resolve()

    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        user_profile = os.environ.get("USERPROFILE")
        if user_profile:
            local_app_data = str(Path(user_profile) / "AppData" / "Local")

    if local_app_data:
        base = Path(local_app_data)
        candidates = [
            base / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft",
            base / "JianyingPro" / "User Data" / "Projects" / "com.lveditor.draft",
        ]
        for path in candidates:
            if path.exists():
                return path.resolve()
        # capcut-cli itself uses this first candidate when no existing store is found.
        return candidates[0].resolve()

    raise RuntimeError(
        "Could not detect the Windows local-app-data folder. Set drafts_dir in config.json "
        "to CapCut's com.lveditor.draft folder."
    )


def scene_boundaries(
    duration: float,
    shot_count: int,
    target_seconds: float,
    minimum_seconds: float,
    captions: list[dict[str, Any]],
) -> list[float]:
    if shot_count <= 1:
        return [0.0, duration]

    boundary_points = [float(cue["end"]) for cue in captions]
    result = [0.0]
    for index in range(1, shot_count):
        target = duration * index / shot_count
        lower = result[-1] + minimum_seconds
        upper = duration - (shot_count - index) * minimum_seconds
        if upper < lower:
            # Guard against rounding at the exact lower bound.
            lower = result[-1] + max(0.05, (duration - result[-1]) / (shot_count - index + 1))
            upper = duration - max(0.05, (shot_count - result[-1]) / (shot_count - index + 1))
        target = min(max(target, lower), upper)

        nearby = [
            point for point in boundary_points
            if lower <= point <= upper and abs(point - target) <= max(1.0, target_seconds * 0.42)
        ]
        if nearby:
            target = min(nearby, key=lambda point: abs(point - target))
        result.append(round(target, 3))

    result.append(round(duration, 3))
    result[0] = 0.0
    result[-1] = round(duration, 3)
    return result


def choose_scene_indices(image_count: int, shot_count: int) -> list[int]:
    if shot_count <= 0 or image_count <= 0:
        return []
    if shot_count <= image_count:
        if shot_count == 1:
            return [0]
        return [
            round(index * (image_count - 1) / (shot_count - 1))
            for index in range(shot_count)
        ]
    return [index % image_count for index in range(shot_count)]



def create_whiteboard_assets(
    output_dir: Path, width: int, height: int, scene_count: int, presenter_count: int,
    scene_x: float = -0.25, scene_y: float = -0.02,
    presenter_x: float = 0.72, presenter_y: float = 0.18,
    plain_white: bool = False,
) -> dict[str, Any]:
    """Create local visual assets for a layered whiteboard/explainer edit."""
    try:
        from PIL import Image, ImageDraw, ImageFilter, ImageFont
    except ImportError as exc:
        raise RuntimeError("The whiteboard design needs Pillow; reinstall requirements.txt.") from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    accents = [(16,145,135), (237,145,62), (81,109,208), (222,91,111), (115,143,85)]
    paper = (250,249,245)
    def font(size: int) -> Any:
        for name in ("arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"):
            try:
                return ImageFont.truetype(name, size=size)
            except OSError:
                pass
        return ImageFont.load_default()

    # The requested Nutty Putty style uses a truly solid white canvas: no grid,
    # paper tint, labels, bars, or decorative marks behind the artwork.
    board = Image.new("RGB", (width, height), (255, 255, 255) if plain_white else paper)
    if not plain_white:
        bd = ImageDraw.Draw(board)
        step = max(26, width // 60)
        for yy in range(step, height, step):
            for xx in range(step, width, step):
                bd.ellipse((xx, yy, xx + 2, yy + 2), fill=(230,228,221))
        bd.rounded_rectangle((52,40,322,92), radius=18, fill=(255,255,252), outline=(226,223,214), width=2)
        bd.text((73,55), "VISUAL EXPLAINER", font=font(23), fill=(48,57,67))
        bd.line((54,118,186,118), fill=accents[0], width=5)
        bd.line((198,118,242,118), fill=accents[1], width=5)
        bd.text((width-335,57), "WHITEBOARD / MOTION", font=font(17), fill=(137,139,136))
    board_path = output_dir / "whiteboard_canvas.png"
    board.save(board_path, optimize=True)

    cx = round(width / 2 + scene_x * width / 2)
    cy = round(height / 2 + scene_y * height / 2)
    card_w, card_h = int(width * 0.548), int(height * 0.615)
    left, top = cx-card_w//2, cy-card_h//2
    right, bottom = left+card_w, top+card_h
    cards: list[str] = []
    for index in range(scene_count):
        accent = accents[index % len(accents)]
        overlay = Image.new("RGBA", (width,height), (0,0,0,0))
        shadow = Image.new("RGBA", (width,height), (0,0,0,0))
        ImageDraw.Draw(shadow).rounded_rectangle(
            (left+9,top+13,right+9,bottom+13), radius=28, fill=(35,42,52,42)
        )
        overlay = Image.alpha_composite(overlay, shadow.filter(ImageFilter.GaussianBlur(15)))
        draw = ImageDraw.Draw(overlay)
        draw.rounded_rectangle(
            (left,top,right,bottom), radius=26, fill=(255,254,250,255),
            outline=(220,216,207,255), width=3
        )
        draw.rounded_rectangle((left+32,top+24,left+151,top+33), radius=5, fill=(*accent,255))
        label = (right-146,top+18,right-24,top+59)
        pale = tuple(round(c*0.18 + 255*0.82) for c in accent) + (255,)
        draw.rounded_rectangle(label, radius=14, fill=pale, outline=(*accent,100), width=1)
        draw.text((label[0]+13,label[1]+11), "NOTE %02d" % (index+1), font=font(16), fill=(*accent,255))
        if index % 3 == 0:
            y = cy + int(height*0.015*(1 if index%2 == 0 else -1))
            x0, x1 = right+22, min(width-82,right+111)
            draw.line((x0,y,x1,y-3), fill=(*accent,220), width=5)
            draw.line((x1-17,y-16,x1,y-3), fill=(*accent,220), width=5)
            draw.line((x1-17,y+10,x1,y-3), fill=(*accent,220), width=5)
        tx, ty = min(width-45,right+20), max(140,top+120+(index%4)*25)
        draw.line((tx,ty,tx+17,ty-7), fill=(*accent,165), width=3)
        card_path = output_dir / ("scene_card_%03d.png" % (index+1))
        overlay.save(card_path, optimize=True)
        cards.append(str(card_path.resolve()))

    plates: list[str] = []
    pcx = round(width/2 + presenter_x*width/2)
    pcy = round(height/2 + presenter_y*height/2)
    pw, ph = int(width*0.195), int(height*0.56)
    pl, pt = pcx-pw//2, pcy-ph//2
    pr, pb = pl+pw, pt+ph
    for index in range(presenter_count):
        accent = accents[index % len(accents)]
        plate = Image.new("RGBA", (width,height), (0,0,0,0))
        draw = ImageDraw.Draw(plate)
        draw.rounded_rectangle(
            (pl,pt,pr,pb), radius=150, fill=(*accent,24), outline=(*accent,118), width=4
        )
        sx, sy = pl+30, pt+82
        draw.line((sx-16,sy,sx+7,sy-3), fill=(*accent,190), width=4)
        draw.line((sx-5,sy-17,sx+3,sy+3), fill=(*accent,190), width=4)
        draw.ellipse((pr-29,pt+145,pr-17,pt+157), fill=(*accent,185))
        plate_path = output_dir / ("presenter_backplate_%02d.png" % (index+1))
        plate.save(plate_path, optimize=True)
        plates.append(str(plate_path.resolve()))
    return {"background": str(board_path.resolve()), "scene_cards": cards, "presenter_backplates": plates}


def load_motion_preset(settings: dict[str, Any]) -> dict[str, Any]:
    """Load a named motion profile from presets/motion_presets.json."""
    presets_path = ROOT / "presets" / "motion_presets.json"
    try:
        data = json.loads(presets_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        data = {}
    presets = data.get("presets", {}) if isinstance(data, dict) else {}
    name = str(settings.get("motion_preset", "whiteboard_smooth"))
    preset = presets.get(name)
    if not isinstance(preset, dict):
        log("Unknown motion preset '" + name + "'; using whiteboard_smooth.")
        preset = presets.get("whiteboard_smooth", {})
    return dict(preset)


def transition_for_scene(index: int, motion: dict[str, Any] | None = None) -> tuple[str, float]:
    """Return a hard cut or a sparse, purposeful transition from the selected motion profile."""
    motion = motion or {}
    rules = motion.get("transitions", {})
    default = rules.get("default", {"slug": "dissolve", "duration": 0.24})
    number = index + 1
    for rule in rules.get("accents", []):
        every = int(rule.get("every", 0) or 0)
        if every > 0 and number % every == 0:
            return str(rule.get("slug", default.get("slug", "dissolve"))), float(rule.get("duration", default.get("duration", 0.24)))
    return str(default.get("slug", "dissolve")), float(default.get("duration", 0.24))



def split_timed_text(start: float, end: float, text: str, max_words: int = 5, min_hold: float = 0.85) -> list[dict[str, Any]]:
    """Split a long cue into readable phrase chunks and allocate time by word count."""
    words = re.findall(r"\S+", str(text).strip())
    span = max(0.0, float(end) - float(start))
    if not words or span <= 0:
        return []
    max_words = max(1, int(max_words))
    desired_chunks = max(1, math.ceil(len(words) / max_words))
    max_chunks_by_reading_time = max(1, int(span / max(0.35, min_hold)))
    chunk_count = min(desired_chunks, max_chunks_by_reading_time)
    chunk_size = math.ceil(len(words) / chunk_count)
    chunks = [words[index:index + chunk_size] for index in range(0, len(words), chunk_size)]
    total_words = sum(len(chunk) for chunk in chunks)
    cursor_words = 0
    result: list[dict[str, Any]] = []
    for chunk in chunks:
        cue_start = float(start) + span * cursor_words / total_words
        cursor_words += len(chunk)
        cue_end = float(start) + span * cursor_words / total_words
        if cue_end - cue_start >= 0.25:
            result.append({
                "start": round(cue_start, 3),
                "end": round(cue_end, 3),
                "text": " ".join(chunk),
            })
    return result


def load_text_animation_preset(name: str) -> dict[str, Any]:
    preset_path = ROOT / "presets" / "text_animation_presets.json"
    try:
        data = json.loads(preset_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    presets = data.get("presets", {}) if isinstance(data, dict) else {}
    selected = presets.get(name)
    return dict(selected) if isinstance(selected, dict) else {}


def make_spec(
    config: dict[str, Any], audio: Path, images: list[Path], presenters: list[Path],
    duration: float, captions: list[dict[str, Any]], captions_path: Path | None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    settings = config.get("settings", {})
    motion = load_motion_preset(settings)
    canvas = config.get("canvas", {})
    layout_mode = str(settings.get("layout_mode", "whiteboard_card")).strip().lower()
    full_frame = layout_mode in {"full_frame", "full-frame", "fullframe"}
    hybrid_mode = layout_mode in {"hybrid_whiteboard", "hybrid", "mixed_whiteboard"}
    width, height = int(canvas.get("width", 1920)), int(canvas.get("height", 1080))
    target = max(1.0, float(settings.get("target_shot_seconds", motion.get("target_shot_seconds", 3.8))))
    minimum = max(0.75, float(settings.get("minimum_shot_seconds", motion.get("minimum_shot_seconds", 1.8))))
    configured_boundaries = config.get("storyboard_boundaries", [])
    use_custom_boundaries = bool(settings.get("use_storyboard_boundaries", False))
    custom_boundaries: list[float] = []
    if use_custom_boundaries and isinstance(configured_boundaries, list):
        try:
            custom_boundaries = [float(value) for value in configured_boundaries]
            valid = (
                len(custom_boundaries) == len(images) + 1
                and abs(custom_boundaries[0]) <= 0.05
                and abs(custom_boundaries[-1] - duration) <= 0.15
                and all(right > left for left, right in zip(custom_boundaries, custom_boundaries[1:]))
            )
        except (TypeError, ValueError):
            valid = False
        if valid:
            shot_count = len(images)
            boundaries = custom_boundaries
            indices = list(range(len(images)))
            log("Using " + str(shot_count) + " story-aligned storyboard segments.")
        else:
            log("Configured storyboard boundaries did not match the scene images/audio; using automatic timing instead.")
            use_custom_boundaries = False
    if not use_custom_boundaries:
        shot_count = max(1, max(len(images), int(round(duration / target))))
        feasible = max(1, int(duration / minimum))
        if shot_count > feasible:
            shot_count = feasible
            log("The narration is short relative to the available images. "
                + str(len(images)-min(len(images),shot_count))
                + " image(s) will be omitted to preserve readable shot lengths.")
        shot_count = min(shot_count, max(1, int(math.ceil(duration/0.45))))
        boundaries = scene_boundaries(duration, shot_count, target, minimum, captions)
        indices = choose_scene_indices(len(images), shot_count)
    scene_x = float(settings.get("scene_image_x", -0.25))
    scene_y = float(settings.get("scene_image_y", -0.02))
    presenter_x = float(settings.get("presenter_x", 0.72))
    presenter_y = float(settings.get("presenter_y", 0.18))
    assets = create_whiteboard_assets(
        BUILD_DIR / "visuals" / datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
        width, height, 0 if (full_frame or hybrid_mode) else shot_count,
        len(presenters) if settings.get("presenter_overlay", True) else 0,
        scene_x=scene_x, scene_y=scene_y, presenter_x=presenter_x, presenter_y=presenter_y,
        plain_white=hybrid_mode,
    )

    scene_items: list[dict[str, Any]] = []
    frame_items: list[dict[str, Any]] = []
    scene_rows: list[dict[str, Any]] = []
    for index, image_index in enumerate(indices):
        shot_start, shot_end = boundaries[index], boundaries[index+1]
        shot_duration = max(0.25, shot_end-shot_start)
        image_path = images[image_index]
        ref, frame_ref = "scene_%03d" % (index+1), "frame_%03d" % (index+1)
        media_type = "video" if image_path.suffix.lower() in {".mp4", ".mov", ".webm", ".m4v"} else "photo"
        midpoint = (shot_start+shot_end)/2
        context = next((str(cue["text"]) for cue in captions
                        if float(cue["start"]) <= midpoint <= float(cue["end"])), "")
        beat = next((item for item in config.get("story_beats", [])
                     if float(item.get("start_s", 0.0)) <= midpoint <= float(item.get("end_s", duration))),
                    {})
        if not context:
            context = str(beat.get("text", ""))
        shock_level = int(beat.get("shock_level", 0) or 0)
        # Nutty Putty's hybrid mode always stays on the plain white canvas.
        # Energy comes from moving artwork, quick overlays, and scene changes—not
        # from replacing the white background with a full-screen background image.
        shot_full_bleed = full_frame
        if hybrid_mode:
            card_scale = float(settings.get("card_scene_scale", 0.54))
            layout_side = "full_bleed" if shot_full_bleed else ("left" if index % 3 == 0 else ("center" if index % 3 == 1 else "right"))
            shot_scale = 1.0 if shot_full_bleed else card_scale
            shot_x = 0.0 if shot_full_bleed else (scene_x if layout_side == "left" else (0.0 if layout_side == "center" else -scene_x))
            shot_y = 0.0 if shot_full_bleed else scene_y
        else:
            layout_side = "full_bleed" if full_frame else "left"
            shot_scale = float(settings.get("scene_image_scale", 1.0 if full_frame else 0.50))
            shot_x = 0.0 if full_frame else scene_x
            shot_y = 0.0 if full_frame else scene_y
        scene_items.append({
            "type":media_type, "path":str(image_path), "start":round(shot_start,3),
            "duration":round(shot_duration,3), "ref":ref,
            "scale":shot_scale, "x":shot_x, "y":shot_y, "rotation":0
        })
        # The story-specific hybrid mode intentionally has no card/frame artwork.
        # The pure-white canvas stays visible around every moving source image.
        if not full_frame and not hybrid_mode and layout_side == "left":
            frame_items.append({
                "type":"photo", "path":assets["scene_cards"][index],
                "start":round(shot_start,3), "duration":round(shot_duration,3),
                "ref":frame_ref, "scale":1.0, "x":0.0, "y":0.0
            })
        layout_label = {
            "left": "A_subject-left_host-right",
            "center": "B_centered-hero",
            "right": "A_mirrored_subject-right_host-left",
            "full_bleed": "G_full-illustrated-action",
        }.get(layout_side, "A_subject-left_host-right")
        if not hybrid_mode:
            layout_label = "full-frame-illustration" if shot_full_bleed else "whiteboard-card-left / presenter-right"
        scene_rows.append({
            "start":shot_start, "end":shot_end, "duration":shot_duration,
            "image":str(image_path), "caption_context":context, "scene_ref":ref,
            "frame_ref":frame_ref,
            "layout":layout_label,
            "layout_template":layout_label,
            "layout_side":layout_side,
            "base_x":shot_x, "base_y":shot_y,
            "full_bleed":shot_full_bleed,
            "emotion":str(beat.get("emotion", "tense" if shot_full_bleed else "calm")),
            "shock_level":shock_level,
            "trigger_word":str(beat.get("trigger_word", "")),
        })

    operations: list[dict[str, Any]] = []
    start_scale = float(settings.get("scene_zoom_start", 1.0 if full_frame else motion.get("scene_zoom_start", 0.485)))
    end_scale = float(settings.get("scene_zoom_end", 1.06 if full_frame else motion.get("scene_zoom_end", 0.505)))
    pan_amount = float(settings.get("scene_pan_amount", motion.get("scene_pan_amount", 0.012)))
    for index, shot in enumerate(scene_rows):
        ref, frame_ref = str(shot["scene_ref"]), str(shot["frame_ref"])
        seconds = round(float(shot["duration"]),3)
        zoom_in = index%2 == 0
        scale_a, scale_b = (start_scale,end_scale) if zoom_in else (end_scale,start_scale)
        drift = pan_amount if index%2 == 0 else -pan_amount
        shot_base_x = float(shot.get("base_x", 0.0 if shot.get("full_bleed", full_frame) else scene_x))
        shot_base_y = float(shot.get("base_y", 0.0 if shot.get("full_bleed", full_frame) else scene_y))
        x_a, x_b = shot_base_x-drift, shot_base_x+drift
        y_a, y_b = shot_base_y+0.008, shot_base_y-0.008
        entrance_slug, entrance_duration = transition_for_scene(index, motion)
        scale_pop = entrance_slug.strip().lower() in {"scale-pop", "scale_pop", "scalepop"}
        # A few story cuts use an entrance scale-pop instead of a native transition:
        # begin slightly enlarged (never shrink below frame coverage), overshoot, then settle.
        if scale_pop:
            pop_peak_time = min(0.085, max(0.06, seconds * 0.08))
            pop_settle_time = min(max(pop_peak_time + 0.06, entrance_duration), max(0.14, seconds * 0.20))
            operations.extend([
                {"op":"keyframe","target":ref,"property":"uniform_scale","time":0.0,"value":scale_a * 1.025},
                {"op":"keyframe","target":ref,"property":"uniform_scale","time":round(pop_peak_time,3),"value":min(1.22, scale_a * 1.075),"easing":"ease-out"},
                {"op":"keyframe","target":ref,"property":"uniform_scale","time":round(pop_settle_time,3),"value":scale_a,"easing":"ease-out"},
                {"op":"keyframe","target":ref,"property":"uniform_scale","time":seconds,"value":scale_b,"easing":"ease-in-out"},
            ])
        else:
            if hybrid_mode:
                slide_in_duration = min(0.24, max(0.14, seconds * 0.11))
                operations.extend([
                    {"op":"keyframe","target":ref,"property":"uniform_scale","time":0.0,"value":scale_a * 0.86},
                    {"op":"keyframe","target":ref,"property":"uniform_scale","time":round(slide_in_duration,3),"value":scale_a * 1.045,"easing":"ease-out"},
                    {"op":"keyframe","target":ref,"property":"uniform_scale","time":round(slide_in_duration + 0.08,3),"value":scale_a,"easing":"ease-out"},
                    {"op":"keyframe","target":ref,"property":"uniform_scale","time":seconds,"value":scale_b,"easing":"ease-in-out"},
                ])
            else:
                # Keep the restrained original profile for other project presets.
                operations.extend([
                    {"op":"keyframe","target":ref,"property":"uniform_scale","time":0.0,"value":scale_a},
                    {"op":"keyframe","target":ref,"property":"uniform_scale","time":seconds,"value":scale_b,"easing":"ease-in-out"},
                ])
        entrance_directions = [
            (1.36, shot_base_y), (-1.36, shot_base_y),
            (shot_base_x, 1.28), (shot_base_x, -1.28),
        ]
        exit_directions = [
            (-1.36, shot_base_y), (1.36, shot_base_y),
            (shot_base_x, -1.28), (shot_base_x, 1.28),
        ]
        entry_x, entry_y = entrance_directions[index % len(entrance_directions)]
        exit_x, exit_y = exit_directions[index % len(exit_directions)]
        initial_x, initial_y = (entry_x, entry_y) if hybrid_mode else (x_a, y_a)
        final_x, final_y = (exit_x, exit_y) if hybrid_mode else (x_b, y_b)
        operations.extend([
            {"op":"keyframe","target":ref,"property":"position_x","time":0.0,"value":initial_x},
            {"op":"keyframe","target":ref,"property":"position_x","time":seconds,"value":final_x,"easing":"ease-in-out"},
            {"op":"keyframe","target":ref,"property":"position_y","time":0.0,"value":initial_y},
            {"op":"keyframe","target":ref,"property":"position_y","time":seconds,"value":final_y,"easing":"ease-in-out"},
        ])
        # Keep every still visibly alive: pulse its scale and drift its position at
        # intervals below one second, layered over the slow alternating push/pull.
        pulse_time = 0.72
        phase = (index % 4) * (math.pi / 2)
        t = pulse_time
        while t < seconds - 0.18:
            progress = t / max(0.25, seconds)
            base_scale = scale_a + (scale_b - scale_a) * progress
            pulse = 0.010 * math.sin((math.tau * t / 1.48) + phase)
            operations.extend([
                {"op":"keyframe","target":ref,"property":"uniform_scale","time":round(t,3),
                 "value":round(max(0.1, base_scale + pulse),4),"easing":"ease-in-out"},
                {"op":"keyframe","target":ref,"property":"position_x","time":round(t,3),
                 "value":round(shot_base_x + 0.006 * math.sin(math.tau*t/1.32 + phase),4),"easing":"ease-in-out"},
                {"op":"keyframe","target":ref,"property":"position_y","time":round(t,3),
                 "value":round(shot_base_y + 0.006 * math.cos(math.tau*t/1.48 + phase),4),"easing":"ease-in-out"},
            ])
            t += pulse_time

        shock_level = int(shot.get("shock_level", 0) or 0)
        if shock_level >= 2:
            # Impact beats get a snap-zoom and short decaying shake; delay it until
            # the flying image is on-canvas, so the image never teleports into place.
            impact_offset = 0.27 if hybrid_mode else 0.0
            snap_factor = 1.14 if shock_level >= 3 else 1.09
            snap_peak = min(1.25, max(scale_a * snap_factor, scale_a + (0.06 if shock_level >= 3 else 0.035)))
            shake = 0.012 if shock_level >= 3 else 0.006
            operations.extend([
                {"op":"keyframe","target":ref,"property":"uniform_scale","time":round(impact_offset + 0.06,3),"value":snap_peak,"easing":"ease-out"},
                {"op":"keyframe","target":ref,"property":"uniform_scale","time":round(impact_offset + 0.20,3),"value":scale_a,"easing":"ease-out"},
                {"op":"keyframe","target":ref,"property":"position_x","time":round(impact_offset + 0.06,3),"value":shot_base_x + shake},
                {"op":"keyframe","target":ref,"property":"position_x","time":round(impact_offset + 0.12,3),"value":shot_base_x - shake},
                {"op":"keyframe","target":ref,"property":"position_x","time":round(impact_offset + 0.19,3),"value":shot_base_x + shake * 0.45},
                {"op":"keyframe","target":ref,"property":"position_x","time":round(impact_offset + 0.28,3),"value":shot_base_x},
                {"op":"keyframe","target":ref,"property":"position_y","time":round(impact_offset + 0.06,3),"value":shot_base_y - shake * 0.6},
                {"op":"keyframe","target":ref,"property":"position_y","time":round(impact_offset + 0.12,3),"value":shot_base_y + shake * 0.6},
                {"op":"keyframe","target":ref,"property":"position_y","time":round(impact_offset + 0.19,3),"value":shot_base_y - shake * 0.2},
                {"op":"keyframe","target":ref,"property":"position_y","time":round(impact_offset + 0.28,3),"value":shot_base_y},
            ])
        if shock_level >= 3:
            impact_offset = 0.27 if hybrid_mode else 0.0
            operations.extend([
                {"op":"keyframe","target":ref,"property":"rotation","time":round(impact_offset + 0.0,3),"value":0.0},
                {"op":"keyframe","target":ref,"property":"rotation","time":round(impact_offset + 0.06,3),"value":1.0},
                {"op":"keyframe","target":ref,"property":"rotation","time":round(impact_offset + 0.12,3),"value":-1.15},
                {"op":"keyframe","target":ref,"property":"rotation","time":round(impact_offset + 0.19,3),"value":0.65},
                {"op":"keyframe","target":ref,"property":"rotation","time":round(impact_offset + 0.27,3),"value":-0.25},
                {"op":"keyframe","target":ref,"property":"rotation","time":round(impact_offset + 0.36,3),"value":0.0},
            ])
        if hybrid_mode:
            # Land on the selected composition after the entrance, drift/pulse while
            # visible, then fly out quickly to expose the clean white canvas at each cut.
            slide_in_duration = min(0.24, max(0.14, seconds * 0.11))
            exit_duration = min(0.22, max(0.14, seconds * 0.10))
            exit_start = max(slide_in_duration + 0.10, seconds - exit_duration)
            operations.extend([
                {"op":"keyframe","target":ref,"property":"position_x","time":round(slide_in_duration,3),"value":x_a,"easing":"ease-out"},
                {"op":"keyframe","target":ref,"property":"position_y","time":round(slide_in_duration,3),"value":y_a,"easing":"ease-out"},
                {"op":"keyframe","target":ref,"property":"position_x","time":round(exit_start,3),"value":x_b,"easing":"ease-in-out"},
                {"op":"keyframe","target":ref,"property":"position_y","time":round(exit_start,3),"value":y_b,"easing":"ease-in-out"},
                {"op":"keyframe","target":ref,"property":"position_x","time":seconds,"value":exit_x,"easing":"ease-in"},
                {"op":"keyframe","target":ref,"property":"position_y","time":seconds,"value":exit_y,"easing":"ease-in"},
            ])
        if index < len(scene_rows)-1:
            slug, cut_duration = transition_for_scene(index, motion)
            # "cut" is deliberately represented by the absence of a transition operation.
            if slug.strip().lower() in {"scale-pop", "scale_pop", "scalepop"}:
                # Already handled as a keyframed entrance at the start of this clip.
                pass
            elif slug.strip().lower() not in {"", "cut", "hard-cut", "none"} and cut_duration > 0:
                operations.append({"op":"transition","target":ref,"slug":slug,"duration":cut_duration})
                if not full_frame:
                    operations.append({"op":"transition","target":frame_ref,"slug":slug,"duration":cut_duration})

    # Brief second-image inserts accent selected high-impact beats while leaving a large
    # amount of clean white space. They use the next adjacent story illustration as a teaser.
    secondary_items: list[dict[str, Any]] = []
    secondary_motion: list[dict[str, Any]] = []
    if hybrid_mode and len(images) > 1:
        video_suffixes = {".mp4", ".mov", ".webm", ".m4v"}
        for index, shot in enumerate(scene_rows):
            if index == 0:
                continue
            shock_level = int(shot.get("shock_level", 0) or 0)
            if shock_level < 2 and index % 5 != 3:
                continue
            source_index = indices[index] if index < len(indices) else index % len(images)
            next_index = (source_index + 1) % len(images)
            for _ in range(len(images)):
                if images[next_index].suffix.lower() not in video_suffixes:
                    break
                next_index = (next_index + 1) % len(images)
            next_path = images[next_index]
            if next_path == Path(str(shot["image"])):
                continue
            shot_duration = float(shot["duration"])
            overlay_offset = min(0.48, shot_duration * 0.22)
            overlay_duration = min(0.86, shot_duration - overlay_offset - 0.16)
            if overlay_duration < 0.30:
                continue
            main_x = float(shot.get("base_x", 0.0))
            if abs(main_x) < 0.10:
                target_x = 0.58 if index % 2 == 0 else -0.58
            else:
                target_x = -0.58 if main_x > 0 else 0.58
            target_y = -0.04 if index % 2 == 0 else 0.05
            entry_x = 1.34 if target_x > 0 else -1.34
            exit_y = 1.28 if index % 2 == 0 else -1.28
            ref = "secondary_%03d" % (len(secondary_items) + 1)
            start_at = round(float(shot["start"]) + overlay_offset, 3)
            overlay_duration = round(overlay_duration, 3)
            media_type = "video" if next_path.suffix.lower() in video_suffixes else "photo"
            secondary_items.append({
                "type": media_type, "path": str(next_path), "start": start_at,
                "duration": overlay_duration, "ref": ref, "scale": 0.24,
                "x": target_x, "y": target_y,
            })
            secondary_motion.append({
                "ref": ref, "start": start_at, "duration": overlay_duration,
                "path": str(next_path), "target_x": target_x, "target_y": target_y,
                "entry_x": entry_x, "exit_y": exit_y,
            })
            enter = min(0.17, overlay_duration * 0.25)
            settle = min(0.26, enter + 0.07)
            exit_start = max(settle + 0.08, overlay_duration - 0.16)
            operations.extend([
                {"op":"keyframe","target":ref,"property":"uniform_scale","time":0.0,"value":0.12},
                {"op":"keyframe","target":ref,"property":"uniform_scale","time":round(enter,3),"value":0.275,"easing":"ease-out"},
                {"op":"keyframe","target":ref,"property":"uniform_scale","time":round(settle,3),"value":0.24,"easing":"ease-out"},
                {"op":"keyframe","target":ref,"property":"position_x","time":0.0,"value":entry_x},
                {"op":"keyframe","target":ref,"property":"position_x","time":round(enter,3),"value":target_x,"easing":"ease-out"},
                {"op":"keyframe","target":ref,"property":"position_x","time":round(exit_start,3),"value":target_x,"easing":"ease-in-out"},
                {"op":"keyframe","target":ref,"property":"position_x","time":overlay_duration,"value":target_x},
                {"op":"keyframe","target":ref,"property":"position_y","time":0.0,"value":target_y + 0.10},
                {"op":"keyframe","target":ref,"property":"position_y","time":round(enter,3),"value":target_y,"easing":"ease-out"},
                {"op":"keyframe","target":ref,"property":"position_y","time":round(exit_start,3),"value":target_y},
                {"op":"keyframe","target":ref,"property":"position_y","time":overlay_duration,"value":exit_y,"easing":"ease-in"},
            ])

    presenter_items: list[dict[str, Any]] = []
    plate_items: list[dict[str, Any]] = []
    presenter_rows: list[dict[str, Any]] = []
    if presenters and settings.get("presenter_overlay", True) and duration >= 4.0:
        presenter_scale = float(settings.get("presenter_scale", 0.42))
        presenter_mode = str(settings.get("presenter_mode", "persistent")).strip().lower()
        if presenter_mode == "reset":
            # Brief host returns, rather than an avatar covering the story art continuously.
            cadence = max(30.0, float(settings.get("presenter_pose_seconds", 35.0)))
            hold = min(3.0, max(1.0, float(settings.get("presenter_reset_duration", 2.2))))
            # Let the opening establish the subject first; presenter resets begin after one cadence.
            starts = [float(value) for value in range(int(cadence), max(1, int(duration)), int(cadence))]
            pose_plan = [
                (start, min(duration, start + hold), index % len(presenters))
                for index, start in enumerate(starts) if start < duration
            ]
        else:
            pose_target = max(4.5, float(settings.get("presenter_pose_seconds", motion.get("presenter_pose_seconds", 9.5))))
            count = min(len(presenters), max(1, int(round(duration / pose_target))))
            pose_indices = choose_scene_indices(len(presenters), count)
            pose_boundaries = [round(duration * i / count, 3) for i in range(count + 1)]
            pose_plan = [
                (pose_boundaries[index], pose_boundaries[index + 1], pose_index)
                for index, pose_index in enumerate(pose_indices)
            ]

        for index, (pose_start, pose_end, pose_index) in enumerate(pose_plan, start=1):
            pose_duration = max(0.25, pose_end - pose_start)
            ref, plate_ref = "presenter_%02d" % index, "presenter_plate_%02d" % index
            presenter_path = presenters[pose_index]
            host_x = presenter_x
            if hybrid_mode:
                host_scene = next((row for row in scene_rows
                                   if float(row["start"]) <= pose_start < float(row["end"])), None)
                side = str(host_scene.get("layout_side", "full_bleed")) if host_scene else "full_bleed"
                if side == "left":
                    host_x = 0.72
                elif side == "right":
                    host_x = -0.72
                else:
                    host_x = 0.72 if index % 2 else -0.72
            presenter_items.append({
                "type":"photo","path":str(presenter_path),"start":round(pose_start, 3),
                "duration":round(pose_duration, 3),"ref":ref,"scale":presenter_scale,
                "x":host_x,"y":presenter_y
            })
            plate_index = min(pose_index, len(assets["presenter_backplates"]) - 1) if assets["presenter_backplates"] else -1
            if plate_index >= 0:
                plate_items.append({
                    "type":"photo","path":assets["presenter_backplates"][plate_index],
                    "start":round(pose_start, 3),"duration":round(pose_duration, 3),"ref":plate_ref,
                    "scale":1.0,"x":0.0,"y":0.0
                })
            presenter_rows.append({
                "start":pose_start,"end":pose_end,"image":str(presenter_path),
                "ref":ref,"backplate_ref":plate_ref,
                "side":"left" if host_x < 0 else "right"
            })
            mid = round(pose_duration / 2, 3)
            operations.extend([
                {"op":"keyframe","target":ref,"property":"uniform_scale","time":0.0,"value":presenter_scale * 0.97 if presenter_mode == "reset" else presenter_scale},
                {"op":"keyframe","target":ref,"property":"uniform_scale","time":min(0.18, mid),"value":presenter_scale,"easing":"ease-out"},
                {"op":"keyframe","target":ref,"property":"uniform_scale","time":round(pose_duration, 3),"value":presenter_scale,"easing":"ease-in-out"},
                {"op":"keyframe","target":ref,"property":"position_y","time":0.0,"value":presenter_y + (0.035 if presenter_mode == "reset" else 0.008)},
                {"op":"keyframe","target":ref,"property":"position_y","time":min(0.22, mid),"value":presenter_y,"easing":"ease-out"},
                {"op":"keyframe","target":ref,"property":"position_y","time":round(pose_duration, 3),"value":presenter_y + 0.008,"easing":"ease-in-out"},
            ])
            if index < len(pose_plan) and presenter_mode != "reset":
                operations.append({"op":"transition","target":ref,"slug":"dissolve","duration":0.28})
                if settings.get("presenter_backplate", True) and plate_index >= 0:
                    operations.append({"op":"transition","target":plate_ref,"slug":"dissolve","duration":0.28})

    icon_items: list[dict[str, Any]] = []
    for index, overlay in enumerate(settings.get("icon_overlays", []), start=1):
        raw_icon_path = str(overlay.get("path", "")).strip()
        icon_path = Path(os.path.expandvars(raw_icon_path)).expanduser()
        if not icon_path.is_absolute():
            icon_path = CONFIG_PATH.parent / icon_path
        if not icon_path.is_file():
            log("Configured icon overlay is missing; skipped: " + raw_icon_path)
            continue
        scene_id = str(overlay.get("scene_id", "")).strip()
        try:
            requested_duration = max(0.25, float(overlay.get("duration", 1.4)))
            if overlay.get("start_seconds") is not None:
                icon_start = max(0.0, float(overlay.get("start_seconds", 0.0)))
                scene = next((row for row in scene_rows
                              if float(row["start"]) <= icon_start < float(row["end"])), None)
                if scene is None:
                    log("Icon absolute start falls outside the timeline; skipped: " + str(icon_start))
                    continue
                scene_id = str(scene["scene_ref"])
            else:
                scene = next((row for row in scene_rows if row.get("scene_ref") == scene_id), None)
                if scene is None:
                    log("Icon overlay references an unknown scene; skipped: " + scene_id)
                    continue
                offset = max(0.0, float(overlay.get("offset", 0.35)))
                icon_start = float(scene["start"]) + offset
            icon_end = min(float(scene["end"]), icon_start + requested_duration)
            icon_scale = float(overlay.get("scale", 0.16))
            icon_x = float(overlay.get("x", -0.56))
            icon_y = float(overlay.get("y", -0.42))
            if icon_start >= float(scene["end"]) or icon_end - icon_start < 0.25:
                log("Icon offset leaves too little room in " + scene_id + "; skipped.")
                continue
            if not (0.03 <= icon_scale <= 1.0 and -1.0 <= icon_x <= 1.0 and -1.0 <= icon_y <= 1.0):
                log("Invalid icon transform for " + scene_id + "; skipped.")
                continue
            ref = "icon_%03d" % index
            segment_duration = round(icon_end - icon_start, 3)
            icon_items.append({
                "type": "photo",
                "path": str(icon_path.resolve()),
                "start": round(icon_start, 3),
                "duration": segment_duration,
                "ref": ref,
                "scale": icon_scale * 0.88,
                "x": icon_x,
                "y": icon_y + 0.035,
            })
            enter_duration = min(0.18, segment_duration * 0.35)
            operations.extend([
                {"op":"keyframe","target":ref,"property":"uniform_scale","time":0.0,"value":icon_scale * 0.88},
                {"op":"keyframe","target":ref,"property":"uniform_scale","time":round(enter_duration,3),"value":icon_scale,"easing":"ease-out"},
                {"op":"keyframe","target":ref,"property":"position_y","time":0.0,"value":icon_y + 0.035},
                {"op":"keyframe","target":ref,"property":"position_y","time":round(enter_duration,3),"value":icon_y,"easing":"ease-out"},
            ])
        except (TypeError, ValueError):
            log("Invalid icon overlay settings; skipped: " + repr(overlay))

    audio_items = [{
        "path":str(audio),"start":0.0,"duration":round(duration,3),
        "volume":float(settings.get("voice_volume",0.96)),"ref":"voiceover"
    }]
    sfx_items: list[dict[str, Any]] = []
    for index, item in enumerate(settings.get("sound_effects", [])):
        raw = item.get("path","")
        path = Path(os.path.expandvars(str(raw))).expanduser()
        if not path.is_file():
            log("Optional local SFX path was not found; skipped: " + str(raw))
            continue
        try:
            start = max(0.0,float(item.get("start",0.0)))
            sound_duration = float(item.get("duration",0.0))
            if sound_duration <= 0:
                sound_duration = min(5.0,max(0.3,duration-start))
            if start >= duration:
                continue
            sfx_items.append({
                "path":str(path.resolve()),"start":round(start,3),
                "duration":round(min(sound_duration,duration-start),3),
                "volume":float(item.get("volume",0.16)),"ref":"local_sfx_%02d"%(index+1)
            })
        except (TypeError,ValueError):
            log("Invalid optional SFX entry skipped: " + str(item))

    # capcut-cli compile currently validates audio-fade using CLI flag names rather than
    # this spec's camelCase fields, causing the whole draft to fail before writing. Keep the
    # narration unchanged in the compile spec; any fade can be applied as a post-build CLI edit.
    # Full-sentence narration captions are optional. This project disables them;
    # only concise designed chapter titles and 1–3 word visual callouts remain.
    caption_items: list[dict[str, Any]] = []
    text_preset_name = str(motion.get("text_preset", "marker_caption"))
    text_preset = load_text_animation_preset(text_preset_name)
    transcript_enabled = bool(settings.get("add_captions_when_transcribed", True) and captions_path and captions)
    caption_sources: list[dict[str, Any]] = []
    max_words = int(settings.get("caption_words_per_chunk", text_preset.get("words_per_chunk", 5)))
    min_hold = float(settings.get("caption_min_hold_seconds", 0.85))
    if transcript_enabled:
        for cue in captions:
            cue_start = max(0.0, float(cue.get("start", 0.0)))
            cue_end = min(duration, float(cue.get("end", 0.0)))
            caption_sources.extend(split_timed_text(cue_start, cue_end, str(cue.get("text", "")), max_words, min_hold))
        caption_track_name = "Animated Captions"
    elif settings.get("show_scene_text_without_transcript", True) and config.get("scene_texts"):
        texts = config.get("scene_texts", [])
        for index, scene in enumerate(scene_rows):
            if index >= len(texts) or not str(texts[index]).strip():
                continue
            caption_sources.extend(split_timed_text(
                float(scene["start"]), float(scene["end"]), str(texts[index]),
                max_words, min_hold
            ))
        caption_track_name = "Animated Scene Callouts"
    else:
        caption_track_name = "Animated Captions"

    font_sizes = {
        "marker_caption": 30, "punch_caption": 38, "lower_third": 28,
        "kinetic_caption": 34, "typewriter": 30, "marker_underline": 28,
        "number_pop": 40, "side_callout": 28,
    }
    default_x, default_y = 0.0, float(settings.get("caption_y", 0.77))
    if text_preset_name == "lower_third":
        default_x, default_y = -0.42, float(settings.get("caption_y", 0.72))
    elif text_preset_name == "punch_caption":
        default_x, default_y = 0.0, float(settings.get("caption_y", 0.64))
    elif text_preset_name == "side_callout":
        default_x, default_y = -0.36, float(settings.get("caption_y", 0.22))
    font_size = int(settings.get("caption_font_size", font_sizes.get(text_preset_name, 18)))
    text_color = str(settings.get("caption_color", "#FFFFFF"))
    danger_words = {str(word).lower() for word in settings.get("caption_danger_words", [
        "stuck", "corkscrew", "uncharted", "head first", "gravity", "trapped",
        "hallucinating", "oxygen", "screamed", "snapped", "no pulse", "deeper",
        "dead", "sealed", "concrete", "upside down"
    ])}
    action_words = {str(word).lower() for word in settings.get("caption_action_words", [
        "six feet", "two hundred", "eighteen inches", "fourteen hours",
        "twelve hours", "twenty-seven hours", "4 a.m.", "11:56 p.m.", "24 hours"
    ])}
    for index, cue in enumerate(caption_sources, start=1):
        clip_duration = round(float(cue["end"]) - float(cue["start"]), 3)
        if clip_duration < 0.25:
            continue
        cue_text = str(cue["text"])
        normalized_text = re.sub(r"[^a-z0-9:'. ]+", " ", cue_text.lower())
        if any(phrase in normalized_text for phrase in danger_words):
            cue_color = str(settings.get("caption_danger_color", "#FF3030"))
        elif any(phrase in normalized_text for phrase in action_words):
            cue_color = str(settings.get("caption_action_color", "#FFD447"))
        else:
            cue_color = text_color
        ref = "caption_%04d" % index
        text_item = {
            "text": cue_text,
            "start": round(float(cue["start"]), 3),
            "duration": clip_duration,
            "fontSize": font_size,
            "color": cue_color,
            "x": float(settings.get("caption_x", default_x)),
            "y": default_y + 0.025,
            "ref": ref,
        }
        caption_items.append(text_item)
        operations.append({
            "op": "text-style",
            "target": ref,
            "style": {
                "shadow": True,
                "shadowAlpha": 0.42,
                "shadowColor": "#000000",
                "shadowDistance": 2,
                "shadowSmoothing": 2,
                "borderWidth": float(settings.get("caption_outline_width", 4.0)),
                "borderColor": str(settings.get("caption_outline_color", "#000000")),
                "borderAlpha": float(settings.get("caption_outline_alpha", 1.0)),
            },
        })
        entrance_time = min(0.16, clip_duration * 0.24)
        # CapCut does not reliably render alpha/opacity keyframes on text segments.
        # Use supported position keyframes for the tiny float, plus native text-anim below.
        operations.extend([
            {"op":"keyframe","target":ref,"property":"position_y","time":0.0,"value":default_y + 0.025},
            {"op":"keyframe","target":ref,"property":"position_y","time":round(entrance_time,3),"value":default_y,"easing":"ease-out"},
        ])

    bg_item = {
        "type":"photo","path":assets["background"],"start":0.0,
        "duration":round(duration,3),"ref":"whiteboard_background",
        "scale":1.0,"x":0.0,"y":0.0
    }
    tracks: list[dict[str,Any]] = []
    if not full_frame:
        tracks.append({"type":"video","name":"Whiteboard Background","items":[bg_item]})
        if not hybrid_mode:
            tracks.append({"type":"video","name":"Whiteboard Scene Frames","items":frame_items})
    tracks.append({"type":"video","name":"Scene Artwork","items":scene_items})
    if secondary_items:
        tracks.append({"type":"video","name":"Fast Secondary Image Inserts","items":secondary_items})

    horror_items: list[dict[str, Any]] = []
    horror_path_raw = str(settings.get("horror_overlay_path", "")).strip()
    if horror_path_raw:
        horror_path = Path(os.path.expandvars(horror_path_raw)).expanduser()
        if not horror_path.is_absolute():
            horror_path = CONFIG_PATH.parent / horror_path
        if horror_path.is_file():
            for index, raw_start in enumerate(settings.get("horror_overlay_times", []), start=1):
                try:
                    start = max(0.0, float(raw_start))
                    overlay_duration = min(0.72, max(0.25, float(settings.get("horror_overlay_duration", 0.62))))
                    if start >= duration:
                        continue
                    horror_items.append({
                        "type":"photo","path":str(horror_path.resolve()),"start":round(start, 3),
                        "duration":round(min(overlay_duration, duration - start), 3),
                        "ref":"horror_tint_%02d" % index,"scale":1.0,"x":0.0,"y":0.0
                    })
                except (TypeError, ValueError):
                    log("Invalid horror tint time skipped: " + repr(raw_start))
        else:
            log("Horror tint overlay was not found; skipped: " + horror_path_raw)
    if horror_items:
        tracks.append({"type":"video","name":"Critical Horror Tint","items":horror_items})

    if icon_items:
        tracks.append({"type":"video","name":"Icon Overlays","items":icon_items})
    if plate_items and settings.get("presenter_backplate", True):
        tracks.append({"type":"video","name":"Presenter Accent","items":plate_items})
    if presenter_items:
        tracks.append({"type":"video","name":"Presenter Explainer","items":presenter_items})

    # Story-fact callouts are full-frame transparent PNG overlays created by the local project preprocessor.
    # Their background remains transparent, so they form an independent CapCut track over the supplied artwork.
    callout_items: list[dict[str, Any]] = []
    for index, overlay in enumerate(settings.get("callout_overlays", []), start=1):
        raw_path = str(overlay.get("path", "")).strip()
        callout_path = Path(os.path.expandvars(raw_path)).expanduser()
        if not callout_path.is_absolute():
            callout_path = CONFIG_PATH.parent / callout_path
        if not callout_path.is_file():
            log("Story fact callout image not found; skipped: " + raw_path)
            continue
        try:
            start = max(0.0, float(overlay.get("start_seconds", 0.0)))
            requested_duration = max(0.25, float(overlay.get("duration", 1.15)))
            if start >= duration:
                continue
            segment_duration = min(requested_duration, duration - start)
            ref = "story_callout_%03d" % index
            callout_items.append({
                "type":"photo","path":str(callout_path.resolve()),"start":round(start, 3),
                "duration":round(segment_duration, 3),"ref":ref,
                "scale":1.0,"x":0.0,"y":0.0
            })
            entrance = min(0.18, segment_duration * 0.32)
            operations.extend([
                {"op":"keyframe","target":ref,"property":"uniform_scale","time":0.0,"value":0.965},
                {"op":"keyframe","target":ref,"property":"uniform_scale","time":round(entrance, 3),"value":1.0,"easing":"ease-out"},
            ])
        except (TypeError, ValueError):
            log("Invalid story callout settings; skipped: " + repr(overlay))
    if callout_items:
        tracks.append({"type":"video","name":"Story Fact Callouts","items":callout_items})

    flash_items: list[dict[str, Any]] = []
    flash_path_raw = str(settings.get("flash_overlay_path", "")).strip()
    if flash_path_raw:
        flash_path = Path(os.path.expandvars(flash_path_raw)).expanduser()
        if not flash_path.is_absolute():
            flash_path = CONFIG_PATH.parent / flash_path
        if flash_path.is_file():
            for index, raw_start in enumerate(settings.get("flash_times", []), start=1):
                try:
                    flash_start = max(0.0, float(raw_start))
                    flash_duration = min(0.09, max(0.05, float(settings.get("flash_duration", 0.067))))
                    if flash_start >= duration:
                        continue
                    flash_items.append({
                        "type":"photo","path":str(flash_path.resolve()),
                        "start":round(flash_start, 3),
                        "duration":round(min(flash_duration, duration - flash_start), 3),
                        "ref":"shock_flash_%02d" % index,
                        "scale":1.0,"x":0.0,"y":0.0
                    })
                except (TypeError, ValueError):
                    log("Invalid shock flash time skipped: " + repr(raw_start))
        else:
            log("Configured flash image not found; flash overlays skipped: " + str(flash_path))
    if flash_items:
        tracks.append({"type":"video","name":"Shock Flash Hits","items":flash_items})
    if caption_items:
        tracks.append({"type":"text","name":caption_track_name,"items":caption_items}
        )

    # Optional continuous music/ambience is kept on its own audio track below narration.
    music_config = config.get("background_music", {})
    if isinstance(music_config, str):
        music_config = {"path": music_config}
    music_path_raw = str(music_config.get("path", "")).strip() if isinstance(music_config, dict) else ""
    music_items: list[dict[str, Any]] = []
    if music_path_raw:
        music_path = Path(os.path.expandvars(music_path_raw)).expanduser()
        if not music_path.is_absolute():
            music_path = CONFIG_PATH.parent / music_path
        if music_path.is_file():
            music_start = max(0.0, float(music_config.get("start", 0.0)))
            music_length = float(music_config.get("duration", duration))
            music_end = min(duration, music_start + max(0.0, music_length))
            if music_end > music_start:
                music_items.append({
                    "path": str(music_path.resolve()), "start": round(music_start, 3),
                    "duration": round(music_end - music_start, 3),
                    "volume": max(0.0, min(1.0, float(music_config.get("volume", 0.22)))),
                    "ref": "background_suspense_bed",
                })
        else:
            log("Configured background music was not found; skipped: " + str(music_path))
    if music_items:
        tracks.append({"type":"audio","name":"Suspense Music / Ambience","items":music_items})

    # Chapter titles use a dedicated text track at the top safe area.
    chapter_items: list[dict[str, Any]] = []
    for index, chapter in enumerate(config.get("chapter_titles", []), start=1):
        try:
            chapter_start = max(0.0, float(chapter.get("start_s", 0.0)))
            chapter_length = max(0.7, float(chapter.get("duration_s", 1.8)))
            chapter_end = min(duration, chapter_start + chapter_length)
            title = str(chapter.get("title", "")).strip()
            if not title or chapter_end <= chapter_start:
                continue
            ref = "chapter_title_%02d" % index
            chapter_items.append({
                "text": title, "start": round(chapter_start, 3),
                "duration": round(chapter_end - chapter_start, 3),
                "fontSize": int(chapter.get("font_size", 32)),
                "color": str(chapter.get("color", "#FFFFFF")),
                "x": float(chapter.get("x", 0.0)),
                "y": float(chapter.get("y", -0.78)),
                "ref": ref,
            })
            operations.append({
                "op":"text-style","target":ref,"style":{
                    "shadow":True,"shadowAlpha":0.55,"shadowColor":"#000000",
                    "shadowDistance":3,"shadowSmoothing":2,
                    "borderWidth":3.0,"borderColor":"#000000","borderAlpha":1.0,
                }
            })
            operations.extend([
                {"op":"keyframe","target":ref,"property":"position_y","time":0.0,"value":float(chapter.get("y",-0.78))+0.03},
                {"op":"keyframe","target":ref,"property":"position_y","time":0.16,"value":float(chapter.get("y",-0.78)),"easing":"ease-out"},
            ])
        except (TypeError, ValueError):
            log("Invalid chapter title record skipped: " + repr(chapter))
    if chapter_items:
        tracks.append({"type":"text","name":"Chapter Titles","items":chapter_items})

    tracks.append({"type":"audio","name":"Narration","items":audio_items})
    if hybrid_mode and secondary_motion:
        configured_cues = settings.get("sound_effects", [])
        for overlay_index, overlay in enumerate(secondary_motion):
            if any(abs(float(item.get("start", 0.0)) - float(overlay["start"])) <= 0.10 for item in sfx_items):
                continue
            if not configured_cues:
                break
            chosen = configured_cues[(overlay_index * 3) % len(configured_cues)]
            cue_path = Path(os.path.expandvars(str(chosen.get("path", "")))).expanduser()
            if not cue_path.is_file():
                continue
            cue_duration = min(0.38, float(overlay["duration"]))
            if cue_duration <= 0:
                continue
            sfx_items.append({
                "path": str(cue_path.resolve()), "start": float(overlay["start"]),
                "duration": cue_duration,
                "volume": min(0.24, max(0.15, float(chosen.get("volume", 0.18)))),
                "ref": "secondary_entrance_sfx_%03d" % (overlay_index + 1),
            })
    if sfx_items:
        sfx_items.sort(key=lambda item: float(item.get("start", 0.0)))
        tracks.append({"type":"audio","name":"Local Sound Effects","items":sfx_items})
    spec = {
        "name":str(config.get("project_name","Video1 Test - Whiteboard Explainer PRO")),
        "width":width,"height":height,"fps":int(canvas.get("fps",30)),
        "ratio":str(canvas.get("ratio","16:9")),"tracks":tracks,"operations":operations
    }
    return spec,scene_rows,presenter_rows


def write_scene_csv(path: Path, scenes: list[dict[str, Any]], presenters: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "start", "end", "duration", "image", "caption_context",
                "scene_ref", "frame_ref", "layout", "layout_template", "layout_side", "base_x", "base_y", "full_bleed", "presenter_ref",
                "emotion", "trigger_word", "shock_level",
            ],
        )
        writer.writeheader()
        for scene in scenes:
            center = (float(scene["start"]) + float(scene["end"])) / 2
            matching = next(
                (p for p in presenters if float(p["start"]) <= center <= float(p["end"])),
                None,
            )
            row = dict(scene)
            row["presenter_ref"] = matching["ref"] if matching else ""
            writer.writerow(row)


def write_sfx_cues(path: Path, duration: float, scenes: list[dict[str, Any]], captions: list[dict[str, Any]]) -> None:
    suggestions: list[tuple[float, str, str]] = []
    suggestions.append((min(0.5, duration * 0.05), "soft cinematic whoosh", "Opening visual entrance"))
    for index, scene in enumerate(scenes):
        if index > 0 and index % 5 == 0:
            suggestions.append((float(scene["start"]), "short transition whoosh", "Mark a larger visual chapter change"))

    keywords = {
        "suspense impact": [
            "suddenly", "secret", "danger", "shocking", "surprise", "mistake", "wrong",
            "but then", "however", "unexpected", "problem", "scared", "fear", "dark",
            "فجأة", "سر", "خطر", "صدمة", "مفاجأة", "خطأ", "مشكلة",
        ],
        "light cartoon pop": [
            "funny", "joke", "ridiculous", "silly", "oops", "imagine that",
            "مضحك", "نكتة", "تخيل",
        ],
    }
    for cue in captions:
        text = str(cue["text"]).lower()
        selected = None
        for sound_name, words in keywords.items():
            if any(word in text for word in words):
                selected = sound_name
                break
        if selected:
            suggestions.append((float(cue["start"]), selected, "Accent near spoken phrase: " + str(cue["text"])))

    if duration > 18:
        suggestions.append((duration * 0.52, "low cinematic hit", "Optional midpoint emphasis"))
    if duration > 12:
        suggestions.append((max(0.1, duration - 2.0), "soft reverse whoosh", "Optional ending transition"))

    suggestions.sort(key=lambda item: item[0])
    filtered: list[tuple[float, str, str]] = []
    for cue in suggestions:
        if cue[0] < 0 or cue[0] >= duration:
            continue
        if filtered and cue[0] - filtered[-1][0] < 3.2:
            continue
        filtered.append(cue)

    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time_seconds", "suggested_capcut_search", "reason", "note"])
        for time_seconds, search, reason in filtered:
            writer.writerow([
                round(time_seconds, 3), search, reason,
                "Suggestion only: manually choose a sound from CapCut's library and keep it below the voice."
            ])


def main(argv: list[str] | None = None) -> int:
    global CONFIG_PATH, BUILD_DIR
    parser = argparse.ArgumentParser(description="Build an editable local CapCut draft.")
    parser.add_argument("--config", default=str(ROOT / "config.json"), help="Project JSON config path.")
    parser.add_argument("--build-dir", default=None, help="Project-local build output directory.")
    args = parser.parse_args(argv)
    CONFIG_PATH = Path(args.config).expanduser().resolve()
    BUILD_DIR = Path(args.build_dir).expanduser().resolve() if args.build_dir else CONFIG_PATH.parent / "build"
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    config = load_config(CONFIG_PATH)
    settings = config.get("settings", {})

    audio_raw = str(config.get("audio", "")).strip()
    audio = Path(os.path.expandvars(audio_raw)).expanduser()
    if not audio.is_absolute():
        audio = CONFIG_PATH.parent / audio
    if not audio.is_file():
        raise RuntimeError(
            "The narration file was not found: " + audio_raw
            + "\nUpdate the audio path in config.json, then run the builder again."
        )
    audio = audio.resolve()
    duration = audio_duration(audio)
    log("Voiceover duration: " + str(round(duration, 2)) + " seconds.")

    raw_scene_images = [str(item) for item in config.get("scene_images", [])]
    images, missing_scenes = usable_paths(raw_scene_images, "scene image")
    if not images:
        raise RuntimeError("No scene images were found. Check scene_images in config.json.")
    raw_presenters = [str(item) for item in config.get("presenter_images", [])]
    presenters, missing_presenters = usable_paths(raw_presenters, "presenter image")

    captions, captions_path = transcribe_if_available(audio, settings)
    spec, scenes, presenter_rows = make_spec(
        config, audio, images, presenters, duration, captions, captions_path
    )

    spec_path = BUILD_DIR / "compile-spec.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    scene_csv = BUILD_DIR / "scene_timing.csv"
    write_scene_csv(scene_csv, scenes, presenter_rows)
    if settings.get("make_sfx_cue_sheet", True):
        write_sfx_cues(BUILD_DIR / "SFX_Cue_Sheet.csv", duration, scenes, captions)

    capcut = shutil.which("capcut")
    if not capcut:
        raise RuntimeError(
            "The capcut command was not found. In PowerShell run: npm install -g capcut-cli. "
            "Then close and reopen VS Code and run the builder again."
        )

    drafts_dir = discover_drafts_dir(str(config.get("drafts_dir", "")))
    drafts_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = "Video1_Whiteboard_Pro_" + stamp
    out_dir = drafts_dir / folder_name
    env = os.environ.copy()
    env["CAPCUT_DRAFT_DIR"] = str(drafts_dir)

    command = [
        capcut, "compile", str(spec_path),
        "--drafts", str(drafts_dir),
        "--out", str(out_dir),
    ]
    log("Creating a real CapCut draft at: " + str(out_dir))
    result = subprocess.run(command, text=True, capture_output=True, env=env, check=False)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.returncode != 0:
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
        raise RuntimeError(
            "capcut-cli could not create the draft. Check the CLI output above, confirm CapCut is closed, "
            "then run capcut doctor and retry."
        )

    payload: dict[str, Any] = {}
    output_text = result.stdout.strip()
    if output_text:
        try:
            payload = json.loads(output_text)
        except json.JSONDecodeError:
            # Some CLI builds print a status line before their pretty-printed JSON.
            decoder = json.JSONDecoder()
            for offset, character in enumerate(output_text):
                if character not in "{[":
                    continue
                try:
                    candidate, _ = decoder.raw_decode(output_text[offset:])
                except json.JSONDecodeError:
                    continue
                if isinstance(candidate, dict) and ("draft_path" in candidate or "refs" in candidate):
                    payload = candidate
                    break

    draft_path = Path(str(payload.get("draft_path", out_dir))).resolve()
    refs = payload.get("refs", {}) if isinstance(payload.get("refs", {}), dict) else {}
    matting_results: list[dict[str, str]] = []
    if presenter_rows:
        for presenter in presenter_rows:
            segment_id = refs.get(str(presenter["ref"]))
            if not segment_id:
                matting_results.append({"ref": str(presenter["ref"]), "status": "missing segment id"})
                continue

            entry: dict[str, str] = {"ref": str(presenter["ref"])}
            if settings.get("presenter_smart_matte", True):
                matte = subprocess.run(
                    [capcut, "matting", str(draft_path), str(segment_id)],
                    text=True, capture_output=True, env=env, check=False,
                )
                okay = matte.returncode == 0
                entry["matting"] = "applied" if okay else "not applied"
                if not okay:
                    entry["matting_detail"] = (matte.stderr or matte.stdout or "").strip()[-500:]
                    log("Smart matting did not apply to " + str(presenter["ref"]) + "; check this pose in CapCut.")
            else:
                entry["matting"] = "disabled in config"

            matting_results.append(entry)


    # Only the opening image gets a zoom-out entrance; other cuts use the deliberate transitions above.
    first_scene_id = refs.get("scene_001")
    if first_scene_id:
        intro_result = subprocess.run(
            [capcut, "image-anim", str(draft_path), str(first_scene_id),
             "--intro", "zoom-out", "--intro-duration", "0.55"],
            text=True, capture_output=True, env=env, check=False,
        )
        if intro_result.returncode != 0:
            log("Opening reveal animation unavailable; keyframed movement remains.")

    if presenter_rows:
        first_presenter_id = refs.get(str(presenter_rows[0]["ref"]))
        last_presenter_id = refs.get(str(presenter_rows[-1]["ref"]))
        if first_presenter_id:
            subprocess.run(
                [capcut, "image-anim", str(draft_path), str(first_presenter_id),
                 "--intro", "fade-in", "--intro-duration", "0.55"],
                text=True, capture_output=True, env=env, check=False,
            )
        if last_presenter_id:
            subprocess.run(
                [capcut, "image-anim", str(draft_path), str(last_presenter_id),
                 "--outro", "fade-out", "--outro-duration", "0.55"],
                text=True, capture_output=True, env=env, check=False,
            )

    text_animation_results: list[dict[str, str]] = []
    selected_motion = load_motion_preset(settings)
    text_preset_name = str(selected_motion.get("text_preset", "marker_caption"))
    text_intro_by_preset = {
        "marker_caption": "fade-in",
        "marker_underline": "fade-in",
        "typewriter": "typewriter",
        "punch_caption": "pop-up",
        "kinetic_caption": "pop-up",
        "lower_third": "fade-in",
        "side_callout": "fade-in",
        "number_pop": "pop-up",
    }
    text_intro = text_intro_by_preset.get(text_preset_name)
    if text_intro:
        text_segments = [
            item for track in spec["tracks"] if track.get("type") == "text"
            for item in track.get("items", [])
        ]
        for item in text_segments:
            segment_id = refs.get(str(item.get("ref", "")))
            if not segment_id or float(item.get("duration", 0.0)) < 0.45:
                continue
            intro_duration = min(0.42, max(0.12, float(item["duration"]) * 0.18))
            result_text_anim = subprocess.run(
                [capcut, "text-anim", str(draft_path), str(segment_id),
                 "--intro", text_intro, "--intro-duration", str(round(intro_duration, 3))],
                text=True, capture_output=True, env=env, check=False,
            )
            entry = {
                "ref": str(item.get("ref", "")),
                "animation": text_intro,
                "status": "applied" if result_text_anim.returncode == 0 else "not applied",
            }
            if result_text_anim.returncode != 0:
                entry["detail"] = (result_text_anim.stderr or result_text_anim.stdout or "").strip()[-300:]
            text_animation_results.append(entry)
        if text_animation_results:
            log("Applied native CapCut text intro animations to " + str(sum(1 for item in text_animation_results if item["status"] == "applied")) + " text segment(s).")

    register_result = subprocess.run(
        [capcut, "register", str(draft_path), "--apply"],
        text=True, capture_output=True, env=env, check=False,
    )
    registered = register_result.returncode == 0
    if registered:
        log("Registered the PRO draft in CapCut: " + spec["name"])
    else:
        detail = (register_result.stderr or register_result.stdout or "").strip()
        log("Automatic registration did not complete; the draft was still created. " + detail[-400:])

    report = {
        "ok": True,
        "project_name": spec["name"],
        "draft_path": str(draft_path),
        "drafts_dir": str(drafts_dir),
        "audio": str(audio),
        "audio_duration_seconds": round(duration, 3),
        "scene_images_available": len(images),
        "scene_images_missing": missing_scenes,
        "presenter_images_available": len(presenters),
        "presenter_images_missing": missing_presenters,
        "scene_segments": len(scenes),
        "presenter_segments": len(presenter_rows),
        "icon_overlay_segments": sum(len(track.get("items", [])) for track in spec["tracks"] if track.get("name") == "Icon Overlays"),
        "registered_in_capcut": registered,
        "visual_assets_dir": str(Path(spec["tracks"][0]["items"][0]["path"]).parent),
        "caption_cues": sum(len(track["items"]) for track in spec["tracks"] if track.get("type") == "text"),
        "caption_file": str(captions_path) if captions_path else None,
        "matting": matting_results,
        "text_animations": text_animation_results,
        "warnings": payload.get("warnings", []),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "notes": [
            "This is an editable CapCut draft, not a rendered MP4.",
            "The visual treatment uses a whiteboard canvas, framed scene cards, and a presenter track.",
            "Scene timing can snap to Whisper caption ends, but semantic image matching still needs human review.",
            "The sound-effects cue sheet contains suggestions only; it does not claim that library SFX were automatically inserted.",
        ],
    }
    (BUILD_DIR / "build_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    log("Draft creation finished.")
    log("Draft directory: " + str(draft_path))
    log("Visual assets: " + str(Path(spec["tracks"][0]["items"][0]["path"]).parent))
    log("Shot plan: " + str(scene_csv))
    if settings.get("make_sfx_cue_sheet", True):
        log("Sound-effect cue sheet: " + str(BUILD_DIR / "SFX_Cue_Sheet.csv"))
    if any(track.get("type") == "text" for track in spec["tracks"]):
        log("Editable phrase-level text overlays were added with fade/float keyframes.")
    elif captions_path:
        log("Whisper transcript exists, but text overlays were disabled by this project's settings.")
    else:
        log("No automatic captions were added. Install Whisper to enable transcript timing and captions.")
    log("Reopen CapCut and inspect the project before exporting.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("\nERROR: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
