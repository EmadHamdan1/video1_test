from __future__ import annotations

import json
from pathlib import Path

from hyperframes_bridge import render_hyperframes_overlay


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
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
        ROOT / "build" / "hyperframes-demo",
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
