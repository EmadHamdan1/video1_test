# Video1 Motion Lab

This is the source library for reusable motion-graphics elements used with the Video1 CapCut production system. It contains editable Remotion source (not just pre-rendered stock clips): a whiteboard scene card, word-by-word kinetic captions, a transition showcase, and transparent documentary overlays.

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
npm run render:casefile:alpha
```

Outputs are written to `motion-lab/out/`, which is intentionally ignored by Git. Whiteboard and transition samples are full-frame video clips. The alpha commands export transparent ProRes 4444 overlays using PNG frames and the `yuva444p10le` pixel format. Import those short MOV files into CapCut and inspect the transparent area before relying on them; codec support can vary by CapCut build. ProRes files can be large, so render only the overlays you actually use.

## Reuse with a story

- `WhiteboardExplainer` accepts `title`, `subtitle`, `imageUrl`, `accent`, and `sceneNumber` input props.
- `KineticCaption` accepts `text`, `accent`, and `mode` (`phrase`, `punch`, or `lower-third`). It staggers word entrances with springs and a restrained underline draw.
- `TransitionShowcase` demonstrates a small, intentional palette: fade and slide transitions with smooth timing.
- `CaseFileOverlay` renders a transparent lower-third. Its kicker, heading, accent rule, and note animate with a GSAP timeline synchronized to Remotion's frame clock. The sample text is illustrative and is not a factual cave map or measurement.

Remotion renders are imported into CapCut as clips. The rest of the timeline (source photos/video, presenter poses, narration, captions, and SFX) remains editable, but a rendered Remotion overlay itself is one video asset in CapCut.

## Toolkit selection

The main timeline remains Python + CapCut. Remotion is the overlay renderer; add specialized libraries only when a shot has a real need for them. See [TOOLKIT_PLAN.md](./TOOLKIT_PLAN.md) for the role of all twelve candidate tools and the staged adoption plan.

## Licensing / costs

Remotion has a special license: individuals and companies of up to three people currently qualify for its free license subject to its terms; larger organizations and automated video products may need another license. Check the current terms before commercial scale-up: https://www.remotion.dev/docs/license/pricing. GSAP's standard license is also subject to its published terms: https://gsap.com/standard-license. This motion lab runs locally after npm dependencies are installed.
