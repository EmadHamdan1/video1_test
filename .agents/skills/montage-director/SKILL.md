---
name: montage-director
description: Plan, assemble, and quality-check narration-driven story videos from local assets and properly licensed stock media.
---

# Montage Director Skill

When working in this repository, act as a documentary editor and a cautious pipeline engineer—not a transition preset collector.

## Before editing

- Read `docs/MONTAGE_UPGRADE.md`, the project config, script/timing output, source catalog, and the latest QA report.
- Inspect available local assets, durations, aspect ratios, duplicates, and credits. Do not claim to have seen images/audio when only local path names are available.
- Build a beat list from the narration. Give each beat a clear visual job, concrete stock search query (e.g. "cave rescue pulley rope system", not "fear"), emotion/mood, shock level from 0–3, and trigger phrase. The engine uses that metadata to select hero entrance recipes; do not mark every beat as maximum shock.
- Preserve the original voiceover and local sources. Never upload private inputs. Never overwrite the only copy of a project.

## Visual story direction

- Create purposeful shot-size and source variation: establishing view, human/detail illustration, map/diagram, contextual B-roll, then a return to the hero image.
- Add licensed stock only when it meaningfully illustrates the current beat. Prefer the nearest beat's query and metadata; do not randomly decorate or use the same image twice.
- Preserve a consistent visual identity. Keep the canvas clean; use whitespace deliberately. Small inserts should remain secondary to the hero image, but use a relevant full-frame stock cut every few scenes when a strong match exists to vary visual scale.
- Review `build/ASSET_STOCK_CONTACT_SHEET.jpg` and the stock manifest before publishing; reject irrelevant/near-duplicate candidates instead of keeping stock just to fill the screen.
- Vary rhythm naturally. Plan visual changes frequently enough to avoid dead holds, but give serious moments room to breathe. Do not impose one rigid cut interval on every video.
- Apply small push/pull/drift to stills; reserve punch zooms, shake, flashes, stronger red accents, and bass impacts for selected moments. Not every entrance needs a sound effect.
- Use the current deterministic motion recipe helpers: pop, left/right slides, rise/drop, diagonal sweep, zoom-through and spin-in, with exits that shrink, slide, drop, tilt or zoom away. Do not reuse one animation for every picture.
- After the opening, maintain an overlapping secondary image layer on most non-presenter scenes. Vary its position and size from the layout recipe; use paired staggered cards on selected high-impact beats to create a three-image composition, not a fixed documentary picture-in-picture.
- Let images change roles: the hero can move to a side, shrink out, or be replaced by a beat-matched full-screen B-roll still; overlays should have their own independent timing and keyframes.
- Keep cutout assets only when the downloaded image truly has transparent pixels. Check the stock manifest/contact sheet; prefer a relevant transparent PNG for a foreground detail when available, but never assume the filename means it has alpha.

## Typography

- Do not place full narration sentences on screen by default. Use short 1–3 word callouts, important numbers/dates, and brief chapter markers.
- Use the helpers in `scripts/text_system.py` for semantic colour, size tiers, safe-area clamping, collision handling, and text motion.
- Keep a restrained palette (ink/white, red for danger, gold for statistics/actions). Do not randomly cycle colours or make all words huge.
- Never guess CapCut CLI keyframe properties. Keep opacity/scale options disabled until a local `capcut describe --command compile` probe confirms the supported property names.
- If alpha is supported, use gentle fade in/out; if not, use the verified position settle and shorten/adjust timing instead of emitting a speculative property.

## Sound and transitions

- Keep dialogue clear and forward. Duck ambience, use subtle impacts sparingly, and ensure SFX durations do not exceed source media.
- Choose cuts, fades, slides, pushes, dissolves, or flashes based on continuity and story energy. Avoid showing off the effect stack.
- Every video/audio segment must be clamped to its true source duration. Any transition must fit adjacent shots.

## Assets and licensing

- Use the implemented stock searcher. It must never scrape provider pages; use their APIs.
- Store source page, licence, creator/attribution, query, and local path in the stock manifest and write credits.
- Respect provider API limits. Avoid bulk downloading. Reject NC/ND by default, and include SA only after explicit approval and compatible downstream use.
- If stock search is unavailable or returns no safe candidate, fall back to local assets.
- Do not auto-run Hugging Face generation as a "free fallback": inference can incur charges and model terms differ. Ask for cost permission when needed and review the model card before publication.
- Never store API keys in Git. Do not check source media into the repository.

## QA and honesty

- Run `python -m unittest discover -s tests -v`; run the project's typecheck/PowerShell parse CI where relevant.
- Read structural messages from `scripts/qa_spec.py` and resolve invalid timing, text collisions, unsafe position, out-of-clip keyframes, long visual gaps, and clip overrun.
- Generate/inspect a contact sheet or sample frames at regular intervals. If frame inspection is unavailable, clearly mark visual review as not done.
- Open the newest generated CapCut draft, not the previous draft. The pipeline builds an editable CapCut project; it does not export the final MP4 unless an export stage is explicitly run.
- Do not say "best", "finished", or "looks good" based solely on passing unit tests. Separate code checks from on-device rendered visual review.


## Bendia-inspired documentary profile

For the Nutty Putty casefile profile, use a white editorial stage and an illustrated-documentary mix rather than copying any single creator's exact frames or assets.

- Keep a clear hero subject and no more than two supporting elements in a composition. Alternate full-frame cave/environment views, a character/action illustration, a close detail, and occasional evidence/photo cards.
- Change the viewer's visual anchor roughly every 1.5–3 seconds when the narration carries a new beat. Hold longer on solemn aftermath and key facts.
- Use quick, directional entrance motion (roughly 0.18–0.32 seconds): pop, slide, rise/drop, tilt-pop or zoom-through. Settle with a small overshoot; reserve shake and stronger zoom for a specific impact.
- Use short editorial labels, dates and numbers, not full sentences. Red is for danger, gold for quantities/actions, and black/white for ordinary labels. Keep labels brief and visible long enough to read.
- Pair only meaningful photo reveals, host entrances or impact beats with a whoosh, click/pop or low hit. Keep effects below narration and do not add a cue to every cut.
- Use a restrained tension bed. Duck it under speech and let it breathe during pauses; the voice remains the primary signal.
- Treat transparent PNGs as cutouts only after checking their alpha channel. JPEG art is opaque unless a separate verified matting stage removes the background; never describe a flat JPEG as a cutout.
- Keep CapCut properties limited to the installed CLI schema. Do not guess opacity, mask or alpha keyframes.
