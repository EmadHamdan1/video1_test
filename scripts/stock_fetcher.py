"""Licensed stock-image retrieval for the montage builder.

Uses provider APIs only (no scraping), stores downloaded assets locally, caches results,
and writes per-asset provenance into assets/stock/stock_manifest.json + CREDITS.txt.
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import os
import re
import socket
import ssl
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

UA = "video1-test-montage/1.1 (local video project)"
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def _http(url: str, headers: dict[str, str] | None = None, timeout: int = 12) -> bytes:
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



def openverse_search(query: str, per_page: int = 8, allow_share_alike: bool = False) -> list[dict[str, Any]]:
    """Openverse's openly-licensed image search; restrict results to commercially usable licences."""
    allowed = "cc0,pdm,by,by-sa" if allow_share_alike else "cc0,pdm,by"
    params = {
        "q": query, "page_size": min(20, per_page), "license": allowed,
        "license_type": "commercial", "extension": "jpg,jpeg,png,webp",
        "filter_dead": "true", "mature": "false",
    }
    data = _json("https://api.openverse.org/v1/images/?" + urllib.parse.urlencode(params), {"Accept": "application/json"})
    out: list[dict[str, Any]] = []
    for result in data.get("results", []):
        short = str(result.get("license", "")).lower()
        if short in {"by-nc", "by-nc-nd", "by-nd", "nc-sampling+", "sampling+"}:
            continue
        if short == "by-sa" and not allow_share_alike:
            continue
        if short not in {"cc0", "pdm", "by"} and not (allow_share_alike and short == "by-sa"):
            continue
        width, height = int(result.get("width") or 0), int(result.get("height") or 0)
        license_version = str(result.get("license_version") or "").strip()
        license_label = {"cc0": "CC0", "pdm": "Public Domain Mark", "by": "CC BY", "by-sa": "CC BY-SA"}.get(short, short.upper())
        if license_version and short in {"by", "by-sa"}:
            license_label += " " + license_version
        creator = html.unescape(str(result.get("creator") or "Unknown author"))
        page_url = str(result.get("foreign_landing_url") or result.get("detail_url") or "")
        out.append({
            "provider": "openverse", "id": str(result.get("id") or ""),
            "kind": "photo", "url": str(result.get("url") or ""),
            "width": width, "height": height, "license": license_label,
            "license_url": str(result.get("license_url") or ""), "page_url": page_url,
            "credit": "%s — %s, via Openverse (%s)" % (creator, license_label, page_url),
        })
    return out


def build_queries(beats: list[dict[str, Any]], max_queries: int = 40) -> list[dict[str, Any]]:
    """Use concrete English scene descriptions; deduplicate queries while preserving order."""
    seen: set[str] = set()
    queries: list[dict[str, Any]] = []
    for index, beat in enumerate(beats):
        # Require an explicit concrete visual query. Trigger words are often abstract
        # facts ("27 HOURS", "NO PULSE") and make poor, irrelevant stock searches.
        query = re.sub(r"\s+", " ", str(beat.get("stock_query") or "")).strip()
        if len(query.split()) < 2:
            query = ""
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


def _image_has_transparency(path: Path) -> bool:
    """Return True only for visible transparent pixels, not merely an RGBA colour model."""
    try:
        from PIL import Image
        with Image.open(path) as image:
            if "A" in image.getbands():
                return image.getchannel("A").getextrema()[0] < 255
            if "transparency" in image.info:
                return True
    except Exception:
        pass
    return False


def _write_contact_sheet(rows: list[dict[str, Any]], project_dir: Path,
                        log: Callable[[str], None]) -> None:
    """Make a review sheet of the locally downloaded stock candidates."""
    usable = [row for row in rows if Path(str(row.get("path", ""))).is_file()]
    if not usable:
        return
    try:
        from PIL import Image, ImageDraw, ImageOps

        columns, cell_w, cell_h = 4, 320, 250
        sheet = Image.new("RGB", (columns * cell_w, ((len(usable) + columns - 1) // columns) * cell_h),
                          (246, 246, 243))
        draw = ImageDraw.Draw(sheet)
        resampling = getattr(Image, "Resampling", Image).LANCZOS
        for index, row in enumerate(usable):
            x, y = (index % columns) * cell_w, (index // columns) * cell_h
            try:
                with Image.open(str(row["path"])) as source:
                    opened = ImageOps.exif_transpose(source)
                    if "A" in opened.getbands() or "transparency" in opened.info:
                        rgba = opened.convert("RGBA")
                        matte = Image.new("RGBA", rgba.size, (246, 246, 243, 255))
                        matte.alpha_composite(rgba)
                        preview = matte.convert("RGB")
                    else:
                        preview = opened.convert("RGB")
                    thumb = ImageOps.contain(preview, (cell_w - 16, cell_h - 62), method=resampling)
                sheet.paste(thumb, (x + (cell_w - thumb.width) // 2, y + 4))
            except Exception as exc:
                draw.text((x + 8, y + 8), "UNREADABLE STOCK IMAGE", fill=(180, 24, 24))
                log("Stock contact sheet could not read %s: %s" % (row.get("path"), exc))
            provider = str(row.get("provider", "source"))
            query = re.sub(r"\s+", " ", str(row.get("query", ""))).strip()
            licence = str(row.get("license", "licence unknown"))
            draw.text((x + 8, y + cell_h - 54), (provider + " | " + licence)[:43], fill=(30, 34, 40))
            draw.text((x + 8, y + cell_h - 34), query[:42], fill=(68, 73, 80))
            draw.text((x + 8, y + cell_h - 16), Path(str(row["path"])).name[:43], fill=(92, 95, 99))
        output = project_dir / "build" / "ASSET_STOCK_CONTACT_SHEET.jpg"
        output.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(output, "JPEG", quality=90, optimize=True)
        log("Stock B-roll contact sheet: " + str(output))
    except Exception as exc:
        log("Could not create the stock contact sheet: " + str(exc))


def _load_manifest(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [item for item in data if isinstance(item, dict) and item.get("path")]
    except (OSError, json.JSONDecodeError, TypeError):
        return []


def _load_api_keys() -> dict[str, str]:
    """Read optional API keys from process environment or a private root .env file."""
    values = {"pexels": os.environ.get("PEXELS_API_KEY", ""),
              "pixabay": os.environ.get("PIXABAY_API_KEY", "")}
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.is_file():
        try:
            for raw in env_path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, value = line.split("=", 1)
                name, value = name.strip(), value.strip().strip('"').strip("'")
                if name == "PEXELS_API_KEY" and not values["pexels"]:
                    values["pexels"] = value
                elif name == "PIXABAY_API_KEY" and not values["pixabay"]:
                    values["pixabay"] = value
        except OSError:
            pass
    return values


def _is_network_connectivity_failure(exc: BaseException) -> bool:
    """Recognise DNS, timeout and TLS transport failures that should trip a run-local circuit breaker."""
    reason = getattr(exc, "reason", None)
    details = " ".join((str(exc), str(reason))).lower()
    network_errors = (socket.gaierror, TimeoutError, socket.timeout)
    if isinstance(exc, network_errors) or isinstance(reason, network_errors):
        return True
    # urllib may wrap socket / TLS errors as URLError, so inspect its reason text too.
    return any(phrase in details for phrase in (
        "getaddrinfo failed",
        "name or service not known",
        "temporary failure in name resolution",
        "nodename nor servname provided",
        "timed out",
        "timeout",
        "handshake operation",
        "ssl error",
        "ssl: certificate_verify_failed",
        "connection reset",
        "connection refused",
        "network is unreachable",
        "429 too many requests",
        "too many requests",
        "rate limit exceeded",
        "503 service unavailable",
    )) or isinstance(exc, ssl.SSLError) or isinstance(reason, ssl.SSLError)


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
    # Backfill alpha metadata for assets cached by an earlier version of the fetcher.
    for item in manifest:
        if "alpha_channel" not in item and str(item.get("kind", "photo")) == "photo":
            item["alpha_channel"] = _image_has_transparency(Path(str(item["path"])))
    have = {(str(item.get("provider", "")), str(item.get("id", ""))) for item in manifest}
    known_hashes = {str(item.get("sha1", "")) for item in manifest if item.get("sha1")}
    keys = _load_api_keys()
    requested = cfg.get("providers", ["pexels", "pixabay", "wikimedia"])
    providers = [provider for provider in requested if provider in {"openverse", "wikimedia"} or keys.get(provider)]
    for provider in requested:
        if provider not in providers:
            log("Stock provider skipped (no API key in environment): " + str(provider))

    # Circuit-break network failures for this run only. A later run retries normally,
    # but read/handshake timeouts and DNS failures won't be repeated for every story beat.
    failed_providers: set[str] = set()
    per_query = max(1, int(cfg.get("per_query", 1)))
    max_total = max(0, int(cfg.get("max_total", 26)))
    min_width = max(320, int(cfg.get("min_width", 1280)))
    # Transparent foreground cutouts can be small because they occupy only a fraction
    # of the frame; let them use a lower resolution threshold than hero/B-roll images.
    min_cutout_width = max(320, min(min_width, int(cfg.get("min_cutout_width", 640))))
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
            if provider in failed_providers:
                continue
            try:
                if provider == "openverse" and kind == "photo":
                    candidates = openverse_search(query["query"], per_page=8,
                                                  allow_share_alike=bool(cfg.get("allow_share_alike", False)))
                elif provider == "pexels":
                    candidates = pexels_search(query["query"], keys["pexels"], kind, per_page=8)
                elif provider == "pixabay":
                    candidates = pixabay_search(query["query"], keys["pixabay"], kind, per_page=8)
                elif provider == "wikimedia" and kind == "photo":
                    candidates = wikimedia_search(query["query"], bool(cfg.get("allow_share_alike", False)), per_page=8)
                else:
                    candidates = []
            except Exception as exc:
                if _is_network_connectivity_failure(exc):
                    failed_providers.add(provider)
                    log(
                        "Stock provider disabled for the rest of this run after a network "
                        "connectivity failure (%s): %s" % (provider, exc)
                    )
                else:
                    log("Stock search failed (%s, %r): %s" % (provider, query["query"], exc))
                continue
            for candidate in candidates:
                if got >= per_query or len(manifest) >= max_total:
                    break
                identifier = str(candidate.get("id", ""))
                url = str(candidate.get("url", ""))
                if not identifier or not url.startswith(("https://", "http://")):
                    continue
                candidate_width = int(candidate.get("width") or 0)
                if candidate_width < min_cutout_width or (provider, identifier) in have:
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
                    alpha_channel = _image_has_transparency(destination) if kind == "photo" else False
                    # Only keep below-target-resolution photos if they're actual transparent
                    # overlays; opaque images stay subject to the hero/B-roll minimum.
                    if kind == "photo" and candidate_width < min_width and not alpha_channel:
                        destination.unlink(missing_ok=True)
                        continue
                except Exception as exc:
                    destination.unlink(missing_ok=True)
                    if _is_network_connectivity_failure(exc):
                        failed_providers.add(provider)
                        log(
                            "Stock provider disabled for the rest of this run after a download "
                            "network failure (%s): %s" % (provider, exc)
                        )
                        break
                    log("Stock download failed (%s): %s" % (url, exc))
                    continue
                digest = hashlib.sha1(destination.read_bytes()).hexdigest()[:12]
                if digest in known_hashes:
                    continue
                manifest.append({
                    **candidate, "path": str(destination.resolve()), "query": query["query"],
                    "beat": query["beat"], "sha1": digest,
                    "alpha_channel": alpha_channel,
                })
                have.add((provider, identifier))
                known_hashes.add(digest)
                got += 1
        if got == 0 and query_key not in cached_query_counts:
            log("No usable licensed stock results for beat %d query %r; using supplied art for that beat." % (query["beat"], query["query"]))
        if providers and all(provider in failed_providers for provider in providers):
            log("All configured stock providers hit network failures; skipping remaining online searches and continuing with supplied local artwork.")
            break

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    credits = sorted({str(item.get("credit", "")) for item in manifest if item.get("credit")})
    credits.insert(0, "Stock-media source credits — review the matching source page before publishing.")
    credits.extend(["", "Openverse: https://openverse.org/ — verify each item's original source and licence; indexed licence data can be inaccurate.",
                    "Pexels: https://www.pexels.com/ — show a prominent link back when using the Pexels API.",
                    "Pixabay: https://pixabay.com/ — cache API results and avoid systematic mass downloads.",
                    "Wikimedia Commons: each file has its own licence; verify the recorded licence and source page."])
    (out_dir / "CREDITS.txt").write_text("\n".join(credits).rstrip() + "\n", encoding="utf-8")
    _write_contact_sheet(manifest, project_dir, log)
    log("Stock media ready: %d local files (manifest: %s)" % (len(manifest), manifest_path))
    return manifest


def _load_selected_reviewed_entries(project_dir: Path,
                                      log: Callable[[str], None] = print) -> list[dict[str, Any]]:
    """Load only explicitly selected, license-reviewed AI illustrations from the asset tool."""
    manifest_path = project_dir / "media_candidates.csv"
    if not manifest_path.is_file():
        return []
    generated: list[dict[str, Any]] = []
    try:
        with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except OSError as exc:
        log("Could not read generated-asset manifest: " + str(exc))
        return []

    for row in rows:
        if str(row.get("kind", "")).lower() not in {"image", "photo"}:
            continue
        if str(row.get("selected", "")).strip().lower() not in {"yes", "true", "1"}:
            continue
        if str(row.get("license_reviewed", "")).strip().lower() not in {"yes", "true", "1"}:
            continue
        path = Path(str(row.get("downloaded_path", "")).strip()).expanduser()
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXT or not _valid_image(path):
            continue
        segment_id = str(row.get("segment_id", "")).strip()
        match = re.fullmatch(r"scene_(\d{1,4})", segment_id)
        if not match:
            log("Reviewed generated image has no valid story scene id; skipped: " + str(path))
            continue
        beat_index = int(match.group(1)) - 1
        if beat_index < 0:
            continue
        width = height = 0
        try:
            from PIL import Image
            with Image.open(path) as image:
                width, height = image.size
        except Exception:
            continue
        generated.append({
            "provider": "reviewed_generated_asset",
            "id": str(row.get("id", path.stem)),
            "kind": "photo",
            "path": str(path.resolve()),
            "query": str(row.get("query", row.get("title", ""))),
            "beat": beat_index,
            "width": width,
            "height": height,
            "license": str(row.get("license", "Generated output — review provider terms")),
            "page_url": str(row.get("source_page", "")),
            "credit": str(row.get("creator", "AI-generated asset")),
            "alpha_channel": _image_has_transparency(path),
            "asset_origin": "selected_and_license_reviewed_local_asset",
            "license_reviewed": True,
        })
    return generated


def load_stock_pool_entries(config: dict[str, Any], project_dir: Path,
                            log: Callable[[str], None] = print) -> list[dict[str, Any]]:
    entries = fetch_stock(config, project_dir, log)
    licensed_stock = [
        item for item in entries
        if item.get("kind") == "photo" and Path(str(item.get("path", ""))).is_file()
    ]
    reviewed_local_assets = _load_selected_reviewed_entries(project_dir, log)
    if reviewed_local_assets:
        log("Selected and license-reviewed local visuals available: %d" % len(reviewed_local_assets))
    return licensed_stock + reviewed_local_assets


def load_stock_pool(config: dict[str, Any], project_dir: Path,
                    log: Callable[[str], None] = print) -> list[Path]:
    """Backward-compatible path-only API used by small scripts."""
    return [Path(item["path"]) for item in load_stock_pool_entries(config, project_dir, log)]
