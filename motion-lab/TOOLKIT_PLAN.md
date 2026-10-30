# Motion toolkit integration plan

## Goal

Improve the existing narration-led photo montage without replacing the Python/CapCut timeline or generating a separate full video. Specialized graphics are rendered as short, reusable overlays and imported into CapCut. Original still images, narration, and the main timeline remain in the existing project.

## Current architecture

- Python selects/times scene images and creates CapCut timeline instructions.
- The hybrid engine supplies keyframed entrances, holds, exits, and overlap.
- Remotion renders selected animated graphic layers.
- CapCut remains the final editable assembly and export environment.

## Tool roles and adoption

| Tool | Intended role in this project | Decision |
|---|---|---|
| Remotion | Main deterministic renderer for transparent titles, labels, diagrams, and visual overlays | Already installed; keep as the rendering core |
| GSAP | Detailed timelines, staggered typography, SVG path reveals, masks, and controlled easing inside Remotion | Phase 1: integrated through `@remotion/gsap` |
| D3.js | Fact-led diagrams: rescue timeline, cave-route schematic, dimensions, and comparison graphics | Phase 2: add when the first verified infographic is designed |
| PixiJS | GPU-accelerated 2D effects such as restrained dust, light falloff, particles, and layered textures | Phase 2: add behind an explicit effects toggle |
| Matter.js | Precomputed physical motion for selected props or debris; not a general-purpose transition system | Conditional: only when a specific shot benefits |
| Lottie Web | Play a supplied/licensed Lottie JSON animation as a short visual insert | Conditional: only when a suitable JSON asset exists |
| Anime.js | Another DOM/SVG animation engine; overlaps heavily with GSAP for this workflow | Do not install alongside GSAP without a unique required feature |
| Motion (formerly Framer Motion) | React UI and gesture/layout animation; its main strengths are less relevant to frame-rendered CapCut overlays | Defer; Remotion + GSAP already cover the selected animation path |
| p5.js | Generative sketches and creative coding; can produce procedural visuals | Optional alternative for a specific sketch, not a second always-on effects engine |
| SVG.js | Programmatic SVG authoring/manipulation | Defer; native SVG plus GSAP and the existing Resvg renderer cover current needs |
| Motion Canvas | A separate TypeScript vector-animation authoring/rendering system | Do not add as a second renderer while Remotion already exists |
| HyperFrames | A separate HTML-to-video renderer with its own CLI and rendering pipeline | Do not add to the production path yet; it duplicates the existing Remotion-to-CapCut route |

## Integration rules

1. Do not install all twelve packages just because they are available. More packages do not automatically improve the edit.
2. Keep animations deterministic: the same frame number must always produce the same image.
3. Render overlays with transparency when CapCut needs to show the original photo beneath them.
4. Preserve the source photo and narration. Never bake an effect into the only copy of an image.
5. Every overlay needs a reason tied to the spoken beat. Avoid decorative clutter, random icons, and unrelated motion.
6. Keep new tools behind independent compositions or feature flags so a failure cannot break the existing CapCut build.
7. Verify facts, dates, route geometry, and measurements before showing them as documentary graphics. Clearly mark illustrative reconstructions as not to scale.

## Phase sequence

- Phase 1: GSAP-powered transparent lower-third / case-file overlay. Confirm typecheck, render, alpha import, and visual quality in CapCut.
- Phase 2: D3 infographic compositions and PixiJS atmosphere experiments, each with a preview and an enable/disable switch.
- Phase 3: consider Matter.js and Lottie only for scenes that genuinely need physics or an existing animation asset.
