from __future__ import annotations

import array
import csv
import difflib
import hashlib
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import wave
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects" / "nutty-putty-cave"
AUDIO_SOURCE = Path(r"D:\Videos Chanel\v2\p1\ElevenLabs_2026-06-03T09_19_08_Mark - Natural Conversations_pvc_sp100_s39_sb75_se0_b_m2.mp3")
IMAGE_SOURCES = [
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606041806.jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606041829.jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606041830.jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606041831.jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606041832.jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606041838.jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606041841.jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606051731.jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606051732.jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606051733.jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606051734 (1).jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606051734.jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606051735.jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606051736.jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606051738.jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606051739 (1).jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606051739.jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606051740.jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606051741 (1).jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606051741.jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606051742.jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606051743.jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606051744 (1).jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606051744.jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606051746.jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606051748.jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_animation_scene_202606051750.jpeg"),
    Path(r"D:\Videos Chanel\v2\p1\Cartoon_horror-comedy_2D_informational_2D_202606051736.jpeg"),
]
PRESENTER_SOURCES = [
    Path(r"C:\Users\EmQr\Desktop\v1\3._Holding_a_stick_pointer_like_202605101854.jpeg"),
    Path(r"C:\Users\EmQr\Desktop\v1\3._Holding_a_stick_pointer_like_202605101902.jpeg"),
    Path("C:/Users/EmQr/Desktop/v1/7._Shrugging_“I_don’t_know”_202605101855.jpeg"),
    Path(r"C:\Users\EmQr\Desktop\v1\8._Pointing_at_something_while_202605101855.jpeg"),
]
STORY_EN = [
    "NUTTY PUTTY CAVE — November 24th, 2009.",
    "John Jones, twenty-six years old, married, loved caves.",
    "He entered Nutty Putty Cave in Utah with eleven people, family and friends.",
    "The cave was beginner-friendly, well-mapped, he'd done this before.",
    "John and his brother got bored of the easy sections and pushed deeper.",
    "They reached a passage called the Corkscrew.",
    "Five years earlier, a sixteen-year-old boy got stuck there for fourteen hours.",
    "John was six feet tall, two hundred pounds, he kept going.",
    "He saw an opening ahead, thought he could turn around there.",
    "What he didn't know — that area was completely uncharted, nobody had ever been there.",
    "He started sliding downward, head first, feet up.",
    "The opening: eighteen inches by ten.",
    "Gravity pulling him deeper.",
    "His brother climbed out to call for help.",
    "John waited, upside down, every breath a shallow gasp.",
    "Teams arrived, equipment arrived, they worked all night.",
    "After twelve hours, John started hallucinating, oxygen dropping.",
    "They connected him to a device, he spoke to his wife, told her he would be out soon.",
    "4 a.m. The pulley activated, John screamed, legs turned blue, no pulse.",
    "Then the rope snapped, hit the rescuer's face, concussion, he left the cave.",
    "John slipped deeper.",
    "11:56 p.m. November 25th.",
    "Twenty-seven hours upside down.",
    "John Jones was declared dead.",
    "The cave was sealed with concrete. John is still inside.",
    "What if nobody came at all? The next one — nobody did. For twenty-four hours.",
]
STORY_AR = [
    "كهف نوتي بوتي — 24 نوفمبر 2009.",
    "جون جونز، يبلغ من العمر ستة وعشرين عاماً، متزوج، وكان يحب الكهوف.",
    "دخل كهف نوتي بوتي في يوتا مع أحد عشر شخصاً من العائلة والأصدقاء.",
    "كان الكهف مناسباً للمبتدئين ومخططاً جيداً، وقد خاض التجربة من قبل.",
    "شعر جون وأخوه بالملل من الأقسام السهلة وتوغلا إلى الداخل.",
    "وصلا إلى ممر يُدعى المفتاح اللولبي.",
    "قبل خمس سنوات، علق فتى يبلغ من العمر ستة عشر عاماً هناك لمدة أربع عشرة ساعة.",
    "كان طول جون ستة أقدام ووزنه مئتي رطل، ومع ذلك واصل التقدم.",
    "رأى فتحة أمامه وظن أنه يستطيع الاستدارة هناك.",
    "ما لم يكن يعلمه أن المنطقة غير مستكشفة تماماً ولم يذهب إليها أحد من قبل.",
    "بدأ ينزلق إلى الأسفل، رأسه أولاً وقدماه إلى الأعلى.",
    "كان قياس الفتحة ثماني عشرة بوصة في عشر بوصات.",
    "كانت الجاذبية تسحبه إلى عمق أكبر.",
    "خرج أخوه من الكهف لطلب المساعدة.",
    "انتظر جون مقلوباً، وكل نفس كان شهقة ضعيفة.",
    "وصلت فرق الإنقاذ والمعدات، وعملوا طوال الليل.",
    "بعد اثنتي عشرة ساعة، بدأ جون بالهلوسة وانخفض الأكسجين.",
    "وصلوه بجهاز، وتحدث إلى زوجته وأخبرها أنه سيخرج قريباً.",
    "الساعة الرابعة صباحاً. تحركت البكرة، صرخ جون، ازرقت ساقاه ولم يعد هناك نبض.",
    "ثم انقطع الحبل وضرب وجه المنقذ وأصابه بارتجاج، فغادر الكهف.",
    "انزلق جون إلى عمق أكبر.",
    "الساعة 11:56 مساءً، 25 نوفمبر.",
    "سبع وعشرون ساعة مقلوباً.",
    "أُعلن عن وفاة جون جونز.",
    "أُغلق الكهف بالخرسانة. لا يزال جون في الداخل.",
    "ماذا لو لم يأتِ أحد مطلقاً؟ الحالة التالية — لم يأتِ أحد لمدة أربع وعشرين ساعة.",
]
BEAT_META = [
    ("tense", 1, "CAVE"), ("calm", 0, "JOHN"), ("calm", 0, "ELEVEN PEOPLE"),
    ("calm", 0, "BEGINNER-FRIENDLY"), ("tense", 1, "DEEPER"), ("scary", 2, "CORKSCREW"),
    ("scary", 2, "FOURTEEN HOURS"), ("tense", 1, "TWO HUNDRED"), ("tense", 1, "TURN AROUND"),
    ("scary", 2, "UNCHARTED"), ("shocking", 3, "HEAD FIRST"), ("scary", 2, "EIGHTEEN INCHES"),
    ("scary", 2, "GRAVITY"), ("tense", 1, "HELP"), ("scary", 2, "EVERY BREATH"),
    ("tense", 1, "ALL NIGHT"), ("shocking", 3, "OXYGEN"), ("sad", 2, "HIS WIFE"),
    ("shocking", 3, "NO PULSE"), ("shocking", 3, "ROPE SNAPPED"), ("scary", 2, "DEEPER"),
    ("tense", 2, "11:56 P.M."), ("sad", 3, "27 HOURS"), ("sad", 3, "DECLARED DEAD"),
    ("solemn", 3, "CONCRETE"), ("scary", 2, "WHAT IF"),
]
STOCK_QUERIES = [
    "Utah limestone cave entrance",
    "spelunker exploring dark cave",
    "group of cave explorers",
    "cave map and exploration route",
    "narrow limestone cave passage",
    "tight corkscrew cave passage",
    "cave rescue headlamp equipment",
    "spelunker crawling narrow cave",
    "narrow cave opening limestone",
    "uncharted underground cave passage",
    "caver trapped in narrow rocks",
    "narrow rock crevice cave",
    "rock tunnel cave formation",
    "cave rescue emergency phone",
    "confined cave passage flashlight",
    "cave rescue team equipment",
    "portable oxygen monitor medical",
    "worried family emergency phone",
    "cave rescue pulley rope system",
    "damaged climbing rope carabiner",
    "spelunker descending cave passage",
    "Utah cave rescue operation",
    "cave rescue team ropes pulley",
    "cave entrance memorial concrete",
    "sealed cave entrance rock",
    "empty underground cave passage",
]

CHAPTERS = [
    (0, "THE CAVE"), (5, "THE CORKSCREW"), (9, "NO TURNING BACK"),
    (13, "THE RESCUE"), (18, "THE PULLEY"), (21, "27 HOURS"),
    (24, "SEALED FOREVER"), (25, "THE NEXT CASE"),
]
SFX_EVENTS = [
    ("NUTTY PUTTY", "whoosh", 0.30), ("ELEVEN PEOPLE", "soft_click", 0.24),
    ("CORKSCREW", "scratch", 0.30), ("FOURTEEN HOURS", "low_hit", 0.33),
    ("UNCHARTED", "pop", 0.27), ("HEAD FIRST", "bass_drop", 0.40),
    ("UPSIDE DOWN", "heartbeat", 0.28), ("TEAMS ARRIVED", "whoosh", 0.25),
    ("OXYGEN DROPPING", "air_gasp", 0.30), ("HIS WIFE", "soft_click", 0.18),
    ("NO PULSE", "low_hit", 0.42), ("ROPE SNAPPED", "rope_snap", 0.43),
    ("JOHN SLIPPED", "bass_drop", 0.38), ("TWENTY SEVEN HOURS", "heartbeat", 0.28),
    ("DECLARED DEAD", "low_hit", 0.40), ("SEALED WITH CONCRETE", "concrete_thud", 0.39),
    ("WHAT IF", "scratch", 0.27), ("TWENTY FOUR HOURS", "low_hit", 0.30),
]
ICON_CHAPTERS = [
    ("map-pin", "#FFD447"), ("compass", "#FFFFFF"), ("triangle-alert", "#FF3030"),
    ("phone", "#FFD447"), ("heart-pulse", "#FF3030"), ("clock", "#FF3030"),
    ("construction", "#FF3030"), ("arrow-down", "#FFD447"),
]
WORD_RE = re.compile(r"\d+(?::\d+)?(?:st|nd|rd|th)?|[A-Za-z]+(?:'[A-Za-z]+)?", re.I)
SAMPLE_RATE = 22050


def log(message: str) -> None:
    print("[nutty-putty] " + message, flush=True)


def norm_word(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.lower().replace("’", "'"))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", value)


def ensure_dirs() -> None:
    for relative in (
        "assets/images", "assets/presenter", "assets/audio", "assets/audio/sfx",
        "assets/icons", "assets/generated", "assets/generated/icons",
        "assets/generated/fullframe_images", "build",
    ):
        (PROJECT / relative).mkdir(parents=True, exist_ok=True)


def run_process(command: list[str], cwd: Path | None = None, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=str(cwd) if cwd else None, text=True, encoding="utf-8", errors="replace",
                          capture_output=True, check=False, timeout=timeout)


def ffprobe_duration(path: Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("FFprobe was not found. The check_tools.ps1 result should show ffprobe READY.")
    result = run_process([
        ffprobe, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ], timeout=60)
    if result.returncode != 0:
        raise RuntimeError("FFprobe could not read " + str(path) + ": " + result.stderr[-500:])
    try:
        duration = float(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError("FFprobe returned an invalid duration for " + str(path)) from exc
    if not math.isfinite(duration) or duration <= 0:
        raise RuntimeError("Media duration is empty or invalid: " + str(path))
    return duration


def copy_sources(simple: bool = False) -> tuple[list[Path], list[Path], Path, Path, dict[str, Any]]:
    missing_required = [path for path in [AUDIO_SOURCE, *IMAGE_SOURCES] if not path.is_file()]
    if missing_required:
        details = "\n".join("  - " + str(path) for path in missing_required)
        raise FileNotFoundError("Required source files were not found. Check the exact Windows paths:\n" + details)
    available_presenters = [path for path in PRESENTER_SOURCES if path.is_file()]
    missing_presenters = [path for path in PRESENTER_SOURCES if not path.is_file()]
    if missing_presenters:
        log("Optional presenter poses missing; using the available poses only: " +
            ", ".join(path.name for path in missing_presenters))
    source_map: dict[str, Any] = {"images": [], "presenter": [], "audio": []}
    images: list[Path] = []
    for index, source in enumerate(IMAGE_SOURCES, start=1):
        target = PROJECT / "assets" / "images" / ("%03d_story%s" % (index, source.suffix.lower()))
        shutil.copy2(source, target)
        images.append(target.resolve())
        source_map["images"].append({"original": str(source), "local": str(target.resolve()), "sequence": index})
    presenters: list[Path] = []
    for index, source in enumerate(available_presenters, start=1):
        target = PROJECT / "assets" / "presenter" / ("pose_%02d%s" % (index, source.suffix.lower()))
        shutil.copy2(source, target)
        presenters.append(target.resolve())
        source_map["presenter"].append({"original": str(source), "local": str(target.resolve()), "sequence": index})
    source_copy = PROJECT / "assets" / "audio" / "narration_source.mp3"
    shutil.copy2(AUDIO_SOURCE, source_copy)
    source_map["audio"].append({"original": str(AUDIO_SOURCE), "local": str(source_copy.resolve())})
    if simple:
        log("Basic CapCut mode: keeping the supplied narration MP3 unchanged.")
        return images, presenters, source_copy.resolve(), source_copy.resolve(), source_map
    master = PROJECT / "assets" / "audio" / "narration_master.wav"
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg was not found. Run check_tools.ps1 and fix the FFmpeg row first.")
    filters = "highpass=f=70,acompressor=threshold=0.125:ratio=2.5:attack=15:release=120:makeup=2,loudnorm=I=-14:TP=-1:LRA=7"
    log("Preparing a clean voice master (high-pass, gentle compression, -16 LUFS target, -3 dBTP ceiling).")
    result = run_process([
        ffmpeg, "-y", "-i", str(source_copy), "-af", filters, "-ar", "48000", "-ac", "2",
        "-c:a", "pcm_s24le", str(master),
    ], timeout=None)
    if result.returncode != 0 or not master.is_file():
        raise RuntimeError("FFmpeg could not create narration_master.wav:\n" + (result.stderr or result.stdout)[-1800:])
    return images, presenters, source_copy.resolve(), master.resolve(), source_map


def fit_image_to_frame(source: Path, target: Path) -> None:
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        # Extend with a sampled neutral edge colour instead of aggressively cropping faces/props.
        corners = [image.getpixel(point) for point in (
            (0, 0), (image.width - 1, 0), (0, image.height - 1), (image.width - 1, image.height - 1)
        )]
        background = tuple(round(sum(color[channel] for color in corners) / len(corners)) for channel in range(3))
        # Contain the complete drawing on a 16:9 canvas. ImageOps.pad crops to fill and
        # can cut off illustrated faces or props, so we deliberately avoid that here.
        contained = ImageOps.contain(image, (1920, 1080), method=Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (1920, 1080), background)
        offset = ((1920 - contained.width) // 2, (1080 - contained.height) // 2)
        canvas.paste(contained, offset)
        target.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(target, "JPEG", quality=94, optimize=True, progressive=True)


def make_contact_sheet(images: list[Path], output: Path) -> None:
    columns, cell_w, cell_h = 4, 360, 246
    rows = max(1, math.ceil(len(images) / columns))
    sheet = Image.new("RGB", (columns * cell_w, rows * cell_h), (248, 246, 240))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
    for index, path in enumerate(images):
        x, y = (index % columns) * cell_w, (index // columns) * cell_h
        try:
            with Image.open(path) as opened:
                image = ImageOps.contain(ImageOps.exif_transpose(opened).convert("RGB"), (cell_w - 16, cell_h - 44))
            sheet.paste(image, (x + (cell_w - image.width) // 2, y + 3))
            draw.text((x + 8, y + cell_h - 32), "%02d | %s" % (index + 1, path.name[:39]), fill=(28, 32, 38), font=font)
        except Exception as exc:
            draw.text((x + 8, y + 8), "UNREADABLE: " + path.name[:28], fill=(185, 20, 20), font=font)
            draw.text((x + 8, y + 28), str(exc)[:45], fill=(185, 20, 20), font=font)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, "JPEG", quality=90, optimize=True)


def make_fullframe_versions(images: list[Path]) -> list[Path]:
    result: list[Path] = []
    previous_digest = ""
    for source in images:
        # Omit only byte-identical consecutive images. Near-duplicates with different
        # encodings are retained for human review rather than being guessed away.
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest == previous_digest:
            log("Skipping consecutive byte-identical still: " + source.name)
            continue
        target = PROJECT / "assets" / "generated" / "fullframe_images" / ("%03d_fullframe.jpg" % (len(result) + 1))
        fit_image_to_frame(source, target)
        result.append(target.resolve())
        previous_digest = digest
    return result


def make_local_chapter_icons(chapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Draw simple chapter badges locally with Pillow; never fetch icons or install renderers."""
    generated = PROJECT / "assets" / "generated" / "icons"
    generated.mkdir(parents=True, exist_ok=True)
    overlays: list[dict[str, Any]] = []

    for index, (name, color) in enumerate(ICON_CHAPTERS):
        target = generated / ("%02d_%s.png" % (index + 1, name))
        image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        accent_hex = color.lstrip("#")
        accent = tuple(int(accent_hex[offset:offset + 2], 16) for offset in (0, 2, 4)) + (255,)
        white = (250, 249, 245, 255)
        ink = (24, 28, 34, 245)
        draw.ellipse((18, 18, 238, 238), fill=ink, outline=accent, width=10)

        if name == "map-pin":
            draw.ellipse((82, 52, 174, 144), outline=white, width=10)
            draw.ellipse((111, 81, 145, 115), fill=accent)
            draw.line([(91, 125), (128, 198), (165, 125)], fill=white, width=10, joint="curve")
        elif name == "compass":
            draw.polygon([(128, 48), (185, 183), (128, 157), (71, 183)], fill=accent, outline=white)
            draw.line([(128, 48), (128, 157)], fill=white, width=8)
            draw.ellipse((115, 115, 141, 141), fill=ink, outline=white, width=5)
        elif name == "triangle-alert":
            draw.polygon([(128, 48), (207, 194), (49, 194)], outline=accent, fill=ink)
            draw.line([(128, 94), (128, 143)], fill=white, width=14)
            draw.ellipse((120, 158, 136, 174), fill=white)
        elif name == "phone":
            draw.rounded_rectangle((83, 48, 173, 207), radius=15, outline=white, width=10)
            draw.line([(109, 69), (147, 69)], fill=accent, width=7)
            draw.ellipse((119, 179, 137, 197), fill=accent)
        elif name == "heart-pulse":
            draw.line([(49, 128), (83, 128), (103, 91), (126, 166), (148, 111), (168, 139), (207, 139)],
                      fill=white, width=11, joint="curve")
        elif name == "clock":
            draw.ellipse((58, 58, 198, 198), outline=white, width=11)
            draw.line([(128, 80), (128, 129), (163, 151)], fill=accent, width=12, joint="curve")
        elif name == "construction":
            draw.line([(78, 190), (177, 91)], fill=white, width=17)
            draw.line([(66, 84), (105, 123)], fill=accent, width=18)
            draw.line([(153, 62), (195, 104)], fill=white, width=18)
            draw.line([(139, 77), (178, 38)], fill=accent, width=12)
        else:
            draw.line([(128, 54), (128, 168)], fill=white, width=14)
            draw.line([(78, 126), (128, 180), (178, 126)], fill=accent, width=14, joint="curve")

        image.save(target, optimize=True)
        chapter_start = float(chapters[index].get("start_s", 2.0)) + 0.15 if index < len(chapters) else 2.15
        overlays.append({
            "name": name, "path": str(target.resolve()),
            "start_seconds": round(chapter_start, 3), "duration": 1.15,
            "x": 0.78, "y": -0.53, "scale": 0.115, "color": color,
        })

    log("Created " + str(len(overlays)) + " local chapter icons with Pillow; no network requests.")
    return overlays


def synth_sfx(kind: str, path: Path, duration: float, seed: int) -> None:
    rng = random.Random(seed)
    count = max(1, int(duration * SAMPLE_RATE))
    samples = array.array("h")
    for index in range(count):
        t = index / SAMPLE_RATE
        x = t / max(0.001, duration)
        env = math.exp(-5.5 * x)
        white = rng.uniform(-1.0, 1.0)
        if kind == "whoosh":
            env = math.sin(math.pi * min(1.0, x)) ** 1.6
            value = 0.23 * white * env + 0.11 * math.sin(math.tau * (90 + 100 * x) * t) * env
        elif kind == "pop":
            value = 0.38 * math.sin(math.tau * (1000 * math.exp(-4 * x) + 160) * t) * env
        elif kind == "scratch":
            value = 0.29 * white * env * (1.0 if x < 0.38 else 0.18) + 0.12 * math.sin(math.tau * (440 + 900 * x) * t) * env
        elif kind == "bass_drop":
            value = 0.48 * math.sin(math.tau * (105 - 64 * x) * t) * env + 0.08 * white * env
        elif kind == "heartbeat":
            pulse = math.exp(-((x - 0.23) / 0.075) ** 2) + 0.83 * math.exp(-((x - 0.43) / 0.09) ** 2)
            value = 0.36 * math.sin(math.tau * 62 * t) * pulse + 0.07 * math.sin(math.tau * 44 * t) * pulse
        elif kind == "air_gasp":
            env = math.sin(math.pi * min(1.0, x)) ** 1.3 * (0.6 + 0.4 * math.sin(math.tau * 4 * t))
            value = 0.22 * white * env + 0.10 * math.sin(math.tau * (180 + 95 * x) * t) * env
        elif kind == "low_hit":
            value = (0.47 * math.sin(math.tau * (70 - 25 * x) * t) + 0.10 * math.sin(math.tau * 42 * t)) * env
        elif kind == "rope_snap":
            value = 0.40 * white * math.exp(-28 * x) + 0.16 * math.sin(math.tau * (480 - 280 * x) * t) * env
            if x < 0.12:
                value += 0.16 * math.sin(math.tau * 1800 * t)
        elif kind == "soft_click":
            transient = math.exp(-((x - 0.09) / 0.045) ** 2)
            value = 0.25 * math.sin(math.tau * 1200 * t) * transient + 0.09 * math.sin(math.tau * 250 * t) * env
        else:
            value = 0.43 * math.sin(math.tau * (58 - 18 * x) * t) * env + 0.12 * white * math.exp(-20 * x)
        samples.append(int(max(-0.82, min(0.82, value)) * 32767))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(samples.tobytes())


def make_music(path: Path, duration: float, shock_times: list[float]) -> None:
    samples = array.array("h")
    duck_ranges = [(max(0, t - 0.46), max(0, t - 0.04)) for t in shock_times]
    for index in range(max(1, int(math.ceil(duration * SAMPLE_RATE)))):
        t = index / SAMPLE_RATE
        slow = 0.82 + 0.18 * math.sin(math.tau * 0.075 * t)
        value = (
            0.105 * math.sin(math.tau * 55.0 * t)
            + 0.036 * math.sin(math.tau * 82.41 * t + 0.2 * math.sin(math.tau * 0.08 * t))
            + 0.022 * math.sin(math.tau * 110.0 * t)
            + 0.010 * math.sin(math.tau * 164.81 * t)
        ) * slow
        if t < min(duration * 0.10, 16.0):
            phase = t % 2.25
            if phase < 0.42:
                value += 0.016 * math.sin(math.tau * (220.0 if phase < 0.21 else 293.66) * phase)
        for start, end in duck_ranges:
            if start <= t <= end:
                edge = min(t - start, end - t)
                value *= 0.10 + 0.16 * min(1.0, max(0.0, edge / 0.08))
                break
        samples.append(int(max(-0.30, min(0.30, value)) * 32767))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(samples.tobytes())


def make_horror_overlay() -> Path:
    """Create a brief transparent red-black tint/vignette used only on the most severe story beats."""
    target = PROJECT / "assets" / "generated" / "red_horror_overlay.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (1920, 1080), (72, 0, 0, 27))
    draw = ImageDraw.Draw(image)
    # Concentric black edge strokes create a restrained vignette. This image is placed only for
    # a short interval at the rope-snap / no-pulse / death / sealing beats, never across the whole edit.
    for index in range(18):
        inset = (17 - index) * 25
        alpha = int(4 + (index / 17) * 72)
        draw.rectangle(
            (inset, inset, 1919 - inset, 1079 - inset),
            outline=(0, 0, 0, alpha),
            width=26,
        )
    image.save(target, optimize=True)
    return target.resolve()


def make_sfx_files() -> dict[str, Path]:
    lengths = {
        "whoosh": 0.48, "pop": 0.22, "scratch": 0.42, "bass_drop": 0.80,
        "heartbeat": 0.72, "air_gasp": 0.62, "low_hit": 0.72,
        "rope_snap": 0.34, "soft_click": 0.16, "concrete_thud": 0.64,
    }
    results = {}
    for index, (kind, length) in enumerate(lengths.items(), start=1):
        path = PROJECT / "assets" / "audio" / "sfx" / (kind + ".wav")
        synth_sfx(kind, path, length, 2009 + index)
        results[kind] = path.resolve()
    return results



FACT_CALLOUTS = [
    ("TWENTY SIX YEARS OLD", "26 YEARS OLD", "neutral"),
    ("ELEVEN PEOPLE", "11 PEOPLE", "action"),
    ("CORKSCREW", "CORKSCREW", "danger"),
    ("FOURTEEN HOURS", "14 HOURS", "danger"),
    ("TWO HUNDRED", "200 LB", "action"),
    ("UNCHARTED", "UNCHARTED", "danger"),
    ("EIGHTEEN INCHES", "18 × 10 IN", "danger"),
    ("TWELVE HOURS", "12 HOURS", "danger"),
    ("4 A M", "4:00 AM", "danger"),
    ("NO PULSE", "NO PULSE", "danger"),
    ("ROPE SNAPPED", "ROPE SNAPPED", "danger"),
    ("TWENTY SEVEN HOURS", "27 HOURS", "danger"),
    ("SEALED WITH CONCRETE", "SEALED FOREVER", "danger"),
    ("TWENTY FOUR HOURS", "24 HOURS", "action"),
]


def make_fact_callouts(tokens: list[dict[str, Any]], duration: float) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    target_dir = PROJECT / "assets" / "generated" / "callouts"
    target_dir.mkdir(parents=True, exist_ok=True)
    font_path_candidates = [
        Path(r"C:\Windows\Fonts\arialbd.ttf"),
        Path(r"C:\Windows\Fonts\Arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    font_path = next((candidate for candidate in font_path_candidates if candidate.is_file()), None)
    for index, (phrase, label, mood) in enumerate(FACT_CALLOUTS, start=1):
        found = find_phrase(tokens, phrase)
        if not found:
            continue
        start = float(found[0])
        if start >= duration:
            continue
        width, height = 1920, 1080
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        x0, y0, x1, y1 = 1350, 220, 1835, 365
        if mood == "danger":
            fill, accent, ink = (240, 68, 68, 248), (255, 255, 255, 255), (20, 20, 20, 255)
        elif mood == "action":
            fill, accent, ink = (246, 207, 69, 250), (240, 68, 68, 255), (20, 20, 20, 255)
        else:
            fill, accent, ink = (250, 249, 245, 248), (21, 168, 156, 255), (20, 20, 20, 255)
        # Tiny offset shadow and bold black stroke keep the callout readable over detailed art.
        draw.rounded_rectangle((x0 + 7, y0 + 8, x1 + 7, y1 + 8), radius=22, fill=(0, 0, 0, 65))
        draw.rounded_rectangle((x0, y0, x1, y1), radius=22, fill=fill, outline=ink, width=6)
        draw.rounded_rectangle((x0 + 18, y0 + 18, x0 + 30, y1 - 18), radius=6, fill=accent)
        font_size = 44 if len(label) < 15 else 36
        try:
            font = ImageFont.truetype(str(font_path), font_size) if font_path else ImageFont.load_default()
        except OSError:
            font = ImageFont.load_default()
        # Keep callouts short; wrap only if a platform font has an unexpectedly large glyph width.
        text_box = draw.textbbox((0, 0), label, font=font, stroke_width=1)
        text_width, text_height = text_box[2] - text_box[0], text_box[3] - text_box[1]
        if text_width > x1 - x0 - 62:
            font_size = max(28, font_size - 8)
            try:
                font = ImageFont.truetype(str(font_path), font_size) if font_path else ImageFont.load_default()
            except OSError:
                font = ImageFont.load_default()
            text_box = draw.textbbox((0, 0), label, font=font, stroke_width=1)
            text_width, text_height = text_box[2] - text_box[0], text_box[3] - text_box[1]
        tx = x0 + 38 + max(0, (x1 - x0 - 56 - text_width) // 2)
        ty = y0 + (y1 - y0 - text_height) // 2 - 4
        draw.text((tx, ty), label, font=font, fill=ink, stroke_width=1, stroke_fill=ink)
        path = target_dir / ("%02d_%s.png" % (index, re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")))
        image.save(path, optimize=True)
        output.append({
            "label": label, "path": str(path.resolve()), "start_seconds": round(start, 3),
            "duration": min(1.25, max(0.75, duration - start)), "mood": mood,
            "trigger_phrase": phrase,
        })
    return output


def tokenise_story(lines: list[str]) -> list[dict[str, Any]]:
    tokens = []
    for line_index, line in enumerate(lines):
        for match in WORD_RE.finditer(line):
            value = match.group(0)
            tokens.append({
                "index": len(tokens), "line_index": line_index,
                "text": value, "norm": norm_word(value),
                "start_s": 0.0, "end_s": 0.0, "timing_estimated": True,
            })
    return tokens


def find_cached_whisper_model() -> Path | None:
    """Return an already-cached faster-whisper base.en snapshot, without network access."""
    cache_roots: list[Path] = []
    hf_home = os.environ.get("HF_HOME")
    hub_cache = os.environ.get("HUGGINGFACE_HUB_CACHE")
    if hf_home:
        cache_roots.append(Path(hf_home) / "hub")
    if hub_cache:
        cache_roots.append(Path(hub_cache))
    cache_roots.extend([
        Path.home() / ".cache" / "huggingface" / "hub",
        Path.home() / ".huggingface" / "hub",
    ])
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        cache_roots.append(Path(local_app_data) / "huggingface" / "hub")

    seen: set[str] = set()
    for root in cache_roots:
        key = str(root.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        snapshots = root / "models--Systran--faster-whisper-base.en" / "snapshots"
        if not snapshots.is_dir():
            continue
        candidates = sorted(
            (path for path in snapshots.iterdir()
             if path.is_dir() and (path / "model.bin").is_file() and (path / "config.json").is_file()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            return candidates[0]
    return None


def install_and_transcribe(audio: Path) -> tuple[list[dict[str, Any]], str]:
    """Use only an already-installed package and cached model. Never pip-install or fetch models."""
    try:
        from faster_whisper import WhisperModel
    except Exception:
        log("Whisper not installed; skipping word alignment without installing anything.")
        return [], "ESTIMATED: local faster-whisper package unavailable; downloads disabled"

    model_path = find_cached_whisper_model()
    if model_path is None:
        log("No cached faster-whisper base.en model found; skipping transcription without downloading it.")
        return [], "ESTIMATED: Whisper model is not cached locally; downloads disabled"

    try:
        threads = max(2, min(8, os.cpu_count() or 4))
        log("Using the cached base.en Whisper model from disk; network access is disabled.")
        model = WhisperModel(
            str(model_path), device="cpu", compute_type="int8",
            cpu_threads=threads, local_files_only=True,
        )
        segments, info = model.transcribe(
            str(audio), language="en", word_timestamps=True, vad_filter=True, beam_size=5,
        )
        words = []
        for segment in segments:
            for word in getattr(segment, "words", []) or []:
                text = str(word.word).strip()
                normalized = norm_word(text)
                if normalized:
                    words.append({
                        "text": text, "norm": normalized,
                        "start_s": max(0.0, float(word.start)),
                        "end_s": max(float(word.start) + 0.04, float(word.end)),
                    })
        if not words:
            return [], "ESTIMATED: cached faster-whisper returned no word timestamps"
        return words, "cached faster-whisper base.en word timestamps; language=" + str(getattr(info, "language", "en"))
    except Exception as exc:
        log("Local Whisper run failed; using estimated timing and making no download attempt. " + str(exc))
        return [], "ESTIMATED: local faster-whisper failed: " + str(exc)


def align_tokens(reference: list[dict[str, Any]], heard: list[dict[str, Any]], duration: float) -> float:
    if not reference:
        return 0.0
    if not heard:
        total = sum(max(1, len(item["norm"])) for item in reference)
        cursor = 0.0
        for item in reference:
            span = duration * max(1, len(item["norm"])) / total
            item["start_s"], item["end_s"] = cursor, min(duration, cursor + span)
            item["timing_estimated"] = True
            cursor += span
        return 0.0
    matcher = difflib.SequenceMatcher(
        a=[item["norm"] for item in reference],
        b=[item["norm"] for item in heard],
        autojunk=False,
    )
    mapping: dict[int, int] = {}
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            mapping[block.a + offset] = block.b + offset
    for ref_index, heard_index in mapping.items():
        reference[ref_index]["start_s"] = float(heard[heard_index]["start_s"])
        reference[ref_index]["end_s"] = float(heard[heard_index]["end_s"])
        reference[ref_index]["timing_estimated"] = False
    cursor = 0
    while cursor < len(reference):
        if cursor in mapping:
            cursor += 1
            continue
        begin = cursor
        while cursor < len(reference) and cursor not in mapping:
            cursor += 1
        finish = cursor
        left_index, right_index = begin - 1, finish
        left = float(reference[left_index]["end_s"]) if left_index >= 0 and left_index in mapping else 0.0
        right = float(reference[right_index]["start_s"]) if right_index < len(reference) and right_index in mapping else duration
        if right <= left:
            right = min(duration, left + 0.12 * (finish - begin))
        count, span = finish - begin, max(0.0, right - left)
        for index in range(begin, finish):
            offset = index - begin
            reference[index]["start_s"] = left + span * offset / max(1, count)
            reference[index]["end_s"] = left + span * (offset + 1) / max(1, count)
            reference[index]["timing_estimated"] = True
    previous_end = 0.0
    for item in reference:
        start = min(max(0.0, float(item["start_s"])), max(0.0, duration - 0.08))
        start = max(start, previous_end - 0.015)
        end = min(duration, max(start + 0.06, float(item["end_s"])))
        if end <= start:
            start, end = max(0.0, duration - 0.08), duration
        item["start_s"], item["end_s"] = round(start, 3), round(end, 3)
        previous_end = end
    return len(mapping) / max(1, len(reference))


def line_timing(lines: list[str], tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: list[list[dict[str, Any]]] = [[] for _ in lines]
    for token in tokens:
        grouped[int(token["line_index"])].append(token)
    result = []
    for index, line in enumerate(lines):
        group = grouped[index]
        if group:
            start = min(float(item["start_s"]) for item in group)
            end = max(float(item["end_s"]) for item in group)
        else:
            start, end = 0.0, 0.1
        result.append({
            "line_index": index, "text": line,
            "start_s": round(start, 3), "end_s": round(end, 3), "tokens": group,
        })
    return result


def find_phrase(tokens: list[dict[str, Any]], phrase: str) -> tuple[float, int, int] | None:
    wanted = [norm_word(word) for word in WORD_RE.findall(phrase.replace("-", " ")) if norm_word(word)]
    norms = [str(token["norm"]) for token in tokens]
    if not wanted:
        return None
    for index in range(max(0, len(norms) - len(wanted) + 1)):
        if norms[index:index + len(wanted)] == wanted:
            return float(tokens[index]["start_s"]), index, index + len(wanted)
    return None


def srt_time(seconds: float) -> str:
    total = max(0, round(seconds * 1000))
    h, rem = divmod(total, 3600000)
    m, rem = divmod(rem, 60000)
    sec, ms = divmod(rem, 1000)
    return "%02d:%02d:%02d,%03d" % (h, m, sec, ms)


def write_captions(tokens: list[dict[str, Any]], lines: list[str]) -> list[dict[str, Any]]:
    grouped: list[list[dict[str, Any]]] = [[] for _ in lines]
    for token in tokens:
        grouped[int(token["line_index"])].append(token)
    cues = []
    previous_end = 0.0
    for group in grouped:
        chunk: list[dict[str, Any]] = []
        for token in group:
            gap = float(token["start_s"]) - float(chunk[-1]["end_s"]) if chunk else 0.0
            if chunk and (len(chunk) >= 3 or gap > 0.34):
                start, end = float(chunk[0]["start_s"]), float(chunk[-1]["end_s"])
                start = max(previous_end, start)
                if end - start >= 0.25:
                    cues.append({"start": round(start, 3), "end": round(end, 3),
                                 "text": " ".join(item["text"] for item in chunk)})
                    previous_end = end
                chunk = []
            chunk.append(token)
        if chunk:
            start, end = max(previous_end, float(chunk[0]["start_s"])), float(chunk[-1]["end_s"])
            if end - start >= 0.25:
                cues.append({"start": round(start, 3), "end": round(end, 3),
                             "text": " ".join(item["text"] for item in chunk)})
                previous_end = end
    path = PROJECT / "build" / "captions.srt"
    path.parent.mkdir(parents=True, exist_ok=True)
    chunks = [
        str(index) + "\n" + srt_time(item["start"]) + " --> " + srt_time(item["end"]) + "\n" + item["text"]
        for index, item in enumerate(cues, start=1)
    ]
    path.write_text("\n\n".join(chunks) + ("\n" if chunks else ""), encoding="utf-8-sig")
    return cues


def write_arabic_subtitles(path: Path, rows: list[dict[str, Any]], max_words: int = 4) -> list[dict[str, Any]]:
    """Write a separate Arabic SRT using the aligned English sentence time windows."""
    cues: list[dict[str, Any]] = []
    previous_end = 0.0
    for index, translation in enumerate(STORY_AR):
        if index >= len(rows):
            break
        words = [word for word in str(translation).strip().split() if word]
        if not words:
            continue
        sentence_start = max(previous_end, float(rows[index]["start_s"]))
        sentence_end = max(sentence_start + 0.3, float(rows[index]["end_s"]))
        chunk_size = max(2, int(max_words))
        while math.ceil(len(words) / chunk_size) > 1 and (sentence_end - sentence_start) / math.ceil(len(words) / chunk_size) < 0.72:
            chunk_size += 1
        chunks = [words[offset:offset + chunk_size] for offset in range(0, len(words), chunk_size)]
        weights = [sum(max(1, len(re.sub(r"[،؛.!؟:]+$", "", word))) for word in chunk) for chunk in chunks]
        total_weight = max(1, sum(weights))
        cursor, accumulated = sentence_start, 0
        for chunk_index, chunk in enumerate(chunks):
            accumulated += weights[chunk_index]
            if chunk_index == len(chunks) - 1:
                end = sentence_end
            else:
                end = sentence_start + (sentence_end - sentence_start) * accumulated / total_weight
            end = min(float(rows[-1]["end_s"]), max(cursor + 0.25, end))
            cues.append({"start": round(cursor, 3), "end": round(end, 3),
                         "text": " ".join(chunk), "line_index": index})
            cursor = end
        previous_end = sentence_end
    path.parent.mkdir(parents=True, exist_ok=True)
    blocks = [
        str(index) + "\n" + srt_time(cue["start"]) + " --> " + srt_time(cue["end"]) + "\n" + cue["text"]
        for index, cue in enumerate(cues, start=1)
    ]
    path.write_text("\n\n".join(blocks) + ("\n" if blocks else ""), encoding="utf-8-sig")
    return cues


def fit_storyboard_boundaries(rows: list[dict[str, Any]], tokens: list[dict[str, Any]], duration: float,
                              target_count: int, intro_duration: float) -> list[float]:
    anchors = [0.0]
    if intro_duration > 0:
        anchors.append(min(duration, intro_duration))
    for row in rows[1:]:
        value = float(row["start_s"])
        if value > anchors[-1] + 0.72 and value < duration - 0.45:
            anchors.append(value)
    if anchors[-1] < duration:
        anchors.append(duration)
    anchors = sorted(set(round(max(0.0, min(duration, value)), 3) for value in anchors))
    if anchors[0] != 0.0:
        anchors.insert(0, 0.0)
    if anchors[-1] != round(duration, 3):
        anchors.append(round(duration, 3))
    # Merge very short sentence beats first; shots under 0.8 s are not readable in this style.
    while len(anchors) > 2:
        short = [index for index in range(1, len(anchors) - 1)
                 if min(anchors[index] - anchors[index - 1], anchors[index + 1] - anchors[index]) < 0.8]
        if not short:
            break
        remove_index = min(short, key=lambda i: min(anchors[i] - anchors[i - 1], anchors[i + 1] - anchors[i]))
        anchors.pop(remove_index)
    while len(anchors) < target_count + 1:
        intervals = [(anchors[i + 1] - anchors[i], i) for i in range(len(anchors) - 1)
                     if anchors[i + 1] - anchors[i] >= 2.4]
        if not intervals:
            break
        _, index = max(intervals)
        left, right = anchors[index], anchors[index + 1]
        midpoint = (left + right) / 2
        candidates = [
            float(token["start_s"]) for token in tokens
            if left + 1.0 <= float(token["start_s"]) <= right - 1.0
        ]
        split = min(candidates, key=lambda value: abs(value - midpoint)) if candidates else midpoint
        anchors.insert(index + 1, round(split, 3))
    while len(anchors) > target_count + 1:
        candidates = []
        for index in range(1, len(anchors) - 1):
            left, middle, right = anchors[index - 1:index + 2]
            candidates.append((max(middle - left, right - middle), index))
        _, remove_index = min(candidates)
        anchors.pop(remove_index)
    # Last-resort even boundaries retain full coverage if there are too few long intervals to split.
    if len(anchors) != target_count + 1 or any(b <= a for a, b in zip(anchors, anchors[1:])):
        anchors = [round(duration * i / target_count, 3) for i in range(target_count + 1)]
    anchors[0], anchors[-1] = 0.0, round(duration, 3)
    return anchors


def make_chapters(rows: list[dict[str, Any]], duration: float, intro_duration: float) -> list[dict[str, Any]]:
    sections = []
    for row_index, title in CHAPTERS:
        if row_index >= len(rows):
            continue
        start = float(rows[row_index]["start_s"])
        if row_index == 0:
            start = max(start, intro_duration)
        sections.append({"title": title, "start_s": min(start, duration), "duration_s": 1.0,
                         "font_size": 31, "color": "#FFFFFF", "x": 0.0, "y": -0.78})
    sections.sort(key=lambda item: item["start_s"])
    for index, item in enumerate(sections):
        end = float(sections[index + 1]["start_s"]) if index + 1 < len(sections) else duration
        item["duration_s"] = max(0.7, end - float(item["start_s"]))
    return sections


def create_story_timeline(lines: list[str], rows: list[dict[str, Any]], tokens: list[dict[str, Any]],
                          images: list[Path], boundaries: list[float], chapters: list[dict[str, Any]],
                          duration: float, timing_mode: str, sfx_events: list[dict[str, Any]]) -> dict[str, Any]:
    scenes = []
    for index, image in enumerate(images):
        start, end = boundaries[index], boundaries[index + 1]
        midpoint = (start + end) / 2
        row = next((entry for entry in rows if float(entry["start_s"]) <= midpoint <= float(entry["end_s"])), None)
        line_index = int(row["line_index"]) if row else min(len(rows) - 1, index)
        emotion, shock, trigger = BEAT_META[line_index] if line_index < len(BEAT_META) else ("tense", 1, "STORY")
        chapter = next((item["title"] for item in reversed(chapters) if float(item["start_s"]) <= start), "THE CAVE")
        scene_sfx = [{"file": item["file"], "time_s": item["start"], "volume": item["volume"]}
                     for item in sfx_events if start <= item["start"] < end]
        layout_side = ("left", "center", "right")[index % 3]
        layout_template = {
            "left": "A_subject-left_host-right",
            "center": "B_centered-hero",
            "right": "A_mirrored_subject-right_host-left",
        }[layout_side]
        entry_direction = ("right", "left", "bottom", "top")[index % 4]
        exit_direction = ("left", "right", "top", "bottom")[index % 4]
        scene_start = round(start, 3)
        scenes.append({
            "scene_id": "scene_%03d" % (index + 1),
            "start_s": scene_start, "end_s": round(end, 3),
            "start_frame": round(start * 30), "end_frame": round(end * 30),
            "trigger_word": trigger, "chapter": chapter, "emotion": emotion, "shock_level": shock,
            "layout_template": layout_template, "layout_side": layout_side, "full_bleed": False,
            "background": "#FFFFFF",
            "layers": [{
                "asset": str(image), "layer": "L2", "position": layout_side + " third on pure-white canvas",
                "size_percent_frame_height": 55,
                "scale": "55% to 60% with 0.72 s zoom pulses",
                "entrance": "slide from " + entry_direction + " + overshoot pop (0.14–0.24 s)",
                "exit": "slide toward " + exit_direction + " over final 0.14–0.22 s",
                "idle_loop": "continuous zoom pulse and 1–3% positional drift",
                "partial_changes": [
                    {"type": "trigger-word impact pulse", "trigger_word": trigger, "at_s": round(float(row["start_s"]), 3) if row else round(midpoint, 3)},
                    {"type": "brief red tint / camera shake", "trigger_word": trigger, "at_s": round(float(row["start_s"]), 3) if row else round(midpoint, 3)} if shock >= 2 else {"type": "subtle scale pulse", "trigger_word": trigger, "at_s": round(midpoint, 3)},
                ],
            }],
            "camera": "snap zoom + decaying shake" if shock >= 2 else "alternating push-in / pull-out with continuous drift",
            "text": {"content": "", "focus_word": trigger, "chapter_title": chapter, "max_words": 3,
                     "narration_captions": "disabled; only brief designed callouts and chapter titles"},
            "transition_in": "scale-pop replacement" if index and (index + 1) % 7 == 0 else "hard cut with directional entrance",
            "sfx": scene_sfx,
            "music": {"track": "assets/audio/sfx/suspense_bed.wav", "target_dbfs_approx": -24,
                      "duck_db": 6, "pre_shock_dip_s": 0.4 if shock >= 3 else 0.0},
            "notes": "Timing source: " + timing_mode + ". Check ASSET_CONTACT_SHEET.jpg; subject-to-sentence matching still needs visual review.",
        })
    return {
        "project": "Nutty Putty Cave",
        "canvas": {"width": 1920, "height": 1080, "fps": 30, "ratio": "16:9", "background": "#FFFFFF"},
        "voiceover_duration_s": round(duration, 3),
        "timing_mode": timing_mode,
        "word_count": len(tokens),
        "story_beats": [{
            "line_index": row["line_index"], "text": row["text"],
            "start_s": row["start_s"], "end_s": row["end_s"],
            "emotion": BEAT_META[row["line_index"]][0],
            "shock_level": BEAT_META[row["line_index"]][1],
            "trigger_word": BEAT_META[row["line_index"]][2],
        } for row in rows],
        "chapter_titles": chapters,
        "scene_timeline": scenes,
        "sound_effect_events": sfx_events,
        "transition_policy": {
            "default": "hard cut plus animated fly-in/fly-out",
            "accent": "keyframed scale-pop replacement every 7th cut; white flash only on death reveal",
            "secondary_image_inserts": "brief adjacent-image overlays on selected high-impact beats",
            "forbidden": ["wipe", "spin", "cube", "page curl", "glitch pack", "decorative zoom blur"],
        },
        "review_note": "ASSET_CONTACT_SHEET.jpg was generated locally. File metadata is inspectable, but image semantics are not asserted automatically.",
    }



def inventory_asset(path: Path, asset_type: str, original: str = "") -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": path.stem, "path": str(path.resolve()), "original_path": original or str(path.resolve()),
        "type": asset_type, "size_bytes": path.stat().st_size, "dimensions": None, "duration_s": None,
        "alpha_channel": False, "tags": [asset_type], "description": path.name, "confidence": "high",
    }
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    row["sha256"] = digest
    if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
        with Image.open(path) as image:
            row["dimensions"] = {"width": image.width, "height": image.height}
            row["alpha_channel"] = "A" in image.getbands() or "transparency" in image.info
    elif path.suffix.lower() in {".mp3", ".wav", ".mp4", ".mov", ".m4v", ".webm"}:
        try:
            row["duration_s"] = round(ffprobe_duration(path), 3)
        except Exception as exc:
            row["problem"] = "Duration could not be read: " + str(exc)
    return row



def prepare_simple_project(
    source_images: list[Path], presenter_images: list[Path], narration: Path, source_map: dict[str, Any]
) -> int:
    """Build only supplied images + the original narration; no title card, ASR, music or SFX."""
    fullframe_images = make_fullframe_versions(source_images)
    make_contact_sheet(source_images, PROJECT / "build" / "ASSET_CONTACT_SHEET.jpg")
    duration = ffprobe_duration(narration)
    tokens = tokenise_story(STORY_EN)
    align_tokens(tokens, [], duration)
    rows = line_timing(STORY_EN, tokens)
    timing_mode = "ESTIMATED from script length and narration duration; Whisper skipped"
    (PROJECT / "build" / "word_timestamps.json").write_text(
        json.dumps({"source": timing_mode, "alignment_ratio": 0.0, "words": tokens, "sentences": rows},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    boundaries = fit_storyboard_boundaries(rows, tokens, duration, len(fullframe_images), 0.0)
    scene_texts = (STORY_EN + [STORY_EN[-1]] * max(0, len(fullframe_images) - len(STORY_EN)))[:len(fullframe_images)]
    settings = {
        "motion_preset": "nutty_putty_casefile", "layout_mode": "full_frame",
        "use_storyboard_boundaries": True, "scene_image_scale": 1.0,
        "scene_image_x": 0.0, "scene_image_y": 0.0,
        "scene_zoom_start": 1.0, "scene_zoom_end": 1.065, "scene_pan_amount": 0.006,
        "target_shot_seconds": 2.65, "minimum_shot_seconds": 1.25,
        "presenter_overlay": True, "presenter_mode": "reset", "presenter_backplate": False,
        "presenter_smart_matte": True, "presenter_scale": 0.31, "presenter_x": 0.72, "presenter_y": 0.35,
        "presenter_pose_seconds": 35.0, "presenter_reset_duration": 2.15,
        "use_precomputed_captions": False, "transcribe_if_whisper_available": False,
        "add_captions_when_transcribed": False, "show_scene_text_without_transcript": False,
        "voice_volume": 1.0, "voice_fade_in": 0.0, "voice_fade_out": 0.0,
        "make_sfx_cue_sheet": False, "sound_effects": [],
        "icon_overlays": [], "callout_overlays": [],
        "flash_overlay_path": "", "flash_times": [],
        "horror_overlay_path": "", "horror_overlay_times": [],
    }
    config = {
        "project_name": "Nutty Putty Cave — Basic CapCut Edit", "drafts_dir": "",
        "audio": str(narration.resolve()),
        "scene_images": [str(path.resolve()) for path in fullframe_images],
        "scene_texts": scene_texts,
        "presenter_images": [str(path.resolve()) for path in presenter_images],
        "canvas": {"width": 1920, "height": 1080, "fps": 30, "ratio": "16:9"},
        "storyboard_boundaries": boundaries,
        "story_beats": [
            {"scene_id": "story_%03d" % (i + 1), "text": row["text"],
             "start_s": row["start_s"], "end_s": row["end_s"],
             "emotion": BEAT_META[i][0], "shock_level": BEAT_META[i][1], "trigger_word": BEAT_META[i][2],
             "stock_query": STOCK_QUERIES[i]}
            for i, row in enumerate(rows)
        ],
        "chapter_titles": [], "background_music": {}, "settings": settings,
    }
    for name in ("project.json", "config.json"):
        (PROJECT / name).write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    original_map = {}
    for group in source_map.values():
        for entry in group:
            original_map[str(Path(entry["local"]).resolve())] = entry["original"]
    catalog = []
    for image in source_images:
        catalog.append(inventory_asset(image, "story_art_original", original_map.get(str(image.resolve()), "")))
    for image in fullframe_images:
        catalog.append(inventory_asset(image, "story_art_16x9"))
    for image in presenter_images:
        item = inventory_asset(image, "host_avatar_pose", original_map.get(str(image.resolve()), ""))
        item["tags"] = ["host_avatar", "pose category requires visual confirmation"]
        item["confidence"] = "low"
        catalog.append(item)
    catalog.append(inventory_asset(narration, "voiceover", str(AUDIO_SOURCE)))
    hashes: dict[str, list[str]] = {}
    for item in catalog:
        if item.get("sha256"):
            hashes.setdefault(item["sha256"], []).append(item["path"])
    duplicates = [items for items in hashes.values() if len(items) > 1]
    unreadable = [item for item in catalog if item.get("problem")]
    catalog_doc = {
        "version": 1, "project": "Nutty Putty Cave — Basic CapCut Edit",
        "created_at": datetime.now().isoformat(timespec="seconds"), "asset_count": len(catalog),
        "counts_by_type": {kind: sum(a.get("type") == kind for a in catalog)
                           for kind in sorted({str(a.get("type", "unknown")) for a in catalog})},
        "duplicates": duplicates, "unreadable": unreadable,
        "visual_review_status": "Contact sheet created. Semantic image-to-script matching requires a visual review.",
        "assets": catalog,
    }
    (PROJECT / "build" / "ASSET_CATALOG.json").write_text(
        json.dumps(catalog_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    timeline = create_story_timeline(STORY_EN, rows, tokens, fullframe_images, boundaries, [],
                                     duration, timing_mode, [])
    timeline.update({
        "asset_count": len(catalog), "caption_count": 0, "arabic_subtitle_count": 0,
        "sfx_count": 0, "music_enabled": False, "title_card_enabled": False, "whisper_enabled": False,
        "source_image_count": len(source_images),
    })
    (PROJECT / "build" / "timeline.json").write_text(
        json.dumps(timeline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (PROJECT / "build" / "MISSING_ASSETS.json").write_text(json.dumps({
        "items": [
            {"asset": "cave cross-section illustration", "status": "optional; not generated in basic mode",
             "prompt": "16:9 flat-vector narrow Utah cave passage, cream background, bold black outlines, no text."},
            {"asset": "rescue pulley illustration", "status": "optional; not generated in basic mode",
             "prompt": "16:9 flat-vector cave rescue pulley and rope under tension, clear silhouette, no text."},
        ],
        "policy": "First make sure the basic editable CapCut draft opens correctly; optional effects can be added later."
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (PROJECT / "build" / "ASSET_CATALOG_SUMMARY.md").write_text(
        "# Basic Asset Catalog\n\n"
        f"- Supplied story images: {len(source_images)}\n- Processed 16:9 images: {len(fullframe_images)}\n"
        f"- Presenter poses: {len(presenter_images)}\n- Voiceover: original MP3, unchanged\n"
        "- Whisper: skipped\n- Title card, music, SFX, captions, icons and callouts: disabled\n"
        f"- Duplicate groups: {len(duplicates)}\n- Unreadable files: {len(unreadable)}\n- Timing: {timing_mode}\n",
        encoding="utf-8"
    )
    (PROJECT / "build" / "QA_REPORT.md").write_text(
        "# Nutty Putty Cave — Basic Build QA\n\n"
        "- Uses supplied story images and the original narration MP3 only.\n"
        "- No Remotion title card, no SFX, no music, no subtitles on the CapCut timeline, no Whisper.\n"
        "- 1920x1080, 30 fps, 16:9. Images use restrained push-in keyframes; presenter images may briefly return every ~35 seconds.\n"
        f"- Narration duration: {duration:.3f}s. Scene timing is estimated from text length because Whisper is skipped.\n"
        "- Review images against narration in CapCut; image filenames alone do not confirm semantic matching.\n"
        "- This is an editable CapCut draft, not a final MP4 export.\n",
        encoding="utf-8"
    )
    log("Basic mode: no title card, no Whisper, no SFX, no music, no captions.")
    log(f"Project prepared: {PROJECT}")
    log(f"Voiceover duration: {duration:.2f}s; images: {len(source_images)}; processed: {len(fullframe_images)}")
    log("Contact sheet: " + str(PROJECT / "build" / "ASSET_CONTACT_SHEET.jpg"))
    return 0


def prepare(project_override: str | None = None, simple: bool = False) -> int:
    global PROJECT
    if project_override:
        candidate = Path(project_override).expanduser()
        PROJECT = candidate.resolve() if candidate.is_absolute() else (ROOT / candidate).resolve()
    ensure_dirs()
    source_images, presenter_images, source_audio, master_audio, source_map = copy_sources(simple=simple)
    (PROJECT / "story.txt").write_text("\n".join(STORY_EN) + "\n", encoding="utf-8")
    (PROJECT / "story_ar.txt").write_text("\n".join(STORY_AR) + "\n", encoding="utf-8")
    (PROJECT / "source_files.json").write_text(json.dumps(source_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (PROJECT / "README.md").write_text(
        "# Nutty Putty Cave video project\n\nAll copied media is local to this project. Do not commit or upload personal source assets.\n"
        "Use run_nutty_putty.ps1 from the repository root to rebuild the editable CapCut draft.\n",
        encoding="utf-8",
    )

    if simple:
        return prepare_simple_project(source_images, presenter_images, master_audio, source_map)

    fullframe_images = make_fullframe_versions(source_images)
    make_contact_sheet(source_images, PROJECT / "build" / "ASSET_CONTACT_SHEET.jpg")

    intro = PROJECT / "assets" / "generated" / "nutty-putty-title.mp4"
    npm = shutil.which("npm")
    if npm and (ROOT / "motion-lab" / "node_modules").is_dir():
        log("Rendering the 2-second Remotion title card.")
        result = subprocess.run([npm, "run", "render:nutty-title"], cwd=str(ROOT / "motion-lab"),
                                text=True, encoding="utf-8", errors="replace",
                                capture_output=True, check=False, timeout=None)
        if result.returncode != 0 or not intro.is_file():
            log("Remotion title render did not finish successfully; continuing without the title clip.")
            log((result.stderr or result.stdout or "")[-1200:])
            intro_path = None
        else:
            intro_path = intro.resolve()
    else:
        log("Remotion dependencies not available; proceeding without the custom title clip.")
        intro_path = None

    duration = ffprobe_duration(master_audio)
    heard, mode = install_and_transcribe(master_audio)
    tokens = tokenise_story(STORY_EN)
    match_ratio = align_tokens(tokens, heard, duration)
    if heard:
        timing_mode = mode + "; script alignment " + str(round(match_ratio * 100, 1)) + "%"
    else:
        timing_mode = mode + "; script-weighted timing"
    rows = line_timing(STORY_EN, tokens)
    captions = write_captions(tokens, STORY_EN)
    arabic_captions = write_arabic_subtitles(PROJECT / "build" / "captions_ar.srt", rows)
    (PROJECT / "build" / "word_timestamps.json").write_text(
        json.dumps({"source": timing_mode, "alignment_ratio": round(match_ratio, 3),
                    "words": tokens, "sentences": rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    sound_paths = make_sfx_files()
    shock_times = []
    for index, (_, shock, trigger) in enumerate(BEAT_META):
        if shock >= 3:
            match = find_phrase(tokens, trigger)
            if match:
                shock_times.append(float(match[0]))
    music_path = PROJECT / "assets" / "audio" / "sfx" / "suspense_bed.wav"
    make_music(music_path, duration, shock_times)
    sfx_events = []
    for label, kind, volume in SFX_EVENTS:
        match = find_phrase(tokens, label)
        if not match:
            continue
        start = max(0.0, min(duration - 0.1, float(match[0])))
        sfx_duration = ffprobe_duration(sound_paths[kind])
        if start + sfx_duration > duration:
            continue
        sfx_events.append({
            "label": label, "file": kind, "path": str(sound_paths[kind]),
            "start": round(start, 3), "duration": round(sfx_duration, 3), "volume": volume,
            "volume_db": round(20 * math.log10(max(volume, 0.0001)), 1),
        })
    sfx_events.sort(key=lambda item: item["start"])
    # The same sound kind never plays consecutively; preserve a few frames between repeats.
    for index in range(1, len(sfx_events)):
        if sfx_events[index]["file"] == sfx_events[index - 1]["file"]:
            sfx_events[index]["start"] = round(max(
                sfx_events[index]["start"],
                sfx_events[index - 1]["start"] + sfx_events[index - 1]["duration"] + 0.06,
            ), 3)
    settings = {
        "motion_preset": "nutty_putty_casefile",
        "layout_mode": "hybrid_whiteboard",
        # Licensed stills are selected by story beat and stored with credits/provenance.
        "stock_media": {"enabled": True, "providers": ["openverse", "pexels", "pixabay", "wikimedia"],
                        "per_query": 1, "max_total": 32, "max_queries": 26, "hero_every": 5,
                        "min_width": 1280, "allow_video": False, "allow_share_alike": False},
        "insert_every": 1,
        # Do not guess CapCut text opacity/scale property names. Enable only after local CLI probe.
        "text_caps": {},
        "callout_font_size": 20,
        "chapter_font_max": 20,
        "use_storyboard_boundaries": True,
        "scene_image_scale": 1.0, "scene_image_x": -0.24, "scene_image_y": -0.02,
        "card_scene_scale": 0.55,
        "scene_zoom_start": 0.55, "scene_zoom_end": 0.60, "scene_pan_amount": 0.018,
        "target_shot_seconds": 2.65, "minimum_shot_seconds": 1.25,
        "presenter_overlay": True, "presenter_mode": "reset", "presenter_backplate": False,
        "presenter_smart_matte": True, "presenter_scale": 0.31, "presenter_x": 0.72, "presenter_y": 0.35,
        "presenter_pose_seconds": 35.0, "presenter_reset_duration": 2.15,
        "use_precomputed_captions": True, "transcribe_if_whisper_available": False,
        "add_captions_when_transcribed": False, "show_scene_text_without_transcript": False,
        "caption_words_per_chunk": 3, "caption_min_hold_seconds": 0.52, "caption_font_size": 36,
        "caption_color": "#FFFFFF", "caption_danger_color": "#FF3030", "caption_action_color": "#FFD447",
        "caption_outline_width": 4.0, "caption_outline_color": "#000000", "caption_outline_alpha": 1.0,
        "caption_y": 0.66, "caption_x": 0.0,
        "voice_volume": 0.96, "voice_fade_in": 0.06, "voice_fade_out": 0.65,
        "make_sfx_cue_sheet": False, "flash_duration": 0.067,
        "caption_danger_words": ["stuck", "corkscrew", "uncharted", "head first", "gravity", "hallucinating",
                                 "oxygen", "screamed", "snapped", "no pulse", "deeper", "dead", "sealed",
                                 "concrete", "upside down"],
        "caption_action_words": ["eleven people", "fourteen hours", "six feet", "two hundred", "eighteen inches",
                                 "twelve hours", "twenty seven hours", "24 hours"],
        "sound_effects": [
            {"path": item["path"], "start": item["start"], "duration": item["duration"], "volume": item["volume"]}
            for item in sfx_events
        ],
    }
    chapters = make_chapters(rows, duration, 2.0 if intro_path else 0.0)
    overlays = make_local_chapter_icons(chapters)
    fact_overlays = make_fact_callouts(tokens, duration)

    # Give each visible callout and chapter-badge entrance a light, time-aligned audio cue.
    # Avoid piling a small click over an existing major story impact at the same timestamp.
    for index, item in enumerate(fact_overlays):
        start = float(item["start_seconds"])
        if any(abs(float(event["start"]) - start) <= 0.12 for event in sfx_events):
            continue
        kind = "pop" if item["mood"] == "danger" else "soft_click"
        path = sound_paths[kind]
        length = min(ffprobe_duration(path), max(0.08, duration - start))
        if length <= 0:
            continue
        gain = 0.20 if item["mood"] == "danger" else 0.16
        sfx_events.append({
            "label": "Callout entrance — " + item["label"], "file": kind, "path": str(path),
            "start": round(start, 3), "duration": round(length, 3), "volume": gain,
            "volume_db": round(20 * math.log10(gain), 1),
        })
    for index, chapter in enumerate(chapters):
        start = min(duration - 0.08, float(chapter["start_s"]) + 0.15)
        if start < 0 or any(abs(float(event["start"]) - start) <= 0.12 for event in sfx_events):
            continue
        kind = "soft_click" if index % 2 == 0 else "pop"
        path = sound_paths[kind]
        length = min(ffprobe_duration(path), max(0.08, duration - start))
        if length <= 0:
            continue
        gain = 0.18
        sfx_events.append({
            "label": "Chapter icon entrance — " + str(chapter["title"]),
            "file": kind, "path": str(path), "start": round(start, 3),
            "duration": round(length, 3), "volume": gain,
            "volume_db": round(20 * math.log10(gain), 1),
        })
    # Brief whooshes support the host-avatar reset entrances (not every cut gets a noisy effect).
    presenter_cadence = 35
    for presenter_start in range(presenter_cadence, max(1, int(duration)), presenter_cadence):
        if any(abs(float(event["start"]) - presenter_start) <= 0.14 for event in sfx_events):
            continue
        kind = "whoosh"
        path = sound_paths[kind]
        length = min(ffprobe_duration(path), max(0.08, duration - presenter_start))
        gain = 0.18
        sfx_events.append({
            "label": "Presenter reset entrance", "file": kind, "path": str(path),
            "start": round(float(presenter_start), 3), "duration": round(length, 3), "volume": gain,
            "volume_db": round(20 * math.log10(gain), 1),
        })

    # Ensure the same sample is not used twice in succession. Keep the event time and swap
    # to a related alternate transient instead of moving a sound away from its spoken trigger.
    sfx_events.sort(key=lambda item: item["start"])
    alternates = {
        "whoosh": "scratch", "scratch": "whoosh",
        "pop": "soft_click", "soft_click": "pop",
        "low_hit": "concrete_thud", "concrete_thud": "low_hit",
        "bass_drop": "low_hit", "heartbeat": "soft_click",
        "air_gasp": "whoosh", "rope_snap": "scratch",
    }
    for index in range(1, len(sfx_events)):
        previous, current = sfx_events[index - 1], sfx_events[index]
        if current["file"] == previous["file"]:
            alternate = alternates.get(str(current["file"]), "soft_click")
            current["file"] = alternate
            current["path"] = str(sound_paths[alternate])
            current["duration"] = round(min(
                ffprobe_duration(sound_paths[alternate]), max(0.08, duration - float(current["start"]))
            ), 3)
    settings["sound_effects"] = [
        {"path": item["path"], "start": item["start"], "duration": item["duration"], "volume": item["volume"]}
        for item in sfx_events
    ]

    scene_images = ([intro_path] if intro_path else []) + fullframe_images
    fallback_texts = STORY_EN + [STORY_EN[-1]] * max(0, len(fullframe_images) - len(STORY_EN))
    scene_texts = (["NUTTY PUTTY CAVE"] if intro_path else []) + fallback_texts[:len(fullframe_images)]
    boundaries = fit_storyboard_boundaries(rows, tokens, duration, len(scene_images), 2.0 if intro_path else 0.0)
    if intro_path:
        boundaries[1] = min(duration, 2.0)
        if boundaries[2] <= boundaries[1]:
            boundaries[2] = min(duration, boundaries[1] + 1.0)
        # Redistribute the remaining boundaries smoothly while keeping all segment edges monotonic.
        if any(b <= a for a, b in zip(boundaries, boundaries[1:])):
            boundaries = [round(duration * i / len(scene_images), 3) for i in range(len(scene_images) + 1)]
            boundaries[0], boundaries[-1] = 0.0, round(duration, 3)

    # Add a short sound cue exactly at each new scene entrance, not just at story keywords.
    # Major level-3 danger beats get a bass drop; calmer switches rotate clean pops/whooshes.
    transition_samples = ("whoosh", "pop", "soft_click", "scratch")
    for scene_index in range(1, len(scene_images)):
        event_time = float(boundaries[scene_index])
        if event_time >= duration - 0.08:
            continue
        story_row = next(
            (row for row in rows
             if float(row["start_s"]) <= event_time < float(row["end_s"])),
            None,
        )
        line_index = int(story_row["line_index"]) if story_row else min(len(BEAT_META) - 1, scene_index - 1)
        shock_level = BEAT_META[line_index][1] if 0 <= line_index < len(BEAT_META) else 1
        kind = "bass_drop" if shock_level >= 3 else transition_samples[scene_index % len(transition_samples)]
        path = sound_paths[kind]
        cue_duration = min(ffprobe_duration(path), duration - event_time)
        if cue_duration <= 0:
            continue
        gain = 0.27 if shock_level >= 3 else 0.20
        sfx_events.append({
            "label": "Scene entrance " + str(scene_index + 1),
            "file": kind, "path": str(path), "start": round(event_time, 3),
            "duration": round(cue_duration, 3), "volume": gain,
            "volume_db": round(20 * math.log10(gain), 1),
        })

    # Re-sort and keep consecutive one-shots varied; keep scene-entry cue times exact.
    sfx_events.sort(key=lambda item: item["start"])
    alternates = {
        "whoosh": "scratch", "scratch": "whoosh",
        "pop": "soft_click", "soft_click": "pop",
        "low_hit": "concrete_thud", "concrete_thud": "low_hit",
        "bass_drop": "low_hit", "heartbeat": "soft_click",
        "air_gasp": "whoosh", "rope_snap": "scratch", "concrete_thud": "low_hit",
    }
    for cue_index in range(1, len(sfx_events)):
        previous, current = sfx_events[cue_index - 1], sfx_events[cue_index]
        if current["file"] == previous["file"]:
            alternate = alternates.get(str(current["file"]), "soft_click")
            current["file"] = alternate
            current["path"] = str(sound_paths[alternate])
            current["duration"] = round(min(
                ffprobe_duration(sound_paths[alternate]), max(0.08, duration - float(current["start"]))
            ), 3)
    settings["sound_effects"] = [
        {"path": item["path"], "start": item["start"], "duration": item["duration"], "volume": item["volume"]}
        for item in sfx_events
    ]

    flash_path = PROJECT / "assets" / "generated" / "white_flash.png"
    Image.new("RGB", (1920, 1080), (255, 255, 255)).save(flash_path, optimize=True)
    horror_path = make_horror_overlay()
    horror_phrases = ["HEAD FIRST", "NO PULSE", "ROPE SNAPPED", "DECLARED DEAD", "CONCRETE"]
    horror_times = []
    for phrase in horror_phrases:
        match = find_phrase(tokens, phrase)
        if match and 0 <= float(match[0]) < duration:
            horror_times.append(round(float(match[0]), 3))
    death_match = find_phrase(tokens, "DECLARED DEAD")
    flash_times = [round(float(death_match[0]), 3)] if death_match and float(death_match[0]) < duration else []
    config = {
        "project_name": "Nutty Putty Cave — Horror Story",
        "drafts_dir": "",
        "audio": str(master_audio),
        "scene_images": [str(item) for item in scene_images],
        "scene_texts": scene_texts,
        "presenter_images": [str(item) for item in presenter_images],
        "canvas": {"width": 1920, "height": 1080, "fps": 30, "ratio": "16:9"},
        "storyboard_boundaries": boundaries,
        "story_beats": [
            {"scene_id": "story_%03d" % (index + 1), "text": row["text"],
             "start_s": row["start_s"], "end_s": row["end_s"],
             "emotion": BEAT_META[index][0], "shock_level": BEAT_META[index][1],
             "trigger_word": BEAT_META[index][2], "stock_query": STOCK_QUERIES[index]}
            for index, row in enumerate(rows)
        ],
        "chapter_titles": chapters,
        "background_music": {"path": str(music_path.resolve()), "start": 0.0,
                              "duration": round(duration, 3), "volume": 0.16},
        "settings": settings,
    }
    config["settings"]["icon_overlays"] = overlays
    config["settings"]["callout_overlays"] = fact_overlays
    config["settings"]["flash_overlay_path"] = str(flash_path.resolve())
    config["settings"]["flash_times"] = flash_times
    config["settings"]["horror_overlay_path"] = str(horror_path)
    config["settings"]["horror_overlay_times"] = horror_times
    (PROJECT / "project.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (PROJECT / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    source_origins = {}
    for group in source_map.values():
        for entry in group:
            source_origins[str(Path(entry["local"]).resolve())] = entry["original"]
    catalog = []
    for image in source_images:
        try:
            catalog.append(inventory_asset(image, "story_art_original", source_origins.get(str(image.resolve()), "")))
        except Exception as exc:
            catalog.append({"id": image.name, "path": str(image), "type": "story_art_original", "problem": str(exc)})
    for image in fullframe_images:
        catalog.append(inventory_asset(image, "story_art_16x9"))
    for image in presenter_images:
        try:
            item = inventory_asset(image, "host_avatar_pose", source_origins.get(str(image.resolve()), ""))
            item["tags"] = ["host_avatar", "pose category based on filename; visual confirmation needed"]
            item["confidence"] = "low"
            catalog.append(item)
        except Exception as exc:
            catalog.append({"id": image.name, "path": str(image), "type": "host_avatar_pose", "problem": str(exc)})
    catalog.append(inventory_asset(source_audio, "voiceover_source", str(AUDIO_SOURCE)))
    catalog.append(inventory_asset(master_audio, "voiceover_master", str(AUDIO_SOURCE)))
    catalog.append(inventory_asset(horror_path, "horror_tint_overlay"))
    catalog.append(inventory_asset(flash_path.resolve(), "white_flash_overlay"))
    if intro_path and intro_path.is_file():
        catalog.append(inventory_asset(intro_path, "remotion_motion_graphic"))
    for path in sorted((PROJECT / "assets" / "audio" / "sfx").glob("*.wav")):
        catalog.append(inventory_asset(path, "music" if path.name == "suspense_bed.wav" else "sfx"))
    for path in sorted((PROJECT / "assets" / "generated" / "icons").glob("*.png")):
        catalog.append(inventory_asset(path, "procedural_chapter_icon"))
    for path in sorted((PROJECT / "assets" / "generated" / "callouts").glob("*.png")):
        catalog.append(inventory_asset(path, "story_fact_callout"))
    for path in sorted((PROJECT / "assets" / "icons").glob("*.svg")):
        catalog.append({
            "id": path.stem, "path": str(path.resolve()), "type": "lucide_icon_source",
            "size_bytes": path.stat().st_size, "dimensions": None, "duration_s": None,
            "alpha_channel": True, "tags": ["Lucide SVG", "ISC license in assets/icons/LUCIDE-LICENSE.txt"],
            "description": "SVG source for a chapter badge", "confidence": "high",
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    hashes: dict[str, list[str]] = {}
    for item in catalog:
        if item.get("sha256"):
            hashes.setdefault(item["sha256"], []).append(item["path"])
    duplicates = [paths for paths in hashes.values() if len(paths) > 1]
    unreadable = [item for item in catalog if item.get("problem")]
    catalog_doc = {
        "version": 1, "project": "Nutty Putty Cave",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "asset_count": len(catalog),
        "counts_by_type": {kind: sum(item.get("type") == kind for item in catalog)
                           for kind in sorted({str(item.get("type", "unknown")) for item in catalog})},
        "duplicates": duplicates, "unreadable": unreadable,
        "visual_review_status": "Contact sheet created, but script does not claim automatic semantic recognition of the supplied pixels.",
        "assets": catalog,
    }
    (PROJECT / "build" / "ASSET_CATALOG.json").write_text(json.dumps(catalog_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    timeline = create_story_timeline(STORY_EN, rows, tokens, scene_images, boundaries, chapters, duration, timing_mode, sfx_events)
    timeline["asset_count"] = len(catalog)
    timeline["caption_count"] = 0
    timeline["narration_caption_cues_generated_but_not_overlaid"] = len(captions)
    timeline["arabic_subtitle_count"] = len(arabic_captions)
    timeline["arabic_subtitle_file"] = str((PROJECT / "build" / "captions_ar.srt").resolve())
    timeline["icon_overlays"] = overlays
    timeline["callout_overlays"] = fact_overlays
    timeline["critical_horror_tint_times_s"] = horror_times
    timeline["white_flash_times_s"] = flash_times
    timeline["source_image_count"] = len(source_images)
    (PROJECT / "build" / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (PROJECT / "build" / "SFX_Cue_Sheet.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["start", "end", "label", "file", "volume", "volume_db", "path"])
        writer.writeheader()
        for item in sfx_events:
            writer.writerow({"start": item["start"], "end": round(item["start"] + item["duration"], 3),
                             "label": item["label"], "file": item["file"], "volume": item["volume"],
                             "volume_db": item["volume_db"], "path": item["path"]})
    missing = {
        "items": [
            {"asset": "cave passage cross-section", "status": "confirm the closest supplied image on the contact sheet",
             "prompt": "16:9 flat-vector 2D educational illustration of a twisting narrow Utah limestone cave passage, clean cream background, 3-5 px black outline, muted earth tones, no text or watermark."},
            {"asset": "rescue pulley and rope", "status": "confirm whether supplied art contains this detail",
             "prompt": "16:9 flat-vector 2D rescue pulley and rope under tension in a narrow cave, clear bold silhouette, controlled dark palette, no gore, no text."},
            {"asset": "sealed cave entrance", "status": "confirm whether supplied art contains the final sealed entrance",
             "prompt": "16:9 flat-vector 2D cave entrance sealed by a smooth concrete plug, solemn cream and charcoal palette, simple strong shapes, 3-5 px black outline, no text."},
        ],
        "policy": "No third-party historical press photos were mixed into the flat-vector 2D style. If a key illustration is missing, the prompt above is ready for generation after visual review.",
    }
    (PROJECT / "build" / "MISSING_ASSETS.json").write_text(json.dumps(missing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = [
        "# Asset catalog summary", "",
        "- Supplied story images: " + str(len(source_images)),
        "- 16:9 processed story images: " + str(len(fullframe_images)),
        "- Presenter pose images: " + str(len(presenter_images)),
        "- Voiceover source and normalized master: 2",
        "- Original synthesized SFX: " + str(len(sound_paths)),
        "- Suspense music beds: 1",
        "- Locally drawn chapter icons rendered: " + str(len(overlays)),
        "- Animated fact callouts generated: " + str(len(fact_overlays)),
        "- Remotion title clip rendered: " + ("yes" if intro_path else "no"),
        "- Exact duplicate groups detected by SHA-256: " + str(len(duplicates)),
        "- Unreadable media files: " + str(len(unreadable)),
        "- Word alignment: " + timing_mode,
        "",
        "Check ASSET_CONTACT_SHEET.jpg before publication. Pose labels and story-to-image matches remain low-confidence until a human visually confirms the supplied files.",
    ]
    (PROJECT / "build" / "ASSET_CATALOG_SUMMARY.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    (PROJECT / "build" / "QA_REPORT.md").write_text(
        "# Nutty Putty Cave — initial preparation QA\n\n"
        "- Prepared local copies of all supplied source images, presenter poses and narration.\n"
        "- Created an audio master with high-pass, gentle compression and loudness normalization.\n"
        "- Story text remains the caption authority; cached local Whisper is used only if already installed with its model, otherwise timings are estimated.\n"
        "- Created a flat-vector Remotion title clip when rendering dependencies were available.\n"
        "- Generated original SFX on scene entrances and story impacts, plus a suspense bed with pre-shock dips.\n"
        "- Chapter icons are drawn locally with Pillow; no icon or model downloads are attempted.\n"
        "- Motion style: hybrid whiteboard/card scenes with occasional full-bleed action beats, continuous sub-second pulse/drift, alternating push/pull, and rare scale-pop transitions.\n"
        "- IMPORTANT: source frames have not been semantically classified by a vision model in this script. Review ASSET_CONTACT_SHEET.jpg and the first 10 seconds, rope-snap section, sealed-cave ending and final teaser in CapCut.\n"
        "- Music is an original synthesized suspense bed, not a third-party track. Check audio meters in CapCut before publishing.\n",
        encoding="utf-8",
    )
    log("Project prepared at: " + str(PROJECT))
    log("Voiceover duration: " + str(round(duration, 2)) + " seconds; " + timing_mode)
    log("Images: " + str(len(source_images)) + "; presenter poses: " + str(len(presenter_images)) +
        "; icons rendered: " + str(len(overlays)) + "; timed sound cues: " + str(len(sfx_events)))
    log("Contact sheet: " + str(PROJECT / "build" / "ASSET_CONTACT_SHEET.jpg"))
    log("Next step: close CapCut, then let run_nutty_putty.ps1 build the editable draft.")
    return 0


def finalize(build_exit_code: int, project_override: str | None = None) -> int:
    project = Path(project_override).expanduser() if project_override else PROJECT
    if not project.is_absolute():
        project = ROOT / project
    build_dir = project / "build"
    timeline_path = build_dir / "timeline.json"
    timeline = json.loads(timeline_path.read_text(encoding="utf-8-sig")) if timeline_path.is_file() else {}
    scene_csv = build_dir / "scene_timing.csv"
    rows = []
    if scene_csv.is_file():
        with scene_csv.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    for row in rows:
        for key in ("start", "end", "duration"):
            try:
                row[key + "_s"] = round(float(row.pop(key)), 3)
            except (ValueError, TypeError):
                pass
    timeline["rendered_shots"] = rows
    timeline["build_exit_code"] = build_exit_code
    timeline["build_status"] = "built" if build_exit_code == 0 and rows else "failed or incomplete"
    if rows:
        timeline_path.write_text(json.dumps(timeline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    durations = []
    for row in rows:
        try:
            durations.append(float(row.get("duration_s", 0)))
        except (ValueError, TypeError):
            pass
    config = json.loads((project / "project.json").read_text(encoding="utf-8-sig"))
    catalog = json.loads((build_dir / "ASSET_CATALOG.json").read_text(encoding="utf-8-sig"))
    qa = [
        "# Nutty Putty Cave — QA report", "",
        "- Build status: " + ("PASS: editable CapCut draft was created." if build_exit_code == 0 and rows else "INCOMPLETE: inspect the build log and CapCut CLI report."),
        "- Canvas: 1920x1080, 30 fps, 16:9.",
        "- Narration duration: " + str(timeline.get("voiceover_duration_s", "unknown")) + " seconds.",
        "- Timing source: " + str(timeline.get("timing_mode", "not recorded")) + ".",
        "- Supplied story images: " + str(len([a for a in catalog["assets"] if a.get("type") == "story_art_original"])),
        "- Rendered timeline shots: " + str(len(rows)),
        "- Longest rendered shot: " + (str(round(max(durations), 2)) + " seconds" if durations else "not available"),
        "- Presenter poses: " + str(len([a for a in catalog["assets"] if a.get("type") == "host_avatar_pose"])),
        "- Timed English caption cues on timeline: " + str(timeline.get("caption_count", "not recorded")),
        "- Full-sentence narration captions: disabled; short impact callouts and chapter titles only.",
        "- Scene entrance SFX cues: " + str(sum(1 for item in timeline.get("sound_effect_events", []) if str(item.get("label", "")).startswith("Scene entrance"))),
        "- Visual rhythm: hybrid whiteboard/card layouts with full-bleed action beats, sub-second zoom pulses and position drift.",
        "- Arabic subtitle cues (separate SRT, not placed on timeline): " + str(timeline.get("arabic_subtitle_count", "not recorded")),
        "- Chapter titles: " + str(len(config.get("chapter_titles", []))),
        "- Story fact callouts: " + str(len(config.get("settings", {}).get("callout_overlays", []))),
        "- Critical horror tint moments: " + str(len(config.get("settings", {}).get("horror_overlay_times", []))),
        "- White flash hits (kept rare): " + str(len(config.get("settings", {}).get("flash_times", []))),
        "- Local sound effects on timeline: " + str(len(config.get("settings", {}).get("sound_effects", []))),
        "- Chapter icons on timeline: " + str(len(config.get("settings", {}).get("icon_overlays", []))),
        "- Music bed: original synthesized low suspense bed with brief pre-shock dips.",
        "- Transitions: hard cuts by default, a keyframed scale-pop accent about every 14th shot, and a rare white flash at the declared-dead beat; no wipes, spins, cubes or glitch presets.",
        "- Important: the contact sheet aids visual review, but the script cannot confirm that every illustration depicts the exact sentence. Inspect critical beats before export.",
        "",
        "## Manual visual QA required in CapCut", "",
        "- Check the first two seconds and confirm the topic is immediately visible.",
        "- Check the Corkscrew, gravity / head-first, pulley / rope-snap, no-pulse, sealed cave and final teaser sections.",
        "- Confirm presenter matte, title safe area, short callouts not covering faces, image crop/letterbox, image motion, SFX timing and loudness meters.",
        "- No final rendered MP4 is claimed by this workflow: capcut-cli creates the editable CapCut draft, which must be previewed and exported from CapCut.",
    ]
    if durations and max(durations) > 5.0:
        qa.append("- WARNING: at least one rendered shot exceeds 5 seconds and should be shortened or given internal motion.")
    if not rows:
        qa.append("- WARNING: scene_timing.csv was not created; the build may have stopped before timeline compilation.")
    (build_dir / "QA_REPORT.md").write_text("\n".join(qa) + "\n", encoding="utf-8")
    log("Updated QA report: " + str(build_dir / "QA_REPORT.md"))
    log("Rendered shot count: " + str(len(rows)))
    # QA generation succeeded even when CapCut build failed; the PowerShell runner
    # checks the recorded build exit code separately and reports the correct failure.
    return 0


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Prepare or finalize the Nutty Putty Cave CapCut project.")
    parser.add_argument("--stage", choices=("prepare", "finalize"), default="prepare")
    parser.add_argument("--project", default=None)
    parser.add_argument("--build-exit-code", type=int, default=0)
    parser.add_argument("--simple", action="store_true",
                        help="Images + original narration only; skip title render, Whisper, music and sound effects.")
    args = parser.parse_args()
    if args.stage == "prepare":
        return prepare(args.project, simple=args.simple)
    return finalize(args.build_exit_code, args.project)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        log("ERROR: " + str(exc))
        raise SystemExit(1)
