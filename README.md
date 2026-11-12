# Video1 Test — local-first montage builder

This repository builds an **editable, multitrack CapCut Desktop project** from local narration and illustrations. It does not export a final MP4 automatically. The target style is narration-led documentary montage: changing visual sources, restrained motion, concise designed callouts, purposeful sound, and a clean timeline—not a pile of random transitions.

## Latest montage workflow

The story-specific full build uses the hybrid_whiteboard engine:

- Pure-white canvas with hero illustrations alternating left / right / centre.
- Individually timed entrance, hold motion and exit keyframes; short overlap between scene layers where useful.
- A larger, story-aware motion vocabulary: pop, directional slides, drop/rise, tilt-pop, diagonal sweep, zoom-through and spin-in, plus shrink, slide, drop, tilt and zoom exits. Entrance choice reads each beat's emotion, shock level and trigger phrase, so high danger and solemn aftermath do not receive the same transition.
- A layered secondary image on nearly every post-opening scene, with 7 layout patterns, separate keyframes, and occasional paired-card collages that place 3 images on screen at once. The pair enters with a small stagger and uses different exit recipes rather than simply cutting away.
- Selective secondary B-roll images chosen from a query attached to the closest story beat, instead of always recycling the next local image.
- A full-screen, cropped 16:9 stock B-roll hero about every fifth scene when a relevant, unused match exists; the original supplied art is used when no nearby beat match is available.
- A local ASSET_STOCK_CONTACT_SHEET.jpg lets you review fetched images alongside their provider, query, and licence before publishing.
- Concise keyword and chapter text styled by scripts/text_system.py: a restrained ink/red/gold palette, three semantic size tiers, safe-area clamping, collision nudging, and semantic slam/tilt/zoom/pop/directional-slide/rise animations with scale-out.
- Optional sound accents for selected entrances / story beats. Effects are not forced onto every element.
- Structural spec QA in scripts/qa_spec.py: invalid/overlong clips, keyframes after clip end, very large or off-safe text, overlapping labels and long gaps between visible starts are logged as QA messages.
- Source media stays local. A manifest and CREDITS.txt are created for fetched stock images.

The full build adds concrete English stock-search terms to each prepared story beat. Verified transparent PNGs are marked in the asset manifest and preferred for secondary cutout-style layers when available; ordinary opaque stock images remain supported. The stock searcher tries Openverse and Wikimedia Commons without API keys. Pexels and Pixabay are optional when their keys are present in process environment variables or the root .env. If a provider fails or no image survives filtering, the project falls back to its existing local artwork.

## Unified production pipeline

The current architecture uses one production plan and several specialised tools:

- Python creates the time-aligned shot/layer plan and performs read-only toolchain detection.
- CapCut keeps the supplied photos, narration, music and sound effects editable.
- HyperFrames + GSAP renders compound HTML/SVG/image layers. Every layer receives a selected entrance, a separate camera-drift/hold recipe, and a separate exit/transition recipe.
- Remotion + GSAP renders selected React compositions such as case-file overlays. Its bridge passes exact scene FPS and duration-in-frames to the renderer.
- Every transparent ProRes output is checked with FFprobe for alpha pixel format and exact duration before it becomes a separate CapCut track.
- The motion catalogue contains 224 deterministic choreography variants across 16 behaviour families. The director selects by role, emotion, impact and recent use; CapCut-compatible choices map onto verified native transform keyframes, while richer masks/blur/vector motion stay in GSAP renderers.
- Narration remains internal timing/reference data. The production plan explicitly disables transcript/subtitle overlays.

The generated reports are written to the project's build folder: `production_plan.json`, `TOOLCHAIN_REPORT.md`, `RENDERER_MANIFEST.json`, `ASSET_DEPARTMENT_REPORT.json/.md`, `ASSET_GENERATION_QUEUE.json`, and `QA_REPORT.md`. These reports validate structure and metadata; they do not replace review of the actual CapCut preview.

### Missing illustrations and AI-generated assets

The preparation stage creates `projects/nutty-putty-cave/scene_plan.csv` once and preserves it on later runs so reviewed scene prompts are not overwritten. The asset department writes `ASSET_GENERATION_QUEUE.json` with scene-specific visual gaps and prompts that follow the supplied 2D cartoon art direction.

The existing Hugging Face generator is connected to this queue, but it never runs automatically. Generation may consume provider credits. First review the prompt and cost, then explicitly run the command for the missing scene:

```powershell
.\.venv\Scripts\python.exe .\scripts\prepare_assets.py generate-image --project projects\nutty-putty-cave --scene-id scene_012 --prompt "Paste the reviewed prompt from ASSET_GENERATION_QUEUE.json" --confirm-possible-cost
```

The generated file is not inserted merely because it exists. Review the model/provider terms and the generated image, then mark its candidate ID as approved:

```powershell
.\.venv\Scripts\python.exe .\scripts\prepare_assets.py review-license --project projects\nutty-putty-cave --id C0001 --notes "Reviewed model card and provider terms; approved for this video."
```

Use the actual candidate ID returned by the asset manifest. The candidate must remain selected and have `license_reviewed=yes` before the engine can consider it for the matching story beat.

To create a real transparent cutout from a selected and reviewed local image, install the optional dependency only when needed:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-cutout.txt
.\.venv\Scripts\python.exe .\scripts\prepare_assets.py remove-background --project projects/nutty-putty-cave --id C0001 --confirm-model-download
```

Use the actual candidate ID. The first run may download a local segmentation model. The command requires explicit acknowledgement, preserves the source licence review, verifies visible transparent pixels, and creates a new selected PNG candidate. Inspect the cutout edges before using it. Opaque illustrations remain ordinary image layers; only files with real transparent pixels may be used as cutouts. The engine never fakes transparency with a white/black matte.

## Run the latest version

1. Ensure the local working copy is on `feat/universal-montage-engine`, preserve local changes, and **close CapCut completely**.
2. Confirm Remotion and GSAP dependencies exist in `motion-lab/node_modules`. If absent, review `motion-lab/package.json` and run `npm install` from `motion-lab` once.
3. From the repository root, run:

       cd F:\video1_test
       .\run_unified_pipeline.ps1

4. This safe launcher does not switch branches, pull, reset, or clean the working tree. It prepares local assets, searches licensed stock for beat queries, creates the production and asset plans, renders selected HyperFrames/Remotion layers, and builds an editable CapCut draft.
5. Review `projects\nutty-putty-cave\build\QA_REPORT.md`, `ASSET_DEPARTMENT_REPORT.md`, `production_plan.json`, `TOOLCHAIN_REPORT.md`, and `RENDERER_MANIFEST.json`.
6. Open the newest CapCut draft, review representative scenes and all story-critical moments, then export only after visual and audio QA.

The legacy `.\run_nutty_putty.ps1` performs Git branch switching and pulling. Do not use it while local changes are present; use `.\run_unified_pipeline.ps1` instead.

## HyperFrames + Remotion graphics bridge

The main CapCut timeline remains the editable assembly. HyperFrames is an optional renderer for transparent titles, callouts and connecting arrows. It does not replace the source-photo tracks or the Python keyframe engine.

The bridge is disabled unless the project config contains a top-level `hyperframes` object with `enabled: true` and a reviewed `elements` list. The current bridge accepts `title`, `callout`, `arrow`, `image`, `shape`, and short functional `text` elements. Images are copied into the generated composition's local assets folder; shape and text layers receive independent GSAP timelines. A future story planner can populate that list from narration beats and verified relationships.

Example config fragment:

```json
{
  "hyperframes": {
    "enabled": true,
    "version": "0.8.221",
    "workers": 2,
    "elements": [
      {
        "id": "corkscrew-title",
        "type": "title",
        "start": 8.4,
        "duration": 3.1,
        "kicker": "CASE FILE",
        "title": "THE CORKSCREW",
        "note": "Illustrative reconstruction",
        "x": 0.06,
        "y": 0.70,
        "width": 0.68,
        "font_size": 52,
        "accent": "#D94C42"
      },
      {
        "id": "rope-direction",
        "type": "arrow",
        "start": 12.0,
        "duration": 2.2,
        "x1": 0.22,
        "y1": 0.44,
        "x2": 0.66,
        "y2": 0.55,
        "label": "LOAD DIRECTION",
        "accent": "#D94C42"
      }
    ]
  }
}
```

The bridge renders one full-duration transparent ProRes 4444 MOV and appends it as a separate topmost CapCut video track. Each image, shape, text, title, callout and arrow gets its own GSAP timeline with three coordinated decisions: entrance, camera drift while visible, and transition/exit. The motion recipes are selected deterministically from the shared catalogue. FFprobe verifies the codec, alpha pixel format and output duration before the draft is compiled.

The bridge uses the existing local `hyperframes-engine/hyperframes.json` when present, but does not require that untracked folder: a minimal build-local HyperFrames project config is created automatically when it is absent. The user's local template is never modified. Rendering prefers the local GSAP bundle from `motion-lab/node_modules`; a version-pinned CDN is the fallback. Verify alpha import in the installed CapCut version before publication.

The renderer consumes story-specific graphic instructions from the project configuration. The asset department can prepare beat-specific prompts and route selected, source/license-reviewed image assets into the matching beat. Semantic image recognition is not claimed automatically: source-to-beat relevance and generated/cutout edge quality still require visual review.

To render a smoke-test composition without changing a real project's config or CapCut draft, run:

```powershell
python .\scripts\render_hyperframes_demo.py
```

The six-second demo writes a transparent overlay MOV under `build\hyperframes-demo\hyperframes\overlay.mov`. It does not create or modify a CapCut project.

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

GitHub Actions checks Python compilation and tests, Windows PowerShell parsing, Motion Lab types, a real Remotion ProRes-alpha render, and a real layered HyperFrames ProRes-alpha render. These are renderer smoke tests, not a final quality judgement of the complete documentary; review the newest CapCut draft and exported MP4 before publication.

The persistent AI editing brief lives at .agents/skills/montage-director/SKILL.md. The detailed style / quality workflow is in docs/MONTAGE_UPGRADE.md; the GitHub motion research and keyframe recipe design are in docs/MOTION_REFERENCES.md.
