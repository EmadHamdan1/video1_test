# Montage upgrade: how the pipeline should edit

This guide is the persistent editing brief for new projects as well as the Nutty Putty build.

## What's connected

- `scripts/stock_fetcher.py`: query-level stock-photo search, local caching, licence filtering, duplicate checks, provenance manifest, and credits.
- `scripts/text_system.py`: small semantic type tiers, one restrained ink/red/gold palette, safe-area clamping, overlap nudging, and keyframed text movement.
- `scripts/qa_spec.py`: structural checks for invalid timing, text size/safe areas/overlap, late keyframes, clips past the end, and long gaps without new visual starts.
- `scripts/hybrid_engine.py`: use stock stills as relevant secondary B-roll, apply text-system helpers, and print QA findings during spec creation.
- `scripts/prepare_nutty_putty.py`: supplies a concrete English visual search query for each story beat. Full mode enables stock search, capped at 32 assets.

## Stock-media behaviour and safety

The full Nutty Putty preparation enables Openverse and Wikimedia Commons without keys. Pexels and Pixabay are optional and only run if `PEXELS_API_KEY` / `PIXABAY_API_KEY` exist in the local environment. If a provider is unavailable, search fails, or no suitable image passes filters, the edit falls back to the supplied art. It must not scrape pages, search for random decorative images, or invent footage.

The fetcher accepts Openverse CC0, Public Domain Mark, and CC BY by default; Wikimedia follows the same general policy. NC and ND licences are rejected. Share-alike is disabled unless explicitly opted into. Provider metadata can be wrong or incomplete, so review `projects/nutty-putty-cave/assets/stock/stock_manifest.json` and `CREDITS.txt` before publishing; copy any required source credits into the video description. The source page and original licence remain the authority. Pexels attribution/link-back rules and Pixabay's cache / anti-bulk-download rules still apply.

Stock images are downloaded locally and cached; they are not embedded into Git. The asset folder belongs to the local CapCut project. Never commit API keys or user source media. This pipeline intentionally requests still images by default (`allow_video: false`) because all clip durations must be checked against the actual media duration before use. The hybrid engine now uses a relevant, unused stock still as a full-frame 16:9 hero about every fifth scene when a nearby beat match exists, plus smaller secondary inserts on selected beats. Each fetched candidate appears in `build/ASSET_STOCK_CONTACT_SHEET.jpg`, with its query and licence label, for human review.

Hugging Face image generation is not an automatic fallback: an inference provider/model can incur charges and model output licences vary. Use the existing `scripts/prepare_assets.py` workflow for deliberate generation/review, only after confirming the model card, permission, and possible cost.

## Style rules

1. Build the story from narration and time-aligned beats first; every image should illustrate a concrete spoken noun/action/place, not merely the emotion of the sentence.
2. Plan variation, not continuous noise. Alternate wide establishing visuals, medium story illustrations, tight details, maps/diagrams, occasional small B-roll inserts, and selected full-screen stock cuts. Avoid repeating the same motion or inserting a sticker on every cut.
3. Keep a still visibly alive with a slow push/pull or tiny drift; reserve snap zoom, shake, flash, stronger SFX, and red accents for genuinely high-impact beats.
4. Use one text hierarchy: short keyword (usually 1–3 words), statistic/date, and chapter label. Keep font size inside the tested tier range, place text inside the safe area, avoid simultaneous collisions, and prefer dark ink on white with red or gold only for semantic emphasis.
5. Use a brief vertical settle for title/callout keyframes. Opacity and scale keyframes are deliberately disabled by default until the installed local `capcut-cli` schema has been probed. Do not guess whether the property is `alpha` or `opacity`.
6. Use sound where it supports a story change or a meaningful entrance. Keep transient SFX below narration, avoid repeated identical sounds in a row, and do not add an effect to every element.
7. Transitions should support continuity: mostly direct cuts/short dissolves where supported, with selective slide/push/flash or blur accents. A transition must not exceed either adjacent clip and should never hide weak visual storytelling. The editable CapCut path now uses 10 directional/scale/rotation hero entrances and multiple exits, plus reusable secondary-layer recipes; see docs/MOTION_REFERENCES.md.

## Local CapCut schema probe

On the target PC (with the intended CLI build installed), inspect supported compile properties before activating extra text properties or transitions:

```powershell
capcut doctor
capcut describe --command compile | Select-String -Pattern "alpha|opacity|animation|transition|fade|mask|easing|text"
```

Only after the output verifies a property should `settings.text_caps` be set. For example, use the exact supported property if the output says `alpha`; set `{"opacity_property":"alpha","scale":true}` only if both alpha and scale keyframes are confirmed. Until then, keep `text_caps` empty. This is a deliberate compatibility safeguard.

## Repeatable quality-control loop

1. Run unit tests and syntax checks.
2. Build the editable CapCut draft, read every `QA:` line, fix structural findings, then rebuild.
3. Open the newest draft—not an older project—and confirm the stock manifest/credits exist if stock search succeeded.
4. Extract a contact sheet or sample one frame every ~5 seconds, inspect the opening, a calm section, a peak, the midpoint, and the ending. Check subject relevance, visual scale, cut direction, safe margins, and visual repetition.
5. Review sound against narration and check peaks/ducking with headphones.
6. Export a test MP4 from CapCut and watch it end-to-end before calling the edit done. CI proves code tests, not that a rendered edit looks good.

## References

- Openverse API: https://api.openverse.org/v1/
- Pexels API docs: https://www.pexels.com/api/documentation/
- Pixabay API docs: https://pixabay.com/api/docs/
- Wikimedia Commons API: https://www.mediawiki.org/wiki/API:Imageinfo
- Remotion transitions: https://www.remotion.dev/docs/transitions
- MotionKit reusable motion design patterns: https://github.com/SkyBlueHeat/MotionKit
- Kinetic Titles (MIT, alpha-channel title overlays): https://github.com/bsewell/kinetic-titles
- Video Agent FFmpeg xfade transition recipe: https://github.com/agamm/video-agent/blob/main/.claude/skills/video-transitions/SKILL.md
- Pipeline/motion research for this repository: docs/MOTION_REFERENCES.md
- FFmpeg filters: https://ffmpeg.org/ffmpeg-filters.html
- GitHub editing workflow ideas: https://github.com/copiadigital/footage-montage
- GitHub video-editing pipeline examples: https://github.com/gitethanwoo/video-editing
- Curated video skills: https://github.com/ella-wang-opus/awesome-video-skills


## Nutty Putty: Bendia-inspired casefile profile

The project profile is an original adaptation of broad editing principles observed in two public Bendia videos. It is not a frame-for-frame copy.

- White background and high-contrast illustrated storytelling remain the visual foundation.
- Hero illustrations are enlarged and alternate left, right and centre. Relevant stock images are limited to a small approved set; the engine can use a stock still as an occasional full-frame break and as a smaller evidence insert.
- The default shot target is about 2.45 seconds (minimum 1.35 seconds), but story boundaries and the narrator's line timing take priority. Keep quieter aftermath beats slower.
- Secondary cards are selectively enabled, not forced onto every scene. High-impact layouts may use two small evidence cards, keeping the hero readable.
- Short fact cards and keyword callouts are enabled for matched phrases. Keep them brief, collision-aware and high-contrast; use red for danger and gold for numbers/actions.
- The sound-effects module first searches for the local `Saoud_SFX_Pack`. It accepts `SAOUD_SFX_PACK` as an explicit folder override, scans supported audio formats, matches filenames to a small set of sound roles, and converts selected clips to project-local WAV files. If no category match exists or conversion fails, the existing generated effect is used as a fallback.
- The user pack is never uploaded or committed. `build/SFX_PACK_MANIFEST.json` records which pack files were used and which categories fell back.
- The pipeline does not automatically remove backgrounds from the original JPEG illustrations. Use only genuinely transparent art as cutouts; any manual or third-party matting must be verified visually in CapCut before export.

The build remains an **editable CapCut draft**, not a final MP4. Visual matching, audio balance, transparent edges and final export must be checked in CapCut on the workstation that owns the source assets.
