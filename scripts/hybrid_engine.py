"""Hybrid whiteboard motion engine: pure-white canvas, pop-in/pop-out elements,
overlapping exits, idle motion, keyword callouts (no captions)."""
from __future__ import annotations

import math
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stock_fetcher
import text_system as ts
import motion_recipes as mr
from qa_spec import audit_spec

TAU = math.tau
VIDEO_SUFFIXES = {".mp4", ".mov", ".webm", ".m4v"}
LAYOUT_CYCLE = ["left", "right", "center", "left", "center", "right"]
ENTRANCES = [
    "pop", "slide", "drop", "tilt_pop", "slide_left", "slide_right",
    "rise", "diagonal_sweep", "zoom_through", "spin_in", "pop", "slide",
]
EXITS = ["shrink", "slide_out", "shrink", "drop_out", "tilt_away", "zoom_away"]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _tri(t: float, t0: float, tp: float, t1: float, amp: float) -> float:
    if t <= t0 or t >= t1:
        return 0.0
    if t <= tp:
        return amp * (t - t0) / max(1e-6, tp - t0)
    return amp * (t1 - t) / max(1e-6, t1 - tp)


def _interp(t: float, points: list[tuple[float, float]]) -> float:
    if not points or t <= points[0][0] or t >= points[-1][0]:
        return 0.0
    for (ta, va), (tb, vb) in zip(points, points[1:]):
        if ta <= t <= tb:
            return va + (vb - va) * (t - ta) / max(1e-6, tb - ta)
    return 0.0


class _Timeline:
    """Collects keyframes and emits sorted, de-duplicated, clamped operations."""

    def __init__(self) -> None:
        self.durations: dict[str, float] = {}
        self.keys: dict[tuple[str, str], list[tuple[float, float, str | None]]] = {}
        self.other: list[dict[str, Any]] = []

    def clip(self, ref: str, duration: float) -> None:
        self.durations[ref] = float(duration)

    def key(self, ref: str, prop: str, time: float, value: float, easing: str | None = None) -> None:
        self.keys.setdefault((ref, prop), []).append((float(time), float(value), easing))

    def ops(self) -> list[dict[str, Any]]:
        out = list(self.other)
        for (ref, prop), items in self.keys.items():
            limit = self.durations.get(ref, 1e9)
            cleaned: list[tuple[float, float, str | None]] = []
            for t, v, e in sorted(items, key=lambda it: it[0]):
                t = _clamp(t, 0.0, limit)
                if cleaned and t - cleaned[-1][0] < 0.012:
                    cleaned[-1] = (cleaned[-1][0], v, e)
                else:
                    cleaned.append((t, v, e))
            for t, v, e in cleaned:
                op: dict[str, Any] = {
                    "op": "keyframe", "target": ref, "property": prop,
                    "time": round(t, 3), "value": round(v, 4),
                }
                if e:
                    op["easing"] = e
                out.append(op)
        return out


def pop_motion(tl: _Timeline, ref: str, D: float, S: float, x: float, y: float,
               tilt: float = 0.0, enter: float = 0.28, exit_len: float = 0.16,
               float_amp: float = 0.010, from_dx: float = 0.0, from_dy: float = 0.10,
               phase: float = 0.0) -> None:
    """Generic element: overshoot pop-in, idle float, quick shrink-out."""
    E = _clamp(enter, 0.12, max(0.12, D * 0.45))
    f = E / 0.28
    xs = _clamp(D - exit_len, E + 0.05, D)
    tl.key(ref, "uniform_scale", 0.0, 0.05 * S)
    tl.key(ref, "uniform_scale", 0.14 * f, 1.14 * S, "ease-out")
    tl.key(ref, "uniform_scale", 0.22 * f, 0.96 * S, "ease-in-out")
    tl.key(ref, "uniform_scale", E, S, "ease-out")
    tl.key(ref, "position_x", 0.0, x + from_dx)
    tl.key(ref, "position_x", E * 0.7, x, "ease-out")
    tl.key(ref, "position_y", 0.0, y + from_dy)
    tl.key(ref, "position_y", E * 0.7, y, "ease-out")
    tl.key(ref, "rotation", 0.0, tilt * 2.5)
    tl.key(ref, "rotation", E, tilt, "ease-out")
    n = max(1, int((xs - E) / 0.375))
    for i in range(1, n + 1):
        t = E + (xs - E) * i / n
        ramp = _clamp((t - E) / 0.45, 0.0, 1.0)
        tl.key(ref, "position_y", t, y + float_amp * ramp * math.sin(TAU * t / 1.5 + phase), "ease-in-out")
        tl.key(ref, "uniform_scale", t, S * (1 + 0.004 * ramp * math.sin(TAU * t / 1.8 + phase)), "ease-in-out")
    ys = y + float_amp * _clamp((xs - E) / 0.45, 0.0, 1.0) * math.sin(TAU * xs / 1.5 + phase)
    tl.key(ref, "position_x", xs, x, "ease-in-out")
    tl.key(ref, "rotation", xs, tilt, "ease-in-out")
    tl.key(ref, "uniform_scale", xs + 0.4 * (D - xs), 1.06 * S, "ease-out")
    tl.key(ref, "uniform_scale", D, 0.05 * S, "ease-in")
    tl.key(ref, "rotation", D, tilt + (6.0 if tilt >= 0 else -6.0), "ease-in")
    tl.key(ref, "position_y", D, ys - 0.02, "ease-in")


def scene_motion(tl: _Timeline, ref: str, D: float, S: float, bx: float, by: float,
                 index: int, edge: int, shock: int, is_last: bool,
                 pan_amount: float, push: float) -> str:
    """Hero image: entrance recipe -> living hold -> overlapping exit. Returns entrance kind."""
    E = _clamp(D * 0.22, 0.16, 0.30)
    f = E / 0.30
    exit_len = 0.0 if is_last else _clamp(D * 0.14, 0.10, 0.18)
    xs = min(D, max(E + 0.12, D - exit_len))
    kind = "punch" if shock >= 3 else ENTRANCES[index % len(ENTRANCES)]

    def T(v: float) -> float:
        return v * f

    if kind == "pop":
        sk = [(0, .06 * S, None), (T(.14), 1.12 * S, "ease-out"), (T(.22), .97 * S, "ease-in-out"), (E, S, "ease-out")]
        xk = [(0, bx, None), (E, bx, "ease-out")]
        yk = [(0, by + .06, None), (T(.16), by - .012, "ease-out"), (E, by, "ease-out")]
        rk = [(0, -edge * 5.0, None), (T(.18), edge * 1.2, "ease-out"), (E, 0.0, "ease-out")]
    elif kind == "slide":
        sk = [(0, .82 * S, None), (T(.20), 1.04 * S, "ease-out"), (E, S, "ease-out")]
        xk = [(0, bx + edge * .62, None), (T(.18), bx - edge * .02, "ease-out"), (E, bx, "ease-out")]
        yk = [(0, by, None), (E, by, "ease-out")]
        rk = [(0, -edge * 4.0, None), (T(.20), edge * 1.0, "ease-out"), (E, 0.0, "ease-out")]
    elif kind in {"slide_left", "slide_right"}:
        direction = -1.0 if kind == "slide_left" else 1.0
        sk = [(0, .78 * S, None), (T(.18), 1.06 * S, "ease-out"), (E, S, "ease-out")]
        xk = [(0, bx + direction * 1.18, None), (T(.18), bx - direction * .025, "ease-out"), (E, bx, "ease-out")]
        yk = [(0, by + .015 * direction, None), (E, by, "ease-out")]
        rk = [(0, -direction * 6.0, None), (T(.18), direction * 1.5, "ease-out"), (E, 0.0, "ease-out")]
    elif kind == "drop":
        sk = [(0, .94 * S, None), (T(.16), 1.02 * S, "ease-in"), (T(.22), 1.05 * S, "ease-out"), (E, S, "ease-out")]
        xk = [(0, bx, None), (E, bx, "ease-out")]
        yk = [(0, by - .62, None), (T(.16), by + .035, "ease-in"), (T(.24), by - .015, "ease-out"), (E, by, "ease-in-out")]
        rk = [(0, edge * 3.0, None), (E, 0.0, "ease-out")]
    elif kind == "rise":
        sk = [(0, .84 * S, None), (T(.18), 1.06 * S, "ease-out"), (E, S, "ease-out")]
        xk = [(0, bx, None), (E, bx, "ease-out")]
        yk = [(0, by + .68, None), (T(.18), by - .025, "ease-out"), (E, by, "ease-out")]
        rk = [(0, -edge * 3.0, None), (E, 0.0, "ease-out")]
    elif kind == "diagonal_sweep":
        sk = [(0, .76 * S, None), (T(.18), 1.08 * S, "ease-out"), (E, S, "ease-out")]
        xk = [(0, bx + edge * .88, None), (T(.18), bx - edge * .02, "ease-out"), (E, bx, "ease-out")]
        yk = [(0, by + .62, None), (T(.18), by - .02, "ease-out"), (E, by, "ease-out")]
        rk = [(0, -edge * 8.0, None), (T(.18), edge * 1.5, "ease-out"), (E, 0.0, "ease-out")]
    elif kind == "zoom_through":
        sk = [(0, 1.42 * S, None), (T(.14), .90 * S, "ease-out"), (T(.22), 1.06 * S, "ease-out"), (E, S, "ease-out")]
        xk = [(0, bx + edge * .05, None), (E, bx, "ease-out")]
        yk = [(0, by, None), (E, by, "ease-out")]
        rk = [(0, 0.0, None), (E, 0.0, "ease-out")]
    elif kind == "spin_in":
        sk = [(0, .08 * S, None), (T(.16), 1.10 * S, "ease-out"), (T(.23), .97 * S, "ease-in-out"), (E, S, "ease-out")]
        xk = [(0, bx + edge * .28, None), (E, bx, "ease-out")]
        yk = [(0, by - .18, None), (E, by, "ease-out")]
        rk = [(0, edge * 18.0, None), (T(.16), -edge * 3.0, "ease-out"), (E, 0.0, "ease-out")]
    elif kind == "tilt_pop":
        sk = [(0, .06 * S, None), (T(.15), 1.10 * S, "ease-out"), (T(.23), .98 * S, "ease-in-out"), (E, S, "ease-out")]
        xk = [(0, bx + edge * .05, None), (E, bx, "ease-out")]
        yk = [(0, by + .08, None), (E, by, "ease-out")]
        rk = [(0, -edge * 9.0, None), (T(.20), edge * 2.0, "ease-out"), (E, 0.0, "ease-out")]
    else:  # punch (shock): snap zoom down onto the frame
        sk = [(0, 1.30 * S, None), (T(.12), .97 * S, "ease-out"), (T(.22), 1.0 * S, "ease-out"), (E, S, "ease-out")]
        xk = [(0, bx, None), (E, bx, "ease-out")]
        yk = [(0, by, None), (E, by, "ease-out")]
        rk = [(0, 0.0, None), (E, 0.0, "ease-out")]

    for prop, keys in (("uniform_scale", sk), ("position_x", xk), ("position_y", yk), ("rotation", rk)):
        for t, v, e in keys:
            tl.key(ref, prop, t, v, e)

    hold_len = max(1e-3, xs - E)
    phase = (index % 5) * 1.1
    drift_out = index % 3 == 1
    pan_dir = 1 if index % 2 == 0 else -1

    scale_events: list[tuple[float, float, float, float]] = []
    shake_x: list[tuple[float, float]] = []
    shake_y: list[tuple[float, float]] = []
    rot_events: list[tuple[float, float]] = []
    if hold_len >= 0.9:
        tp = E + hold_len * 0.52
        scale_events.append((tp - .04, tp + .06, tp + .20, .055))
    if shock >= 2 and hold_len >= 0.5:
        te = E + 0.06
        scale_events.append((te, te + .05, te + .22, .12 if shock >= 3 else .07))
        sa = .012 if shock >= 3 else .006
        shake_x = [(te, 0.0)] + [(te + .05 * (i + 1), sa * ((-1) ** i) * (1 - i / 6)) for i in range(5)] + [(te + .36, 0.0)]
        shake_y = [(te, 0.0)] + [(te + .05 * (i + 1), -.6 * sa * ((-1) ** i) * (1 - i / 6)) for i in range(5)] + [(te + .36, 0.0)]
        if shock >= 3:
            rot_events = [(te, 0.0), (te + .06, 1.0), (te + .12, -1.15), (te + .19, .65), (te + .27, -.25), (te + .36, 0.0)]

    def at(t: float) -> tuple[float, float, float, float]:
        p = _clamp((t - E) / hold_len, 0.0, 1.0)
        ramp = _clamp((t - E) / 0.45, 0.0, 1.0)
        base = S * (1.0 - 0.03 * p) if drift_out else S * (1.0 + push * p)
        bump = sum(_tri(t, *ev) for ev in scale_events)
        sc = base * (1.0 + bump) * (1.0 + 0.004 * ramp * math.sin(TAU * t / 1.8 + phase))
        x = bx + pan_dir * pan_amount * p + ramp * 0.006 * math.sin(TAU * t / 2.2 + phase) + _interp(t, shake_x)
        y = by + ramp * 0.009 * math.sin(TAU * t / 1.5 + phase) + _interp(t, shake_y)
        r = ramp * 0.8 * math.sin(TAU * t / 2.0 + phase) + _interp(t, rot_events)
        return sc, x, y, r

    times = {xs}
    n = max(1, int(hold_len / 0.375))
    for i in range(n + 1):
        times.add(E + hold_len * i / n)
    for a, b, c, _ in scale_events:
        times.update((a, b, c))
    for pts in (shake_x, shake_y, rot_events):
        times.update(t for t, _ in pts)
    for t in sorted(t for t in times if E - 1e-6 <= t <= xs + 1e-6):
        sc, x, y, r = at(t)
        tl.key(ref, "uniform_scale", t, sc, "ease-in-out")
        tl.key(ref, "position_x", t, x, "ease-in-out")
        tl.key(ref, "position_y", t, y, "ease-in-out")
        tl.key(ref, "rotation", t, r, "ease-in-out")

    if exit_len > 0:
        sc, x, y, r = at(xs)
        ek = EXITS[index % len(EXITS)]
        if ek == "shrink":
            tl.key(ref, "uniform_scale", xs + 0.4 * (D - xs), sc * 1.05, "ease-out")
            tl.key(ref, "uniform_scale", D, .05 * S, "ease-in")
            tl.key(ref, "rotation", D, r + edge * 6.0, "ease-in")
        elif ek in {"slide_out", "slide_out_left", "slide_out_right"}:
            direction = edge if ek == "slide_out" else (-1.0 if ek == "slide_out_left" else 1.0)
            tl.key(ref, "position_x", D, bx + direction * .98, "ease-in")
            tl.key(ref, "uniform_scale", D, .82 * sc, "ease-in")
            tl.key(ref, "rotation", D, r + direction * 5.0, "ease-in")
        elif ek == "tilt_away":
            tl.key(ref, "position_x", D, bx + edge * .30, "ease-in")
            tl.key(ref, "uniform_scale", D, .82 * sc, "ease-in")
            tl.key(ref, "rotation", D, r + edge * 14.0, "ease-in")
        elif ek == "zoom_away":
            tl.key(ref, "uniform_scale", D, 1.30 * sc, "ease-in")
            tl.key(ref, "position_y", D, by - edge * .06, "ease-in")
        else:
            tl.key(ref, "position_y", D, by + .75, "ease-in")
            tl.key(ref, "uniform_scale", D, .92 * sc, "ease-in")
            tl.key(ref, "rotation", D, r - edge * 4.0, "ease-in")
    return kind


def _make_accent_assets(output_dir: Path) -> dict[str, str]:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return {}
    output_dir.mkdir(parents=True, exist_ok=True)

    def font(size: int) -> Any:
        for name in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
            try:
                return ImageFont.truetype(name, size=size)
            except OSError:
                pass
        return ImageFont.load_default()

    result: dict[str, str] = {}
    for key, glyph, fill, ink in (
        ("exclaim", "!", (224, 36, 36, 255), (255, 255, 255, 255)),
        ("question", "?", (246, 207, 69, 255), (21, 25, 30, 255)),
    ):
        img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((24, 24, 488, 488), fill=fill, outline=(21, 25, 30, 255), width=22)
        fnt = font(330)
        box = draw.textbbox((0, 0), glyph, font=fnt)
        w, h = box[2] - box[0], box[3] - box[1]
        draw.text(((512 - w) / 2 - box[0], (512 - h) / 2 - box[1]), glyph, font=fnt, fill=ink)
        path = output_dir / ("accent_%s.png" % key)
        img.save(path, optimize=True)
        result[key] = str(path.resolve())
    return result



def _prepare_stock_hero(source: Path, output_dir: Path, index: int, width: int, height: int,
                        log: Any) -> Path | None:
    """Create a clean 16:9 crop for selected full-screen stock B-roll shots."""
    try:
        from PIL import Image, ImageEnhance, ImageOps

        with Image.open(source) as raw:
            image = ImageOps.exif_transpose(raw).convert("RGB")
            resampling = getattr(Image, "Resampling", Image).LANCZOS
            image = ImageOps.fit(image, (width, height), method=resampling, centering=(0.5, 0.5))
            # A restrained grade helps photographic inserts sit beside stylised illustrations.
            image = ImageEnhance.Color(image).enhance(0.90)
            image = ImageEnhance.Contrast(image).enhance(1.04)
            output_dir.mkdir(parents=True, exist_ok=True)
            out = output_dir / ("stock_hero_%03d.jpg" % (index + 1))
            image.save(out, quality=92, optimize=True)
            return out.resolve()
    except Exception as exc:
        log("Stock hero image could not be prepared; retaining supplied artwork for scene %d: %s"
            % (index + 1, exc))
        return None


def _plan_boundaries(bm: dict, config: dict, settings: dict, images: list, duration: float,
                     captions: list, target: float, minimum: float) -> tuple[list[float], list[int]]:
    log = bm["log"]
    if settings.get("use_storyboard_boundaries", False):
        try:
            custom = [float(v) for v in config.get("storyboard_boundaries", [])]
            valid = (
                len(custom) == len(images) + 1 and abs(custom[0]) <= 0.05
                and abs(custom[-1] - duration) <= 0.15
                and all(b > a for a, b in zip(custom, custom[1:]))
            )
        except (TypeError, ValueError):
            valid = False
        if valid:
            custom[0] = 0.0
            custom[-1] = round(duration, 3)
            log("Using " + str(len(images)) + " story-aligned storyboard segments.")
            return custom, list(range(len(images)))
        log("Configured storyboard boundaries did not match the images/audio; using automatic timing.")
    shot_count = max(1, max(len(images), int(round(duration / target))))
    shot_count = min(shot_count, max(1, int(duration / minimum)))
    shot_count = min(shot_count, max(1, int(math.ceil(duration / 0.45))))
    boundaries = bm["scene_boundaries"](duration, shot_count, target, minimum, captions)
    return boundaries, bm["choose_scene_indices"](len(images), shot_count)


def _sfx_kind(path: Path) -> str:
    name = path.stem.lower()
    if any(k in name for k in ("whoosh", "swoosh", "swish", "slide", "swipe")):
        return "whoosh"
    if any(k in name for k in ("hit", "impact", "boom", "thud", "bass", "slam", "stinger", "drop")):
        return "hit"
    if any(k in name for k in ("pop", "click", "tick", "ding", "bubble", "blip")):
        return "pop"
    return "other"


def make_hybrid_spec(bm: dict, config: dict, audio: Path, images: list, presenters: list,
                     duration: float, captions: list, captions_path: Any):
    log = bm["log"]
    settings = config.get("settings", {})
    motion = bm["load_motion_preset"](settings)
    canvas = config.get("canvas", {})
    width, height = int(canvas.get("width", 1920)), int(canvas.get("height", 1080))
    target = max(1.0, float(settings.get("target_shot_seconds", motion.get("target_shot_seconds", 2.65))))
    minimum = max(0.75, float(settings.get("minimum_shot_seconds", motion.get("minimum_shot_seconds", 1.25))))
    boundaries, indices = _plan_boundaries(bm, config, settings, images, duration, captions, target, minimum)

    visuals_dir = bm["BUILD_DIR"] / "visuals" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    assets = bm["create_whiteboard_assets"](visuals_dir, width, height, 0, 0, plain_white=True)
    accents = _make_accent_assets(visuals_dir)

    scene_x = float(settings.get("scene_image_x", -0.24))
    scene_y = float(settings.get("scene_image_y", -0.02))
    card_scale = float(settings.get("card_scene_scale", motion.get("card_scene_scale", 0.62)))
    pan_amount = _clamp(float(settings.get("scene_pan_amount", motion.get("scene_pan_amount", 0.012))), 0.0, 0.03)
    push = _clamp(float(settings.get("scene_push", 0.07)), 0.0, 0.15)
    tail = _clamp(float(settings.get("scene_exit_overlap", 0.14)), 0.0, 0.3)

    tl = _Timeline()
    beats = config.get("story_beats", [])
    beats = beats if isinstance(beats, list) else []
    stock_pool = stock_fetcher.load_stock_pool_entries(config, bm["CONFIG_PATH"].parent, log)
    if stock_pool:
        log("Licensed stock pool available: %d photo(s)." % len(stock_pool))
    stock_settings = settings.get("stock_media", {}) or {}
    hero_stock_every = max(0, int(stock_settings.get("hero_every", 5)))
    used_stock_heroes: set[str] = set()

    scene_rows: list[dict[str, Any]] = []
    hero_scale: dict[str, float] = {}
    entrance_kind: dict[str, str] = {}
    scene_tracks: list[list[dict[str, Any]]] = [[], []]
    count = len(indices)

    # ---------------- hero scenes (alternate tracks, using occasional full-screen stock B-roll) ----------------
    for index, image_index in enumerate(indices):
        start, end = boundaries[index], boundaries[index + 1]
        d = max(0.25, end - start)
        is_last = index == count - 1
        clip_len = round(d + (0.0 if is_last else tail), 3)
        original_image_path = images[image_index]
        image_path = original_image_path
        ref = "scene_%03d" % (index + 1)
        mid = (start + end) / 2
        beat_index = next((beat_i for beat_i, item in enumerate(beats)
                           if float(item.get("start_s", 0.0)) <= mid <= float(item.get("end_s", duration))), None)
        beat = beats[beat_index] if beat_index is not None else {}
        stock_source_path: str | None = None
        # On a measured cadence, let a beat-matched stock image briefly take over the frame.
        # The title/opening remains local art; a stock still is never selected just to fill a gap.
        if (stock_pool and hero_stock_every > 0 and index > 0
                and (index + 1) % hero_stock_every == 0 and beat_index is not None):
            candidates = sorted(
                stock_pool,
                key=lambda item: abs(int(item.get("beat", -1)) - beat_index),
            )
            candidate = next((
                item for item in candidates
                if abs(int(item.get("beat", -1)) - beat_index) <= 1
                and Path(str(item.get("path", ""))).is_file()
                and str(Path(str(item.get("path", ""))).resolve()) not in used_stock_heroes
            ), None)
            if candidate:
                source_path = Path(str(candidate["path"])).resolve()
                prepared = _prepare_stock_hero(source_path, visuals_dir, index, width, height, log)
                if prepared:
                    image_path = prepared
                    stock_source_path = str(source_path)
                    used_stock_heroes.add(stock_source_path)

        if image_path.suffix.lower() in VIDEO_SUFFIXES:
            try:
                src_len = bm["audio_duration"](image_path)
                clip_len = round(min(clip_len, max(0.25, src_len - 0.001)), 3)
            except Exception:
                pass
        shock = int(beat.get("shock_level", 0) or 0)
        context = next((str(c["text"]) for c in captions if float(c["start"]) <= mid <= float(c["end"])), "") \
            or str(beat.get("text", ""))
        full_bleed_stock = stock_source_path is not None
        if full_bleed_stock:
            side, bx, by, S = "center", 0.0, 0.0, 1.0
        else:
            side = LAYOUT_CYCLE[index % len(LAYOUT_CYCLE)]
            bx = scene_x if side == "left" else (-scene_x if side == "right" else 0.0)
            by = scene_y
            S = card_scale * (1.06 if side == "center" else 1.0)
        edge = -1 if side == "left" else (1 if side == "right" else (1 if index % 2 else -1))
        media_type = "video" if image_path.suffix.lower() in VIDEO_SUFFIXES else "photo"
        scene_tracks[index % 2].append({
            "type": media_type, "path": str(image_path), "start": round(start, 3),
            "duration": clip_len, "ref": ref, "scale": round(S, 4), "x": bx, "y": by, "rotation": 0,
        })
        tl.clip(ref, clip_len)
        entrance_kind[ref] = scene_motion(tl, ref, clip_len, S, bx, by, index, edge, shock, is_last, pan_amount, push)
        hero_scale[ref] = S
        label = ("C_full_bleed_stock_broll" if full_bleed_stock else
                 {"left": "A_subject-left_host-right", "right": "A_mirrored_subject-right_host-left",
                  "center": "B_centered-hero"}[side])
        scene_rows.append({
            "start": start, "end": end, "duration": d, "image": str(image_path),
            "source_image": str(original_image_path), "stock_source_path": stock_source_path,
            "stock_hero": full_bleed_stock,
            "caption_context": context, "scene_ref": ref, "frame_ref": "frame_%03d" % (index + 1),
            "layout": label, "layout_template": label, "layout_side": side,
            "base_x": bx, "base_y": by, "full_bleed": full_bleed_stock,
            "emotion": str(beat.get("emotion", "calm")), "shock_level": shock,
            "trigger_word": str(beat.get("trigger_word", "")),
        })

    sfx_cues: list[tuple[float, list[str]]] = []
    for row in scene_rows:
        kind = entrance_kind[row["scene_ref"]]
        if row["shock_level"] >= 2 or kind == "punch":
            prefs = ["hit", "pop", "other"]
        elif kind == "slide":
            prefs = ["whoosh", "pop", "other"]
        elif kind == "drop":
            prefs = ["hit", "pop", "other"]
        else:
            prefs = ["pop", "whoosh", "other"]
        sfx_cues.append((row["start"], prefs))

    # ---------------- host (presenter) reset beats ----------------
    presenter_items: list[dict[str, Any]] = []
    presenter_rows: list[dict[str, Any]] = []
    host_scenes: set[str] = set()
    if presenters and settings.get("presenter_overlay", True) and duration >= 4.0:
        cadence = max(6.0, float(settings.get("presenter_reset_every_seconds", 14.0 if duration < 300 else 35.0)))
        hold_want = _clamp(float(settings.get("presenter_reset_duration", 2.4)), 1.0, 4.0)
        host_scale = float(settings.get("presenter_scale", 0.42))
        host_y = float(settings.get("presenter_y", 0.18))
        host_abs = abs(float(settings.get("presenter_x", 0.72)))
        k, pose = 1, 0
        while cadence * k < duration - 3.0:
            want = cadence * k
            k += 1
            row = min((r for r in scene_rows if r["scene_ref"] not in host_scenes and r["start"] >= 1.0),
                      key=lambda r: abs(r["start"] - want), default=None)
            if row is None:
                break
            host_scenes.add(row["scene_ref"])
            start_t = row["start"] + 0.10
            hold = round(min(hold_want, row["end"] - start_t - 0.02), 3)
            if hold < 0.8:
                continue
            side = row["layout_side"]
            host_x = host_abs if side == "left" else (-host_abs if side == "right" else (host_abs if pose % 2 == 0 else -host_abs))
            ref = "presenter_%02d" % (len(presenter_items) + 1)
            presenter_items.append({
                "type": "photo", "path": str(presenters[pose % len(presenters)]), "start": round(start_t, 3),
                "duration": hold, "ref": ref, "scale": host_scale, "x": host_x, "y": host_y,
            })
            tl.clip(ref, hold)
            pop_motion(tl, ref, hold, host_scale, host_x, host_y, tilt=0.0, enter=0.26, exit_len=0.16,
                       float_amp=0.008, from_dx=0.18 if host_x > 0 else -0.18, from_dy=0.10, phase=pose)
            presenter_rows.append({
                "start": start_t, "end": start_t + hold, "image": str(presenters[pose % len(presenters)]),
                "ref": ref, "backplate_ref": "", "side": "left" if host_x < 0 else "right",
            })
            sfx_cues.append((start_t, ["whoosh", "pop", "other"]))
            pose += 1

    # ---------------- layered B-roll collages with varied keyframe recipes ----------------
    insert_items: list[dict[str, Any]] = []
    inserted_per_beat: dict[int, int] = {}
    # Avoid immediate repetition, but allow re-use later in a long story when local art is scarce.
    used_insert_paths: dict[str, int] = {
        str(Path(str(row["stock_source_path"])).resolve()): row_index
        for row_index, row in enumerate(scene_rows) if row.get("stock_source_path")
    }
    if len(images) > 1 or stock_pool:
        # After the opening, keep an extra visual layer present on most scenes. The
        # presenter beats already provide another visual subject, so avoid clutter there.
        insert_every = max(1, int(settings.get("insert_every", 1)))
        for index, row in enumerate(scene_rows):
            # Do not reuse the same source in the next four scenes, but don't exhaust the pool.
            used_insert_paths = {path: last_index for path, last_index in used_insert_paths.items()
                                 if index - last_index <= 4}
            if index == 0 or row["scene_ref"] in host_scenes:
                continue
            if int(row["shock_level"]) < 2 and index % insert_every != 0:
                continue

            mid = (float(row["start"]) + float(row["end"])) / 2.0
            beat_index = next((beat_i for beat_i, beat in enumerate(beats)
                               if float(beat.get("start_s", 0.0)) <= mid
                               <= float(beat.get("end_s", duration))), None)
            avoid_paths = {
                str(Path(str(row["image"])).resolve()),
                str(Path(str(row.get("stock_source_path") or "")).resolve())
                    if row.get("stock_source_path") else "",
            } | set(used_insert_paths)

            # Prefer an unused stock still whose recorded query belongs to this beat or an
            # adjacent beat. Do not insert a distant/abstract search result just to fill space.
            ranked_stock = sorted(
                stock_pool,
                key=lambda item: (
                    abs(int(item.get("beat", -1)) - beat_index) if beat_index is not None else 10_000,
                    not bool(item.get("alpha_channel", False)),
                ),
            )
            pick: Path | None = None
            for candidate in ranked_stock:
                candidate_path = Path(str(candidate.get("path", ""))).resolve()
                if not candidate_path.is_file() or str(candidate_path) in avoid_paths:
                    continue
                if beat_index is not None and abs(int(candidate.get("beat", -1)) - beat_index) > 1:
                    continue
                pick = candidate_path
                break

            # Local artwork remains the reliable fallback when a suitable licensed image
            # is unavailable. Choose a different image from the hero layer.
            if pick is None:
                src = indices[index] if index < len(indices) else index % len(images)
                for step in range(1, len(images) + 1):
                    candidate_path = images[(src + step) % len(images)].resolve()
                    if candidate_path.suffix.lower() in VIDEO_SUFFIXES:
                        continue
                    if str(candidate_path) not in avoid_paths:
                        pick = candidate_path
                        break
            if pick is None:
                continue

            layout = mr.overlay_layout(index, float(row.get("base_x", 0.0)),
                                       int(row.get("shock_level", 0)))
            offset = min(0.30, float(row["duration"]) * 0.14)
            base_duration = min(float(row["duration"]) * 0.82, float(row["duration"]) - offset - 0.18)
            if base_duration < 0.42:
                continue

            for slot_index, slot in enumerate(layout["slots"]):
                layer_path = pick
                if slot_index > 0:
                    # A paired collage gets a second, distinct picture. Prefer another
                    # relevant stock item; if none exists, use a different supplied image.
                    layer_path = None
                    for candidate in ranked_stock:
                        candidate_path = Path(str(candidate.get("path", ""))).resolve()
                        if not candidate_path.is_file() or str(candidate_path) in avoid_paths:
                            continue
                        if beat_index is not None and abs(int(candidate.get("beat", -1)) - beat_index) > 1:
                            continue
                        layer_path = candidate_path
                        break
                    if layer_path is None:
                        src = indices[index] if index < len(indices) else index % len(images)
                        for step in range(2, len(images) + 2):
                            candidate_path = images[(src + step) % len(images)].resolve()
                            if candidate_path.suffix.lower() in VIDEO_SUFFIXES:
                                continue
                            if str(candidate_path) not in avoid_paths and candidate_path != pick:
                                layer_path = candidate_path
                                break
                if layer_path is None or str(layer_path) in avoid_paths:
                    continue

                stagger = mr.staggered_pair_offsets(index)[slot_index]
                start_at = round(float(row["start"]) + offset + stagger, 3)
                dur = round(min(base_duration, float(row["end"]) - start_at - 0.08), 3)
                if dur < 0.36:
                    continue

                tx, ty, scale = float(slot["x"]), float(slot["y"]), float(slot["scale"])
                ref = "secondary_%03d" % (len(insert_items) + 1)
                suffix = layer_path.suffix.lower()
                media_type = "video" if suffix in VIDEO_SUFFIXES else "photo"
                insert_items.append({
                    "type": media_type, "path": str(layer_path), "start": start_at,
                    "duration": dur, "ref": ref, "scale": scale, "x": tx, "y": ty,
                })
                used_insert_paths[str(layer_path)] = index
                avoid_paths.add(str(layer_path))
                tl.clip(ref, dur)
                mr.apply_layer_motion(tl, ref, dur, scale, tx, ty, str(slot["recipe"]), index + slot_index)
                if slot_index == 0:
                    sfx_cues.append((start_at, ["pop", "whoosh", "other"]))
            inserted_per_beat[beat_index if beat_index is not None else index] = (
                inserted_per_beat.get(beat_index if beat_index is not None else index, 0)
                + len(layout["slots"])
            )

    # ---------------- accent badges (! on shock, ? on questions) ----------------
    badge_items: list[dict[str, Any]] = []
    if accents:
        for index, row in enumerate(scene_rows):
            blob = row["caption_context"] + " " + row["trigger_word"]
            if row["shock_level"] >= 2:
                key = "exclaim"
            elif "?" in blob or "؟" in blob:
                key = "question"
            else:
                continue
            if row["scene_ref"] in host_scenes:
                continue
            start_t = row["start"] + 0.30
            dur = round(min(1.1, row["end"] - start_t - 0.10), 3)
            if dur < 0.5:
                continue
            S = hero_scale[row["scene_ref"]]
            corner = 1.0 if row["base_x"] <= 0 else -1.0
            x = _clamp(row["base_x"] + corner * S * 0.86, -0.92, 0.92)
            y = row["base_y"] - S * 0.84
            ref = "badge_%03d" % (len(badge_items) + 1)
            badge_items.append({
                "type": "photo", "path": accents[key], "start": round(start_t, 3), "duration": dur,
                "ref": ref, "scale": 0.17, "x": round(x, 3), "y": round(y, 3),
            })
            tl.clip(ref, dur)
            pop_motion(tl, ref, dur, 0.17, x, y, tilt=corner * 8.0, enter=0.24, exit_len=0.14,
                       float_amp=0.012, from_dy=0.0, phase=index)
            sfx_cues.append((start_t, ["hit", "pop", "other"] if key == "exclaim" else ["pop", "other"]))

    # ---------------- configured icon overlays ----------------
    icon_items: list[dict[str, Any]] = []
    for index, overlay in enumerate(settings.get("icon_overlays", []), start=1):
        raw = str(overlay.get("path", "")).strip()
        icon_path = Path(os.path.expandvars(raw)).expanduser()
        if not icon_path.is_absolute():
            icon_path = bm["CONFIG_PATH"].parent / icon_path
        if not icon_path.is_file():
            log("Configured icon overlay is missing; skipped: " + raw)
            continue
        try:
            requested = max(0.25, float(overlay.get("duration", 1.4)))
            if overlay.get("start_seconds") is not None:
                start = max(0.0, float(overlay["start_seconds"]))
                scene = next((r for r in scene_rows if r["start"] <= start < r["end"]), None)
            else:
                scene = next((r for r in scene_rows if r["scene_ref"] == str(overlay.get("scene_id", "")).strip()), None)
                start = (scene["start"] + max(0.0, float(overlay.get("offset", 0.35)))) if scene else 0.0
            if scene is None:
                log("Icon overlay references an unknown scene/time; skipped.")
                continue
            end = min(scene["end"], start + requested)
            scale = float(overlay.get("scale", 0.16))
            x, y = float(overlay.get("x", -0.56)), float(overlay.get("y", -0.42))
            if start >= scene["end"] or end - start < 0.25:
                continue
            if not (0.03 <= scale <= 1.0 and -1.0 <= x <= 1.0 and -1.0 <= y <= 1.0):
                log("Invalid icon transform; skipped.")
                continue
            ref = "icon_%03d" % index
            dur = round(end - start, 3)
            icon_items.append({"type": "photo", "path": str(icon_path.resolve()), "start": round(start, 3),
                               "duration": dur, "ref": ref, "scale": scale, "x": x, "y": y})
            tl.clip(ref, dur)
            pop_motion(tl, ref, dur, scale, x, y, tilt=0.0, enter=0.22, exit_len=0.14,
                       float_amp=0.012, from_dy=0.06, phase=index)
        except (TypeError, ValueError):
            log("Invalid icon overlay settings; skipped: " + repr(overlay))

    # ---------------- story fact callouts (transparent full-frame PNGs) ----------------
    fact_items: list[dict[str, Any]] = []
    if settings.get("show_fact_callouts", True):
        for index, overlay in enumerate(settings.get("callout_overlays", []), start=1):
            raw = str(overlay.get("path", "")).strip()
            path = Path(os.path.expandvars(raw)).expanduser()
            if not path.is_absolute():
                path = bm["CONFIG_PATH"].parent / path
            if not path.is_file():
                log("Story fact callout image not found; skipped: " + raw)
                continue
            try:
                start = max(0.0, float(overlay.get("start_seconds", 0.0)))
                if start >= duration:
                    continue
                seg = round(min(max(0.25, float(overlay.get("duration", 1.15))), duration - start), 3)
                ref = "story_callout_%03d" % index
                fact_items.append({"type": "photo", "path": str(path.resolve()), "start": round(start, 3),
                                   "duration": seg, "ref": ref, "scale": 1.0, "x": 0.0, "y": 0.0})
                tl.clip(ref, seg)
                tl.key(ref, "uniform_scale", 0.0, 0.94)
                tl.key(ref, "uniform_scale", 0.14, 1.04, "ease-out")
                tl.key(ref, "uniform_scale", 0.24, 1.0, "ease-out")
            except (TypeError, ValueError):
                log("Invalid story callout settings; skipped: " + repr(overlay))

    # ---------------- flash + horror tint ----------------
    def overlay_track(path_key: str, times_key: str, dur_key: str, dur_default: float,
                      dur_min: float, dur_max: float, prefix: str) -> list[dict[str, Any]]:
        raw = str(settings.get(path_key, "")).strip()
        if not raw:
            return []
        path = Path(os.path.expandvars(raw)).expanduser()
        if not path.is_absolute():
            path = bm["CONFIG_PATH"].parent / path
        if not path.is_file():
            log("Configured overlay image not found; skipped: " + raw)
            return []
        items = []
        for index, raw_start in enumerate(settings.get(times_key, []), start=1):
            try:
                start = max(0.0, float(raw_start))
                if start >= duration:
                    continue
                length = min(dur_max, max(dur_min, float(settings.get(dur_key, dur_default))))
                items.append({"type": "photo", "path": str(path.resolve()), "start": round(start, 3),
                              "duration": round(min(length, duration - start), 3),
                              "ref": "%s_%02d" % (prefix, index), "scale": 1.0, "x": 0.0, "y": 0.0})
            except (TypeError, ValueError):
                log("Invalid overlay time skipped: " + repr(raw_start))
        return items

    horror_items = overlay_track("horror_overlay_path", "horror_overlay_times", "horror_overlay_duration", 0.62, 0.25, 0.72, "horror_tint")
    flash_items = overlay_track("flash_overlay_path", "flash_times", "flash_duration", 0.067, 0.05, 0.09, "shock_flash")

    # ---------------- concise, collision-aware keyword callouts ----------------
    callout_items: list[dict[str, Any]] = []
    callout_kinds: dict[str, str] = {}
    if settings.get("keyword_callouts", True):
        min_shock = int(settings.get("keyword_callout_min_shock", 1))
        font_size = int(settings.get("callout_font_size", 20))
        for index, row in enumerate(scene_rows):
            word = re.sub(r"\s+", " ", str(row.get("trigger_word", ""))).strip()
            if not word or len(word.split()) > 3:
                continue
            if int(row.get("shock_level", 0)) < min_shock and index % 3 != 0:
                continue
            start_t = float(row["start"]) + 0.22
            dur = round(min(1.15, float(row["duration"]) - 0.32), 3)
            if dur < 0.6:
                continue
            kind = ts.classify(word, int(row.get("shock_level", 0)))
            scale = hero_scale[row["scene_ref"]]
            x, y = ts.safe_xy(float(row["base_x"]), float(row["base_y"]) + scale + 0.12)
            ref = "kw_%03d" % (len(callout_items) + 1)
            callout_kinds[ref] = kind
            callout_items.append({
                "text": word.upper(), "start": round(start_t, 3), "duration": dur,
                "fontSize": ts.size_for(kind, font_size, word),
                "color": ts.style_for(kind)[0], "x": x, "y": y, "ref": ref,
            })
        ts.avoid_collisions(callout_items)
        for item_index, item in enumerate(callout_items):
            tl.clip(item["ref"], item["duration"])
            tl.other.append({
                "op": "text-style", "target": item["ref"],
                "style": ts.style_for(callout_kinds[item["ref"]])[1],
            })
            ts.text_motion(
                tl, item["ref"], item["duration"], item["y"], settings.get("text_caps"),
                recipe=ts.choose_text_recipe(callout_kinds[item["ref"]], item_index),
                x=float(item["x"]), direction=-1.0 if float(item["x"]) < 0 else 1.0,
            )

    # ---------------- chapter titles (small, dark, top) ----------------
    chapter_items: list[dict[str, Any]] = []
    for index, chapter in enumerate(config.get("chapter_titles", []), start=1):
        try:
            c_start = max(0.0, float(chapter.get("start_s", 0.0)))
            c_end = min(duration, c_start + max(0.9, float(chapter.get("duration_s", 1.6))))
            title = str(chapter.get("title", "")).strip()
            if not title or c_end <= c_start:
                continue
            color = str(chapter.get("color", "#15191E"))
            if color.strip().lower() in {"#fff", "#ffffff", "white"}:
                color = "#15191E"
            size = ts.size_for("chapter", min(int(chapter.get("font_size", 18)),
                                               int(settings.get("chapter_font_max", 22))), title)
            x, y = ts.safe_xy(float(chapter.get("x", 0.0)), float(chapter.get("y", -0.86)))
            ref = "chapter_title_%02d" % index
            chapter_items.append({"text": title, "start": round(c_start, 3), "duration": round(c_end - c_start, 3),
                                  "fontSize": size, "color": color, "x": x, "y": y, "ref": ref})
            tl.clip(ref, c_end - c_start)
            tl.other.append({"op": "text-style", "target": ref, "style": ts.style_for("chapter")[1]})
            ts.text_motion(
                tl, ref, c_end - c_start, y, settings.get("text_caps"),
                recipe=ts.choose_text_recipe("chapter", index - 1), x=x,
                direction=-1.0 if x < 0 else 1.0,
            )
        except (TypeError, ValueError):
            log("Invalid chapter title record skipped: " + repr(chapter))

    # ---------------- audio: narration, music, explicit + automatic SFX ----------------
    audio_items = [{"path": str(audio), "start": 0.0, "duration": round(duration, 3),
                    "volume": float(settings.get("voice_volume", 0.96)), "ref": "voiceover"}]
    pool: list[dict[str, Any]] = []
    sfx_items: list[dict[str, Any]] = []
    for index, item in enumerate(settings.get("sound_effects", [])):
        path = Path(os.path.expandvars(str(item.get("path", "")))).expanduser()
        if not path.is_file():
            log("Optional local SFX path was not found; skipped: " + str(item.get("path", "")))
            continue
        pool.append({"path": path, "volume": float(item.get("volume", 0.16)), "kind": _sfx_kind(path)})
        try:
            start = max(0.0, float(item.get("start", 0.0)))
            length = float(item.get("duration", 0.0)) or min(5.0, max(0.3, duration - start))
            if start >= duration:
                continue
            length = bm["bounded_audio_clip_duration"](path, min(length, duration - start))
            if length < 0.03:
                continue
            sfx_items.append({"path": str(path.resolve()), "start": round(start, 3), "duration": length,
                              "volume": float(item.get("volume", 0.16)), "ref": "local_sfx_%02d" % (index + 1)})
        except (TypeError, ValueError):
            log("Invalid optional SFX entry skipped: " + str(item))

    if settings.get("auto_entrance_sfx", True) and pool:
        explicit = [i["start"] for i in sfx_items]
        counters: dict[str, int] = {}

        def pick(prefs: list[str]) -> dict[str, Any]:
            for pref in prefs:
                options = [p for p in pool if p["kind"] == pref]
                if options:
                    choice = options[counters.get(pref, 0) % len(options)]
                    counters[pref] = counters.get(pref, 0) + 1
                    return choice
            choice = pool[counters.get("any", 0) % len(pool)]
            counters["any"] = counters.get("any", 0) + 1
            return choice

        for t, prefs in sorted(sfx_cues, key=lambda c: c[0]):
            if t >= duration - 0.05 or any(abs(t - s) <= 0.10 for s in explicit):
                continue
            choice = pick(prefs)
            length = bm["bounded_audio_clip_duration"](choice["path"], 0.6)
            if length < 0.03:
                continue
            sfx_items.append({"path": str(choice["path"].resolve()), "start": round(t, 3), "duration": length,
                              "volume": round(_clamp(choice["volume"], 0.10, 0.22), 3),
                              "ref": "auto_sfx_%03d" % (len(sfx_items) + 1)})

    sfx_items.sort(key=lambda it: it["start"])
    resolved: list[dict[str, Any]] = []
    for item in sfx_items:
        if resolved:
            prev = resolved[-1]
            gap = item["start"] - prev["start"]
            if gap < prev["duration"] + 0.005:
                trimmed = round(gap - 0.005, 3)
                if trimmed < 0.05:
                    resolved.pop()
                else:
                    prev["duration"] = trimmed
        resolved.append(item)

    music_items: list[dict[str, Any]] = []
    music_cfg = config.get("background_music", {})
    if isinstance(music_cfg, str):
        music_cfg = {"path": music_cfg}
    music_raw = str(music_cfg.get("path", "")).strip() if isinstance(music_cfg, dict) else ""
    if music_raw:
        music_path = Path(os.path.expandvars(music_raw)).expanduser()
        if not music_path.is_absolute():
            music_path = bm["CONFIG_PATH"].parent / music_path
        if music_path.is_file():
            m_start = max(0.0, float(music_cfg.get("start", 0.0)))
            m_end = min(duration, m_start + max(0.0, float(music_cfg.get("duration", duration))))
            if m_end > m_start:
                music_items.append({"path": str(music_path.resolve()), "start": round(m_start, 3),
                                    "duration": round(m_end - m_start, 3),
                                    "volume": max(0.0, min(1.0, float(music_cfg.get("volume", 0.22)))),
                                    "ref": "background_suspense_bed"})
        else:
            log("Configured background music was not found; skipped: " + str(music_path))

    # ---------------- assemble tracks ----------------
    tracks: list[dict[str, Any]] = [
        {"type": "video", "name": "Whiteboard Background", "items": [{
            "type": "photo", "path": assets["background"], "start": 0.0, "duration": round(duration, 3),
            "ref": "whiteboard_background", "scale": 1.0, "x": 0.0, "y": 0.0}]},
        {"type": "video", "name": "Scene Artwork", "items": scene_tracks[0]},
    ]
    if scene_tracks[1]:
        tracks.append({"type": "video", "name": "Scene Artwork B", "items": scene_tracks[1]})
    if insert_items:
        tracks.append({"type": "video", "name": "Fast Secondary Image Inserts", "items": insert_items})
    if horror_items:
        tracks.append({"type": "video", "name": "Critical Horror Tint", "items": horror_items})
    if badge_items:
        tracks.append({"type": "video", "name": "Accent Badges", "items": badge_items})
    if icon_items:
        tracks.append({"type": "video", "name": "Icon Overlays", "items": icon_items})
    if presenter_items:
        tracks.append({"type": "video", "name": "Presenter Explainer", "items": presenter_items})
    if fact_items:
        tracks.append({"type": "video", "name": "Story Fact Callouts", "items": fact_items})
    if flash_items:
        tracks.append({"type": "video", "name": "Shock Flash Hits", "items": flash_items})
    if callout_items:
        tracks.append({"type": "text", "name": "Keyword Callouts", "items": callout_items})
    if chapter_items:
        tracks.append({"type": "text", "name": "Chapter Titles", "items": chapter_items})
    if music_items:
        tracks.append({"type": "audio", "name": "Suspense Music / Ambience", "items": music_items})
    tracks.append({"type": "audio", "name": "Narration", "items": audio_items})
    if resolved:
        tracks.append({"type": "audio", "name": "Local Sound Effects", "items": resolved})

    spec = {
        "name": str(config.get("project_name", "Video1 Test - Whiteboard Explainer PRO")),
        "width": width, "height": height, "fps": int(canvas.get("fps", 30)),
        "ratio": str(canvas.get("ratio", "16:9")), "tracks": tracks, "operations": tl.ops(),
    }
    for issue in audit_spec(spec, duration=duration):
        log("QA: " + issue)
    return spec, scene_rows, presenter_rows