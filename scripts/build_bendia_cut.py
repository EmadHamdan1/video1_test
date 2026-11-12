from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys
from bisect import bisect_right
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects" / "nutty-putty-bendia-cut"
WIDTH, HEIGHT, FPS = 1920, 1080, 30
AUDIO_NAME = "ElevenLabs_2026-06-03T09_19_08_Mark - Natural Conversations_pvc_sp100_s39_sb75_se0_b_m2.mp3"
IMAGE_NAMES = [
    "Cartoon_horror-comedy_2D_animation_scene_202606041806.jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606041829.jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606041830.jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606041831.jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606041832.jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606041838.jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606041841.jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606051731.jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606051732.jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606051733.jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606051734 (1).jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606051734.jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606051735.jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606051736.jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606051738.jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606051739 (1).jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606051739.jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606051740.jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606051741 (1).jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606051741.jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606051742.jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606051743.jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606051744 (1).jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606051744.jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606051746.jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606051748.jpeg",
    "Cartoon_horror-comedy_2D_animation_scene_202606051750.jpeg",
    "Cartoon_horror-comedy_2D_informational_2D_202606051736.jpeg",
]
STORY = [
    "NUTTY PUTTY CAVE November 24th 2009.",
    "John Jones twenty six years old married loved caves.",
    "He entered Nutty Putty Cave in Utah with eleven people family and friends.",
    "The cave was beginner friendly well mapped he had done this before.",
    "John and his brother got bored of the easy sections and pushed deeper.",
    "They reached a passage called the Corkscrew.",
    "Five years earlier a sixteen year old boy got stuck there for fourteen hours.",
    "John was six feet tall two hundred pounds he kept going.",
    "He saw an opening ahead thought he could turn around there.",
    "What he did not know that area was completely uncharted nobody had ever been there.",
    "He started sliding downward head first feet up.",
    "The opening eighteen inches by ten.",
    "Gravity pulling him deeper.",
    "His brother climbed out to call for help.",
    "John waited upside down every breath a shallow gasp.",
    "Teams arrived equipment arrived they worked all night.",
    "After twelve hours John started hallucinating oxygen dropping.",
    "They connected him to a device he spoke to his wife told her he would be out soon.",
    "4 a.m. The pulley activated John screamed legs turned blue no pulse.",
    "Then the rope snapped hit the rescuer face concussion he left the cave.",
    "John slipped deeper.",
    "11:56 p.m. November 25th.",
    "Twenty seven hours upside down.",
    "John Jones was declared dead.",
    "The cave was sealed with concrete John is still inside.",
    "What if nobody came at all The next one nobody did for twenty four hours.",
]
HEADLINES = [
    ["NOV 24, 2009", "UTAH"],
    ["JOHN JONES", "AGE 26"],
    ["11 PEOPLE", "FAMILY TRIP"],
    ["BEGINNER ROUTE", "HE KNEW CAVES"],
    ["GOING DEEPER", "ONE BAD TURN"],
    ["THE CORKSCREW", "TIGHT PASSAGE"],
    ["14 HOURS", "A WARNING"],
    ["6 FT  •  200 LB", "HE KEPT GOING"],
    ["TURN AROUND?", "NOT THIS TIME"],
    ["UNCHARTED", "NO ONE HAD BEEN"],
    ["HEAD FIRST", "NO ROOM TO TURN"],
    ["18 × 10 IN", "THE OPENING"],
    ["GRAVITY", "PULLING HIM DOWN"],
    ["GET HELP", "BROTHER ESCAPES"],
    ["EVERY BREATH", "UPSIDE DOWN"],
    ["ALL NIGHT", "RESCUE TEAMS"],
    ["OXYGEN DROPPING", "12 HOURS LATER"],
    ["ONE LAST CALL", "HIS WIFE"],
    ["4:00 A.M.", "NO PULSE"],
    ["ROPE SNAPPED", "RESCUER INJURED"],
    ["FURTHER DOWN", "NO WAY BACK"],
    ["11:56 P.M.", "NOVEMBER 25"],
    ["27 HOURS", "UPSIDE DOWN"],
    ["DECLARED DEAD", "JOHN JONES"],
    ["SEALED IN CONCRETE", "STILL INSIDE"],
    ["THE NEXT CASE", "NO ONE CAME"],
]
SHOCK_LINES = {6, 9, 10, 11, 14, 16, 18, 19, 20, 23, 24, 25}
SFX_EVENTS = [
    (0, "whoosh", 0.16),
    (10, "bass_drop", 0.23),
    (14, "air_gasp", 0.14),
    (16, "heartbeat", 0.15),
    (18, "low_hit", 0.22),
    (19, "rope_snap", 0.26),
    (23, "low_hit", 0.22),
    (24, "concrete_thud", 0.22),
    (25, "scratch", 0.15),
]
EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac", ".aiff", ".wma"}


def log(message: str) -> None:
    print("[bendia-cut] " + message, flush=True)


def run(command: list[str], timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command, text=True, encoding="utf-8", errors="replace",
        capture_output=True, check=False, timeout=timeout,
    )


def ffprobe_duration(path: Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe is missing from PATH.")
    result = run([
        ffprobe, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ], timeout=45)
    if result.returncode != 0:
        raise RuntimeError("ffprobe could not read " + str(path) + ": " + result.stderr[-500:])
    value = float(result.stdout.strip())
    if not math.isfinite(value) or value <= 0:
        raise RuntimeError("Invalid narration duration: " + str(value))
    return value


def font(size: int, heavy: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        [Path(r"C:\Windows\Fonts\impact.ttf"), Path(r"C:\Windows\Fonts\arialbd.ttf"),
         Path(r"C:\Windows\Fonts\Arial Bold.ttf")]
        if heavy else
        [Path(r"C:\Windows\Fonts\arial.ttf"), Path(r"C:\Windows\Fonts\tahoma.ttf")]
    )
    for candidate in candidates:
        if candidate.is_file():
            try:
                return ImageFont.truetype(str(candidate), size=size)
            except OSError:
                pass
    return ImageFont.load_default()


def copy_originals() -> tuple[Path, list[Path]]:
    source_dir_raw = os.getenv("NUTTY_PUTTY_IMAGES_DIR", r"F:\Videos Chanel\videos\v2\p1").strip()
    audio_raw = os.getenv("NUTTY_PUTTY_AUDIO", "").strip()
    source_dir = Path(os.path.expandvars(source_dir_raw)).expanduser()
    audio = Path(os.path.expandvars(audio_raw)).expanduser() if audio_raw else source_dir / AUDIO_NAME
    image_paths = [source_dir / name for name in IMAGE_NAMES]
    missing = [p for p in [audio, *image_paths] if not p.is_file()]
    if missing:
        raise FileNotFoundError(
            "Original source media is missing. No old montage assets will be used:\n"
            + "\n".join("  - " + str(p) for p in missing)
        )
    source_root = PROJECT / "source_originals"
    image_dir = source_root / "images"
    audio_dir = source_root / "audio"
    image_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_copy = audio_dir / "narration_original.mp3"
    shutil.copy2(audio, audio_copy)
    copied: list[Path] = []
    for index, path in enumerate(image_paths, start=1):
        target = image_dir / ("%02d_" % index + path.name)
        shutil.copy2(path, target)
        copied.append(target.resolve())
    log("Copied original narration and " + str(len(copied)) + " original illustrations.")
    return audio_copy.resolve(), copied


def line_boundaries(duration: float) -> list[float]:
    weights = [max(1, len(re.findall(r"\b[\w']+\b", line))) for line in STORY]
    total = float(sum(weights))
    boundaries = [0.0]
    cursor = 0.0
    for weight in weights:
        cursor += duration * weight / total
        boundaries.append(cursor)
    boundaries[-1] = duration
    return boundaries


def scene_plan(duration: float) -> list[dict[str, Any]]:
    count = max(40, min(48, round(duration / 2.35)))
    boundaries = line_boundaries(duration)
    starts = [duration * i / count for i in range(count)]
    rows: list[dict[str, Any]] = []
    used_per_line: dict[int, int] = {}
    for index, start in enumerate(starts):
        end = duration * (index + 1) / count
        middle = (start + end) / 2
        line_index = max(0, min(len(STORY) - 1, bisect_right(boundaries, middle) - 1))
        occurrence = used_per_line.get(line_index, 0)
        used_per_line[line_index] = occurrence + 1
        image_index = round(line_index * (len(IMAGE_NAMES) - 1) / (len(STORY) - 1))
        variant = (index + occurrence) % 3
        shock = line_index in SHOCK_LINES
        rows.append({
            "index": index, "start": round(start, 4), "end": round(end, 4),
            "duration": round(end - start, 4), "line_index": line_index,
            "image_index": image_index, "variant": variant, "shock": shock,
            "headline": HEADLINES[line_index][occurrence % len(HEADLINES[line_index])],
        })
    return rows


def rounded_shadow(base: Image.Image, box: tuple[int, int, int, int], radius: int = 24) -> Image.Image:
    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow)
    x0, y0, x1, y1 = box
    draw.rounded_rectangle((x0 + 15, y0 + 18, x1 + 15, y1 + 18), radius=radius, fill=(0, 0, 0, 95))
    return Image.alpha_composite(base.convert("RGBA"), shadow.filter(ImageFilter.GaussianBlur(20)))


def place_framed_image(canvas: Image.Image, path: Path, box: tuple[int, int, int, int],
                       dark: bool, zoom_variant: int) -> Image.Image:
    x0, y0, x1, y1 = box
    canvas = rounded_shadow(canvas, box, 18 if dark else 28)
    draw = ImageDraw.Draw(canvas)
    panel = (16, 18, 23, 255) if dark else (255, 255, 255, 255)
    outline = (255, 255, 255, 255) if dark else (18, 18, 20, 255)
    draw.rounded_rectangle(box, radius=18 if dark else 28, fill=panel, outline=outline, width=5)
    with Image.open(path) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")
        if zoom_variant == 1 and image.width > 2 and image.height > 2:
            inset_x, inset_y = round(image.width * 0.075), round(image.height * 0.075)
            image = image.crop((inset_x, inset_y, image.width - inset_x, image.height - inset_y))
        elif zoom_variant == 2 and image.width > 2 and image.height > 2:
            # A second, deliberately moderate crop creates a detail-cut variation.
            inset_x, inset_y = round(image.width * 0.13), round(image.height * 0.10)
            image = image.crop((inset_x, inset_y, image.width - inset_x, image.height - inset_y))
        inner = ImageOps.contain(image, (x1 - x0 - 38, y1 - y0 - 38), method=Image.Resampling.LANCZOS)
    px = x0 + (x1 - x0 - inner.width) // 2
    py = y0 + (y1 - y0 - inner.height) // 2
    canvas.alpha_composite(inner.convert("RGBA"), (px, py))
    draw = ImageDraw.Draw(canvas)
    accent = (230, 37, 45, 255) if dark else (220, 33, 40, 255)
    draw.rounded_rectangle((x0 + 22, y0 + 18, x0 + 178, y0 + 27), radius=4, fill=accent)
    return canvas


def draw_arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int],
               color: tuple[int, int, int, int], width: int = 9) -> None:
    draw.line((start, end), fill=color, width=width)
    import math as _math
    angle = _math.atan2(end[1] - start[1], end[0] - start[0])
    size = 26
    left = (end[0] - size * _math.cos(angle - 0.55), end[1] - size * _math.sin(angle - 0.55))
    right = (end[0] - size * _math.cos(angle + 0.55), end[1] - size * _math.sin(angle + 0.55))
    draw.polygon([end, left, right], fill=color)


def create_scene_plate(row: dict[str, Any], image_path: Path, output: Path) -> None:
    index = int(row["index"])
    shock = bool(row["shock"])
    layout = ("full", "left", "right", "split")[index % 4]
    if shock and index % 2 == 0:
        layout = "full"
    dark = layout == "full" or shock
    bg = (14, 16, 20, 255) if dark else (248, 248, 245, 255)
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), bg)
    draw = ImageDraw.Draw(canvas)
    red = (225, 35, 43, 255)
    yellow = (255, 205, 55, 255)
    ink = (20, 21, 23, 255)
    white = (250, 250, 248, 255)

    if layout == "full":
        box = (72, 65, 1848, 1015)
        canvas = place_framed_image(canvas, image_path, box, True, int(row["variant"]))
        draw = ImageDraw.Draw(canvas)
        # Strong case-file crop marks frame the image without covering the artwork.
        for x, y, sx, sy in [(80, 73, 1, 1), (1840, 73, -1, 1), (80, 1005, 1, -1), (1840, 1005, -1, -1)]:
            draw.line((x, y, x + sx * 76, y), fill=yellow, width=6)
            draw.line((x, y, x, y + sy * 48), fill=yellow, width=6)
        draw.rounded_rectangle((112, 108, 330, 158), radius=12, fill=red)
        draw.text((134, 121), "CASE FILE", font=font(24, True), fill=white)
        draw.rounded_rectangle((1590, 914, 1798, 968), radius=12, fill=(10, 11, 14, 225), outline=red, width=3)
        draw.text((1621, 928), "UTAH  /  2009", font=font(22, True), fill=white)
    else:
        # An editorial image stage with a clear typography lane: never a static title card.
        if layout == "left":
            box = (66, 130, 1168, 948)
            text_lane = (1230, 170, 1840, 900)
        elif layout == "right":
            box = (752, 130, 1854, 948)
            text_lane = (82, 170, 690, 900)
        else:
            box = (66, 130, 1185, 948)
            text_lane = (1240, 160, 1848, 930)
        canvas = place_framed_image(canvas, image_path, box, False, int(row["variant"]))
        draw = ImageDraw.Draw(canvas)
        lx0, ly0, lx1, ly1 = text_lane
        draw.rounded_rectangle((lx0, ly0, lx1, ly1), radius=20, fill=(255, 255, 255, 255))
        draw.rectangle((lx0, ly0, lx0 + 18, ly1), fill=red)
        draw.line((lx0 + 42, ly1 - 112, lx1 - 30, ly1 - 112), fill=yellow, width=12)
        draw.line((lx0 + 42, ly0 + 80, lx0 + 210, ly0 + 80), fill=ink, width=5)
        draw.text((lx0 + 42, ly0 + 34), "FIELD NOTES", font=font(24, True), fill=red)
        # A restrained red pointer connects the typography lane to the evidence image.
        if layout == "left":
            draw_arrow(draw, (lx0 + 10, ly0 + 310), (box[2] - 40, box[1] + 250), red, 8)
        elif layout == "right":
            draw_arrow(draw, (lx1 - 20, ly0 + 310), (box[0] + 55, box[1] + 260), red, 8)
        else:
            # A second evidence inset is a fresh crop of the source illustration, not a legacy montage asset.
            inset = (1320, 520, 1790, 835)
            canvas = place_framed_image(canvas, image_path, inset, False, 2)
            draw = ImageDraw.Draw(canvas)
            draw_arrow(draw, (1240, 440), (1160, 490), red, 8)

    # A small visual index is part of the scene, not a separate opening/title card.
    draw = ImageDraw.Draw(canvas)
    num = "%02d" % (index + 1)
    number_color = yellow if dark else red
    draw.text((84, 1005 if dark else 42), num, font=font(28, True), fill=number_color)
    # Quick marker accents vary by beat; they do not cover the subject or text.
    if shock:
        draw.line((WIDTH - 300, 70, WIDTH - 120, 70), fill=red, width=12)
        draw.line((WIDTH - 260, 91, WIDTH - 110, 91), fill=yellow, width=5)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output, "PNG", optimize=True)


def sfx_pack_dir() -> Path | None:
    raw = os.getenv("SAOUD_SFX_PACK", "").strip()
    candidates = [Path(raw)] if raw else []
    candidates.extend([
        ROOT / "Saoud_SFX_Pack",
        Path(r"F:\video1_test\Saoud_SFX_Pack"),
        Path.home() / "Downloads" / "Saoud_SFX_Pack",
        Path.home() / "Desktop" / "Saoud_SFX_Pack",
    ])
    return next((p.expanduser() for p in candidates if p and p.is_dir()), None)


def find_sfx(pack: Path | None, category: str) -> Path | None:
    if not pack:
        return None
    keywords = {
        "whoosh": ("whoosh", "swoosh", "sweep", "swish"),
        "bass_drop": ("bass", "drop", "impact", "cinematic hit"),
        "air_gasp": ("gasp", "breath", "inhale", "air"),
        "heartbeat": ("heartbeat", "heart beat", "pulse", "heart"),
        "low_hit": ("low hit", "low_hit", "impact", "boom", "hit"),
        "rope_snap": ("rope", "snap", "break", "crack"),
        "concrete_thud": ("concrete", "thud", "stone", "heavy hit"),
        "scratch": ("scratch", "rewind", "vinyl"),
    }
    files = [p for p in pack.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONS]
    terms = keywords.get(category, (category,))
    for term in terms:
        match = next((p for p in files if term in p.stem.lower().replace("-", " ").replace("_", " ")), None)
        if match:
            return match
    return None


def prepare_audio(audio_source: Path, duration: float) -> tuple[Path, Path | None]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is missing from PATH.")
    audio_dir = PROJECT / "assets" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    voice = audio_dir / "voice_master_new.wav"
    voice_filter = (
        "highpass=f=70,"
        "acompressor=threshold=0.12:ratio=2.4:attack=12:release=110:makeup=1.8,"
        "loudnorm=I=-14:TP=-1:LRA=7,"
        "afade=t=in:st=0:d=0.05,"
        "afade=t=out:st=%.3f:d=0.65" % max(0.0, duration - 0.65)
    )
    result = run([
        ffmpeg, "-y", "-i", str(audio_source), "-af", voice_filter,
        "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", str(voice),
    ], timeout=None)
    if result.returncode != 0 or not voice.is_file():
        raise RuntimeError("Could not prepare the new voice master: " + (result.stderr or "")[-1000:])

    # A newly generated, very quiet underground air-bed. This is not imported from the prior edit.
    ambience = audio_dir / "original_cave_air_bed.wav"
    ambient_filter = (
        "[0:a]highpass=f=38,lowpass=f=420,volume=0.52[n];"
        "[1:a]lowpass=f=68,volume=0.11[t];"
        "[n][t]amix=inputs=2:duration=longest,volume=0.13,"
        "afade=t=in:st=0:d=1.8,afade=t=out:st=%.3f:d=4[out]" % max(0.0, duration - 4.0)
    )
    ambient = run([
        ffmpeg, "-y",
        "-f", "lavfi", "-i",
        "anoisesrc=color=pink:amplitude=0.012:sample_rate=48000:duration=%.3f" % duration,
        "-f", "lavfi", "-i",
        "sine=frequency=48:sample_rate=48000:duration=%.3f" % duration,
        "-filter_complex", ambient_filter, "-map", "[out]",
        "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(ambience),
    ], timeout=None)
    return voice.resolve(), ambience.resolve() if ambient.returncode == 0 and ambience.is_file() else None


def make_spec(audio: Path, voice: Path, ambience: Path | None, images: list[Path],
              duration: float, rows: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    visuals_dir = PROJECT / "assets" / "bendia_scenes"
    visuals_dir.mkdir(parents=True, exist_ok=True)
    visual_items: list[dict[str, Any]] = []
    text_items: list[dict[str, Any]] = []
    operations: list[dict[str, Any]] = []
    scene_manifest: list[dict[str, Any]] = []

    for row in rows:
        idx = int(row["index"])
        image_path = images[int(row["image_index"])]
        plate = visuals_dir / ("scene_%03d.png" % (idx + 1))
        create_scene_plate(row, image_path, plate)
        ref = "bendia_scene_%03d" % (idx + 1)
        start, length = float(row["start"]), float(row["duration"])
        direction = -1.0 if idx % 2 else 1.0
        visual_items.append({
            "type": "photo", "path": str(plate.resolve()), "start": round(start, 3),
            "duration": round(length, 3), "ref": ref, "scale": 1.0, "x": 0.0, "y": 0.0,
        })
        # Fast controlled pop/slide followed by a restrained living hold.
        operations.extend([
            {"op": "keyframe", "target": ref, "property": "uniform_scale", "time": 0.0, "value": 0.93 if idx % 3 else 1.08},
            {"op": "keyframe", "target": ref, "property": "uniform_scale", "time": 0.16, "value": 1.035, "easing": "ease-out"},
            {"op": "keyframe", "target": ref, "property": "uniform_scale", "time": 0.28, "value": 1.0, "easing": "ease-in-out"},
            {"op": "keyframe", "target": ref, "property": "uniform_scale", "time": round(length, 3), "value": 1.045, "easing": "ease-in-out"},
            {"op": "keyframe", "target": ref, "property": "position_x", "time": 0.0, "value": direction * 0.055},
            {"op": "keyframe", "target": ref, "property": "position_x", "time": 0.22, "value": 0.0, "easing": "ease-out"},
            {"op": "keyframe", "target": ref, "property": "position_x", "time": round(length, 3), "value": -direction * 0.018, "easing": "ease-in-out"},
        ])
        if bool(row["shock"]):
            operations.extend([
                {"op": "keyframe", "target": ref, "property": "rotation", "time": 0.0, "value": -1.2},
                {"op": "keyframe", "target": ref, "property": "rotation", "time": 0.12, "value": 0.5, "easing": "ease-out"},
                {"op": "keyframe", "target": ref, "property": "rotation", "time": 0.24, "value": 0.0, "easing": "ease-out"},
            ])
        if idx > 0 and idx % 7 == 6:
            operations.append({"op": "transition", "target": ref, "slug": "mix", "duration": 0.12})

        headline = str(row["headline"])
        text_ref = "impact_word_%03d" % (idx + 1)
        dark = (idx % 4 == 0) or bool(row["shock"])
        layout = ("full", "left", "right", "split")[idx % 4]
        if bool(row["shock"]) and idx % 2 == 0:
            layout = "full"
        if layout == "left":
            text_x, text_y = 0.66, -0.10
        elif layout == "right":
            text_x, text_y = -0.66, -0.10
        elif layout == "split":
            text_x, text_y = 0.68, -0.34
        else:
            text_x, text_y = 0.0, 0.76
        color = "#FFD23F" if dark else ("#E2272E" if idx % 3 == 0 else "#17181B")
        font_size = 72 if len(headline) <= 15 else 60
        text_items.append({
            "text": headline, "start": round(start + min(0.08, length * 0.04), 3),
            "duration": round(max(0.55, length - 0.12), 3),
            "fontSize": font_size, "color": color, "x": text_x, "y": text_y + 0.06,
            "ref": text_ref,
        })
        operations.extend([
            {"op": "text-style", "target": text_ref, "style": {
                "shadow": True, "shadowAlpha": 0.48, "shadowColor": "#000000",
                "shadowDistance": 3, "shadowSmoothing": 2,
                "borderWidth": 2.0, "borderColor": "#101010", "borderAlpha": 0.72,
            }},
            {"op": "keyframe", "target": text_ref, "property": "position_y", "time": 0.0, "value": text_y + 0.10},
            {"op": "keyframe", "target": text_ref, "property": "position_y", "time": 0.18, "value": text_y, "easing": "ease-out"},
            {"op": "keyframe", "target": text_ref, "property": "uniform_scale", "time": 0.0, "value": 0.84},
            {"op": "keyframe", "target": text_ref, "property": "uniform_scale", "time": 0.18, "value": 1.04, "easing": "ease-out"},
            {"op": "keyframe", "target": text_ref, "property": "uniform_scale", "time": 0.28, "value": 1.0, "easing": "ease-in-out"},
        ])
        scene_manifest.append({
            "shot": idx + 1, "start": start, "end": row["end"], "source_image": image_path.name,
            "story_line": int(row["line_index"]) + 1, "headline": headline,
            "layout": layout, "shock_beat": bool(row["shock"]),
        })

    tracks: list[dict[str, Any]] = [
        {"type": "video", "name": "BENDIA CUT — Story Visuals", "items": visual_items},
        {"type": "text", "name": "Impact Words — no subtitles", "items": text_items},
        {"type": "audio", "name": "Narration — original voice", "items": [{
            "path": str(voice), "start": 0.0, "duration": round(duration, 3),
            "volume": 0.96, "ref": "original_voice",
        }]},
    ]

    if ambience:
        tracks.append({"type": "audio", "name": "Cave Atmosphere — original generated bed", "items": [{
            "path": str(ambience), "start": 0.0, "duration": round(duration, 3),
            "volume": 0.12, "ref": "cave_air_bed",
        }]})

    pack = sfx_pack_dir()
    sound_items: list[dict[str, Any]] = []
    line_starts = line_boundaries(duration)
    if pack:
        log("Saoud SFX pack: " + str(pack))
        for event_line, category, volume in SFX_EVENTS:
            source = find_sfx(pack, category)
            if not source:
                log("SFX not found in pack for " + category + "; skipped.")
                continue
            target_time = max(0.12, min(duration - 0.25, line_starts[event_line] + 0.18))
            sound_duration = min(2.2, ffprobe_duration(source))
            sound_items.append({
                "path": str(source.resolve()), "start": round(target_time, 3),
                "duration": round(sound_duration, 3), "volume": volume,
                "ref": "saoud_%02d" % (len(sound_items) + 1),
            })
        if sound_items:
            tracks.append({"type": "audio", "name": "Saoud SFX — story moments", "items": sound_items})
    else:
        log("Saoud SFX pack was not found; building without external sound effects.")

    spec = {
        "name": "Nutty Putty Cave — Bendia Cut",
        "width": WIDTH, "height": HEIGHT, "fps": FPS, "ratio": "16:9",
        "tracks": tracks, "operations": operations,
    }
    manifest = {
        "project": "Nutty Putty Cave — Bendia Cut",
        "duration_seconds": round(duration, 3),
        "shot_count": len(rows),
        "source_image_count": len(images),
        "voice_starts_at_zero": True,
        "intro_card": False,
        "subtitle_track": False,
        "sfx_used": len(sound_items),
        "scenes": scene_manifest,
    }
    return spec, manifest


def parse_json_output(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        for offset, char in enumerate(text):
            if char != "{":
                continue
            try:
                value, _ = decoder.raw_decode(text[offset:])
                if isinstance(value, dict) and ("draft_path" in value or "refs" in value):
                    return value
            except json.JSONDecodeError:
                continue
    return {}


def build_capcut(spec: Path, duration: float) -> tuple[Path, dict[str, Any]]:
    capcut = shutil.which("capcut")
    if not capcut:
        raise RuntimeError("capcut CLI is missing. Install capcut-cli and reopen PowerShell.")
    raw_shell = os.getenv("NUTTY_PUTTY_CAPCUT_SHELL", "").strip()
    if not raw_shell:
        raise RuntimeError(
            "Create a fresh empty project in CapCut, close CapCut, then set "
            "NUTTY_PUTTY_CAPCUT_SHELL to that project's folder."
        )
    shell = Path(os.path.expandvars(raw_shell)).expanduser().resolve()
    if not shell.is_dir() or not any((shell / name).is_file() for name in ("draft_content.json", "draft_info.json")):
        raise RuntimeError("NUTTY_PUTTY_CAPCUT_SHELL is not a CapCut project folder.")
    command = [capcut, "compile", str(spec), "--into", str(shell)]
    if (shell / "Timelines").is_dir():
        command.append("--active-timeline")
    env = os.environ.copy()
    env["CAPCUT_DRAFT_DIR"] = str(shell.parent)
    check = run([*command, "--check"], timeout=None)
    if check.stdout.strip():
        print(check.stdout.strip())
    if check.returncode != 0:
        raise RuntimeError(
            "The selected CapCut shell is not blank/compatible. Create a new empty project and close CapCut.\n"
            + (check.stderr or check.stdout)[-1600:]
        )
    result = run(command, timeout=None)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.returncode != 0:
        raise RuntimeError("CapCut could not compile the fresh Bendia cut:\n" + (result.stderr or "")[-2200:])
    payload = parse_json_output(result.stdout)
    draft = Path(str(payload.get("draft_path", shell))).resolve()
    register = run([capcut, "register", str(draft), "--materials", "--apply"], timeout=None)
    if register.stdout.strip():
        log(register.stdout.strip()[-1000:])
    if register.returncode != 0:
        log("Registration warning: " + (register.stderr or register.stdout)[-800:])

    checks: list[dict[str, Any]] = []
    for name, args in [
        ("version", [capcut, "version", str(draft)]),
        ("lint", [capcut, "lint", str(draft)]),
        ("diagnose", [capcut, "diagnose", str(draft), "-H"]),
    ]:
        checked = run(args, timeout=None)
        detail = (checked.stdout + "\n" + checked.stderr).strip()
        checks.append({"name": name, "exit_code": checked.returncode, "output": detail[-12000:]})
        log("CapCut " + name + " check: exit " + str(checked.returncode))
    return draft, {"checks": checks, "registered": register.returncode == 0}


def main() -> int:
    if PROJECT.exists():
        shutil.rmtree(PROJECT)
    PROJECT.mkdir(parents=True, exist_ok=True)
    audio_source, images = copy_originals()
    duration = ffprobe_duration(audio_source)
    voice, ambience = prepare_audio(audio_source, duration)
    rows = scene_plan(duration)
    log("Designing " + str(len(rows)) + " new shots at approximately " +
        str(round(duration / len(rows), 2)) + " seconds each.")
    spec_data, manifest = make_spec(audio_source, voice, ambience, images, duration, rows)
    build_dir = PROJECT / "build"
    build_dir.mkdir(parents=True, exist_ok=True)
    spec_path = build_dir / "bendia_cut_spec.json"
    spec_path.write_text(json.dumps(spec_data, ensure_ascii=False, indent=2), encoding="utf-8")
    (build_dir / "BENDIA_EDIT_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (build_dir / "BENDIA_EDIT_NOTES.md").write_text(
        "# Nutty Putty Cave — New Bendia-inspired edit\n\n"
        "- Rebuilt from original narration and original story illustrations only.\n"
        "- No prior montage timeline, generated images, presenter plates, old music, or old callout assets are imported.\n"
        "- No intro/title card: the first scene and narration both begin at 00:00.\n"
        "- 16:9, 1920x1080, 30 fps.\n"
        "- Rapid image rhythm, alternating dark evidence punches and clean white editorial frames, red/yellow marker graphics, oversized impact words, restrained motion, story-specific Saoud sound effects, and a newly generated quiet cave air bed.\n"
        "- No full-sentence subtitles.\n\n"
        "The CapCut draft is editable. Preview the full timeline and verify the mix before exporting.\n",
        encoding="utf-8",
    )
    draft, compatibility = build_capcut(spec_path, duration)
    compatibility_path = build_dir / "CAPCUT_COMPATIBILITY_REPORT.txt"
    compatibility_path.write_text(
        "\n\n".join(
            "=== " + item["name"] + " (exit " + str(item["exit_code"]) + ") ===\n" + item["output"]
            for item in compatibility["checks"]
        ) + "\n",
        encoding="utf-8",
    )
    manifest["draft_path"] = str(draft)
    manifest["compatibility_report"] = str(compatibility_path)
    manifest["registered"] = compatibility["registered"]
    (build_dir / "BENDIA_EDIT_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log("BUILD SUCCESSFUL")
    log("New CapCut draft: " + str(draft))
    log("New independent project assets: " + str(PROJECT))
    log("Shots: " + str(len(rows)) + " | tracks: " + str(len(spec_data["tracks"])) +
        " | Saoud effects: " + str(manifest["sfx_used"]))
    log("No opening card. No files from the prior montage were imported.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        log("ERROR: " + str(exc))
        raise SystemExit(1)
