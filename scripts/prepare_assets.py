from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECTS_DIR = ROOT / "projects"
ENV_FILE = ROOT / ".env"
USER_AGENT = "Video1-Montage-Asset-Helper/1.0 (personal local video workflow)"
MAX_DOWNLOAD_BYTES = 80 * 1024 * 1024
_OPENVERSE_TOKEN_CACHE: str | None = None
_OPENVERSE_TOKEN_EXPIRES_AT = 0.0
MANIFEST_FIELDS = [
    "id", "kind", "segment_id", "query", "title", "creator", "source",
    "license", "license_url", "source_page", "preview_url", "download_url",
    "selected", "downloaded_path", "downloaded_at", "license_reviewed", "review_notes",
    "start_seconds", "volume", "notes",
]
STOP_WORDS = {
    "the", "and", "for", "with", "from", "that", "this", "then", "than",
    "into", "when", "where", "what", "which", "who", "whom", "were", "was",
    "are", "is", "be", "been", "being", "have", "has", "had", "will", "would",
    "could", "should", "can", "may", "might", "not", "but", "about", "after",
    "before", "over", "under", "very", "more", "most", "some", "such", "their",
    "there", "they", "them", "its", "his", "her", "our", "your", "you", "she",
    "him", "how", "why", "all", "any", "each", "one", "two", "as", "at", "by",
    "of", "on", "in", "to", "up", "out", "off", "a", "an", "i", "it", "we",
}
LICENSE_FIELDS = ("LicenseShortName", "LicenseUrl", "UsageTerms", "Artist", "Credit", "ImageDescription")


def log(message: str) -> None:
    print("[assets] " + message, flush=True)


def load_env_file(path: Path = ENV_FILE) -> None:
    """Load KEY=value lines without replacing environment variables already set."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            os.environ.setdefault(key, value)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        slug = "project-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    return slug[:64].strip("-") or "new-project"


def clean_text(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def safe_web_url(value: Any, *, allow_file: bool = False) -> str:
    """Allow only safe external HTTP(S) links, plus file URLs for gallery-local previews."""
    raw = str(value or "").strip()
    if not raw:
        return ""
    parsed = urllib.parse.urlparse(raw)
    allowed = {"http", "https"} | ({"file"} if allow_file else set())
    if parsed.scheme.lower() not in allowed:
        return ""
    if parsed.scheme.lower() in {"http", "https"} and not parsed.netloc:
        return ""
    if parsed.scheme.lower() == "file" and not allow_file:
        return ""
    return raw


def safe_ext(url: str, content_type: str = "", kind: str = "image") -> str:
    extension = Path(urllib.parse.urlparse(url).path).suffix.lower()
    allowed = {
        "image": {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"},
        "video": {".mp4", ".mov", ".webm"},
        "audio": {".mp3", ".wav", ".ogg", ".flac", ".m4a"},
        "icon": {".svg"},
    }
    if extension in allowed.get(kind, set()):
        return extension
    content_type = content_type.split(";", 1)[0].strip().lower()
    mapping = {
        "image/jpeg": ".jpg", "image/jpg": ".jpg", "image/png": ".png",
        "image/webp": ".webp", "image/gif": ".gif", "image/svg+xml": ".svg",
        "image/avif": ".avif", "video/mp4": ".mp4", "video/quicktime": ".mov",
        "video/webm": ".webm", "audio/mpeg": ".mp3", "audio/mp3": ".mp3",
        "audio/wav": ".wav", "audio/ogg": ".ogg", "audio/flac": ".flac", "audio/mp4": ".m4a",
    }
    mapped = mapping.get(content_type, "")
    if mapped in allowed.get(kind, set()):
        return mapped
    fallback = {"image": ".jpg", "video": ".mp4", "audio": ".mp3", "icon": ".svg"}
    return fallback.get(kind, ".bin")


def request_json(url: str, headers: dict[str, str] | None = None, timeout: int = 25) -> dict[str, Any]:
    request_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    request_headers.update(headers or {})
    request = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read(12 * 1024 * 1024)
    result = json.loads(raw.decode("utf-8", errors="replace"))
    if not isinstance(result, dict):
        raise ValueError("API returned an unexpected JSON shape.")
    return result


def openverse_token() -> str | None:
    global _OPENVERSE_TOKEN_CACHE, _OPENVERSE_TOKEN_EXPIRES_AT
    if _OPENVERSE_TOKEN_CACHE and time.monotonic() < _OPENVERSE_TOKEN_EXPIRES_AT - 60:
        return _OPENVERSE_TOKEN_CACHE
    client_id = os.environ.get("OPENVERSE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("OPENVERSE_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return None
    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }).encode()
    request = urllib.request.Request(
        "https://api.openverse.org/v1/auth_tokens/token/",
        data=data,
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        payload = json.loads(response.read(1024 * 1024).decode("utf-8", errors="replace"))
    token = payload.get("access_token")
    if token:
        _OPENVERSE_TOKEN_CACHE = str(token)
        _OPENVERSE_TOKEN_EXPIRES_AT = time.monotonic() + float(payload.get("expires_in", 3600))
        return _OPENVERSE_TOKEN_CACHE
    return None


def get_openverse_results(kind: str, query: str, limit: int) -> list[dict[str, Any]]:
    endpoint = "images" if kind == "image" else "audio"
    params = urllib.parse.urlencode({
        "q": query, "page_size": min(max(1, limit), 20), "mature": "false",
    })
    headers: dict[str, str] = {}
    try:
        token = openverse_token()
    except Exception as exc:
        log("Openverse credentials were not accepted; trying anonymous search: " + str(exc))
        token = None
    if token:
        headers["Authorization"] = "Bearer " + token
    payload = request_json("https://api.openverse.org/v1/" + endpoint + "/?" + params, headers)
    return [item for item in payload.get("results", []) if isinstance(item, dict)]


def commons_results(query: str, limit: int) -> list[dict[str, Any]]:
    params = {
        "action": "query",
        "format": "json",
        "origin": "*",
        "generator": "search",
        "gsrsearch": "filetype:bitmap " + query,
        "gsrnamespace": "6",
        "gsrlimit": str(min(max(1, limit), 20)),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": "1000",
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    payload = request_json(url, {"Accept": "application/json"})
    pages = payload.get("query", {}).get("pages", {})
    results = []
    for page in pages.values() if isinstance(pages, dict) else []:
        info_list = page.get("imageinfo", [])
        if not info_list:
            continue
        info = info_list[0]
        meta = info.get("extmetadata", {}) or {}
        def meta_value(name: str) -> str:
            item = meta.get(name, {})
            if isinstance(item, dict):
                return clean_text(item.get("value", ""))
            return clean_text(item)
        page_id = page.get("pageid", "")
        results.append({
            "provider": "Wikimedia Commons",
            "title": clean_text(page.get("title", "")),
            "creator": meta_value("Artist"),
            "license": meta_value("LicenseShortName") or meta_value("UsageTerms") or "Unverified / inspect source page",
            "license_url": meta_value("LicenseUrl"),
            "source_page": "https://commons.wikimedia.org/?curid=" + str(page_id),
            "preview_url": info.get("thumburl", info.get("url", "")),
            "download_url": info.get("url", ""),
            "notes": "Review file page, attribution requirements and any non-copyright restrictions.",
        })
    return results


def pixabay_results(kind: str, query: str, limit: int) -> list[dict[str, Any]]:
    key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not key:
        return []
    if kind not in {"image", "video"}:
        return []
    endpoint = "videos" if kind == "video" else ""
    base = "https://pixabay.com/api/" + (endpoint + "/" if endpoint else "")
    params = {
        "key": key,
        "q": query,
        "per_page": str(min(max(3, limit), 20)),
        "safesearch": "true",
    }
    if kind == "image":
        params["image_type"] = "photo"
    payload = request_json(base + "?" + urllib.parse.urlencode(params))
    results = []
    for item in payload.get("hits", []):
        if kind == "video":
            video_choices = item.get("videos", {}) or {}
            best = video_choices.get("medium") or video_choices.get("small") or video_choices.get("tiny") or {}
            download_url = best.get("url", "")
            preview_url = item.get("userImageURL", "")
        else:
            download_url = item.get("largeImageURL") or item.get("webformatURL", "")
            preview_url = item.get("previewURL", "")
        results.append({
            "provider": "Pixabay",
            "title": clean_text(item.get("tags", query)),
            "creator": clean_text(item.get("user", "")),
            "license": "Pixabay Content License — review current terms",
            "license_url": "https://pixabay.com/service/license-summary/",
            "source_page": item.get("pageURL", "https://pixabay.com/"),
            "preview_url": preview_url,
            "download_url": download_url,
            "notes": "Do not redistribute the source file by itself; review Content License and third-party rights.",
        })
    return results


def pexels_results(kind: str, query: str, limit: int) -> list[dict[str, Any]]:
    key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not key or kind not in {"image", "video"}:
        return []
    endpoint = "videos/search" if kind == "video" else "search"
    params = urllib.parse.urlencode({"query": query, "per_page": min(max(1, limit), 15)})
    payload = request_json(
        "https://api.pexels.com/v1/" + endpoint + "?" + params,
        {"Authorization": key},
    )
    source_items = payload.get("videos" if kind == "video" else "photos", [])
    results = []
    for item in source_items:
        if kind == "image":
            download_url = item.get("src", {}).get("large2x") or item.get("src", {}).get("large", "")
            preview_url = item.get("src", {}).get("medium", "")
            title = "Photo " + str(item.get("id", ""))
            source_page = item.get("url", "https://www.pexels.com/")
            creator = item.get("photographer", "")
        else:
            files = item.get("video_files", [])
            chosen = next((f for f in files if f.get("quality") == "sd" and f.get("file_type") == "video/mp4"), None)
            chosen = chosen or next((f for f in files if f.get("file_type") == "video/mp4"), {})
            download_url = chosen.get("link", "")
            preview_url = item.get("image", "")
            title = "Video " + str(item.get("id", ""))
            source_page = item.get("url", "https://www.pexels.com/videos/")
            creator = item.get("user", {}).get("name", "")
        results.append({
            "provider": "Pexels",
            "title": clean_text(title),
            "creator": clean_text(creator),
            "license": "Pexels License — review current terms",
            "license_url": "https://www.pexels.com/license/",
            "source_page": source_page,
            "preview_url": preview_url,
            "download_url": download_url,
            "notes": "Show a link/credit to Pexels when using API results; do not redistribute media by itself.",
        })
    return results


def freesound_results(query: str, limit: int) -> list[dict[str, Any]]:
    token = os.environ.get("FREESOUND_API_KEY", "").strip()
    if not token:
        return []
    params = urllib.parse.urlencode({
        "query": query,
        "fields": "id,name,username,previews,license,url,description,duration,tags",
        "page_size": min(max(1, limit), 15),
        "sort": "score",
        "token": token,
    })
    payload = request_json("https://freesound.org/apiv2/search/text/?" + params)
    results = []
    for item in payload.get("results", []):
        previews = item.get("previews", {}) or {}
        download_url = previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3", "")
        results.append({
            "provider": "Freesound (preview file)",
            "title": clean_text(item.get("name", "")),
            "creator": clean_text(item.get("username", "")),
            "license": clean_text(item.get("license", "")) or "See sound page",
            "license_url": clean_text(item.get("license", "")),
            "source_page": item.get("url", "https://freesound.org/"),
            "preview_url": download_url,
            "download_url": download_url,
            "notes": "This downloads the API preview, not necessarily the original file; verify license before use.",
        })
    return results


def normalize_candidate(raw: dict[str, Any], kind: str, query: str, segment_id: str) -> dict[str, str]:
    return {
        "id": "",
        "kind": kind,
        "segment_id": segment_id,
        "query": query,
        "title": clean_text(raw.get("title", query)),
        "creator": clean_text(raw.get("creator", "")),
        "source": clean_text(raw.get("provider", raw.get("source", ""))),
        "license": clean_text(raw.get("license", "")) or "Unknown — inspect source page",
        "license_url": str(raw.get("license_url", "") or ""),
        "source_page": str(raw.get("source_page", raw.get("foreign_landing_url", "")) or ""),
        "preview_url": str(raw.get("preview_url", raw.get("thumbnail", "")) or ""),
        "download_url": str(raw.get("download_url", raw.get("url", "")) or ""),
        "selected": "no",
        "downloaded_path": "",
        "downloaded_at": "",
        "license_reviewed": "no",
        "review_notes": "",
        "start_seconds": "",
        "volume": "0.12",
        "notes": clean_text(raw.get("notes", "")),
    }


def search_provider(kind: str, query: str, limit: int, segment_id: str = "") -> list[dict[str, str]]:
    load_env_file()
    raw_results: list[dict[str, Any]] = []
    providers = []
    if kind in {"image", "audio"}:
        try:
            for item in get_openverse_results(kind, query, limit):
                raw_results.append({
                    "provider": "Openverse",
                    "title": item.get("title", ""),
                    "creator": item.get("creator", ""),
                    "license": (str(item.get("license", "")) + (" " + str(item.get("license_version", "")) if item.get("license_version") else "")).strip(),
                    "license_url": item.get("license_url", ""),
                    "source_page": item.get("foreign_landing_url", ""),
                    "preview_url": item.get("thumbnail", ""),
                    "download_url": item.get("url", ""),
                    "notes": item.get("attribution", "") or "Review the source page and the complete license terms.",
                })
            providers.append("Openverse")
        except Exception as exc:
            log("Openverse unavailable for this query: " + str(exc))
    if kind == "image":
        try:
            raw_results.extend(commons_results(query, limit))
            providers.append("Wikimedia Commons")
        except Exception as exc:
            log("Wikimedia Commons unavailable for this query: " + str(exc))
    if kind in {"image", "video"}:
        for provider_name, fn in (("Pixabay", pixabay_results), ("Pexels", pexels_results)):
            try:
                results = fn(kind, query, limit)
                raw_results.extend(results)
                if results:
                    providers.append(provider_name)
            except Exception as exc:
                log(provider_name + " unavailable for this query: " + str(exc))
    if kind == "audio":
        try:
            results = freesound_results(query, limit)
            raw_results.extend(results)
            if results:
                providers.append("Freesound")
        except Exception as exc:
            log("Freesound unavailable for this query: " + str(exc))

    candidates: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw_results:
        source_page = str(item.get("source_page", item.get("foreign_landing_url", "")) or "")
        dedupe = source_page.strip().lower() or (
            clean_text(item.get("title", "")).lower() + "|" + str(item.get("download_url", ""))
        )
        if not dedupe or dedupe in seen:
            continue
        seen.add(dedupe)
        normalized = normalize_candidate(item, kind, query, segment_id)
        # Do not offer direct download for records without an actual media URL.
        if normalized["download_url"] and urllib.parse.urlparse(normalized["download_url"]).scheme not in {"http", "https"}:
            normalized["download_url"] = ""
        candidates.append(normalized)

    if not candidates:
        log("No candidates returned. Add optional API keys in .env for Pixabay/Pexels/Freesound, or try another query.")
    else:
        log("Found " + str(len(candidates)) + " candidate(s) from " + (", ".join(providers) or "available sources") + ".")
    return candidates[: max(limit * 3, limit)]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] = MANIFEST_FIELDS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def project_paths(project: str) -> dict[str, Path]:
    project_path = Path(project).expanduser()
    if not project_path.is_absolute():
        project_path = ROOT / project_path
    project_path = project_path.resolve()
    return {
        "root": project_path,
        "config": project_path / "project.json",
        "story": project_path / "story.txt",
        "assets": project_path / "assets",
        "images": project_path / "assets" / "images",
        "videos": project_path / "assets" / "videos",
        "audio": project_path / "assets" / "audio",
        "icons": project_path / "assets" / "icons",
        "generated": project_path / "assets" / "generated",
        "build": project_path / "build",
        "manifest": project_path / "media_candidates.csv",
        "plan": project_path / "scene_plan.csv",
    }


def new_project(name: str, project_dir: str | None = None) -> Path:
    slug = slugify(name)
    if project_dir:
        target = Path(project_dir).expanduser()
        if not target.is_absolute():
            target = ROOT / target
    else:
        target = PROJECTS_DIR / slug
    target = target.resolve()
    if target.exists() and any(target.iterdir()):
        raise FileExistsError("Project folder already exists and is not empty: " + str(target))
    target.mkdir(parents=True, exist_ok=True)
    paths = project_paths(str(target))
    for key in ("images", "videos", "audio", "icons", "generated", "build"):
        paths[key].mkdir(parents=True, exist_ok=True)
    story = paths["story"]
    if not story.exists():
        story.write_text("Paste the narration script or story here. One paragraph or sentence per beat works best.\n", encoding="utf-8")
    config = {
        "project_name": name,
        "drafts_dir": "",
        "audio": "",
        "scene_images": [],
        "scene_texts": [],
        "presenter_images": [],
        "canvas": {"width": 1920, "height": 1080, "fps": 30, "ratio": "16:9"},
        "settings": {
            "motion_preset": "whiteboard_smooth",
            "target_shot_seconds": 3.8,
            "minimum_shot_seconds": 1.8,
            "presenter_overlay": True,
            "presenter_smart_matte": True,
            "presenter_scale": 0.42,
            "presenter_x": 0.72,
            "presenter_y": 0.18,
            "presenter_pose_seconds": 9.5,
            "scene_image_scale": 0.50,
            "scene_image_x": -0.25,
            "scene_image_y": -0.02,
            "voice_volume": 0.96,
            "voice_fade_in": 0.16,
            "voice_fade_out": 0.7,
            "transcribe_if_whisper_available": True,
            "whisper_model": "base",
            "add_captions_when_transcribed": True,
            "make_sfx_cue_sheet": True,
            "sound_effects": [],
        },
    }
    paths["config"].write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (paths["root"] / "README.md").write_text(
        "# " + name + "\n\nProject-local assets live under assets/. The project is intentionally ignored by Git. "
        "See the system repository README for search, download, licensing and build commands.\n",
        encoding="utf-8",
    )
    log("Created project folder: " + str(target))
    log("Next: edit story.txt, then run the plan command.")
    return target


def split_story(text: str) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?؟])\s+|\n+", text)
    scenes: list[str] = []
    for part in parts:
        sentence = re.sub(r"\s+", " ", part).strip(" \t-•")
        if sentence:
            scenes.append(sentence)
    return scenes


def make_search_query(sentence: str, max_words: int = 9) -> str:
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*|[\u0600-\u06FF]{2,}", sentence.lower())
    kept: list[str] = []
    for token in tokens:
        if token in STOP_WORDS or token.isdigit():
            continue
        if token not in kept:
            kept.append(token)
        if len(kept) >= max_words:
            break
    if len(kept) < 2:
        return sentence[:120].strip()
    return " ".join(kept)



def make_sfx_search_query(sentence: str) -> str:
    text = sentence.lower()
    groups = [
        (["scared", "fear", "monster", "ghost", "dark", "danger", "horror", "creepy", "suddenly",
          "خوف", "مخيف", "مرعب", "وحش", "شبح", "خطر", "ظلام", "فجأة", "رعب"],
         "horror suspense impact riser"),
        (["funny", "joke", "ridiculous", "silly", "oops", "laugh", "surprised",
          "مضحك", "نكتة", "كوميدي", "غريب", "صدمة", "مفاجأة"],
         "cartoon pop boing comedic sting"),
        (["run", "running", "move", "moving", "fast", "enter", "exit", "switch", "transition",
          "يركض", "تحرك", "تحركت", "انتقل", "دخل", "خرج", "بسرعة"],
         "short whoosh transition"),
        (["reveal", "discovered", "secret", "finally", "truth", "كشف", "اكتشف", "سر", "الحقيقة", "أخيراً"],
         "cinematic reveal riser soft hit"),
    ]
    for words, query in groups:
        if any(word in text for word in words):
            return query
    return "subtle transition whoosh soft pop"


def make_scene_plan(project: str) -> Path:
    paths = project_paths(project)
    if not paths["config"].is_file() or not paths["story"].is_file():
        raise FileNotFoundError("Project config/story not found. Create a project first.")
    story = paths["story"].read_text(encoding="utf-8-sig", errors="replace")
    sentences = split_story(story)
    if not sentences or sentences[0].startswith("Paste the narration script"):
        raise ValueError("Replace the placeholder in story.txt with your story/narration first.")
    rows = []
    for index, sentence in enumerate(sentences, start=1):
        visual_query = make_search_query(sentence)
        rows.append({
            "segment_id": "scene_%03d" % index,
            "sentence": sentence,
            "search_query": visual_query,
            "visual_prompt": "Create a clear, literal visual of: " + sentence,
            "sfx_search_query": make_sfx_search_query(sentence),
            "text_overlay": sentence,
            "asset_kind": "image",
            "selected_candidate_id": "",
            "notes": "Review/translate search_query if results are weak; verify each media license before publication.",
        })
    write_csv(paths["plan"], rows, [
        "segment_id", "sentence", "search_query", "visual_prompt", "sfx_search_query",
        "text_overlay", "asset_kind", "selected_candidate_id", "notes"
    ])
    log("Planned " + str(len(rows)) + " visual beat(s): " + str(paths["plan"]))
    log("Search queries are suggestions; review them and translate to English when that improves results.")
    return paths["plan"]


def next_candidate_id(rows: list[dict[str, str]]) -> str:
    largest = 0
    for row in rows:
        match = re.fullmatch(r"C(\d{4,})", str(row.get("id", "")))
        if match:
            largest = max(largest, int(match.group(1)))
    return "C%04d" % (largest + 1)


def append_candidates(project: str, candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    paths = project_paths(project)
    existing = read_csv(paths["manifest"])
    current = next_candidate_id(existing)
    counter = int(current[1:])
    known = {
        (row.get("source_page", "").strip().lower(), row.get("kind", ""), row.get("segment_id", ""))
        for row in existing
    }
    added = []
    for item in candidates:
        unique = (item.get("source_page", "").strip().lower(), item.get("kind", ""), item.get("segment_id", ""))
        if unique in known:
            continue
        row = {field: item.get(field, "") for field in MANIFEST_FIELDS}
        row["id"] = "C%04d" % counter
        counter += 1
        existing.append(row)
        added.append(row)
        known.add(unique)
    write_csv(paths["manifest"], existing)
    write_gallery(paths)
    return added


def search_command(project: str, query: str, kind: str, limit: int, segment_id: str = "") -> None:
    paths = project_paths(project)
    if not paths["root"].is_dir():
        raise FileNotFoundError("Project folder not found. Run new-project first.")
    candidates = search_provider(kind, query, limit, segment_id)
    added = append_candidates(project, candidates)
    log("Added " + str(len(added)) + " new candidate(s) to " + str(paths["manifest"]))
    log("Review results in " + str(paths["root"] / "media_gallery.html"))
    if not added:
        log("No new entries were added; results may already be in the manifest.")


def search_plan(project: str, kind: str, limit: int, max_scenes: int) -> None:
    paths = project_paths(project)
    if not paths["plan"].is_file():
        make_scene_plan(project)
    plan_rows = read_csv(paths["plan"])
    results_count = 0
    for row in plan_rows[:max_scenes]:
        query_field = "sfx_search_query" if kind == "audio" else "search_query"
        query = row.get(query_field, "").strip() or row.get("search_query", "").strip()
        if not query:
            continue
        log("Searching " + row["segment_id"] + ": " + query)
        candidates = search_provider(kind, query, limit, row["segment_id"])
        added = append_candidates(project, candidates)
        results_count += len(added)
        time.sleep(0.25)
    log("Search-plan added " + str(results_count) + " candidate(s).")
    log("Open " + str(paths["root"] / "media_gallery.html") + " and inspect source/license details before downloading.")


def write_gallery(paths: dict[str, Path]) -> Path:
    rows = read_csv(paths["manifest"])
    cards = []
    for row in rows:
        title = html.escape(row.get("title", "") or "Untitled")
        source = html.escape(row.get("source", ""))
        creator = html.escape(row.get("creator", ""))
        license_name = html.escape(row.get("license", "Unknown"))
        candidate_id = html.escape(row.get("id", ""))
        query = html.escape(row.get("query", ""))
        segment = html.escape(row.get("segment_id", "") or "unassigned")
        source_url = html.escape(safe_web_url(row.get("source_page", "")), quote=True)
        preview_raw = row.get("preview_url", "").strip()
        downloaded_raw = row.get("downloaded_path", "").strip()
        local_preview = False
        if not preview_raw and downloaded_raw and Path(downloaded_raw).is_file():
            try:
                preview_raw = Path(downloaded_raw).resolve().as_uri()
                local_preview = True
            except ValueError:
                preview_raw = ""
        preview = html.escape(safe_web_url(preview_raw, allow_file=local_preview), quote=True)
        license_url = html.escape(safe_web_url(row.get("license_url", "")), quote=True)
        dl = html.escape(downloaded_raw)
        license_reviewed = row.get("license_reviewed", "no").strip().lower() in {"yes", "true", "1"}
        review_status = '<p class="reviewed">License reviewed</p>' if license_reviewed else '<p class="needs-review">License needs review before publication</p>'
        kind = row.get("kind", "")
        if preview and kind in {"image", "icon"}:
            preview_markup = '<img loading="lazy" src="' + preview + '" alt="' + title + '">'
        elif preview and kind == "video":
            preview_markup = '<video controls preload="none" src="' + preview + '"></video>'
        elif preview and kind == "audio":
            preview_markup = '<audio controls preload="none" src="' + preview + '"></audio>'
        else:
            preview_markup = '<div class="no-preview">No preview — open source</div>'
        image = preview_markup
        cards.append(
            '<article class="card"><div class="preview">' + image + '</div>'
            '<div class="body"><div class="top"><strong>' + candidate_id + '</strong><span>' +
            html.escape(row.get("kind", "")) + ' · ' + segment + '</span></div>'
            '<h2>' + title + '</h2><p>' + source + ((" · " + creator) if creator else "") + '</p>'
            '<p class="query">Query: ' + query + '</p><p class="license">' + license_name + '</p>'
            '<p>' + (('<a href="' + license_url + '" target="_blank" rel="noreferrer">License</a> · ') if license_url else '') +
            (('<a href="' + source_url + '" target="_blank" rel="noreferrer">Source page</a>') if source_url else 'No source URL') + '</p>'
            + review_status
            + ('<p class="downloaded">Downloaded: ' + html.escape(dl) + '</p>' if dl else '<p class="pending">Not downloaded — use explicit IDs with the download command.</p>')
            + '</div></article>'
        )
    page = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Media review gallery</title><style>
body{margin:0;background:#f3f4f6;color:#17202a;font:15px/1.45 system-ui,Segoe UI,sans-serif}
header{padding:24px 5vw;background:#18212f;color:#f7f8fa}header h1{margin:0 0 8px;font-size:24px}
main{padding:24px 4vw}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:18px}
.card{background:white;border:1px solid #d8dde5;border-radius:14px;overflow:hidden;box-shadow:0 4px 14px #12203a0c}
.preview{height:185px;background:#e7eaf0;display:grid;place-items:center}.preview img,.preview video{width:100%;height:100%;object-fit:contain}.preview audio{width:92%}
.no-preview{color:#6b7280}.body{padding:15px}.top{display:flex;justify-content:space-between;color:#64748b;font-size:12px}
h2{font-size:16px;line-height:1.3;margin:12px 0 7px}.body p{margin:6px 0;overflow-wrap:anywhere}
.query{color:#475569}.license{font-weight:600}.pending{color:#925c16}.downloaded{color:#137454}
a{color:#245fc7;text-decoration:none}a:hover{text-decoration:underline}
.reviewed{color:#137454;font-weight:700}.needs-review{color:#925c16;font-weight:700}
</style></head><body><header><h1>Media Review Gallery</h1><p>Review each source and license. Nothing is automatically downloaded. Choose candidate IDs explicitly in PowerShell.</p></header>
<main><p>Candidate count: """ + str(len(rows)) + """</p><div class="grid">""" + "\n".join(cards) + """</div></main></body></html>"""
    gallery_path = paths["root"] / "media_gallery.html"
    gallery_path.write_text(page, encoding="utf-8")
    return gallery_path


def download_candidate(project: str, candidate_id: str) -> Path:
    paths = project_paths(project)
    rows = read_csv(paths["manifest"])
    row = next((item for item in rows if item.get("id", "").upper() == candidate_id.upper()), None)
    if row is None:
        raise KeyError("Candidate ID not found: " + candidate_id)
    existing_download = row.get("downloaded_path", "").strip()
    if existing_download and Path(existing_download).is_file():
        log(candidate_id + " is already downloaded: " + existing_download)
        return Path(existing_download)
    url = row.get("download_url", "").strip()
    if urllib.parse.urlparse(url).scheme not in {"https", "http"}:
        raise ValueError(
            candidate_id + " has no direct media URL. Open its source page and download it manually if permitted."
        )

    kind = row.get("kind", "image")
    target_dir = {"image": paths["images"], "video": paths["videos"], "audio": paths["audio"], "icon": paths["icons"]}.get(kind, paths["generated"])
    target_dir.mkdir(parents=True, exist_ok=True)
    stem = slugify(row.get("title", "") or candidate_id)
    safe_name = (stem[:60] or candidate_id) + "-" + candidate_id.lower()
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    part_path: Path | None = None
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            content_type = response.headers.get("Content-Type", "")
            declared_size = response.headers.get("Content-Length")
            if declared_size and int(declared_size) > MAX_DOWNLOAD_BYTES:
                raise ValueError("File is larger than the configured 80 MiB safety limit.")
            extension = safe_ext(url, content_type, kind)
            target_path = target_dir / (safe_name + extension)
            part_path = target_path.with_suffix(target_path.suffix + ".part")
            total = 0
            with part_path.open("wb") as output:
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    total += len(block)
                    if total > MAX_DOWNLOAD_BYTES:
                        raise ValueError("File exceeded the configured 80 MiB safety limit.")
                    output.write(block)
        if content_type.lower().startswith("text/html"):
            raise ValueError("The server returned an HTML page, not a direct media file.")
        if not part_path or part_path.stat().st_size < 128:
            raise ValueError("The downloaded file is empty or unusually small.")
        supported_extensions = {
            "image": {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"},
            "video": {".mp4", ".mov", ".webm"},
            "audio": {".mp3", ".wav", ".ogg", ".flac", ".m4a"},
            "icon": {".svg"},
        }
        if target_path.suffix.lower() not in supported_extensions.get(kind, set()):
            raise ValueError(
                "Unsupported extension " + target_path.suffix + " for " + kind
                + ". Use the dedicated icons command for SVG icon assets."
            )
        part_path.replace(target_path)
        for existing in rows:
            if existing.get("id") == row.get("id"):
                existing["selected"] = "yes"
                existing["downloaded_path"] = str(target_path.resolve())
                existing["downloaded_at"] = datetime.now().isoformat(timespec="seconds")
                existing.setdefault("license_reviewed", "no")
        write_csv(paths["manifest"], rows)
        write_gallery(paths)
        target_path.with_suffix(target_path.suffix + ".source.txt").write_text(
            "Source page: " + row.get("source_page", "") + "\n"
            + "Creator: " + row.get("creator", "") + "\n"
            + "License: " + row.get("license", "") + "\n"
            + "License URL: " + row.get("license_url", "") + "\n"
            + "Downloaded: " + datetime.now().isoformat(timespec="seconds") + "\n"
            + "Review the full source page and any third-party rights before publishing.\n",
            encoding="utf-8",
        )
        log("Downloaded " + candidate_id + " -> " + str(target_path))
        return target_path
    except Exception:
        if part_path and part_path.exists():
            part_path.unlink(missing_ok=True)
        raise


def review_license(project: str, candidate_id: str, notes: str) -> None:
    """Record a human's completed license/source review in the local manifest."""
    paths = project_paths(project)
    rows = read_csv(paths["manifest"])
    candidate = next((row for row in rows if row.get("id", "").upper() == candidate_id.upper()), None)
    if candidate is None:
        raise KeyError("Candidate ID not found: " + candidate_id)
    if not candidate.get("source_page", "").strip() or not candidate.get("license", "").strip():
        raise ValueError("Cannot mark review complete without source page and license metadata.")
    if not notes.strip():
        raise ValueError("Provide a short review note, e.g. 'Commercial use permitted; attribution added.'")
    candidate["license_reviewed"] = "yes"
    candidate["review_notes"] = notes.strip()
    write_csv(paths["manifest"], rows)
    write_gallery(paths)
    log("Marked " + candidate_id + " as license-reviewed. This records your review; it is not legal advice.")


def download_icons(project: str, names: list[str]) -> list[Path]:
    paths = project_paths(project)
    paths["icons"].mkdir(parents=True, exist_ok=True)
    license_url = "https://raw.githubusercontent.com/lucide-icons/lucide/main/LICENSE"
    license_path = paths["icons"] / "LUCIDE-LICENSE.txt"
    if not license_path.exists():
        request = urllib.request.Request(license_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=25) as response:
            license_path.write_bytes(response.read(1024 * 1024))
    output = []
    rows = read_csv(paths["manifest"])
    for name in names:
        icon_name = name.strip().lower()
        if not re.fullmatch(r"[a-z0-9-]+", icon_name):
            log("Skipped invalid icon name: " + name)
            continue
        url = "https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/" + icon_name + ".svg"
        target = paths["icons"] / (icon_name + ".svg")
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                svg = response.read(1024 * 512).decode("utf-8", errors="strict")
            if "<svg" not in svg.lower() or "<script" in svg.lower() or "javascript:" in svg.lower():
                log("Rejected unexpected SVG content for icon: " + icon_name)
                continue
            target.write_text(svg, encoding="utf-8")
            output.append(target)
            rows.append({
                "id": next_candidate_id(rows), "kind": "icon", "segment_id": "",
                "query": icon_name, "title": icon_name, "creator": "Lucide contributors",
                "source": "Lucide", "license": "ISC", "license_url": license_url,
                "source_page": "https://lucide.dev/icons/" + icon_name,
                "preview_url": "", "download_url": url, "selected": "yes",
                "downloaded_path": str(target.resolve()),
                "downloaded_at": datetime.now().isoformat(timespec="seconds"),
                "license_reviewed": "yes",
                "review_notes": "Lucide ISC license file saved alongside this icon.",
                "start_seconds": "", "volume": "",
                "notes": "Open source SVG icon; include LUCIDE-LICENSE.txt when redistributing the source icon.",
            })
        except urllib.error.HTTPError as exc:
            log("Could not fetch icon " + icon_name + ": HTTP " + str(exc.code))
        except urllib.error.URLError as exc:
            log("Could not fetch icon " + icon_name + ": " + str(exc.reason))
    write_csv(paths["manifest"], rows)
    write_gallery(paths)
    log("Downloaded " + str(len(output)) + " SVG icon(s) into " + str(paths["icons"]))
    return output


def generate_hf_image(
    project: str, scene_id: str, prompt: str | None, model: str | None, confirm_possible_cost: bool,
) -> Path:
    """Generate one story illustration through Hugging Face Inference Providers."""
    load_env_file()
    if not confirm_possible_cost:
        raise ValueError(
            "Image inference may consume paid provider credits. Re-run with --confirm-possible-cost "
            "only after reviewing your HF account/provider pricing."
        )
    token = os.environ.get("HF_TOKEN", "").strip()
    model = (model or os.environ.get("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-dev")).strip()
    if not token:
        raise ValueError("HF_TOKEN is missing. Add a Hugging Face token with Inference Providers permission to the local .env.")
    try:
        from huggingface_hub import InferenceClient
    except ImportError as exc:
        raise RuntimeError(
            "Optional AI image support is not installed. Run: "
            ".\\.venv\\Scripts\\python.exe -m pip install -r requirements-ai.txt"
        ) from exc

    paths = project_paths(project)
    if not paths["config"].is_file():
        raise FileNotFoundError("Project config not found. Create the project first.")
    plan_rows = read_csv(paths["plan"])
    scene = next((row for row in plan_rows if row.get("segment_id") == scene_id), None)
    if scene is None:
        raise KeyError("Scene ID was not found in scene_plan.csv: " + scene_id)
    scene_text = scene.get("sentence", "").strip()
    scene_visual_prompt = scene.get("visual_prompt", "").strip() or ("Create a clear, literal visual of: " + scene_text)
    if not scene_text and not prompt:
        raise ValueError("This scene has no text. Provide --prompt explicitly.")
    style = (
        "Create one 16:9 high-quality editorial illustration for a polished whiteboard explainer. "
        "Clear focal subject, strong readable silhouette, coherent visual storytelling, uncluttered composition, "
        "professional lighting, clean edges, tasteful texture. No lettering, captions, watermarks, logos, or UI. "
    )
    final_prompt = (prompt or scene_visual_prompt).strip()
    final_prompt = style + final_prompt
    log("Calling Hugging Face Inference Providers. Provider availability, model access and cost depend on your account.")

    client = InferenceClient(api_key=token)
    image = client.text_to_image(prompt=final_prompt, model=model)
    paths["generated"].mkdir(parents=True, exist_ok=True)
    target = paths["generated"] / (slugify(scene_id + "-" + scene_text[:45]) + "-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".png")
    image.save(target, format="PNG")

    manifest = read_csv(paths["manifest"])
    candidate_id = next_candidate_id(manifest)
    model_page = "https://huggingface.co/" + model
    manifest.append({
        "id": candidate_id,
        "kind": "image",
        "segment_id": scene_id,
        "query": final_prompt,
        "title": "AI-generated illustration — " + scene_id,
        "creator": "Generated by Hugging Face Inference Providers; review model terms",
        "source": "Hugging Face Inference Providers",
        "license": "Generated output — model/provider terms need review",
        "license_url": model_page,
        "source_page": model_page,
        "preview_url": "",
        "download_url": "",
        "selected": "yes",
        "downloaded_path": str(target.resolve()),
        "downloaded_at": datetime.now().isoformat(timespec="seconds"),
        "license_reviewed": "no",
        "review_notes": "",
        "start_seconds": "",
        "volume": "",
        "notes": (
            "Generated image. This is not a legal determination of output rights. "
            "Check model card, provider terms, and any applicable content restrictions."
        ),
    })
    write_csv(paths["manifest"], manifest)
    write_gallery(paths)
    (target.with_suffix(".png.source.txt")).write_text(
        "Scene ID: " + scene_id + "\n"
        + "Prompt: " + final_prompt + "\n"
        + "Model: " + model + "\n"
        + "Model page: " + model_page + "\n"
        + "Generated: " + datetime.now().isoformat(timespec="seconds") + "\n"
        + "Check model/provider terms before publication.\n",
        encoding="utf-8",
    )
    log("Generated image " + candidate_id + " -> " + str(target))
    return target


def apply_project(project: str, audio: str | None = None, presenter_dir: str | None = None, include_sfx: bool = False) -> Path:
    paths = project_paths(project)
    if not paths["config"].is_file():
        raise FileNotFoundError("Project config not found: " + str(paths["config"]))
    config = json.loads(paths["config"].read_text(encoding="utf-8-sig"))
    rows = read_csv(paths["manifest"])
    images = []
    for row in rows:
        local = row.get("downloaded_path", "").strip()
        if row.get("kind") in {"image", "video"} and local and Path(local).is_file():
            if row.get("selected", "yes").strip().lower() not in {"yes", "true", "1", "selected"}:
                continue
            images.append(row)
    # One selected asset per story beat, in story order. Multiple candidates can be reviewed
    # in the CSV; set selected=no on alternatives before applying if more than one was downloaded.
    plan_rows = read_csv(paths["plan"])
    segment_order = {row["segment_id"]: line for line, row in enumerate(plan_rows, start=1)}
    sentence_by_segment = {row["segment_id"]: row.get("sentence", "") for row in plan_rows}
    images.sort(key=lambda row: (segment_order.get(row.get("segment_id", ""), 100000), row.get("id", "")))
    chosen_rows: list[dict[str, str]] = []
    chosen: list[Path] = []
    seen_segments: set[str] = set()
    for row in images:
        seg = row.get("segment_id", "")
        if seg and seg in seen_segments:
            continue
        if seg:
            seen_segments.add(seg)
        chosen_rows.append(row)
        chosen.append(Path(row["downloaded_path"]).resolve())

    if not chosen:
        chosen = sorted(
            (path.resolve() for media_dir in (paths["images"], paths["videos"])
             for path in media_dir.glob("*") if path.is_file()
             and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm", ".m4v"}),
            key=lambda path: path.name.lower(),
        )
    if chosen:
        config["scene_images"] = [str(path) for path in chosen]
        if chosen_rows:
            config["scene_texts"] = [
                sentence_by_segment.get(row.get("segment_id", ""), "") for row in chosen_rows
            ]
        else:
            # Manually placed files in assets/images and assets/videos have no manifest segment IDs.
            # Pair them with story beats by filename order as a useful fallback, while keeping review required.
            config["scene_texts"] = [row.get("sentence", "") for row in plan_rows[:len(chosen)]]
        log("Added " + str(len(chosen)) + " local scene image/video asset(s) and story labels to project.json.")
    else:
        log("No downloaded images found. Search and download candidate IDs before building.")
    if audio:
        audio_path = Path(audio).expanduser()
        if not audio_path.is_file():
            raise FileNotFoundError("Narration file not found: " + str(audio_path))
        config["audio"] = str(audio_path.resolve())

    if presenter_dir:
        presenter_path = Path(presenter_dir).expanduser()
        if not presenter_path.is_dir():
            raise FileNotFoundError("Presenter folder not found: " + str(presenter_path))
        poses = sorted(
            (p.resolve() for p in presenter_path.iterdir() if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}),
            key=lambda path: path.name.lower(),
        )
        config["presenter_images"] = [str(path) for path in poses]
        log("Added " + str(len(poses)) + " presenter pose image(s).")

    if include_sfx:
        effects = []
        plan_rows = read_csv(paths["plan"])
        plan_order = {row["segment_id"]: index for index, row in enumerate(plan_rows)}
        try:
            target_interval = float(config.get("settings", {}).get("target_shot_seconds", 3.8))
            if target_interval < 1.0:
                target_interval = 3.8
        except (TypeError, ValueError):
            target_interval = 3.8

        # Prefer real timings from an earlier build by mapping each story beat's scene image.
        def path_key(raw: str) -> str:
            try:
                return str(Path(raw).expanduser().resolve()).casefold()
            except (OSError, RuntimeError):
                return str(raw).casefold()

        media_by_segment = {}
        for row in rows:
            local = row.get("downloaded_path", "").strip()
            segment = row.get("segment_id", "").strip()
            if row.get("kind") in {"image", "video"} and segment and local and Path(local).is_file():
                if row.get("selected", "yes").strip().lower() in {"yes", "true", "1", "selected"}:
                    media_by_segment.setdefault(segment, local)

        timeline_start_by_image = {}
        for scene in read_csv(paths["build"] / "scene_timing.csv"):
            image_path = scene.get("image", "").strip()
            start_value = scene.get("start", "").strip()
            if image_path and start_value:
                try:
                    timeline_start_by_image.setdefault(path_key(image_path), float(start_value))
                except ValueError:
                    pass

        updated_sfx_rows = 0
        for row in rows:
            local = row.get("downloaded_path", "").strip()
            if row.get("kind") != "audio" or not local or not Path(local).is_file():
                continue
            try:
                explicit_start = row.get("start_seconds", "").strip()
                segment = row.get("segment_id", "").strip()
                volume = float(row.get("volume", "0.10") or "0.10")
                if explicit_start:
                    start = float(explicit_start)
                else:
                    scene_image = media_by_segment.get(segment, "")
                    start = timeline_start_by_image.get(path_key(scene_image)) if scene_image else None
                    if start is None:
                        beat_index = plan_order.get(segment)
                        start = max(0.0, float(beat_index or 0) * target_interval + 0.18)
                    row["start_seconds"] = str(round(start, 3))
                    updated_sfx_rows += 1
                if start < 0 or volume < 0 or volume > 1:
                    log("Skipped invalid SFX timing/volume for " + row.get("id", "unknown"))
                    continue
                effects.append({
                    "path": local, "start": round(start, 3),
                    "volume": volume, "duration": 0
                })
            except (TypeError, ValueError):
                log("Skipped invalid SFX manifest row " + row.get("id", "unknown"))

        write_csv(paths["manifest"], rows)
        config.setdefault("settings", {})["sound_effects"] = effects
        log("Added " + str(len(effects)) + " local sound effect(s) to the separate CapCut track.")
        if updated_sfx_rows:
            log("Assigned approximate scene timings to " + str(updated_sfx_rows) + " SFX row(s) with no saved start_seconds. Review in media_candidates.csv / CapCut.")

    paths["config"].write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log("Updated local project config: " + str(paths["config"]))
    return paths["config"]


def preflight_project(project: str) -> dict[str, Any]:
    """Check local project paths, settings and license-review reminders before building."""
    paths = project_paths(project)
    errors: list[str] = []
    warnings: list[str] = []
    report: dict[str, Any] = {
        "project": str(paths["root"]),
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "errors": errors,
        "warnings": warnings,
        "asset_counts": {},
    }
    if not paths["config"].is_file():
        errors.append("Missing project.json. Run new-project first.")
        report["ok"] = False
        paths["build"].mkdir(parents=True, exist_ok=True)
        (paths["build"] / "preflight_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        log("Preflight failed: " + errors[0])
        return report

    try:
        config = json.loads(paths["config"].read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append("Could not read project.json: " + str(exc))
        config = {}

    audio_raw = str(config.get("audio", "") or "").strip()
    if not audio_raw:
        errors.append("Narration path is empty. Run apply --audio <absolute-path>.")
    else:
        audio_path = Path(os.path.expandvars(audio_raw)).expanduser()
        if not audio_path.is_absolute():
            audio_path = paths["root"] / audio_path
        if not audio_path.is_file():
            errors.append("Narration file does not exist: " + str(audio_path))

    scene_media = []
    missing_scene_media = []
    for raw in config.get("scene_images", []):
        media_path = Path(os.path.expandvars(str(raw))).expanduser()
        if not media_path.is_absolute():
            media_path = paths["root"] / media_path
        if media_path.is_file():
            scene_media.append(media_path.resolve())
        else:
            missing_scene_media.append(str(media_path))
    if not scene_media:
        errors.append("No usable scene media is configured. Search/download assets, then run apply.")
    if missing_scene_media:
        warnings.append(str(len(missing_scene_media)) + " configured scene media path(s) are missing.")
    report["asset_counts"]["scene_media_available"] = len(scene_media)
    report["asset_counts"]["scene_media_missing"] = len(missing_scene_media)

    scene_texts = config.get("scene_texts", [])
    if scene_texts and len(scene_texts) != len(config.get("scene_images", [])):
        warnings.append("scene_texts count differs from scene_images. Scene callouts may not match every clip.")

    presenter_paths = []
    for raw in config.get("presenter_images", []):
        media_path = Path(os.path.expandvars(str(raw))).expanduser()
        if not media_path.is_absolute():
            media_path = paths["root"] / media_path
        if media_path.is_file():
            presenter_paths.append(media_path.resolve())
    report["asset_counts"]["presenter_images_available"] = len(presenter_paths)
    if config.get("presenter_images") and not presenter_paths:
        warnings.append("Presenter images are configured but none exist. The draft will be built without the presenter.")
    elif config.get("presenter_images") and len(presenter_paths) < len(config.get("presenter_images", [])):
        warnings.append("Some presenter paths are missing; the builder will skip them.")

    preset_name = str(config.get("settings", {}).get("motion_preset", "whiteboard_smooth"))
    preset_path = ROOT / "presets" / "motion_presets.json"
    try:
        presets = json.loads(preset_path.read_text(encoding="utf-8-sig")).get("presets", {})
        if preset_name not in presets:
            warnings.append("Unknown motion preset '" + preset_name + "'. The builder falls back to whiteboard_smooth.")
        else:
            report["motion_preset"] = preset_name
    except (OSError, json.JSONDecodeError):
        warnings.append("Motion preset library could not be loaded.")

    manifest = read_csv(paths["manifest"])
    downloaded_rows = [row for row in manifest if row.get("downloaded_path", "").strip()]
    unreviewed = [row for row in downloaded_rows if row.get("license_reviewed", "no").strip().lower() not in {"yes", "true", "1"}]
    report["asset_counts"]["downloaded_assets"] = len(downloaded_rows)
    report["asset_counts"]["downloaded_assets_needing_license_review"] = len(unreviewed)
    if unreviewed:
        warnings.append(
            str(len(unreviewed)) + " downloaded asset(s) still need license review. "
            "Review the manifest/gallery and record decisions before public or commercial release."
        )

    report["ok"] = len(errors) == 0
    paths["build"].mkdir(parents=True, exist_ok=True)
    report_path = paths["build"] / "preflight_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for error in errors:
        log("ERROR: " + error)
    for warning in warnings:
        log("WARNING: " + warning)
    log(("Preflight passed" if report["ok"] else "Preflight failed") + ". Report: " + str(report_path))
    return report


def build_project(project: str, python_executable: str | None = None) -> int:
    paths = project_paths(project)
    report = preflight_project(project)
    if not report.get("ok"):
        raise RuntimeError("Preflight failed. Fix the errors above, then run the build command again.")
    if python_executable:
        python = python_executable
    else:
        candidate = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        python = str(candidate) if candidate.is_file() else sys.executable
    builder = ROOT / "scripts" / "build_montage.py"
    command = [python, str(builder), "--config", str(paths["config"].resolve()), "--build-dir", str(paths["build"].resolve())]
    log("Launching editable CapCut build for " + str(paths["root"]))
    import subprocess
    result = subprocess.run(command, cwd=str(ROOT), check=False)
    return int(result.returncode)


def command_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Local asset pipeline for editable CapCut explainer projects. Search results are never downloaded without an explicit download command."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("new-project", help="Create an isolated local project folder.")
    create.add_argument("--name", required=True)
    create.add_argument("--dir", default=None, help="Optional custom project folder.")
    plan = sub.add_parser("plan", help="Split story.txt into visual beats and search queries.")
    plan.add_argument("--project", required=True)
    search = sub.add_parser("search", help="Search media APIs for a query.")
    search.add_argument("--project", required=True)
    search.add_argument("--query", required=True)
    search.add_argument("--kind", choices=["image", "audio", "video"], default="image")
    search.add_argument("--segment-id", default="")
    search.add_argument("--limit", type=int, default=6)
    plan_search = sub.add_parser("search-plan", help="Search for candidate assets for the first story beats.")
    plan_search.add_argument("--project", required=True)
    plan_search.add_argument("--kind", choices=["image", "audio", "video"], default="image")
    plan_search.add_argument("--limit-per-scene", type=int, default=3)
    plan_search.add_argument("--max-scenes", type=int, default=8)
    download = sub.add_parser("download", help="Download only the candidate IDs explicitly selected by you.")
    download.add_argument("--project", required=True)
    download.add_argument("--ids", required=True, help="Comma-separated IDs, such as C0001,C0004.")
    review = sub.add_parser("review-license", help="Record a human-reviewed license/source check for one manifest item.")
    review.add_argument("--project", required=True)
    review.add_argument("--id", required=True)
    review.add_argument("--notes", required=True, help="Brief note of what you checked.")

    icons = sub.add_parser("icons", help="Download selected Lucide SVG icons.")
    icons.add_argument("--project", required=True)
    icons.add_argument("--names", required=True, help="Comma-separated Lucide icon names in kebab-case.")
    gen = sub.add_parser("generate-image", help="Generate an illustration from a scene using Hugging Face Inference Providers.")
    gen.add_argument("--project", required=True)
    gen.add_argument("--scene-id", required=True, help="Scene ID from scene_plan.csv.")
    gen.add_argument("--prompt", default=None, help="Optional more detailed prompt; otherwise use the scene sentence.")
    gen.add_argument("--model", default=None, help="Model ID; defaults to HF_IMAGE_MODEL in .env, then black-forest-labs/FLUX.1-dev.")
    gen.add_argument("--confirm-possible-cost", action="store_true", help="Explicitly acknowledge that provider inference may cost credits.")

    apply = sub.add_parser("apply", help="Add downloaded images/audio and local voiceover to project.json.")
    apply.add_argument("--project", required=True)
    apply.add_argument("--audio", default=None, help="Local narration audio path.")
    apply.add_argument("--presenter-dir", default=None, help="Folder containing presenter pose images.")
    apply.add_argument("--include-sfx", action="store_true", help="Include downloaded audio with a numeric start_seconds in the manifest.")
    preflight = sub.add_parser("preflight", help="Check files and settings before building CapCut.")
    preflight.add_argument("--project", required=True)
    build = sub.add_parser("build", help="Create and register the editable CapCut draft for the project.")
    build.add_argument("--project", required=True)
    build.add_argument("--python", default=None, help="Optional path to the system repository's virtualenv Python.")
    return parser


def main(argv: list[str] | None = None) -> int:
    load_env_file()
    args = command_parser().parse_args(argv)
    if getattr(args, "limit", 6) < 1 or getattr(args, "limit_per_scene", 3) < 1:
        raise ValueError("Search limit must be at least 1.")
    if getattr(args, "max_scenes", 8) < 1:
        raise ValueError("max-scenes must be at least 1.")

    if args.command == "new-project":
        new_project(args.name, args.dir)
    elif args.command == "plan":
        make_scene_plan(args.project)
    elif args.command == "search":
        search_command(args.project, args.query, args.kind, min(args.limit, 20), args.segment_id)
    elif args.command == "search-plan":
        search_plan(args.project, args.kind, min(args.limit_per_scene, 10), min(args.max_scenes, 25))
    elif args.command == "download":
        for candidate_id in [item.strip() for item in args.ids.split(",") if item.strip()]:
            download_candidate(args.project, candidate_id)
    elif args.command == "review-license":
        review_license(args.project, args.id, args.notes)
    elif args.command == "icons":
        names = [item.strip() for item in args.names.split(",") if item.strip()]
        download_icons(args.project, names)
    elif args.command == "generate-image":
        generate_hf_image(args.project, args.scene_id, args.prompt, args.model, args.confirm_possible_cost)
    elif args.command == "apply":
        apply_project(args.project, args.audio, args.presenter_dir, args.include_sfx)
    elif args.command == "preflight":
        report = preflight_project(args.project)
        return 0 if report.get("ok") else 2
    elif args.command == "build":
        return build_project(args.project, args.python)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, FileNotFoundError, KeyError, FileExistsError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        print("\nERROR: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
