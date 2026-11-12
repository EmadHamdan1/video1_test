from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable

AUDIO_EXTENSIONS = {
    ".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac", ".aiff", ".aif", ".wma"
}

# Filename matching is deliberately conservative. A file is selected only when
# its name contains a useful category hint; otherwise the caller uses a safe fallback.
CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "whoosh": ("whoosh", "swoosh", "swish", "paper", "slide", "sweep", "swipe", "transition"),
    "pop": ("pop", "plop", "bubble", "blip", "tap"),
    "scratch": ("scratch", "rewind", "vinyl", "record", "scrape", "brake", "stop"),
    "bass_drop": ("bass drop", "bass", "sub drop", "low boom", "cinematic boom", "boom"),
    "heartbeat": ("heartbeat", "heart beat", "pulse", "heart monitor", "monitor beep"),
    "air_gasp": ("gasp", "breath", "inhale", "air gasp", "breathing"),
    "low_hit": ("low hit", "low impact", "thump", "impact", "punch", "hit", "slam"),
    "rope_snap": ("rope", "snap", "crack", "break", "whip"),
    "soft_click": ("soft click", "click", "camera", "shutter", "button", "type", "paper tap"),
    "concrete_thud": ("concrete", "stone", "heavy thud", "thud", "heavy slam", "door slam"),
}


def _normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def _candidate_dirs(repo_root: Path, project_dir: Path, audio_source: Path) -> list[Path]:
    home = Path.home()
    return [
        audio_source.parent / "Saoud_SFX_Pack",
        repo_root / "Saoud_SFX_Pack",
        repo_root / "assets" / "Saoud_SFX_Pack",
        project_dir / "Saoud_SFX_Pack",
        project_dir / "assets" / "audio" / "Saoud_SFX_Pack",
        home / "Downloads" / "Saoud_SFX_Pack",
        home / "Desktop" / "Saoud_SFX_Pack",
        home / "Music" / "Saoud_SFX_Pack",
    ]


def find_sfx_pack(repo_root: Path, project_dir: Path, audio_source: Path) -> Path | None:
    """Find the named local pack without uploading or copying the original folder."""
    override = os.environ.get("SAOUD_SFX_PACK", "").strip()
    if override:
        configured = Path(os.path.expandvars(override)).expanduser()
        if configured.is_dir():
            return configured.resolve()

    candidates = _candidate_dirs(repo_root, project_dir, audio_source)
    for candidate in candidates:
        if candidate.is_dir():
            return candidate.resolve()

    # Also support the folder being placed one level below the repository or
    # beside the source narration, while avoiding a broad whole-drive scan.
    parents = {repo_root, repo_root.parent, project_dir, project_dir.parent, audio_source.parent}
    for parent in parents:
        if not parent.is_dir():
            continue
        try:
            matches = [
                item for item in parent.iterdir()
                if item.is_dir() and "saoud" in item.name.lower() and "sfx" in item.name.lower()
            ]
        except OSError:
            continue
        if matches:
            return sorted(matches, key=lambda item: item.name.lower())[0].resolve()
    return None


def discover_audio_files(pack_dir: Path | None) -> list[Path]:
    if pack_dir is None or not pack_dir.is_dir():
        return []
    results: list[Path] = []
    try:
        for item in pack_dir.rglob("*"):
            if not item.is_file() or item.suffix.lower() not in AUDIO_EXTENSIONS:
                continue
            if item.name.startswith("."):
                continue
            try:
                if item.stat().st_size < 1024:
                    continue
            except OSError:
                continue
            results.append(item.resolve())
    except OSError:
        return []
    return sorted(results, key=lambda item: str(item).lower())


def _score_name(stem: str, keywords: Iterable[str]) -> int:
    normal = _normalise(stem)
    tokens = set(normal.split())
    score = 0
    for keyword in keywords:
        term = _normalise(keyword)
        if not term:
            continue
        if term == normal:
            score += 30
        elif " " in term and term in normal:
            score += 12
        elif term in tokens:
            score += 8
        elif term in normal:
            score += 3
    return score


def select_sfx_sources(files: list[Path]) -> dict[str, Path]:
    """Map distinct pack files to sound roles using filenames, deterministically."""
    available = [Path(item) for item in files if Path(item).is_file()]
    used: set[Path] = set()
    selected: dict[str, Path] = {}

    # Process more distinctive categories before broad impact/click synonyms.
    order = (
        "rope_snap", "heartbeat", "air_gasp", "concrete_thud", "scratch",
        "whoosh", "bass_drop", "low_hit", "soft_click", "pop",
    )
    for kind in order:
        ranked = sorted(
            (
                (_score_name(path.stem, CATEGORY_KEYWORDS[kind]), path)
                for path in available if path not in used
            ),
            key=lambda item: (-item[0], str(item[1]).lower()),
        )
        if not ranked or ranked[0][0] <= 0:
            continue
        selected[kind] = ranked[0][1]
        used.add(ranked[0][1])

    return selected
