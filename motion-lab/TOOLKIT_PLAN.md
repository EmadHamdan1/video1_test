# Unified motion toolkit

The production timeline remains Python + CapCut. A renderer-neutral shot plan is the contract between story planning, motion design, graphic renderers, and editorial assembly.

## Roles

- **CapCut:** editable source image/video, narration, music, SFX, and the final multitrack draft.
- **HyperFrames + GSAP:** HTML/SVG/Canvas-style compositions, image cutouts, animated diagrams, multi-layer graphics, and complex scene overlays. Output is a transparent ProRes 4444 layer when it must sit above source footage.
- **Remotion + GSAP:** reusable React compositions already used by the project (title cards, case-file overlays, and specialist motion components). Output is a separate media layer with input props.
- **Python director:** reads narration beats, media metadata, asset matches, scene timing, and motion history; writes a deterministic production plan consumed by the render router.
- **Optional specialist packages:** D3 for data-led graphics, PixiJS for particle/atmosphere effects, Matter.js for selected physical simulations, Lottie for supplied animation JSON, and p5.js for deliberately procedural scenes. They are not installed or activated automatically.

## One shared contract

Every visual event is represented in the shot plan with:
- absolute start/end time and source beat ID;
- primary source asset and optional supporting/cutout assets;
- visual purpose, composition, screen-safe bounds, and focal region when known;
- independently timed layers and their renderer assignment;
- motion recipe IDs for entrance, hold, exit, and transition;
- approved screen text (never narration transcript);
- factual notes, provenance, licence, and QA status.

A renderer receives the same shot/layer records. It must not independently invent timing or change a factual relationship. Rendered overlays return to CapCut as named tracks; original source tracks remain editable.

## Determinism and quality

- Motion decisions are seeded from project/shot/layer IDs, not uncontrolled randomness.
- Motion recipes are context-filtered and recent-use-aware.
- Use GSAP for frame-seekable browser timelines; use Remotion's frame clock for React compositions.
- Do not run two animation engines against the same element.
- Use a single pinned GSAP version (3.15.0) across HTML and React renderers.
- Alpha output is checked with FFprobe before the track is added.
- Optional libraries are activated only after the toolchain doctor detects a compatible local install.
- Narration text is analysis/timing input only. Never create subtitle tracks automatically.

## Phases

1. Shared scene/layer schema, toolchain inventory, renderer routing, and deterministic motion catalog.
2. Expand HyperFrames from title/arrow-only overlays into images, vector shapes, labels, and compound layers.
3. Route selected Remotion compositions by ID and serializable props.
4. Add optional D3/PixiJS/Lottie/Matter adapters only when a concrete story scene requires them.
5. Generate and review the first Nutty Putty production plan and draft; visual quality is judged from the rendered output, not unit tests alone.
