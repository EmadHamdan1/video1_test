"""Licensed stock-image retrieval for the montage builder.

Uses provider APIs only (no scraping), stores downloaded assets locally, caches results,
and writes per-asset provenance into assets/stock/stock_manifest.json + CREDITS.txt.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

UA = "video1-test-montage/1.1 (local video project)"
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def _http(url: str, headers: dict[str, str] | None = None, timeout: int = 25) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _json(url: str, headers: dict[str, str] | None = None) -> Any:
    return json.loads(_http(url, headers).decode("utf-8"))


def license_ok(short: str, allow_share_alike: bool = False) -> bool:
    """Accept public domain/CC0 and permissive CC BY; reject NC/ND by default."""
    value = html.unescape((short or "").strip()).lower()
    if value.startswith(("cc0", "public domain", "pd")):
        return True
    if not value.startswith("cc by") or "-nc" in value or "-nd" in value:
        return False
    return allow_share_alike or "-sa" not in value


def pexels_search(query: str, key: str, kind: str = "photo", per_page: int = 8) -> list[dict[str, Any]]:
    """Pexels API. API video endpoint is /v1/videos/search (current documented path)."""
    params = urllib.parse.urlencode({"query": query, "per_page": min(80, per_page), "orientation": "landscape"})
    headers = {"Authorization": key}
    out: list[dict[str, Any]] = []
    if kind == "video":
        data = _json("https://api.pexels.com/v1/videos/search?" + params, headers)
        for video in data.get("videos", []):
            files = [f for f in video.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("width")]
            if not files:
                continue
            file = min(files, key=lambda f: abs(int(f.get("width", 0)) - 1920))
            out.append({
                "provider": "pexels", "id": str(video["id"]), "kind": "video", "url": file.get("link", ""),
                "width": int(file.get("width") or 0), "height": int(file.get("height") or 0),
                "duration": float(video.get("duration") or 0), "license": "Pexels License",
                "page_url": video.get("url", ""),
                "credit": "Video by %s on Pexels (%s)" % ((video.get("user") or {}).get("name", "unknown"), video.get("url", "")),
            })
        return out

    data = _json("https://api.pexels.com/v1/search?" + params, headers)
    for photo in data.get("photos", []):
        src = photo.get("src", {})
        out.append({
            "provider": "pexels", "id": str(photo["id"]), "kind": "photo",
            "url": src.get("large2x") or src.get("original") or src.get("large", ""),
            "width": int(photo.get("width") or 0), "height": int(photo.get("height") or 0),
            "license": "Pexels License", "page_url": photo.get("url", ""),
            "credit": "Photo by %s on Pexels (%s)" % (photo.get("photographer", "unknown"), photo.get("url", "")),
        })
    return out


def pixabay_search(query: str, key: str, kind: str = "photo", per_page: int = 8) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"key": key, "q": query[:100], "per_page": max(3, min(200, per_page)), "safesearch": "true"}
    endpoint = "https://pixabay.com/api/videos/?" if kind == "video" else "https://pixabay.com/api/?"
    if kind == "photo":
        params.update({"image_type": "photo", "orientation": "horizontal"})
    data = _json(endpoint + urllib.parse.urlencode(params))
    out: list[dict[str, Any]] = []
    for hit in data.get("hits", []):
        if kind == "video":
            variants = hit.get("videos", {})
            file = variants.get("large") or variants.get("medium") or variants.get("small") or {}
            url = file.get("url", "")
            width, height = int(file.get("width") or 0), int(file.get("height") or 0)
            duration = float(hit.get("duration") or 0)
        else:
            url = hit.get("largeImageURL", "")
            width, height = int(hit.get("imageWidth") or 0), int(hit.get("imageHeight") or 0)
            duration = 0.0
        if not url:
            continue
        label = "Video" if kind == "video" else "Image"
        out.append({
            "provider": "pixabay", "id": str(hit.get("id", "")), "kind": kind, "url": url,
            "width": width, "height": height, "duration": duration, "license": "Pixabay Content License",
            "page_url": hit.get("pageURL", ""),
            "credit": "%s by %s on Pixabay (%s)" % (label, hit.get("user", "unknown"), hit.get("pageURL", "")),
        })
    return out


def wikimedia_search(query: str, allow_share_alike: bool = False, per_page: int = 8) -> list[dict[str, Any]]:
    params = {
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
        "gsrsearch": query, "gsrlimit": min(50, per_page), "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 1920, "iiextmetadatafilter": "Artist|LicenseShortName|Credit|AttributionRequired",
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    data = _json(url, {"Accept": "application/json"})
    out: list[dict[str, Any]] = []
    pages = (data.get("query", {}).get("pages", {}) or {}).values()
    for page in pages:
        info = (page.get("imageinfo") or [{}])[0]
        if info.get("mime") not in ("image/jpeg", "image/png", "image/webp"):
            continue
        meta = info.get("extmetadata", {}) or {}
        license_name = html.unescape((meta.get("LicenseShortName") or {}).get("value", ""))
        if not license_ok(license_name, allow_share_alike):
            continue
        artist = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", (meta.get("Artist") or {}).get("value", "Unknown")))).strip()
        description_url = info.get("descriptionurl", "")
        url = info.get("thumburl") or info.get("url", "")
        out.append({
            "provider": "wikimedia", "id": str(page.get("pageid", "")), "kind": "photo", "url": url,
            "width": int(info.get("thumbwidth") or info.get("width") or 0),
            "height": int(info.get("thumbheight") or info.get("height") or 0),
            "license": license_name, "page_url": description_url,
            "credit": "%s — %s, via Wikimedia Commons (%s)" % (artist or "Unknown author", license_name, description_url),
        })
    return out


def build_queries(beats: list[dict[str, Any]], max_queries: int = 40) -> list[dict[str, Any]]:
    """Use concrete English scene descriptions; deduplicate queries while preserving order."""
    seen: set[str] = set()
    queries: list[dict[str, Any]] = []
    for index, beat in enumerate(beats):
        query = re.sub(r"\s+", " ", str(beat.get("stock_query") or "")).strip()
        if not query:
            trigger = re.sub(r"\s+", " ", str(beat.get("trigger_word") or "")).strip()
            query = trigger if re.fullmatch(r"[A-Za-z][A-Za-z '\-]{2,48}", trigger) else ""
        key = query.casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        queries.append({
            "beat": index, "query": query,
            "kind": "video" if str(beat.get("stock_kind", "")).lower() == "video" else "photo",
        })
        if len(queries) >= max(0, max_queries):
            break
    return queries


def _extension(url: str, kind: str) -> str:
    ext = Path(urllib.parse.urlparse(url).path).suffix.lower()
    return ext if ext in (IMAGE_EXT if kind == "photo" else {".mp4", ".mov", ".webm"}) else (".jpg" if kind == "photo" else ".mp4")


def _valid_image(path: Path) -> bool:
    try:
        from PIL import Image
        with Image.open(path) as image:
            image.verify()
        return True
    except Exception:
        return False


def _load_manifest(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [item for item in data if isinstance(item, dict) and item.get("path")]
    except (OSError, json.JSONDecodeError, TypeError):
        return []


def fetch_stock(config: dict[str, Any], project_dir: Path, log: Callable[[str], None] = print,
                http_get: Callable[[str], bytes] | None = None) -> list[dict[str, Any]]:
    """Fetch once, cache results, avoid scraping, and preserve credits/licences."""
    cfg = (config.get("settings", {}) or {}).get("stock_media", {}) or {}
    if not cfg.get("enabled", False):
        return []
    http_get = http_get or _http
    out_dir = project_dir / "assets" / "stock"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "stock_manifest.json"
    manifest = _load_manifest(manifest_path)
    manifest = [item for item in manifest if Path(str(item["path"])).is_file()]
    have = {(str(item.get("provider", "")), str(item.get("id", ""))) for item in manifest}
    known_hashes = {str(item.get("sha1", "")) for item in manifest if item.get("sha1")}
    keys = {"pexels": os.environ.get("PEXELS_API_KEY", ""), "pixabay": os.environ.get("PIXABAY_API_KEY", "")}
    requested = cfg.get("providers", ["pexels", "pixabay", "wikimedia"])
    providers = [provider for provider in requested if provider == "wikimedia" or keys.get(provider)]
    for provider in requested:
        if provider not in providers:
            log("Stock provider skipped (no API key in environment): " + str(provider))

    per_query = max(1, int(cfg.get("per_query", 1)))
    max_total = max(0, int(cfg.get("max_total", 26)))
    min_width = max(320, int(cfg.get("min_width", 1280)))
    allow_video = bool(cfg.get("allow_video", False))
    beats = config.get("story_beats", []) if isinstance(config.get("story_beats", []), list) else []
    cached_query_counts: dict[tuple[int, str], int] = {}
    for item in manifest:
        if Path(str(item["path"])).is_file() and item.get("query"):
            key = (int(item.get("beat", -1)), str(item["query"]).casefold())
            cached_query_counts[key] = cached_query_counts.get(key, 0) + 1

    for query in build_queries(beats, int(cfg.get("max_queries", 40))):
        if len(manifest) >= max_total:
            break
        query_key = (int(query["beat"]), str(query["query"]).casefold())
        if cached_query_counts.get(query_key, 0) >= per_query:
            continue
        kind = "video" if query["kind"] == "video" and allow_video else "photo"
        got = 0
        for provider in providers:
            if got >= per_query or len(manifest) >= max_total:
                break
            try:
                if provider == "pexels":
                    candidates = pexels_search(query["query"], keys["pexels"], kind, per_page=8)
                elif provider == "pixabay":
                    candidates = pixabay_search(query["query"], keys["pixabay"], kind, per_page=8)
                elif provider == "wikimedia" and kind == "photo":
                    candidates = wikimedia_search(query["query"], bool(cfg.get("allow_share_alike", False)), per_page=8)
                else:
                    candidates = []
            except Exception as exc:
                log("Stock search failed (%s, %r): %s" % (provider, query["query"], exc))
                continue
            for candidate in candidates:
                if got >= per_query or len(manifest) >= max_total:
                    break
                identifier = str(candidate.get("id", ""))
                url = str(candidate.get("url", ""))
                if not identifier or not url.startswith(("https://", "http://")):
                    continue
                if int(candidate.get("width") or 0) < min_width or (provider, identifier) in have:
                    continue
                if kind == "video" and not allow_video:
                    continue
                destination = out_dir / ("%s_%s%s" % (provider, re.sub(r"[^A-Za-z0-9_-]", "_", identifier), _extension(url, kind)))
                try:
                    if not destination.is_file():
                        destination.write_bytes(http_get(url))
                    if destination.stat().st_size < 1024 or (kind == "photo" and not _valid_image(destination)):
                        destination.unlink(missing_ok=True)
                        continue
                except Exception as exc:
                    log("Stock download failed (%s): %s" % (url, exc))
                    destination.unlink(missing_ok=True)
                    continue
                digest = hashlib.sha1(destination.read_bytes()).hexdigest()[:12]
                if digest in known_hashes:
                    continue
                manifest.append({
                    **candidate, "path": str(destination.resolve()), "query": query["query"],
                    "beat": query["beat"], "sha1": digest,
                })
                have.add((provider, identifier))
                known_hashes.add(digest)
                got += 1
        if got == 0 and query_key not in cached_query_counts:
            log("No usable licensed stock results for beat %d query %r; using supplied art for that beat." % (query["beat"], query["query"]))

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    credits = sorted({str(item.get("credit", "")) for item in manifest if item.get("credit")})
    credits.insert(0, "Stock-media source credits — review the matching source page before publishing.")
    credits.extend(["", "Pexels: https://www.pexels.com/ — show a prominent link back when using the Pexels API.",
                    "Pixabay: https://pixabay.com/ — API results are cached locally; do not make systematic mass downloads.",
                    "Wikimedia Commons: each file has its own licence; verify the recorded licence and source page."])
    (out_dir / "CREDITS.txt").write_text("\n".join(credits).rstrip() + "\n", encoding="utf-8")
    log("Stock media ready: %d local files (manifest: %s)" % (len(manifest), manifest_path))
    return manifest


def load_stock_pool_entries(config: dict[str, Any], project_dir: Path,
                            log: Callable[[str], None] = print) -> list[dict[str, Any]]:
    entries = fetch_stock(config, project_dir, log)
    return [item for item in entries if item.get("kind") == "photo" and Path(str(item.get("path", ""))).is_file()]


def load_stock_pool(config: dict[str, Any], project_dir: Path,
                    log: Callable[[str], None] = print) -> list[Path]:
    """Backward-compatible path-only API used by small scripts."""
    return [Path(item["path"]) for item in load_stock_pool_entries(config, project_dir, log)]
