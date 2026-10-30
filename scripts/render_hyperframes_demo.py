from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

from hyperframes_bridge import render_hyperframes_overlay


ROOT = Path(__file__).resolve().parents[1]


def create_demo_cutout(path: Path) -> None:
    """Create one synthetic transparent object so the smoke test covers local image layers."""
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (720, 720), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((170, 110, 550, 490), outline=(215, 78, 66, 255), width=24)
    draw.ellipse((250, 190, 470, 410), outline=(235, 235, 230, 255), width=18)
    draw.line((360, 15, 360, 110), fill=(235, 235, 230, 255), width=16)
    draw.line((360, 490, 360, 690), fill=(215, 78, 66, 255), width=16)
    draw.rectangle((315, 330, 405, 420), fill=(28, 35, 42, 245), outline=(245, 245, 240, 255), width=8)
    image.save(path, format="PNG", optimize=True)


def main() -> int:
    build_dir = ROOT / "build" / "hyperframes-demo"
    asset_path = build_dir / "source-assets" / "transparent-pulley.png"
    create_demo_cutout(asset_path)

    demo_config = {
        "enabled": True,
        "version": "0.8.221",
        "workers": 2,
        "elements": [
            {
                "id": "demo-title",
                "type": "title",
                "start": 0.25,
                "duration": 4.8,
                "kicker": "VIDEO1 MOTION ENGINE",
                "title": "A CLEAR VISUAL STORY",
                "note": "HyperFrames + GSAP / transparent overlay test",
                "x": 0.06,
                "y": 0.70,
                "width": 0.70,
                "font_size": 54,
                "accent": "#D94C42",
                "emotion": "tense",
                "shock_level": 2,
            },
            {
                "id": "demo-pulley-cutout",
                "type": "image",
                "path": str(asset_path),
                "alt": "Synthetic transparent pulley and rope cutout",
                "start": 0.7,
                "duration": 4.4,
                "x": 0.63,
                "y": 0.14,
                "width": 0.27,
                "height": 0.60,
                "fit": "contain",
                "motion_role": "entrance",
                "emotion": "tense",
                "shock_level": 2,
            },
            {
                "id": "demo-cave-path",
                "type": "shape",
                "shape": "path",
                "path_d": "M0 220 C65 25 145 15 220 155 C295 285 380 265 520 80",
                "start": 1.0,
                "duration": 3.8,
                "x": 0.10,
                "y": 0.23,
                "width": 0.36,
                "height": 0.35,
                "fill": "#202832",
                "stroke": "#D94C42",
                "stroke_width": 11,
                "emotion": "mysterious",
                "shock_level": 2,
            },
            {
                "id": "demo-label",
                "type": "text",
                "text": "ILLUSTRATIVE RECONSTRUCTION",
                "start": 1.25,
                "duration": 3.5,
                "x": 0.12,
                "y": 0.79,
                "width": 0.40,
                "font_size": 20,
                "accent": "#F0D27A",
                "align": "left",
                "emotion": "solemn",
                "shock_level": 1,
            },
            {
                "id": "demo-arrow",
                "type": "arrow",
                "start": 1.1,
                "duration": 3.5,
                "x1": 0.24,
                "y1": 0.35,
                "x2": 0.72,
                "y2": 0.48,
                "label": "CONNECTED DETAIL",
                "accent": "#D94C42",
            },
        ],
    }
    result = render_hyperframes_overlay(
        demo_config,
        build_dir,
        total_duration=6.0,
        project_template=ROOT / "hyperframes-engine",
    )
    if result is None:
        raise RuntimeError("Demo render unexpectedly returned no output.")
    print(json.dumps(result, indent=2))
    print("Demo MOV: " + result["path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
