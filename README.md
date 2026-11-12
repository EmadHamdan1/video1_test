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

## Run the latest version

1. Save edits and **close CapCut completely**.
2. Open PowerShell and run:

       cd F:\video1_test
       git fetch origin
       git switch feat/bendia-inspired-nutty-putty
       git pull origin feat/bendia-inspired-nutty-putty
       .\run_nutty_putty.ps1

3. Let the full build finish. A successful run ends with BUILD SUCCESSFUL. If it ends with BUILD FAILED or a traceback, read the error and projects\nutty-putty-cave\build\QA_REPORT.md; do not open the previous draft and assume it changed.
4. Open the **newest CapCut draft** created by this run. Inspect the beginning, middle, high-impact beats and ending. The automated QA report cannot judge whether the story illustration truly matches the words being spoken.
5. Export and review the MP4 from CapCut only after visual/audio review.

The command .\run_nutty_putty.ps1 -BasicOnly deliberately produces a minimal draft without stock fetching, title card, Whisper, music, sound effects or captions; use it only for diagnosing basic project creation.

## Bendia-inspired Nutty Putty profile

The \`feat/bendia-inspired-nutty-putty\` branch adds an original illustrated-casefile profile: white stage, faster 2.45s target visual rhythm, story-selected pop/slide/zoom motion, selective evidence inserts, brief fact/keyword cards, and restrained sound accents. It does not copy Bendia's frames or assets.

The build searches for a local \`Saoud_SFX_Pack\`. Set an explicit path before running when it is not beside the voiceover or in a standard project/download folder:

       $env:SAOUD_SFX_PACK = "D:\Audio\Saoud_SFX_Pack"

The pack remains on your computer. The build copies only chosen, converted sounds into the ignored project folder and writes \`projects\nutty-putty-cave\build\SFX_PACK_MANIFEST.json\`. Original JPEGs are not magically background-removed; only files with verified transparency are treated as cutouts.

## Configure local Nutty Putty source media

The source audio and 28 story images are not stored in Git. The build accepts their actual local locations through PowerShell environment variables, so it does not require the original `D:\\Videos Chanel\\v2\\p1` folder.

Set the full narration file path and the folder containing the 28 original images (keep their original filenames):

```powershell
$env:NUTTY_PUTTY_AUDIO = "E:\\YourFolder\\narration.mp3"
$env:NUTTY_PUTTY_IMAGES_DIR = "E:\\YourFolder\\images"
.\\run_nutty_putty.ps1
```

Alternatively, place `narration.mp3` and an `images` folder inside one source folder, then set only:

```powershell
$env:NUTTY_PUTTY_SOURCE_DIR = "E:\\YourFolder\\NuttyPuttySource"
.\\run_nutty_putty.ps1
```

The image directory must contain the 28 image files expected by `scripts/prepare_nutty_putty.py`. Presenter poses are optional.

### Recover from CapCut "Couldn't use project" / unusual-path rejection

A CLI build can be written successfully but still be rejected by a newer CapCut desktop version when its source template carries older app-version metadata. The reliable recovery path is to fill a blank project created by the CapCut installation currently on the PC.

1. Update the CLI while CapCut is closed:

```powershell
npm install -g capcut-cli@0.33.1
capcut --version
```

2. Open CapCut, create a new **empty** project named `Nutty Putty Cave - Recovered`, save it, then close CapCut completely.
3. In the same PowerShell window, point the builder at that new project and rebuild:

```powershell
$store = Join-Path $env:LOCALAPPDATA "CapCut\User Data\Projects\com.lveditor.draft"
$shell = Get-ChildItem -LiteralPath $store -Directory |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "draft_content.json") } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $shell) { throw "The new CapCut shell project was not found." }

$env:NUTTY_PUTTY_CAPCUT_SHELL = $shell.FullName
$env:NUTTY_PUTTY_AUDIO = "F:\Videos Chanel\videos\v2\p1\ElevenLabs_2026-06-03T09_19_08_Mark - Natural Conversations_pvc_sp100_s39_sb75_se0_b_m2.mp3"
$env:NUTTY_PUTTY_IMAGES_DIR = "F:\Videos Chanel\videos\v2\p1"

cd F:\video1_test
git pull --ff-only origin feat/bendia-inspired-nutty-putty
.\run_nutty_putty.ps1
```

The builder validates the blank shell with `capcut compile --check` before writing. It keeps the CapCut-created project identity, adds media registration, and records read-only `version`, `lint`, and `diagnose` results in `projects\nutty-putty-cave\build\CAPCUT_COMPATIBILITY_REPORT.txt`. Do not open CapCut while the build is running. Keep the rejected draft as a backup until the recovered one opens correctly.

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
