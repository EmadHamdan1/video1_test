from __future__ import annotations

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


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8-sig") as handle:
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


def transcribe_if_available(audio: Path, settings: dict[str, Any]) -> tuple[list[dict[str, Any]], Path | None]:
    if not settings.get("transcribe_if_whisper_available", True):
        log("Whisper transcription is disabled in config.json.")
        return [], None

    whisper = shutil.which("whisper")
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


def make_spec(
    config: dict[str, Any],
    audio: Path,
    images: list[Path],
    presenters: list[Path],
    duration: float,
    captions: list[dict[str, Any]],
    captions_path: Path | None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    settings = config.get("settings", {})
    target = max(1.0, float(settings.get("target_shot_seconds", 4.2)))
    minimum = max(0.75, float(settings.get("minimum_shot_seconds", 1.6)))
    shot_count = max(1, max(len(images), int(round(duration / target))))
    feasible = max(1, int(duration / minimum))
    if shot_count > feasible:
        shot_count = feasible
        log(
            "The narration is short relative to the number of scene images. "
            + str(len(images) - min(len(images), shot_count))
            + " image(s) will be omitted to avoid excessively fast cuts."
        )
    shot_count = min(shot_count, max(1, int(math.ceil(duration / 0.45))))
    boundaries = scene_boundaries(duration, shot_count, target, minimum, captions)
    indices = choose_scene_indices(len(images), shot_count)

    video_items: list[dict[str, Any]] = []
    scene_rows: list[dict[str, Any]] = []
    scene_refs: list[str] = []
    for index, image_index in enumerate(indices):
        start = boundaries[index]
        end = boundaries[index + 1]
        shot_duration = max(0.25, end - start)
        path = images[image_index]
        ref = "scene_" + str(index + 1).zfill(3)
        scene_refs.append(ref)
        video_items.append({
            "type": "photo",
            "path": str(path),
            "start": round(start, 3),
            "duration": round(shot_duration, 3),
            "ref": ref,
        })
        contextual = ""
        midpoint = (start + end) / 2
        for cue in captions:
            if float(cue["start"]) <= midpoint <= float(cue["end"]):
                contextual = str(cue["text"])
                break
        scene_rows.append({
            "start": start,
            "end": end,
            "duration": shot_duration,
            "image": str(path),
            "caption_context": contextual,
            "scene_ref": ref,
        })

    operations: list[dict[str, Any]] = []
    zoom_start = float(settings.get("scene_zoom_start", 1.0))
    zoom_end = float(settings.get("scene_zoom_end", 1.1))
    transition_slug = str(settings.get("transition_slug", "mix"))
    transition_duration = float(settings.get("transition_seconds", 0.34))
    for index, shot in enumerate(scene_rows):
        ref = str(shot["scene_ref"])
        seconds = round(float(shot["duration"]), 3)
        # Subtle zoom plus a small pan. The direction alternates to avoid a mechanical loop.
        pan_end = 0.035 if index % 2 == 0 else -0.035
        zoom_finish = zoom_end if index % 3 != 2 else max(zoom_start, zoom_end - 0.025)
        operations.extend([
            {"op": "keyframe", "target": ref, "property": "scale_x", "time": 0.0,
             "value": zoom_start, "easing": "ease-in-out"},
            {"op": "keyframe", "target": ref, "property": "scale_x", "time": seconds,
             "value": zoom_finish, "easing": "ease-in-out"},
            {"op": "keyframe", "target": ref, "property": "scale_y", "time": 0.0,
             "value": zoom_start, "easing": "ease-in-out"},
            {"op": "keyframe", "target": ref, "property": "scale_y", "time": seconds,
             "value": zoom_finish, "easing": "ease-in-out"},
            {"op": "keyframe", "target": ref, "property": "position_x", "time": 0.0,
             "value": -pan_end, "easing": "ease-in-out"},
            {"op": "keyframe", "target": ref, "property": "position_x", "time": seconds,
             "value": pan_end, "easing": "ease-in-out"},
        ])
        if index < len(scene_rows) - 1 and transition_duration > 0:
            operations.append({
                "op": "transition",
                "target": ref,
                "slug": transition_slug,
                "duration": transition_duration,
            })

    presenter_items: list[dict[str, Any]] = []
    presenter_rows: list[dict[str, Any]] = []
    if presenters and settings.get("presenter_overlay", True) and duration >= 4.0:
        interval = max(5.0, float(settings.get("presenter_interval_seconds", 8.0)))
        count = min(len(presenters), max(1, int(duration // interval)))
        appearance_duration = min(
            float(settings.get("presenter_duration_seconds", 3.2)),
            max(1.4, duration / max(1.0, count) * 0.62),
            duration,
        )
        for index in range(count):
            pose_index = round(index * (len(presenters) - 1) / max(1, count - 1))
            path = presenters[pose_index]
            start = duration * (index + 1) / (count + 1) - appearance_duration / 2
            start = max(0.0, min(start, max(0.0, duration - appearance_duration)))
            side = -1 if index % 2 == 0 else 1
            x = side * 0.34
            ref = "presenter_" + str(index + 1).zfill(2)
            presenter_items.append({
                "type": "photo",
                "path": str(path),
                "start": round(start, 3),
                "duration": round(appearance_duration, 3),
                "ref": ref,
                "scale": float(settings.get("presenter_scale", 0.42)),
                "x": x,
                "y": 0.22,
            })
            presenter_rows.append({
                "start": start,
                "end": start + appearance_duration,
                "image": str(path),
                "ref": ref,
                "side": "left" if side < 0 else "right",
            })
            operations.extend([
                {"op": "keyframe", "target": ref, "property": "uniform_scale",
                 "time": 0.0, "value": float(settings.get("presenter_scale", 0.42)),
                 "easing": "ease-in-out"},
                {"op": "keyframe", "target": ref, "property": "uniform_scale",
                 "time": round(appearance_duration, 3),
                 "value": float(settings.get("presenter_scale", 0.42)) + 0.015,
                 "easing": "ease-in-out"},
            ])

    audio_track_items = [{
        "path": str(audio),
        "start": 0.0,
        "duration": round(duration, 3),
        "volume": float(settings.get("voice_volume", 0.96)),
        "ref": "voiceover",
    }]
    sfx_items: list[dict[str, Any]] = []
    for index, item in enumerate(settings.get("sound_effects", [])):
        raw_path = item.get("path", "")
        path = Path(os.path.expandvars(str(raw_path))).expanduser()
        if not path.is_file():
            log("Optional local SFX path was not found; skipped: " + str(raw_path))
            continue
        try:
            start = max(0.0, float(item.get("start", 0.0)))
            sound_duration = float(item.get("duration", 0.0))
            if sound_duration <= 0:
                sound_duration = min(5.0, max(0.3, duration - start))
            if start >= duration:
                continue
            sfx_items.append({
                "path": str(path.resolve()),
                "start": round(start, 3),
                "duration": round(min(sound_duration, duration - start), 3),
                "volume": float(item.get("volume", 0.16)),
                "ref": "local_sfx_" + str(index + 1).zfill(2),
            })
        except (TypeError, ValueError):
            log("Invalid optional SFX entry skipped: " + str(item))

    if settings.get("add_captions_when_transcribed", True) and captions_path and captions:
        operations.append({
            "op": "captions",
            "path": captions_path.name,
            "trackName": "Captions",
            "timeOffset": 0.0,
        })

    operations.append({
        "op": "audio-fade",
        "target": "voiceover",
        "fadeIn": float(settings.get("voice_fade_in", 0.12)),
        "fadeOut": float(settings.get("voice_fade_out", 0.65)),
    })

    tracks: list[dict[str, Any]] = [
        {"type": "video", "name": "Scene Images", "items": video_items},
        {"type": "audio", "name": "Voiceover", "items": audio_track_items},
    ]
    if presenter_items:
        tracks.insert(1, {"type": "video", "name": "Presenter Overlay", "items": presenter_items})
    if sfx_items:
        tracks.append({"type": "audio", "name": "Local Sound Effects", "items": sfx_items})

    canvas = config.get("canvas", {})
    spec: dict[str, Any] = {
        "name": str(config.get("project_name", "Video1 Test - Professional Montage")),
        "width": int(canvas.get("width", 1920)),
        "height": int(canvas.get("height", 1080)),
        "fps": int(canvas.get("fps", 30)),
        "ratio": str(canvas.get("ratio", "16:9")),
        "tracks": tracks,
        "operations": operations,
    }
    return spec, scene_rows, presenter_rows


def write_scene_csv(path: Path, scenes: list[dict[str, Any]], presenters: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["start", "end", "duration", "image", "caption_context", "presenter_ref"],
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


def main() -> int:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    config = load_config()
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
    folder_name = "Video1_Montage_" + stamp
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
    try:
        payload = json.loads(output_text) if output_text else {}
    except json.JSONDecodeError:
        for line in reversed(output_text.splitlines()):
            try:
                payload = json.loads(line)
                break
            except json.JSONDecodeError:
                continue

    draft_path = Path(str(payload.get("draft_path", out_dir))).resolve()
    refs = payload.get("refs", {}) if isinstance(payload.get("refs", {}), dict) else {}
    matting_results: list[dict[str, str]] = []
    if settings.get("presenter_smart_matte", True) and presenter_rows:
        for presenter in presenter_rows:
            segment_id = refs.get(str(presenter["ref"]))
            if not segment_id:
                matting_results.append({"ref": str(presenter["ref"]), "status": "missing segment id"})
                continue
            matte = subprocess.run(
                [capcut, "matting", str(draft_path), str(segment_id)],
                text=True, capture_output=True, env=env, check=False,
            )
            okay = matte.returncode == 0
            matting_results.append({
                "ref": str(presenter["ref"]),
                "status": "applied" if okay else "not applied",
                "detail": (matte.stderr or matte.stdout or "").strip()[-500:],
            })
            if not okay:
                log("Smart matting did not apply to " + str(presenter["ref"]) + "; check this pose in CapCut.")

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
        "caption_cues": len(captions),
        "caption_file": str(captions_path) if captions_path else None,
        "matting": matting_results,
        "warnings": payload.get("warnings", []),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "notes": [
            "This is an editable CapCut draft, not a rendered MP4.",
            "Scene timing can snap to Whisper caption ends, but semantic image matching still needs human review.",
            "The sound-effects cue sheet contains suggestions only; it does not claim that library SFX were automatically inserted.",
        ],
    }
    (BUILD_DIR / "build_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    log("Draft creation finished.")
    log("Draft directory: " + str(draft_path))
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
