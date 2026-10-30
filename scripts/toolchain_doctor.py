"""Read-only inventory of media executables and locally installed render libraries."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

PACKAGE_NAMES = {
    "hyperframes": ("hyperframes",),
    "remotion": ("remotion",),
    "remotion_gsap": ("@remotion/gsap",),
    "gsap": ("gsap",),
    "d3": ("d3",),
    "pixi": ("pixi.js",),
    "matter": ("matter-js",),
    "lottie": ("lottie-web",),
    "p5": ("p5",),
    "svgjs": ("@svgdotjs/svg.js", "svg.js"),
    "anime": ("animejs", "anime.js"),
    "motion": ("motion", "framer-motion"),
    "motion_canvas": ("@motion-canvas/core",),
    "resvg": ("@resvg/resvg-js",),
}


def _package_info(root: Path, package: str) -> dict[str, Any] | None:
    package_path = Path(*package.split("/"))
    for node_modules in (root / "motion-lab" / "node_modules", root / "hyperframes-engine" / "node_modules", root / "node_modules"):
        candidate = node_modules / package_path / "package.json"
        if not candidate.is_file():
            continue
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
            return {
                "installed": True,
                "version": str(payload.get("version", "unknown")),
                "path": str(candidate.resolve()),
            }
        except (OSError, json.JSONDecodeError):
            return {"installed": True, "version": "unreadable", "path": str(candidate)}
    return None


def inspect_toolchain(root: Path) -> dict[str, Any]:
    root = root.resolve()
    executables = {
        name: shutil.which(name) for name in ("node", "npm", "npx", "ffmpeg", "ffprobe", "capcut")
    }
    packages: dict[str, Any] = {}
    for capability, candidates in PACKAGE_NAMES.items():
        found = next((info for package in candidates if (info := _package_info(root, package))), None)
        packages[capability] = found or {"installed": False, "version": None, "path": None}

    template = root / "hyperframes-engine"
    packages["hyperframes_template"] = {
        "installed": (template / "hyperframes.json").is_file(),
        "version": None,
        "path": str(template.resolve()) if template.exists() else None,
    }
    return {
        "schema_version": 1,
        "project_root": str(root),
        "executables": executables,
        "packages": packages,
        "renderers": {
            "capcut": bool(executables["capcut"]),
            "hyperframes": bool(executables["npx"] and packages["hyperframes_template"]["installed"]),
            "remotion": bool(packages["remotion"]["installed"]),
            "gsap": bool(packages["gsap"]["installed"]),
        },
    }


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "# Local toolchain inventory",
        "",
        "Read-only detection. This report does not install or update packages.",
        "",
        "## Executables",
        "",
        "| Tool | Status | Path |",
        "|---|---|---|",
    ]
    for name, path in report["executables"].items():
        lines.append(f"| {name} | {'available' if path else 'missing'} | {path or '—'} |")
    lines.extend(["", "## Libraries", "", "| Capability | Status | Version |", "|---|---|---|"])
    for name, details in report["packages"].items():
        lines.append(
            f"| {name} | {'installed' if details['installed'] else 'not detected'} | {details.get('version') or '—'} |"
        )
    lines.extend(["", "## Active renderer paths", ""])
    for name, enabled in report["renderers"].items():
        lines.append(f"- {name}: {'ready' if enabled else 'not ready'}")
    return "\n".join(lines) + "\n"
