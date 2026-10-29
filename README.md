# Video1 Test — local-first montage builder

This repository builds an **editable, multitrack CapCut Desktop project** from local narration and illustrations. It does not export a final MP4 automatically. The target style is narration-led documentary montage: changing visual sources, restrained motion, concise designed callouts, purposeful sound, and a clean timeline—not a pile of random transitions.

## Latest montage workflow

The story-specific full build uses the hybrid_whiteboard engine:

- Pure-white canvas with hero illustrations alternating left / right / centre.
- Individually timed entrance, hold motion and exit keyframes; short overlap between scene layers where useful.
- A larger motion vocabulary: pop, directional slides, drop/rise, tilt-pop, diagonal sweep, zoom-through and spin-in, plus shrink, slide, drop, tilt and zoom exits.
- A layered secondary image on nearly every post-opening scene, with 7 layout patterns, separate keyframes, and occasional paired-card collages that place 3 images on screen at once. The pair enters with a small stagger and uses different exit recipes rather than simply cutting away.
- Selective secondary B-roll images chosen from a query attached to the closest story beat, instead of always recycling the next local image.
- A full-screen, cropped 16:9 stock B-roll hero about every fifth scene when a relevant, unused match exists; the original supplied art is used when no nearby beat match is available.
- A local ASSET_STOCK_CONTACT_SHEET.jpg lets you review fetched images alongside their provider, query, and licence before publishing.
- Concise keyword and chapter text styled by scripts/text_system.py: a restrained ink/red/gold palette, three semantic size tiers, safe-area clamping, collision nudging, vertical settle, scale overshoot and scale-out.
- Optional sound accents for selected entrances / story beats. Effects are not forced onto every element.
- Structural spec QA in scripts/qa_spec.py: invalid/overlong clips, keyframes after clip end, very large or off-safe text, overlapping labels and long gaps between visible starts are logged as QA messages.
- Source media stays local. A manifest and CREDITS.txt are created for fetched stock images.

The full build adds concrete English stock-search terms to each prepared story beat. Verified transparent PNGs are marked in the asset manifest and preferred for secondary cutout-style layers when available; ordinary opaque stock images remain supported. The stock searcher tries Openverse and Wikimedia Commons without API keys. Pexels and Pixabay are optional when their keys are present in process environment variables or the root .env. If a provider fails or no image survives filtering, the project falls back to its existing local artwork.

## Run the latest version

1. Save edits and **close CapCut completely**.
2. Open PowerShell and run:

       cd C:\Users\EmQr\video1_test
       git switch feat/capcut-montage-pipeline
       git pull origin feat/capcut-montage-pipeline
       .\run_nutty_putty.ps1

3. Let the full build finish. A successful run ends with BUILD SUCCESSFUL. If it ends with BUILD FAILED or a traceback, read the error and projects\nutty-putty-cave\build\QA_REPORT.md; do not open the previous draft and assume it changed.
4. Open the **newest CapCut draft** created by this run. Inspect the beginning, middle, high-impact beats and ending. The automated QA report cannot judge whether the story illustration truly matches the words being spoken.
5. Export and review the MP4 from CapCut only after visual/audio review.

The command .\run_nutty_putty.ps1 -BasicOnly deliberately produces a minimal draft without stock fetching, title card, Whisper, music, sound effects or captions; use it only for diagnosing basic project creation.

## Stock sources, keys, licences and credits

- **Openverse:** openly licensed photo search; no API key in this pipeline. See https://api.openverse.org/v1/.
- **Wikimedia Commons:** no normal API key; the search filters to permissive licences by default. See https://www.mediawiki.org/wiki/API:Imageinfo.
- **Pexels:** optional PEXELS_API_KEY; see https://www.pexels.com/api/documentation/. The API asks for a prominent Pexels link and photographer credits where possible.
- **Pixabay:** optional PIXABAY_API_KEY; see https://pixabay.com/api/docs/. Its API has caching requirements and prohibits systematic mass downloads.

To add provider keys, copy .env.example to a private root-level .env and fill only the keys you have. .env is gitignored; never commit it or paste real keys into issues/PRs. Openverse and Wikimedia still work without Pexels/Pixabay keys, subject to internet access and provider limits.

Generated stock files live under projects\nutty-putty-cave\assets\stock\. Review stock_manifest.json and CREDITS.txt before publication, verify the original source page/licence and add the required credits to your video description. Licence metadata can be inaccurate; this manifest is a research aid, not a legal guarantee. Do not upload stock assets to GitHub or redistribute them as a standalone media library. The project directory is intentionally gitignored and must be retained on your PC because the draft refers to local media paths.

Hugging Face image generation is **not triggered automatically**: Inference Providers can use credits or incur costs and models have different terms. Use the existing scripts/prepare_assets.py review/download workflow when deliberately generating or collecting extra assets; check model licence and possible cost first.

## CapCut keyframe compatibility

The text helper currently uses the known position keyframes for the slide/settle motion. Opacity and scale keyframes are intentionally disabled until the exact installed capcut-cli version confirms its supported property names; do not guess that the field is alpha or opacity.

Run locally, with the intended CLI installed:

       capcut doctor
       capcut describe --command compile | Select-String -Pattern "alpha|opacity|animation|transition|fade|mask|easing|text"

Only enable settings.text_caps after the output proves the specific property is supported. Native Remotion transitions are documented in https://www.remotion.dev/docs/transitions; the main CapCut project must use properties actually accepted by the installed CLI.

## Tests and maintenance

Run tests from the repository root:

       .\.venv\Scripts\python.exe -m unittest discover -s tests -v

GitHub Actions also checks Python compilation, timing/asset tests, Windows PowerShell parsing and Motion Lab types. These checks validate source code, not a locally rendered video; a final visual review of the newest CapCut project and exported MP4 is still required.

The persistent AI editing brief lives at .agents/skills/montage-director/SKILL.md. The detailed style / quality workflow is in docs/MONTAGE_UPGRADE.md; the GitHub motion research and keyframe recipe design are in docs/MOTION_REFERENCES.md.
