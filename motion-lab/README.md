# Video1 Motion Lab

Reusable Remotion + GSAP compositions that feed the Video1 production pipeline. These are renderer components, not a second editor: their outputs are imported as named tracks into the editable CapCut draft.

## Available compositions

- `WhiteboardExplainer`: a designed explainer scene.
- `KineticCaption`: kinetic typography component. It is available as a graphic component, but the production policy forbids transcript subtitles.
- `TransitionShowcase`: visual test bed for transition timing.
- `NuttyPuttyTitle`: the story opening graphic.
- `CaseFileOverlay`: a transparent documentary lower-third animated with GSAP.

## Commands

```powershell
cd .\motion-lab
npm install
npm run typecheck
npm run studio
npm run render:casefile:alpha
```

Transparent output uses ProRes 4444 and a PNG frame sequence. Import short samples into CapCut and verify that the empty areas remain transparent. Only rendered components requested by the shot plan should be exported.

## Shared production architecture

CapCut owns editable media tracks and final assembly. Python creates a common shot/layer plan. HyperFrames + GSAP handles HTML/SVG graphics and multi-layer compositions; Remotion + GSAP handles reusable React compositions. Each output is returned to CapCut as its own named track. The two renderers must not animate the same element.

See `TOOLKIT_PLAN.md` for routing, roles, and constraints.
