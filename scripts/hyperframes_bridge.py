"""HyperFrames renderer bridge for layered, independently animated graphics."""
from __future__ import annotations

import html
import json
import math
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import motion_library

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VERSION = "0.8.221"
GSAP_VERSION = "3.15.0"
GSAP_CDN = f"https://cdn.jsdelivr.net/npm/gsap@{GSAP_VERSION}/dist/gsap.min.js"


def _num(value: Any, label: str, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric.") from exc
    if not math.isfinite(number) or not low <= number <= high:
        raise ValueError(f"{label} must be between {low} and {high}.")
    return number


def _safe_id(value: Any, fallback: str) -> str:
    result = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(value or fallback)).strip("-_")
    return result[:48] or fallback


def _color(value: Any, label: str = "accent") -> str:
    result = str(value or "#D94C42")
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", result):
        raise ValueError(f"{label} must use #RRGGBB.")
    return result


def _motion_for(raw: dict[str, Any], ident: str, kind: str) -> dict[str, Any]:
    emotion = str(raw.get("emotion", "neutral"))
    shock = int(raw.get("shock_level", 0) or 0)
    default_role = "element" if kind in {"shape", "text"} else "entrance"
    role = str(raw.get("motion_role", default_role)).strip().lower()
    if role not in {"entrance", "element"}:
        raise ValueError(f"{ident}.motion_role must be entrance or element.")

    supplied = raw.get("motion_recipe")
    recipe = (
        motion_library.get_recipe(str(supplied))
        if supplied else
        motion_library.choose_recipe(role, emotion, shock, ident)
    )
    camera = motion_library.choose_recipe("camera", emotion, shock, ident + ":camera")
    transition = (
        motion_library.get_recipe(str(raw["transition_recipe"]))
        if raw.get("transition_recipe") else
        motion_library.choose_recipe("transition", emotion, shock, ident + ":transition")
    )
    return {
        "id": recipe["id"],
        "enter": recipe["enter"],
        "exit": recipe["exit"],
        "hold_id": camera["id"],
        "hold": camera["exit"]["to"],
        "transition_id": transition["id"],
        "transition": transition["exit"]["to"],
    }


def normalize_elements(elements: Any, total_duration: float) -> list[dict[str, Any]]:
    if not isinstance(elements, list) or len(elements) > 160:
        raise ValueError("hyperframes.elements must be a list with at most 160 items.")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(elements, 1):
        if not isinstance(raw, dict):
            raise ValueError(f"Element {index} must be an object.")
        kind = str(raw.get("type", "")).lower()
        if kind not in {"title", "callout", "arrow", "image", "shape", "text"}:
            raise ValueError(f"Unsupported HyperFrames element type: {kind}.")
        ident = _safe_id(raw.get("id"), f"element-{index:03d}")
        if ident in seen:
            raise ValueError(f"Duplicate element id: {ident}.")
        seen.add(ident)
        start = _num(raw.get("start", 0), f"{ident}.start", 0, total_duration)
        duration = _num(raw.get("duration"), f"{ident}.duration", 0.15, total_duration)
        if start + duration > total_duration + 0.001:
            raise ValueError(f"{ident} ends after the project duration.")
        item: dict[str, Any] = {
            "id": ident,
            "type": kind,
            "start": start,
            "duration": duration,
            "accent": _color(raw.get("accent")),
            "track_index": int(_num(raw.get("track_index", 0), f"{ident}.track_index", 0, 32)),
            "motion": _motion_for(raw, ident, kind),
            "motion_in": _num(raw.get("motion_in", 0.0), f"{ident}.motion_in", 0, duration * 0.7),
            "motion_out": _num(raw.get("motion_out", 0.0), f"{ident}.motion_out", 0, duration * 0.7),
        }
        if kind in {"title", "callout"}:
            heading = str(raw.get("title") or raw.get("text") or "").strip()
            if not heading or len(heading) > 110:
                raise ValueError(f"{ident}.title/text must contain 1–110 characters.")
            item.update({
                "title": html.escape(heading, quote=True),
                "kicker": html.escape(str(raw.get("kicker", ""))[:70], quote=True),
                "note": html.escape(str(raw.get("note", ""))[:100], quote=True),
                "x": _num(raw.get("x", 0.06), f"{ident}.x", 0.0, 0.95),
                "y": _num(raw.get("y", 0.70), f"{ident}.y", 0.0, 0.95),
                "width": _num(raw.get("width", 0.70), f"{ident}.width", 0.05, 1.0),
                "font_size": int(_num(raw.get("font_size", 52), f"{ident}.font_size", 14, 180)),
            })
        elif kind == "arrow":
            for coordinate in ("x1", "y1", "x2", "y2"):
                item[coordinate] = _num(raw.get(coordinate), f"{ident}.{coordinate}", 0.0, 1.0)
            if math.hypot(item["x2"] - item["x1"], item["y2"] - item["y1"]) < 0.025:
                raise ValueError(f"{ident} arrow endpoints are too close.")
            item["label"] = html.escape(str(raw.get("label", ""))[:70], quote=True)
            item["stroke_width"] = int(_num(raw.get("stroke_width", 5), f"{ident}.stroke_width", 1, 24))
        elif kind == "image":
            source = str(raw.get("path") or raw.get("src") or "").strip()
            if not source:
                raise ValueError(f"{ident}.path/src is required for image elements.")
            item.update({
                "source_path": str(Path(os.path.expandvars(source)).expanduser()),
                "x": _num(raw.get("x", 0.1), f"{ident}.x", -0.25, 1.0),
                "y": _num(raw.get("y", 0.1), f"{ident}.y", -0.25, 1.0),
                "width": _num(raw.get("width", 0.8), f"{ident}.width", 0.02, 1.5),
                "height": _num(raw.get("height", 0.8), f"{ident}.height", 0.02, 1.5),
                "fit": str(raw.get("fit", "contain")),
                "rotation": _num(raw.get("rotation", 0), f"{ident}.rotation", -180, 180),
                "scale": _num(raw.get("scale", 1), f"{ident}.scale", 0.05, 4),
                "alt": html.escape(str(raw.get("alt", ""))[:180], quote=True),
            })
            if item["fit"] not in {"contain", "cover", "fill"}:
                raise ValueError(f"{ident}.fit must be contain, cover, or fill.")
        elif kind == "shape":
            shape = str(raw.get("shape", "circle")).lower()
            if shape not in {"circle", "rect", "line", "path"}:
                raise ValueError(f"{ident}.shape must be circle, rect, line, or path.")
            item.update({
                "shape": shape,
                "x": _num(raw.get("x", 0.4), f"{ident}.x", 0, 1),
                "y": _num(raw.get("y", 0.4), f"{ident}.y", 0, 1),
                "width": _num(raw.get("width", 0.2), f"{ident}.width", 0.005, 1),
                "height": _num(raw.get("height", 0.2), f"{ident}.height", 0.005, 1),
                "fill": _color(raw.get("fill", raw.get("accent", "#D94C42")), f"{ident}.fill"),
                "stroke": _color(raw.get("stroke", raw.get("accent", "#D94C42")), f"{ident}.stroke"),
                "stroke_width": int(_num(raw.get("stroke_width", 4), f"{ident}.stroke_width", 0, 36)),
                "rotation": _num(raw.get("rotation", 0), f"{ident}.rotation", -180, 180),
                "path_d": str(raw.get("path_d", "")),
            })
            if shape == "path" and (
                not item["path_d"]
                or not re.fullmatch(r"[MmLlHhVvCcQqSsTtAaZz0-9.,\s+-]+", item["path_d"])
            ):
                raise ValueError(f"{ident}.path_d must be a simple SVG path using path commands and numeric values only.")
        else:  # concise functional text label; not a narration subtitle.
            value = str(raw.get("text", "")).strip()
            if not value or len(value) > 100:
                raise ValueError(f"{ident}.text must contain 1–100 characters.")
            item.update({
                "text": html.escape(value, quote=True),
                "x": _num(raw.get("x", 0.1), f"{ident}.x", 0, 1),
                "y": _num(raw.get("y", 0.1), f"{ident}.y", 0, 1),
                "width": _num(raw.get("width", 0.35), f"{ident}.width", 0.05, 1),
                "font_size": int(_num(raw.get("font_size", 28), f"{ident}.font_size", 12, 120)),
                "align": str(raw.get("align", "left")),
            })
            if item["align"] not in {"left", "center", "right"}:
                raise ValueError(f"{ident}.align must be left, center, or right.")
        result.append(item)
    return result


def _element_markup(item: dict[str, Any], width: int, height: int,
                    asset_map: dict[str, str]) -> str:
    ident, kind = item["id"], item["type"]
    start, duration = item["start"], item["duration"]
    common = (
        f'id="{ident}" class="clip hf-{kind}" data-start="{start:.3f}" '
        f'data-duration="{duration:.3f}" data-track-index="{item["track_index"]}"'
    )
    if kind in {"title", "callout"}:
        label_html = f'<p class="hf-note">{item["note"]}</p>' if item["note"] else ""
        return (
            f'<section {common} style="left:{item["x"]*100:.2f}%;top:{item["y"]*100:.2f}%;'
            f'width:{item["width"]*100:.2f}%">'
            f'<div class="hf-card-inner" data-hf-content>'
            f'<p class="hf-kicker">{item["kicker"]}</p>'
            f'<span class="hf-rule" style="background:{item["accent"]}"></span>'
            f'<h1 style="font-size:{item["font_size"]}px">{item["title"]}</h1>{label_html}</div></section>'
        )
    if kind == "arrow":
        x1, y1 = item["x1"] * width, item["y1"] * height
        x2, y2 = item["x2"] * width, item["y2"] * height
        arrow_label = f'<span class="hf-arrow-label">{item["label"]}</span>' if item["label"] else ""
        return (
            f'<section {common}><svg viewBox="0 0 {width} {height}" preserveAspectRatio="none">'
            f'<defs><marker id="head-{ident}" markerWidth="14" markerHeight="14" '
            f'refX="10" refY="5" orient="auto" markerUnits="userSpaceOnUse">'
            f'<path d="M0,0 L10,5 L0,10 Z" fill="{item["accent"]}"/></marker></defs>'
            f'<path class="hf-arrow-path" d="M{x1:.2f},{y1:.2f} L{x2:.2f},{y2:.2f}" '
            f'fill="none" stroke="{item["accent"]}" stroke-width="{item["stroke_width"]}" '
            f'stroke-linecap="round" marker-end="url(#head-{ident})"/></svg>{arrow_label}</section>'
        )
    if kind == "image":
        src = html.escape(asset_map.get(ident, ""), quote=True)
        left, top = item["x"] * 100, item["y"] * 100
        width_pct, height_pct = item["width"] * 100, item["height"] * 100
        return (
            f'<img {common} src="{src}" alt="{item["alt"]}" '
            f'style="left:{left:.3f}%;top:{top:.3f}%;width:{width_pct:.3f}%;'
            f'height:{height_pct:.3f}%;object-fit:{item["fit"]};'
            f'transform:rotate({item["rotation"]}deg) scale({item["scale"]});"/>'
        )
    if kind == "shape":
        left, top = item["x"] * width, item["y"] * height
        w, h = item["width"] * width, item["height"] * height
        if item["shape"] == "circle":
            shape_markup = f'<ellipse class="hf-shape-core" cx="{w/2:.2f}" cy="{h/2:.2f}" rx="{w/2:.2f}" ry="{h/2:.2f}"/>'
        elif item["shape"] == "rect":
            shape_markup = f'<rect class="hf-shape-core" x="1" y="1" width="{max(0,w-2):.2f}" height="{max(0,h-2):.2f}" rx="12"/>'
        elif item["shape"] == "line":
            shape_markup = f'<path class="hf-shape-core" d="M0,{h/2:.2f} L{w:.2f},{h/2:.2f}" fill="none"/>'
        else:
            shape_markup = f'<path class="hf-shape-core" d="{html.escape(item["path_d"], quote=True)}" fill="none"/>'
        return (
            f'<svg {common} viewBox="0 0 {w:.2f} {h:.2f}" '
            f'style="left:{left:.2f}px;top:{top:.2f}px;width:{w:.2f}px;height:{h:.2f}px;'
            f'transform:rotate({item["rotation"]}deg);overflow:visible">'
            f'<g fill="{item["fill"]}" stroke="{item["stroke"]}" stroke-width="{item["stroke_width"]}" '
            f'stroke-linecap="round" stroke-linejoin="round">{shape_markup}</g></svg>'
        )
    return (
        f'<div {common} data-hf-content style="left:{item["x"]*100:.2f}%;top:{item["y"]*100:.2f}%;'
        f'width:{item["width"]*100:.2f}%;font-size:{item["font_size"]}px;text-align:{item["align"]};'
        f'color:{item["accent"]}">{item["text"]}</div>'
    )


def build_composition_html(total_duration: float, elements: Any,
                           width: int = 1920, height: int = 1080,
                           asset_map: dict[str, str] | None = None) -> str:
    total_duration = _num(total_duration, "total_duration", 0.2, 21600)
    if not (320 <= width <= 7680 and 320 <= height <= 7680):
        raise ValueError("Canvas dimensions must be between 320 and 7680.")
    items = normalize_elements(elements, total_duration)
    assets = asset_map or {}
    clips = [_element_markup(item, width, height, assets) for item in items]
    motions = [
        {
            "id": item["id"],
            "type": item["type"],
            "start": item["start"],
            "duration": item["duration"],
            "motion": item["motion"],
            "hold": item["motion"]["hold"],
            "transition": item["motion"]["transition"],
            "motionIn": item["motion_in"],
            "motionOut": item["motion_out"],
        }
        for item in items
    ]
    motion_json = json.dumps(motions, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width={width}, height={height}">
<script src="./gsap.min.js"></script>
<style>
*{{box-sizing:border-box}} html,body{{margin:0;width:{width}px;height:{height}px;overflow:hidden;background:transparent}}
#root{{position:relative;width:{width}px;height:{height}px;overflow:hidden;background:transparent}}
.clip{{position:absolute;pointer-events:none;transform-origin:center center}}
.hf-card{{display:flex;align-items:flex-end}}
.hf-card-inner{{width:100%;padding:23px 30px 25px 34px;border-left:4px solid #D94C42;
 background:linear-gradient(90deg,rgba(8,13,18,.88),rgba(8,13,18,.62) 76%,rgba(8,13,18,0));
 color:#fff;font-family:Arial,Helvetica,sans-serif;transform-origin:left bottom}}
.hf-kicker{{margin:0 0 11px;color:#e2e5e6;font-size:17px;font-weight:700;letter-spacing:.16em;text-transform:uppercase}}
.hf-rule{{display:block;width:104px;height:4px;margin:0 0 14px;border-radius:3px}}
.hf-card h1{{margin:0;color:#fff;font-family:Arial,Helvetica,sans-serif;font-weight:800;line-height:1.02;
 letter-spacing:-.035em;text-shadow:0 3px 18px rgba(0,0,0,.42);overflow-wrap:anywhere}}
.hf-note{{margin:12px 0 0;color:#d5dadd;font-size:16px;font-weight:600;letter-spacing:.11em;text-transform:uppercase}}
.hf-arrow{{inset:0;width:100%;height:100%}}
.hf-arrow svg{{display:block;width:100%;height:100%;overflow:visible}}
.hf-arrow-path{{filter:drop-shadow(0 2px 7px rgba(0,0,0,.38))}}
.hf-arrow-label{{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);
 padding:8px 13px;border-radius:7px;background:rgba(8,13,18,.88);color:#fff;
 font:700 16px Arial,Helvetica,sans-serif;letter-spacing:.04em}}
.hf-image{{position:absolute;display:block;max-width:none;transform-origin:center center}}
.hf-shape{{position:absolute;overflow:visible}}
.hf-text{{position:absolute;font-family:Arial,Helvetica,sans-serif;font-weight:800;letter-spacing:.02em;text-shadow:0 2px 12px rgba(0,0,0,.36)}}
</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{total_duration:.3f}"
 data-width="{width}" data-height="{height}">{"".join(clips)}</div>
<script>
(() => {{
 const rows={motion_json}; const tl=gsap.timeline({{paused:true}});
 for (const row of rows) {{
  const root=document.getElementById(row.id); if(!root) continue;
  const at=row.start, end=row.start+row.duration;
  if(row.type==="arrow") {{
   const path=root.querySelector(".hf-arrow-path");
   if(path) {{
    const length=path.getTotalLength();
    gsap.set(path,{{strokeDasharray:length,strokeDashoffset:length}});
    tl.to(path,{{strokeDashoffset:0,duration:Math.min(.85,row.duration*.42),ease:"power2.inOut"}},at+.12);
   }}
   const label=root.querySelector(".hf-arrow-label");
   if(label) {{
    tl.fromTo(label,{{autoAlpha:0,y:8}},{{autoAlpha:1,y:0,duration:.3,ease:"power2.out"}},at+.42);
   }}
   const transition={{...row.transition}};
   const transitionDuration=transition.duration||.5;
   const transitionEase=transition.ease||"power2.in";
   delete transition.duration; delete transition.ease;
   tl.to(root,{{...transition,duration:transitionDuration,ease:transitionEase}},
     Math.max(at+.65,end-row.motionOut-transitionDuration));
   continue;
  }}
  const target=(root.matches(".hf-card,.hf-text")?root:(root.querySelector("[data-hf-content]")||root));
  const enter=row.motion.enter, exit=row.motion.exit;
  const enterTo={{...enter.to,duration:enter.to.duration||.65,ease:enter.to.ease||"power3.out"}};
  const enterFrom={{...enter.from}};
  delete enterTo.ease; const easeIn=enter.to.ease||"power3.out";
  const enterAt=at+row.motionIn;
  const enterDuration=enterTo.duration;
  const enterEnd=enterAt+enterDuration;
  tl.fromTo(target,enterFrom,{{...enterTo,ease:easeIn}},enterAt);
  const hold={{...row.hold}};
  const holdDurationHint=hold.duration||1.0;
  const transition={{...row.transition}};
  const outDuration=transition.duration||exit.to.duration||.5;
  const outEase=transition.ease||exit.to.ease||"power2.in";
  delete hold.duration; delete hold.ease;
  delete transition.duration; delete transition.ease;
  const exitAt=Math.max(enterEnd+.05,end-row.motionOut-outDuration);
  const holdDuration=exitAt-enterEnd;
  if(holdDuration>.55) {{
   const holdProperties={{}};
   for (const key of ["x","y","scale","rotation"]) {{
    if (hold[key]!==undefined) holdProperties[key]=hold[key];
   }}
   if(Object.keys(holdProperties).length) {{
    const firstHalf=holdDuration*.5;
    tl.to(target,{{...holdProperties,duration:firstHalf,ease:"sine.inOut"}},enterEnd);
    const settle={{}};
    for (const key of Object.keys(holdProperties)) {{
     settle[key]=(key==="scale"?1:0);
    }}
    tl.to(target,{{...settle,duration:holdDuration-firstHalf,ease:"sine.inOut"}},enterEnd+firstHalf);
   }}
  }}
  tl.to(target,{{...transition,duration:outDuration,ease:outEase}},exitAt);
 }}
 window.__timelines=window.__timelines||{{}};
 window.__timelines["main"]=tl;
}})();
</script></body></html>
"""


def render_hyperframes_overlay(config: dict[str, Any], build_dir: Path,
                               total_duration: float, project_template: Path | None = None) -> dict[str, Any] | None:
    if not isinstance(config, dict) or not config.get("enabled", False) or not config.get("elements"):
        return None
    width, height = int(config.get("width", 1920)), int(config.get("height", 1080))
    template = (project_template or ROOT / "hyperframes-engine").resolve()
    if not (template / "hyperframes.json").is_file():
        raise FileNotFoundError(
            f"HyperFrames template missing at {template}; initialize it from the repository root."
        )

    generated = (build_dir / "hyperframes" / "render-project").resolve()
    output = (build_dir / "hyperframes" / "overlay.mov").resolve()
    if generated.exists():
        shutil.rmtree(generated)
    assets_dir = generated / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(template / "hyperframes.json", generated / "hyperframes.json")
    if (template / "package.json").is_file():
        shutil.copy2(template / "package.json", generated / "package.json")
    (generated / "meta.json").write_text(
        json.dumps({"id": "video1-overlay", "name": "Video1 transparent graphics"}, indent=2),
        encoding="utf-8",
    )

    asset_map: dict[str, str] = {}
    normalized = normalize_elements(config["elements"], total_duration)
    for item in normalized:
        if item["type"] != "image":
            continue
        source = Path(item["source_path"])
        if not source.is_file():
            raise FileNotFoundError(f"HyperFrames image asset not found: {source}")
        extension = source.suffix.lower() or ".png"
        filename = item["id"] + extension
        shutil.copy2(source, assets_dir / filename)
        asset_map[item["id"]] = "assets/" + filename

    gsap_candidates = [
        ROOT / "motion-lab" / "node_modules" / "gsap" / "dist" / "gsap.min.js",
        ROOT / "node_modules" / "gsap" / "dist" / "gsap.min.js",
        template / "node_modules" / "gsap" / "dist" / "gsap.min.js",
    ]
    local_gsap = next((path for path in gsap_candidates if path.is_file()), None)
    if local_gsap:
        shutil.copy2(local_gsap, generated / "gsap.min.js")
    else:
        # Keep a version-pinned CDN fallback for machines where the project dependencies
        # have not yet been installed locally. The build report records this condition.
        pass

    document = build_composition_html(total_duration, config["elements"], width, height, asset_map)
    if not local_gsap:
        document = document.replace(
            '<script src="./gsap.min.js"></script>',
            f'<script src="{GSAP_CDN}"></script>',
        )
    (generated / "index.html").write_text(document, encoding="utf-8")

    version = str(config.get("version", DEFAULT_VERSION))
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("hyperframes.version must be a pinned version such as 0.8.221.")
    workers = int(_num(config.get("workers", 2), "hyperframes.workers", 1, 4))
    timeout = int(_num(config.get("timeout_seconds", 1800), "hyperframes.timeout_seconds", 60, 7200))
    npx, ffprobe = shutil.which("npx"), shutil.which("ffprobe")
    if not npx or not ffprobe:
        raise RuntimeError("Both npx and ffprobe must be available on PATH.")

    output.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    chrome_candidates = [
        env.get("HYPERFRAMES_BROWSER_PATH", ""),
        os.path.join(env.get("ProgramFiles", r"C:\Program Files"), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(env.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(env.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
    ]
    chrome = next((p for p in chrome_candidates if p and Path(p).is_file()), None)
    if chrome:
        env["HYPERFRAMES_BROWSER_PATH"] = chrome

    command = [
        npx, "--yes", f"hyperframes@{version}", "render", str(generated),
        "--format", "mov", "--output", str(output), "--resolution", "landscape",
        "--workers", str(workers), "--strict",
    ]
    rendered = subprocess.run(
        command, cwd=str(ROOT), env=env, text=True, capture_output=True,
        timeout=timeout, check=False,
    )
    if rendered.returncode != 0 or not output.is_file():
        details = (rendered.stderr or rendered.stdout or "No renderer output.").strip()
        raise RuntimeError("HyperFrames render failed:\n" + details[-5000:])

    probe = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name,pix_fmt,width,height,duration", "-of", "json", str(output)],
        text=True, capture_output=True, check=False,
    )
    if probe.returncode != 0:
        raise RuntimeError("ffprobe could not inspect the HyperFrames MOV: " + probe.stderr[-2000:])
    streams = json.loads(probe.stdout).get("streams", [])
    stream = streams[0] if streams else {}
    codec, pixel_format = str(stream.get("codec_name", "")), str(stream.get("pix_fmt", ""))
    if codec != "prores" or "a" not in pixel_format:
        raise RuntimeError(
            f"HyperFrames alpha verification failed: codec={codec!r}, pix_fmt={pixel_format!r}."
        )
    return {
        "path": str(output),
        "codec": codec,
        "pixel_format": pixel_format,
        "width": int(stream.get("width", width)),
        "height": int(stream.get("height", height)),
        "elements": len(normalized),
        "element_types": {
            kind: sum(item["type"] == kind for item in normalized)
            for kind in sorted({item["type"] for item in normalized})
        },
        "gsap_source": "local" if local_gsap else "pinned_cdn_fallback",
        "duration": round(total_duration, 3),
    }


def add_overlay_track(spec: dict[str, Any], render: dict[str, Any], total_duration: float) -> None:
    tracks = spec.setdefault("tracks", [])
    if not isinstance(tracks, list):
        raise ValueError("CapCut compile spec tracks must be a list.")
    tracks.append({
        "type": "video",
        "name": "HyperFrames Motion Graphics",
        "items": [{
            "type": "video", "path": render["path"], "start": 0.0,
            "duration": round(float(total_duration), 3),
            "ref": "hyperframes_motion_graphics",
            "scale": 1.0, "x": 0.0, "y": 0.0, "rotation": 0,
        }],
    })
