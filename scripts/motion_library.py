"""Context-aware, deterministic motion recipe catalogue for all renderers.

The catalogue has 16 distinct motion families and 14 choreographies per family.
Recipes describe GSAP-compatible property states; renderers translate them into
their own execution format without changing shot timing or story intent.
"""
from __future__ import annotations

from hashlib import sha256
from itertools import product
from typing import Any

DIRECTIONS = ("left", "right", "up", "down")
ENERGIES = ("subtle", "balanced", "dramatic")
EASES = ("power2.out", "power3.out", "power4.out", "expo.out")

FAMILIES = (
    ("pan_reveal", "image_entrance", "Directional camera-style reveal"),
    ("scale_focus", "image_entrance", "Optical push or pull into the focal subject"),
    ("diagonal_sweep", "image_entrance", "Diagonal image entrance with controlled settle"),
    ("depth_dolly", "image_entrance", "Perspective-inspired depth push with blur settle"),
    ("tilt_settle", "image_entrance", "Measured rotational reveal and counter-rotation"),
    ("iris_reveal", "image_entrance", "Circular aperture reveal"),
    ("split_reveal", "image_entrance", "Directional split-mask uncover"),
    ("radial_reveal", "image_entrance", "Radial mask expansion with scale settle"),
    ("blur_focus", "image_entrance", "Defocused image resolves into a sharp subject"),
    ("parallax_drift", "camera", "Layer-aware foreground/background drift"),
    ("whip_pan", "transition", "Fast directional camera hand-off"),
    ("push_transition", "transition", "Incoming and outgoing shots exchange screen space"),
    ("orbit_object", "element", "Independent object orbit around its anchor"),
    ("float_drift", "element", "Low-amplitude environmental floating motion"),
    ("path_follow", "element", "Object travels along a curved screen path"),
    ("mask_uncover", "transition", "Layered geometric mask uncovers the next visual"),
)

_VARIANT_ROWS = tuple(
    (direction, energy, EASES[(i + (0 if direction in {"left", "right"} else 1)) % len(EASES)])
    for i, (direction, energy) in enumerate(
        (pair for pair in product(DIRECTIONS, ENERGIES) for _ in range(2))
    )
)[:14]


def _sign(direction: str) -> tuple[float, float]:
    return {
        "left": (-1.0, 0.0),
        "right": (1.0, 0.0),
        "up": (0.0, -1.0),
        "down": (0.0, 1.0),
    }[direction]


def _energy(energy: str) -> float:
    return {"subtle": 0.55, "balanced": 1.0, "dramatic": 1.45}[energy]


def _states(family: str, direction: str, energy: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    sx, sy = _sign(direction)
    amount = _energy(energy)
    travel = 54.0 * amount
    rotation = 5.0 * amount
    base = {"autoAlpha": 1.0, "x": 0, "y": 0, "scale": 1, "rotation": 0, "filter": "blur(0px)"}
    if family == "pan_reveal":
        start = {"autoAlpha": 0, "x": round(sx * travel, 2), "y": round(sy * travel * .18, 2), "scale": .985}
        enter = {**base, "duration": .68 / amount}
        exit = {"autoAlpha": 0, "x": round(-sx * travel * .75, 2), "duration": .46 / amount}
    elif family == "scale_focus":
        start = {"autoAlpha": 0, "scale": round(1.0 - .18 * amount, 4), "filter": "blur(8px)"}
        enter = {**base, "duration": .78 / amount}
        exit = {"autoAlpha": 0, "scale": round(1.08 + .05 * amount, 4), "filter": "blur(5px)", "duration": .52 / amount}
    elif family == "diagonal_sweep":
        start = {"autoAlpha": 0, "x": round(sx * travel, 2), "y": round(sy * travel, 2), "rotation": round(-sx * rotation, 2), "scale": .94}
        enter = {**base, "duration": .72 / amount}
        exit = {"autoAlpha": 0, "x": round(-sx * travel * .72, 2), "y": round(-sy * travel * .48, 2), "duration": .5 / amount}
    elif family == "depth_dolly":
        start = {"autoAlpha": 0, "scale": round(1.28 + .12 * amount, 4), "filter": "blur(12px)"}
        enter = {**base, "duration": .84 / amount}
        exit = {"autoAlpha": 0, "scale": .82, "filter": "blur(9px)", "duration": .56 / amount}
    elif family == "tilt_settle":
        start = {"autoAlpha": 0, "rotation": round(sx * 13 * amount, 2), "y": round(sy * 24 * amount, 2), "scale": .92}
        enter = {**base, "duration": .66 / amount}
        exit = {"autoAlpha": 0, "rotation": round(-sx * 9 * amount, 2), "y": round(-sy * 28 * amount, 2), "duration": .48 / amount}
    elif family == "iris_reveal":
        start = {"autoAlpha": 1, "clipPath": "circle(0% at 50% 50%)", "scale": .96}
        enter = {"clipPath": "circle(75% at 50% 50%)", "scale": 1, "duration": .82 / amount}
        exit = {"clipPath": "circle(0% at 50% 50%)", "duration": .52 / amount}
    elif family == "split_reveal":
        inset = "100% 0% 0% 0%" if direction == "down" else (
            "0% 100% 0% 0%" if direction == "left" else (
                "0% 0% 100% 0%" if direction == "up" else "0% 0% 0% 100%"
            )
        )
        start = {"autoAlpha": 1, "clipPath": f"inset({inset})", "x": round(sx * 12 * amount, 2)}
        enter = {"clipPath": "inset(0% 0% 0% 0%)", "x": 0, "duration": .76 / amount}
        exit = {"clipPath": f"inset({inset})", "duration": .5 / amount}
    elif family == "radial_reveal":
        start = {"autoAlpha": 1, "clipPath": "polygon(50% 50%, 50% 50%, 50% 50%)", "scale": .96}
        enter = {"clipPath": "circle(74% at 50% 50%)", "scale": 1, "duration": .74 / amount}
        exit = {"clipPath": "circle(0% at 50% 50%)", "duration": .5 / amount}
    elif family == "blur_focus":
        start = {"autoAlpha": 0, "filter": "blur(18px)", "scale": 1.035}
        enter = {**base, "duration": .92 / amount}
        exit = {"autoAlpha": 0, "filter": "blur(16px)", "duration": .64 / amount}
    elif family == "parallax_drift":
        start = {"x": round(-sx * 26 * amount, 2), "y": round(-sy * 14 * amount, 2), "scale": 1.04}
        enter = {"x": 0, "y": 0, "scale": 1.0, "duration": 1.4 / amount}
        exit = {"x": round(sx * 22 * amount, 2), "scale": 1.045, "duration": 1.0 / amount}
    elif family == "whip_pan":
        start = {"autoAlpha": 0, "x": round(sx * 280 * amount, 2), "filter": "blur(0px)"}
        enter = {"autoAlpha": 1, "x": 0, "duration": .34 / amount, "ease": "power4.out"}
        exit = {"autoAlpha": 0, "x": round(-sx * 300 * amount, 2), "duration": .3 / amount, "filter": "blur(0px)"}
    elif family == "push_transition":
        start = {"x": round(sx * 100 * amount, 2), "scale": .96}
        enter = {"x": 0, "scale": 1, "duration": .72 / amount}
        exit = {"x": round(-sx * 90 * amount, 2), "scale": 1.035, "duration": .72 / amount}
    elif family == "orbit_object":
        start = {"autoAlpha": 0, "x": round(sx * 34 * amount, 2), "y": round(sy * 34 * amount, 2), "rotation": round(-sx * 18 * amount, 2), "scale": .84}
        enter = {"autoAlpha": 1, "x": 0, "y": 0, "rotation": 0, "scale": 1, "duration": .7 / amount}
        exit = {"autoAlpha": 0, "rotation": round(sx * 26 * amount, 2), "scale": .9, "duration": .48 / amount}
    elif family == "float_drift":
        start = {"autoAlpha": 0, "y": round(sy * 22 * amount, 2), "scale": .97}
        enter = {"autoAlpha": 1, "y": 0, "scale": 1, "duration": .8 / amount}
        exit = {"autoAlpha": 0, "y": round(-sy * 16 * amount, 2), "duration": .56 / amount}
    elif family == "path_follow":
        start = {"autoAlpha": 0, "x": round(sx * 100 * amount, 2), "y": round(-sy * 55 * amount, 2), "rotation": round(-sx * 8 * amount, 2)}
        enter = {"autoAlpha": 1, "x": 0, "y": 0, "rotation": 0, "duration": .92 / amount}
        exit = {"autoAlpha": 0, "x": round(-sx * 80 * amount, 2), "y": round(sy * 40 * amount, 2), "duration": .62 / amount}
    else:  # mask_uncover
        start = {"autoAlpha": 1, "clipPath": "inset(0% 100% 0% 0%)"}
        enter = {"clipPath": "inset(0% 0% 0% 0%)", "duration": .78 / amount}
        exit = {"clipPath": "inset(0% 0% 0% 100%)", "duration": .54 / amount}
    enter["ease"] = EASES[(DIRECTIONS.index(direction) + ENERGIES.index(energy)) % len(EASES)]
    exit["ease"] = "power2.in"
    return start, enter, exit


def build_catalog() -> dict[str, dict[str, Any]]:
    catalogue: dict[str, dict[str, Any]] = {}
    for family, category, purpose in FAMILIES:
        for variant_index, (direction, energy, ease) in enumerate(_VARIANT_ROWS, start=1):
            start, enter, exit_state = _states(family, direction, energy)
            # Easing and path differences are real choreography data, not duration-only aliases.
            enter["ease"] = ease
            identity = f"{family}_{direction}_{energy}_{variant_index:02d}"
            catalogue[identity] = {
                "id": identity,
                "family": family,
                "category": category,
                "purpose": purpose,
                "direction": direction,
                "energy": energy,
                "enter": {"from": start, "to": enter},
                "exit": {"to": exit_state},
                "hold": {"scale": 1.0, "autoAlpha": 1.0},
                "recommended_for": {
                    "tense": ["balanced", "dramatic"],
                    "solemn": ["subtle"],
                    "calm": ["subtle", "balanced"],
                }[energy] if energy in {"subtle", "balanced"} else ["shock", "action"],
            }
    return catalogue


CATALOG = build_catalog()


def get_recipe(recipe_id: str) -> dict[str, Any]:
    try:
        return CATALOG[recipe_id]
    except KeyError as exc:
        raise ValueError(f"Unknown motion recipe: {recipe_id}") from exc


def list_recipes(category: str | None = None) -> list[dict[str, Any]]:
    values = list(CATALOG.values())
    return [item for item in values if category is None or item["category"] == category]


def choose_recipe(role: str, emotion: str, shock_level: int, stable_id: str,
                  recent_ids: list[str] | None = None) -> dict[str, Any]:
    """Choose a deterministic context-aware recipe while avoiding a recent repeat."""
    roles = {
        "entrance": {"image_entrance"},
        "exit": {"image_entrance", "element"},
        "transition": {"transition"},
        "camera": {"camera"},
        "element": {"element"},
    }
    allowed = roles.get(role, set(CATALOG[item]["category"] for item in CATALOG))
    candidates = [item for item in CATALOG.values() if item["category"] in allowed]
    mood = str(emotion or "").strip().lower().replace("-", "_")
    if mood in {"sad", "solemn", "grief", "somber"}:
        candidates = [item for item in candidates if item["energy"] == "subtle" and item["family"] not in {"whip_pan", "tilt_settle"}]
    elif int(shock_level) >= 3:
        candidates = [item for item in candidates if item["energy"] in {"balanced", "dramatic"}]
    elif mood in {"calm", "neutral", "setup"}:
        candidates = [item for item in candidates if item["energy"] != "dramatic"]
    recent = set(recent_ids or [])
    fresh = [item for item in candidates if item["id"] not in recent]
    if fresh:
        candidates = fresh
    if not candidates:
        candidates = list(CATALOG.values())
    digest = sha256(str(stable_id).encode("utf-8")).digest()
    return candidates[int.from_bytes(digest[:4], "big") % len(candidates)]


def apply_capcut_motion(timeline: Any, target: str, duration: float,
                        base_scale: float, x: float, y: float,
                        recipe: dict[str, Any], phase: int = 0) -> None:
    """Translate a catalogue recipe into CapCut's verified transform properties.

    CapCut receives only uniform_scale, position_x, position_y and rotation.
    Masks, opacity, blur and complex paths remain in the HyperFrames/Remotion
    renderers; this function gives the editable source-photo track a compatible
    motion approximation without inventing unsupported CapCut property names.
    """
    d = max(0.28, float(duration))
    s = max(0.04, float(base_scale))
    family = str(recipe.get("family", "pan_reveal"))
    direction = str(recipe.get("direction", "left"))
    energy = str(recipe.get("energy", "balanced"))
    sx, sy = _sign(direction)
    magnitude = _energy(energy)
    enter = min(0.38, max(0.16, d * 0.20))
    exit_len = min(0.30, max(0.14, d * 0.16))
    exit_at = max(enter + 0.08, d - exit_len)

    start_x, start_y, start_scale, start_rotation = x, y, s, 0.0
    end_x, end_y, end_scale, end_rotation = x, y, s, 0.0
    distance = 0.52 * magnitude

    if family in {"pan_reveal", "split_reveal", "mask_uncover"}:
        start_x, start_y, start_scale = x + sx * distance, y + sy * distance * .12, .94 * s
        end_x, end_y = x - sx * distance * .52, y - sy * distance * .18
    elif family in {"scale_focus", "depth_dolly", "blur_focus", "iris_reveal", "radial_reveal"}:
        start_scale = (1.22 if family == "depth_dolly" else .76 if family == "scale_focus" else 1.12) * s
        end_scale = (1.045 if family == "depth_dolly" else .96) * s
    elif family == "diagonal_sweep":
        start_x, start_y, start_scale = x + sx * distance, y + sy * distance, .91 * s
        start_rotation = -sx * 5.0 * magnitude
        end_x, end_y, end_rotation = x - sx * distance * .35, y - sy * distance * .24, 0.0
    elif family == "tilt_settle":
        start_x, start_y, start_scale, start_rotation = x + sx * .10, y + sy * .08, .94 * s, sx * 12 * magnitude
        end_rotation = -sx * 1.2
    elif family == "parallax_drift":
        start_scale, end_scale = 1.015 * s, 1.065 * s
        start_x, end_x = x - sx * .035, x + sx * .035
        start_y, end_y = y - sy * .018, y + sy * .018
    elif family == "whip_pan":
        start_x, start_scale = x + sx * 1.15, 1.04 * s
        end_x, end_scale = x - sx * .95, 1.08 * s
    elif family == "push_transition":
        start_x, start_scale = x + sx * .72, .94 * s
        end_x, end_scale = x - sx * .55, 1.035 * s
    elif family == "orbit_object":
        start_x, start_y, start_scale, start_rotation = x + sx * .18, y + sy * .14, .86 * s, -sx * 18 * magnitude
        end_rotation = sx * 8 * magnitude
    elif family == "float_drift":
        start_y, start_scale = y + sy * .26, .96 * s
        end_y, end_scale = y - sy * .035, 1.015 * s
    elif family == "path_follow":
        start_x, start_y, start_scale = x + sx * .62, y - sy * .34, .9 * s
        end_x, end_y, end_scale = x - sx * .12, y + sy * .08, s
    else:
        start_x, start_scale = x + sx * distance, .92 * s
        end_x = x - sx * distance * .4

    timeline.key(target, "position_x", 0.0, start_x)
    timeline.key(target, "position_y", 0.0, start_y)
    timeline.key(target, "uniform_scale", 0.0, start_scale)
    timeline.key(target, "rotation", 0.0, start_rotation)
    timeline.key(target, "position_x", enter, x, "ease-out")
    timeline.key(target, "position_y", enter, y, "ease-out")
    timeline.key(target, "uniform_scale", enter, s, "ease-out")
    timeline.key(target, "rotation", enter, 0.0, "ease-out")

    # A restrained mid-shot camera move keeps a still alive without adding jitter.
    hold_mid = enter + max(0.08, (exit_at - enter) * .55)
    wobble = .006 * magnitude
    timeline.key(target, "position_x", hold_mid, x + sx * wobble, "ease-in-out")
    timeline.key(target, "position_y", hold_mid, y - sy * wobble * .65, "ease-in-out")
    timeline.key(target, "uniform_scale", hold_mid, (s + end_scale) / 2.0, "ease-in-out")
    timeline.key(target, "position_x", exit_at, x, "ease-in-out")
    timeline.key(target, "position_y", exit_at, y, "ease-in-out")

    if family in {"whip_pan", "push_transition", "pan_reveal", "path_follow"}:
        timeline.key(target, "position_x", d, end_x, "ease-in")
        timeline.key(target, "position_y", d, end_y, "ease-in")
    elif family in {"tilt_settle", "orbit_object", "diagonal_sweep"}:
        timeline.key(target, "rotation", d, end_rotation, "ease-in")
        timeline.key(target, "position_x", d, end_x, "ease-in")
        timeline.key(target, "position_y", d, end_y, "ease-in")
    else:
        timeline.key(target, "uniform_scale", d, end_scale, "ease-in")
        timeline.key(target, "position_x", d, end_x, "ease-in")
        timeline.key(target, "position_y", d, end_y, "ease-in")


def catalogue_summary() -> dict[str, Any]:
    return {
        "recipe_count": len(CATALOG),
        "family_count": len(FAMILIES),
        "families": [
            {"name": name, "category": category, "purpose": purpose}
            for name, category, purpose in FAMILIES
        ],
        "categories": {
            category: sum(item["category"] == category for item in CATALOG.values())
            for category in sorted({item["category"] for item in CATALOG.values()})
        },
    }
