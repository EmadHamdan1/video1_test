# Video1 Motion Lab

This is the source library for reusable motion-graphics elements used with the Video1 CapCut production system. It contains editable Remotion source (not just pre-rendered stock clips): a whiteboard scene card, word-by-word kinetic captions, and a transition showcase.

## Install once

From PowerShell at the repository root:

```powershell
cd .\motion-lab
npm install
npm run typecheck
npm run studio
```

Remotion Studio opens a local preview. Inspect the compositions before rendering.

## Render a motion element

```powershell
npm run render:whiteboard
npm run render:caption
npm run render:caption:alpha
npm run render:transitions
```

Outputs are written to `motion-lab/out/`, which is intentionally ignored by Git. Whiteboard and transition samples are full-frame video clips. `render:caption:alpha` exports the caption layer as ProRes 4444 with an alpha channel, using Remotion's documented transparency settings: https://www.remotion.dev/docs/transparent-videos. Import that short MOV into CapCut and inspect the transparent area before relying on it; codec support can vary by CapCut build. ProRes files can be large, so render only the overlays you actually use.

## Reuse with a story

- `WhiteboardExplainer` accepts `title`, `subtitle`, `imageUrl`, `accent`, and `sceneNumber` input props.
- `KineticCaption` accepts `text`, `accent`, and `mode` (`phrase`, `punch`, or `lower-third`). It staggers word entrances with springs and a restrained underline draw.
- `TransitionShowcase` demonstrates a small, intentional palette: fade and slide transitions with smooth timing. It is a visual lab, not a promise that every Remotion effect exists in CapCut's native catalogue.

Remotion renders are imported into CapCut as clips. The rest of the timeline (source photos/video, presenter poses, narration, captions, and SFX) remains editable, but a rendered Remotion clip itself is one video asset in CapCut.

## Licensing / costs

Remotion's terms depend on the user and organization; review the current official license before using it commercially: https://www.remotion.dev/docs/license/pricing. Provider-based AI images are a separate optional feature and may incur usage charges. This motion lab runs locally after npm dependencies are installed.
