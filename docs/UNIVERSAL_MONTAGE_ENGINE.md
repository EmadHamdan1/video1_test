# Universal Montage Engine — architecture

## Product goal

A reusable, narration-led documentary montage engine. A new project supplies narration, images/video, optional reference assets, and a style profile. The engine plans the edit and chooses tools per visual task. It is not a one-video preset and it must not apply every effect to every shot.

The deliverable remains an editable CapCut Desktop project. Original stills, source videos, voice-over, music and ordinary keyframe motion remain separate timeline elements. Special graphics are rendered as short, reusable overlays/inserts and added as additional tracks.

## What the current engine already does

- Creates a CapCut timeline from local images and narration.
- Supports ten hero entrances, several exits, seven card layouts and secondary-layer keyframes.
- Uses deterministic transform keyframes for position, scale and rotation.
- Can query licensed stock image sources, preserve provenance and create contact sheets.
- Has semantic typography helpers and structural QA.

## What is still missing

- It does not inspect image content to determine the subject's actual location. A generic pan/zoom can therefore move away from the important object or crop it.
- Shot durations can be estimated from audio, but need a reusable beat planner based on aligned narration, visual complexity and story importance.
- The current story-specific preparation script mixes project-specific choices with engine setup. These settings must become reusable project profiles.
- The current engine can place supplied/stock images, but it does not yet create a tailored visual when no suitable image exists.
- The current keyframe recipe selector uses story metadata, not a full comparison of adjacent shots, visual direction and composition.

## Target architecture

```text
New project
  |
  v
1. Media intake and asset manifest
  |  dimensions, duration, duplicate checks, focal regions, semantic tags
  v
2. Story analysis
  |  transcript / word timing -> beats -> entities -> relationships -> importance
  v
3. Visual director
  |  choose: supplied asset | licensed stock | vector diagram | generated illustration
  v
4. Shot and motion planner
  |  duration, shot size, crop, camera path, transition, text, arrows, SFX
  v
5. Renderer router
  |-- CapCut adapter: editable photos/videos, voice, keyframes, tracks
  |-- HyperFrames adapter: procedural scenes, diagrams, animated overlays
  |-- GSAP inside HyperFrames: frame-seekable motion timelines
  |-- D3: data-driven maps, timelines, graphs and relationship diagrams
  |-- PixiJS: optional particles, atmosphere and GPU 2D effects
  |-- Lottie / Matter / p5: only when a shot specifically calls for them
  v
6. CapCut assembly
  |  preserve editable source media; add rendered MOV/PNG overlay tracks
  v
7. QA and review
     timing, crop safety, motion repetition, typography, asset relevance,
     transparent-alpha verification, audio ducking, contact sheets
```

## Core design rule: the edit is planned before it is animated

Every shot should be represented by a renderer-neutral shot record. A planner decides what the viewer should understand before a renderer decides how to animate it.

A future shot record should include:
- narration start/end and exact spoken phrase;
- story beat, importance, emotion, factual confidence;
- visual purpose (place, person, object, action, comparison, geography, consequence, evidence);
- selected source media and why it matches;
- focal subject and bounding box in source-image coordinates;
- output crop, safe margins and camera path;
- visual layers (hero, supporting image, labels, arrows, diagram);
- transition-in/out and relation to adjacent shot;
- text content, hierarchy, screen position and duration;
- sound cue with mix priority;
- renderer choice and whether its output must be transparent.

No random effect selection. Use a deterministic score and seeded variations; the same project and settings must create the same plan.

## Image-aware motion

Do not choose pan direction from shot index alone. First locate the visual subject:
1. Read image dimensions and orientation.
2. Detect faces/objects/foreground or compute a focal-region estimate.
3. Store a normalized bounding box and confidence in the asset manifest.
4. Calculate start/end crops that keep the subject inside a safe region.
5. Use a slow push, pull, lateral drift or parallax only when the source resolution and composition allow it.
6. If detection confidence is low, use a conservative centered move or hold still.

For moving video, track the selected subject and avoid auto-reframing that fights the original camera movement. The first implementation should use local lightweight analysis and optional heavier vision models behind an explicit setting.

## Gap-filling hierarchy

When narration needs a visual and the supplied folder has no suitable image:
1. Reuse a relevant local asset only if it is genuinely relevant; do not force a weak match.
2. Search for a licensed stock photo/video and record creator, source and licence.
3. Build a clear vector/HTML diagram with HyperFrames (object silhouette, labels, route, arrows, sequence, timeline, comparison, cross-section or relationship map).
4. Use an optional image-generation provider for a realistic illustration only when enabled and any cost/model licence is accepted.

HyperFrames is a renderer, not an automatic image-understanding or photorealistic image-generation model. It can construct and animate designed visuals from HTML/CSS/SVG/Canvas and media. It cannot truthfully recreate a missing real photograph by itself. Factual diagrams must be grounded in verified source facts; inferred reconstructions must be labelled illustrative and must not invent measurements or geography.

## Tool responsibilities

| Tool | Engine responsibility | Adoption |
|---|---|---|
| CapCut CLI / existing Python engine | Final editable timeline, source-photo moves, audio and tracks | Keep as the assembly backend |
| HyperFrames | Reusable HTML-native generated scenes, overlays, transitions and gap-filling diagrams; export MOV with alpha where appropriate | Main new graphics backend |
| GSAP | Timelines and precise easing/staggers inside HyperFrames | Primary animation language |
| D3.js | Data-bound maps, timelines, graph/relationship diagrams and charts | Add with first data-led graphic |
| PixiJS | Selective GPU 2D effects, particles, light/atmosphere | Add behind an effect switch after base pipeline works |
| Remotion | Existing React compositions; do not expand a second renderer until migration is measured | Keep legacy compositions temporarily |
| Lottie Web | Play a supplied/licensed Lottie JSON animation | Optional asset adapter |
| Matter.js | Precompute deterministic physical motion for selected object shots | Optional, never on ordinary photo moves |
| p5.js | Procedural generative visuals for a specific scene | Optional |
| SVG.js | Programmatic SVG manipulation where native SVG/D3 is insufficient | Defer |
| Anime.js | Overlaps with GSAP for this project | Do not add beside GSAP without a unique requirement |
| Motion (Framer Motion) | Mainly UI and interaction animation; weak fit for frame-based video timeline work | Defer |
| Motion Canvas | Separate vector-animation renderer; duplicates current Remotion/HyperFrames output path | Defer |
| HyperFrames | HTML/CSS/JS renderer; not the final CapCut editor | Keep as an overlay/insert backend, not a replacement for editable CapCut assembly |

## HyperFrames integration contract

- Generate an HTML composition per planned insert or overlay, not a separate unrelated video project for every clip.
- Use explicit `data-start`, `data-duration`, `data-track-index`, width and height metadata.
- Register GSAP timelines and let HyperFrames own frame seeking and media timing.
- Prefer one overlay composition for related labels/arrows in a beat; use a separate composition for a distinct animated diagram.
- Render short editor-friendly transparent MOV (ProRes 4444) when the graphic must sit over source photos. Use MP4 for full-frame inserts. Do not use transparent WebM as the default CapCut intermediate; editor support is not universal.
- Verify alpha with FFprobe and import a short test into the installed CapCut build before automating it.
- Keep the editable CapCut photo and voice tracks separate. A rendered graphic insert is a flattened visual layer, not a replacement for the source photos.

## Typography and relationships

- Use semantic size tiers and measure text before layout.
- Prefer short phrases, dates and numbers over copying narration as paragraphs.
- Clamp to title-safe margins and avoid overlapping the hero subject.
- Draw connecting arrows only when the narration establishes a real relationship. Use SVG paths with an animated stroke and arrowhead; D3 can position graph nodes/edges for more complex relationships.
- Keep one dominant message per shot. Text, arrow and visual should clarify the same beat, not compete.

## Pacing and transitions

- Shot length is constrained by narration beat boundaries and actual source duration, then adjusted for visual complexity and importance.
- Choose transitions by adjacent-shot continuity: direction, scale, subject location, colour, energy and narrative relation.
- Default to clean cuts or restrained short transitions. Use a distinctive transition only when it explains a change of place, time, viewpoint or emotional intensity.
- Motion variety is measured across a window of shots; do not repeat the same entrance/exit pair too often.
- Avoid camera shake, spin, flashes and zoom punches unless the beat warrants them.

## Safety, factuality and licensing

- Do not invent real people, places, dimensions, routes or evidence. Distinguish a labelled illustrative reconstruction from source photography.
- Keep local input media and secrets local. Do not commit source photos, voice-overs, generated media or API keys.
- Respect the exact stock licence and maintain credits.
- AI-generated images are a separate optional provider, with explicit cost and model/licence review.
- If an image cannot be safely interpreted, do not add a misleading diagram; use a restrained text or neutral transition.

## First integration increment

The optional HyperFrames bridge is now implemented in code: a project can describe reviewed title/callout/arrow elements, HyperFrames renders them into a transparent ProRes 4444 MOV, FFprobe checks the alpha pixel format, and the CapCut compile spec receives a separate video track. It remains disabled by default. This increment does not yet implement automatic story understanding, object detection, missing-visual discovery, or factual diagram generation. The MOV's alpha import must still be checked in the target desktop CapCut build.

## Phased implementation

1. Universal project schema and engine/renderer boundaries; preserve the current CapCut output.
2. HyperFrames template renderer for transparent graphics and gap-filling diagrams, driven from the shot plan.
3. Image focal-region analysis and safe camera path planner.
4. Adjacent-shot transition planner and motion repetition QA.
5. D3 diagrams and arrow/relationship graphics.
6. PixiJS selected atmosphere/effects, then optional Matter/Lottie/p5 adapters.
7. Migrate suitable legacy Remotion compositions only after visual and render-time comparison.

## Acceptance criteria

- A non-Nutty-Putty test project can be run from the same engine with only a different project manifest.
- Supplied image and narration tracks remain editable in CapCut.
- A missing visual concept generates a meaningful vector insert or a documented stock/generation request, not random decoration.
- Still-image motion keeps the detected subject within safe margins.
- Transition and motion choices are deterministic and do not repeat excessively.
- Overlay alpha is verified in the actual local CapCut version.
- QA report includes scene timing, asset match rationale, crop safety, text bounds, transition usage and repeated-motion warnings.
- No claim of perfect output without reviewing a rendered draft and exported video.
