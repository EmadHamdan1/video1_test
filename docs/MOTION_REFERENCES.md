# Motion and transition research for the CapCut hybrid pipeline

This is the research record behind the reusable keyframe system in scripts/motion_recipes.py and the story-scene logic in scripts/hybrid_engine.py.

## GitHub patterns reviewed

### MotionKit — reusable animation system
https://github.com/SkyBlueHeat/MotionKit

Useful ideas: centralise easing/timing tokens, build a small set of named motion recipes, compose scenes from reusable pieces, and keep visual layouts data-driven. MotionKit documents fade, slide, wipe, zoom, push and mask transitions as component-level effects. This repository did not copy its implementation; the CapCut version expresses its own deterministic recipes as timeline keyframes so the clips remain editable.

### Kinetic Titles — kinetic typography
https://github.com/bsewell/kinetic-titles

Useful ideas: a slam with spring-like settle, split/wave/zoom text entrances, per-word staggering and frame-deterministic animation. The project documents Remotion-to-ProRes-4444/PNG-sequence export for alpha-channel overlays and is MIT licensed. The current CapCut pipeline retains editable text layers, using scale overshoot/settle/scale-out; a future optional overlay render can use transparent ProRes/PNG when a fully custom title animation is worth flattening into a clip.

### Video Agent's FFmpeg transition skill
https://github.com/agamm/video-agent/blob/main/.claude/skills/video-transitions/SKILL.md

Useful ideas: pick a transition for the actual cut rather than softening every cut; verify source durations; keep overlaps short; and visually inspect the seam. Its examples use FFmpeg xfade for wipes, slides, dissolves, pixelize, circle and diagonal transitions. This project is an editable CapCut-draft workflow, so the core image movement is made with CapCut timeline keyframes instead of rendering the whole edit through xfade. xfade remains a candidate for a separate final-render/export backend.

### Remotion Transitions — official docs
https://www.remotion.dev/docs/transitions

The official package documents TransitionSeries, scene-to-scene transitions and timing presets. It is appropriate for the existing React/Remotion motion-lab when a whole animated scene should be rendered; it is not a replacement for the Python-to-CapCut timeline generator. Avoid adding package dependencies until the relevant scene is actually going to be rendered through Remotion.

### FFmpeg's transition/filter documentation
https://ffmpeg.org/ffmpeg-filters.html

xfade and afade are useful at render time, but their constraints matter: clips must share compatible frame size/frame rate/pixel format and a transition duration cannot exceed the shorter input. The current narration afade is applied as an audio filter, which does not depend on an undocumented CapCut property.

## What is implemented in this repository

- Hero-scene entrances: pop, slide, drop, tilt-pop, left/right slides, rise, diagonal sweep, zoom-through and spin-in. The selector uses story emotion, shock level and trigger phrase; e.g. sharp physical danger can punch or zoom, while grief/aftermath gets a quieter slide/rise.
- Hero-scene exits: shrink-away, directional slide-away, drop-away, tilt-away and zoom-away.
- Reusable secondary-layer recipes: left/right/top/bottom entrances, scale-pop, tilt-swing, diagonal-sweep, zoom-through, rise-overshoot and drop-bounce; five different exits.
- Seven single-card layouts, plus paired top-card collages. Paired cards start with a slight deterministic stagger rather than appearing at exactly the same instant.
- The full Nutty Putty build now aims for a second visual layer on nearly every scene after the opening (except presenter beats, where the presenter itself adds a second visual). High-impact beats and selected rhythm points create two secondary image cards, resulting in three visual layers when the hero image is present.
- Secondary items normally live for roughly 70–80% of a scene, have separate editable keyframes, and prefer story-relevant licensed stock. When no near-beat stock item is available, they use a different supplied illustration. A recent-use window prevents immediate repetition without exhausting the image pool over a long video.
- If a fetched PNG truly has transparent pixels, the asset manifest records alpha_channel: true and same-beat transparent assets are preferred for secondary/cutout-style positions. The system does not claim a source is a cutout based only on its filename.
- Short text callouts use a restrained palette, semantic sizes, safe-area checks, vertical settle, scale overshoot and scale-out. Alerts select slam/tilt/zoom recipes, statistics select pop/zoom/slide recipes, and keywords/chapters rotate through rise and directional slides. Opacity animation remains disabled unless the installed CLI's property schema is explicitly probed.

## Why these techniques fit this pipeline

The user's end product is a CapCut Desktop project with editable layers, not just an MP4. Therefore, the best default is a bounded set of deterministic keyframe recipes written into the CapCut draft: they can be reviewed, retimed, moved, replaced or removed in CapCut. Remotion/GSAP/FFmpeg are strong complementary tools, but using their rendered output for every image would flatten individual image elements and make it harder to rearrange each card inside CapCut.

The current implementation intentionally prefers movement through position_x, position_y, uniform_scale and rotation. It does not assume that a CapCut CLI build supports alpha, opacity, masks, motion blur or every transition slug. Those capabilities can be enabled after capcut describe --command compile confirms the actual local schema.

## Validation required

- Unit tests verify layout variety, supported transform names, deterministic keyframe timing, paired-card stagger, music/narration fades and no reuse of title videos as still-image overlays.
- CI verifies Python tests, PowerShell parsing and Motion Lab type checking.
- CI does not produce a local CapCut draft or watch the exported film. The newest local draft must be inspected for semantic image matching, visible card collisions, source clip lengths, motion smoothness, text safe areas and audio balance before publication.