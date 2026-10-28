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

    board = Image.new("RGB", (width, height), paper)
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
    """Apply a preset's calm default transition and sparse, purposeful accent transitions."""
    motion = motion or {}
    rules = motion.get("transitions", {})
    default = rules.get("default", {"slug": "dissolve", "duration": 0.24})
    number = index + 1
    for rule in rules.get("accents", []):
        every = int(rule.get("every", 0) or 0)
        if every > 0 and number % every == 0:
            return str(rule.get("slug", default.get("slug", "dissolve"))), float(rule.get("duration", default.get("duration", 0.24))
    return str(default.get("slug", "dissolve")), float(default.get("duration", 0.24))



def make_spec(
    config: dict[str, Any], audio: Path, images: list[Path], presenters: list[Path],
    duration: float, captions: list[dict[str, Any]], captions_path: Path | None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    settings = config.get("settings", {})
    motion = load_motion_preset(settings)
    canvas = config.get("canvas", {})
    width, height = int(canvas.get("width", 1920)), int(canvas.get("height", 1080))
    target = max(1.0, float(settings.get("target_shot_seconds", motion.get("target_shot_seconds", 3.8))))
    minimum = max(0.75, float(settings.get("minimum_shot_seconds", motion.get("minimum_shot_seconds", 1.8))))
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
        width, height, shot_count,
        len(presenters) if settings.get("presenter_overlay", True) else 0,
        scene_x=scene_x, scene_y=scene_y, presenter_x=presenter_x, presenter_y=presenter_y
    )

    scene_items: list[dict[str, Any]] = []
    frame_items: list[dict[str, Any]] = []
    scene_rows: list[dict[str, Any]] = []
    for index, image_index in enumerate(indices):
        shot_start, shot_end = boundaries[index], boundaries[index+1]
        shot_duration = max(0.25, shot_end-shot_start)
        image_path = images[image_index]
        ref, frame_ref = "scene_%03d" % (index+1), "frame_%03d" % (index+1)
        scene_items.append({
            "type":"photo", "path":str(image_path), "start":round(shot_start,3),
            "duration":round(shot_duration,3), "ref":ref,
            "scale":float(settings.get("scene_image_scale",0.50)),
            "x":scene_x, "y":scene_y, "rotation":0
        })
        frame_items.append({
            "type":"photo", "path":assets["scene_cards"][index],
            "start":round(shot_start,3), "duration":round(shot_duration,3),
            "ref":frame_ref, "scale":1.0, "x":0.0, "y":0.0
        })
        midpoint = (shot_start+shot_end)/2
        context = next((str(cue["text"]) for cue in captions
                        if float(cue["start"]) <= midpoint <= float(cue["end"])), "")
        scene_rows.append({
            "start":shot_start, "end":shot_end, "duration":shot_duration,
            "image":str(image_path), "caption_context":context, "scene_ref":ref,
            "frame_ref":frame_ref, "layout":"whiteboard-card-left / presenter-right"
        })

    operations: list[dict[str, Any]] = []
    start_scale = float(settings.get("scene_zoom_start", motion.get("scene_zoom_start", 0.485)))
    end_scale = float(settings.get("scene_zoom_end", motion.get("scene_zoom_end", 0.505)))
    pan_amount = float(settings.get("scene_pan_amount", motion.get("scene_pan_amount", 0.012)))
    for index, shot in enumerate(scene_rows):
        ref, frame_ref = str(shot["scene_ref"]), str(shot["frame_ref"])
        seconds = round(float(shot["duration"]),3)
        zoom_in = index%2 == 0
        scale_a, scale_b = (start_scale,end_scale) if zoom_in else (end_scale,start_scale)
        drift = pan_amount if index%2 == 0 else -pan_amount
        x_a, x_b = scene_x-drift, scene_x+drift
        y_a, y_b = scene_y+0.008, scene_y-0.008
        # First point is linear; the next point supplies easing without spurious warnings.
        operations.extend([
            {"op":"keyframe","target":ref,"property":"uniform_scale","time":0.0,"value":scale_a},
            {"op":"keyframe","target":ref,"property":"uniform_scale","time":seconds,"value":scale_b,"easing":"ease-in-out"},
            {"op":"keyframe","target":ref,"property":"position_x","time":0.0,"value":x_a},
            {"op":"keyframe","target":ref,"property":"position_x","time":seconds,"value":x_b,"easing":"ease-in-out"},
            {"op":"keyframe","target":ref,"property":"position_y","time":0.0,"value":y_a},
            {"op":"keyframe","target":ref,"property":"position_y","time":seconds,"value":y_b,"easing":"ease-in-out"},
        ])
        if index < len(scene_rows)-1:
            slug, cut_duration = transition_for_scene(index, motion)
            operations.append({"op":"transition","target":ref,"slug":slug,"duration":cut_duration})
            operations.append({"op":"transition","target":frame_ref,"slug":slug,"duration":cut_duration})

    presenter_items: list[dict[str, Any]] = []
    plate_items: list[dict[str, Any]] = []
    presenter_rows: list[dict[str, Any]] = []
    if presenters and settings.get("presenter_overlay",True) and duration >= 4.0:
        pose_target = max(4.5,float(settings.get("presenter_pose_seconds",motion.get("presenter_pose_seconds",9.5))))
        count = min(len(presenters),max(1,int(round(duration/pose_target))))
        pose_indices = choose_scene_indices(len(presenters),count)
        pose_boundaries = [round(duration*i/count,3) for i in range(count+1)]
        presenter_scale = float(settings.get("presenter_scale",0.42))
        for index, pose_index in enumerate(pose_indices):
            pose_start, pose_end = pose_boundaries[index],pose_boundaries[index+1]
            pose_duration = max(0.25,pose_end-pose_start)
            ref, plate_ref = "presenter_%02d"%(index+1),"presenter_plate_%02d"%(index+1)
            presenter_path = presenters[pose_index]
            presenter_items.append({
                "type":"photo","path":str(presenter_path),"start":pose_start,
                "duration":pose_duration,"ref":ref,"scale":presenter_scale,
                "x":presenter_x,"y":presenter_y
            })
            plate_items.append({
                "type":"photo","path":assets["presenter_backplates"][index],
                "start":pose_start,"duration":pose_duration,"ref":plate_ref,
                "scale":1.0,"x":0.0,"y":0.0
            })
            presenter_rows.append({
                "start":pose_start,"end":pose_end,"image":str(presenter_path),
                "ref":ref,"backplate_ref":plate_ref,"side":"right"
            })
            mid = round(pose_duration/2,3)
            operations.extend([
                {"op":"keyframe","target":ref,"property":"uniform_scale","time":0.0,"value":presenter_scale},
                {"op":"keyframe","target":ref,"property":"uniform_scale","time":mid,"value":presenter_scale+0.012,"easing":"ease-in-out"},
                {"op":"keyframe","target":ref,"property":"uniform_scale","time":round(pose_duration,3),"value":presenter_scale,"easing":"ease-in-out"},
                {"op":"keyframe","target":ref,"property":"position_y","time":0.0,"value":presenter_y+0.008},
                {"op":"keyframe","target":ref,"property":"position_y","time":mid,"value":presenter_y-0.008,"easing":"ease-in-out"},
                {"op":"keyframe","target":ref,"property":"position_y","time":round(pose_duration,3),"value":presenter_y+0.008,"easing":"ease-in-out"},
            ])
            if index < len(pose_indices)-1:
                operations.append({"op":"transition","target":ref,"slug":"dissolve","duration":0.28})
                operations.append({"op":"transition","target":plate_ref,"slug":"dissolve","duration":0.28})

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

    if settings.get("add_captions_when_transcribed",True) and captions_path and captions:
        operations.append({"op":"captions","path":captions_path.name,"trackName":"Captions","timeOffset":0.0})
    operations.append({
        "op":"audio-fade","target":"voiceover",
        "fadeIn":float(settings.get("voice_fade_in",0.16)),
        "fadeOut":float(settings.get("voice_fade_out",0.7))
    })

    bg_item = {
        "type":"photo","path":assets["background"],"start":0.0,
        "duration":round(duration,3),"ref":"whiteboard_background",
        "scale":1.0,"x":0.0,"y":0.0
    }
    tracks: list[dict[str,Any]] = [
        {"type":"video","name":"Whiteboard Background","items":[bg_item]},
        {"type":"video","name":"Whiteboard Scene Frames","items":frame_items},
        {"type":"video","name":"Scene Artwork","items":scene_items},
    ]
    if plate_items:
        tracks.append({"type":"video","name":"Presenter Accent","items":plate_items})
    if presenter_items:
        tracks.append({"type":"video","name":"Presenter Explainer","items":presenter_items})
    tracks.append({"type":"audio","name":"Narration","items":audio_items})
    if sfx_items:
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
            fieldnames=["start", "end", "duration", "image", "caption_context", "scene_ref", "frame_ref", "layout", "presenter_ref"],
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
        "registered_in_capcut": registered,
        "visual_assets_dir": str(Path(spec["tracks"][0]["items"][0]["path"]).parent),
        "caption_cues": len(captions),
        "caption_file": str(captions_path) if captions_path else None,
        "matting": matting_results,
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
    if captions_path:
        log("Editable captions were added from the local Whisper transcript.")
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
