# Video1 Test — Whiteboard Explainer PRO

This repository builds a **local, editable CapCut Desktop project** from the voiceover, scene illustrations, and presenter poses already stored on the user's PC. Source media is not uploaded to GitHub, and the edit remains a multitrack CapCut draft rather than a flattened MP4.

## What the PRO build changes

- A locally generated whiteboard-paper canvas with subtle dots and a restrained visual identity.
- Each scene illustration sits in a framed card with a soft shadow and small marker-style accents instead of filling the entire 16:9 frame.
- The presenter is on a dedicated foreground track for almost the whole narration. The supplied poses change at measured intervals, with a very small scale/bob animation to avoid a frozen cutout.
- Scene cards use small alternating Ken-Burns moves (scale and position), smooth easing, mostly short dissolves, and occasional documented horizontal/radial blur transitions for emphasis.
- The first scene gets a short reveal; the presenter fades in/out at the beginning/end.
- The launcher installs requirements, creates the project, attempts presenter background matting, and registers the resulting draft in CapCut automatically.
- Editable shot timing and a sound-effect cue sheet are still written to `build/scene_timing.csv` and `build/SFX_Cue_Sheet.csv`.

## Important limits — kept explicit

The media paths point to files on the local Windows PC. GitHub cannot inspect those images or listen to the audio. The current pipeline distributes images in the order configured and times them from narration duration; if local Whisper is installed it can use subtitle boundaries, but **it does not semantically match every illustration to the exact spoken sentence**. Review `build/scene_timing.csv` and move any mismatched scene in CapCut.

Presenter images are JPEGs. The builder asks CapCut to remove their background, but matte quality depends on the actual images and CapCut version. Inspect the first pose; if a white rectangle remains, use CapCut's Remove background / Cutout tool or supply transparent PNGs.

The look is an editable whiteboard-style motion-graphics treatment, not a full hand-drawn animation: still image poses cannot move their hands or lips by themselves. They are animated via scale/position and timed pose changes.

## Requirements

- Windows 10/11
- CapCut Desktop
- Node.js 18+
- Python 3.13 (the launcher uses `py -3.13`)
- `capcut-cli` (installed by the launcher when missing)
- Python packages from `requirements.txt` (`mutagen` and `Pillow`)
- Optional local Whisper CLI for timed captions

## Rebuild the PRO draft

1. Close CapCut completely before running the script.
2. In PowerShell, navigate to the project folder and pull the latest branch changes:

   ```powershell
   cd C:\Users\EmQr\video1_test
   git pull origin feat/capcut-montage-pipeline
   ```

3. Run:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\run_montage.ps1
   ```

The launcher creates a new dated `Video1_Whiteboard_Pro_YYYYMMDD_HHMMSS` draft and attempts to register it in CapCut. The older draft is left in place as a rollback copy. Open **Video1 Test - Whiteboard Explainer PRO** from CapCut's home/project list. The project uses generated assets in `build\visuals`; do not delete that folder while the draft depends on it.

## Quality check before export

Check the first 10 seconds, one middle section, a presenter-pose change, and the final 5 seconds. Confirm the presenter cutout, scene framing, transitions, and voice track. If the images do not match the narration at a particular point, move the image segments using `build/scene_timing.csv` as a guide. The project has not been visually verified on this PC until that playback review is done.

## Recommended toolchain for future edits

- **FFmpeg + FFprobe:** local media inspection, proxy previews, audio/video filters, and duration checks. Install on Windows with `winget install -e --id Gyan.FFmpeg`. Reopen PowerShell afterwards, then verify `ffmpeg -version` and `ffprobe -version`.
- **Arkeonix CapCut MCP (optional local MCP server):** adds tools for inspecting local CapCut drafts and applying keyframes, transitions, filters, masks, and text. Its repository documents backups and advises not to write while CapCut is open: https://github.com/daviilpzDev/arkeonix-capcut-mcp. Install separately from this repository:

  ```powershell
  cd C:\Users\EmQr
  git clone https://github.com/daviilpzDev/arkeonix-capcut-mcp.git
  cd .\arkeonix-capcut-mcp
  npm install
  npm test
  ```

  Then connect `src/server.js` to a compatible local MCP host, such as VS Code Copilot. Installing it alone does not connect it to the ChatGPT web session.
- **Remotion (optional motion-graphics lab):** a separate React-based workspace for custom animated callouts, kinetic typography, hand-drawn/paper-style motion, and transition previews. Short renders can be imported into CapCut; the rendered clip itself is not editable as separate React layers inside CapCut. Start guide: https://www.remotion.dev/docs/. Remotion's free license covers individuals and companies up to three people, subject to its terms: https://www.remotion.dev/docs/license/pricing.
- **Whisper (optional transcription):** can create time-coded captions and candidate narration edit points; it does not decide which image semantically matches each sentence. Install FFmpeg first. From this repository, use `.\.venv\Scripts\python.exe -m pip install -U openai-whisper`. The package pulls PyTorch and can be a large installation, so skip it until timed captions are needed.

Keep the original draft and media as backups. Before any MCP edit, close CapCut, clone the target draft, review planned changes, and inspect the saved project in CapCut before exporting.

## Create a new video project (asset pipeline)

The **system repository is shared**. Create one local folder per video under `projects/`; do not make a new GitHub repository for each episode unless you deliberately want a separate codebase. Projects and downloaded media are ignored by Git so they remain on your PC.

### 1. Create a project and plan the story

Run from the repository root in PowerShell:

```powershell
git pull origin feat/capcut-montage-pipeline
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\asset_tool.ps1 new-project --name "Horror Explainer Episode 01"
```

The command prints the actual project path. In that folder, replace the placeholder in `story.txt` with the narration script (one sentence or paragraph per visual beat works best), then run:

```powershell
.\asset_tool.ps1 plan --project projects\horror-explainer-episode-01
```

The planner writes `scene_plan.csv`, with one row per sentence, a segment ID, and a suggested search query. The query is a first draft: verify it, especially for Arabic stories where an English translation may yield more stock-media results.

### 2. Search and review images or video

```powershell
.\asset_tool.ps1 search-plan --project projects\horror-explainer-episode-01 --kind image --max-scenes 8 --limit-per-scene 3
Start-Process .\projects\horror-explainer-episode-01\media_gallery.html
```

Open `media_gallery.html` to compare previews, sources, creators, and license details. The search command does **not** download everything automatically. Choose candidate IDs from the gallery/manifest, then download only those IDs:

```powershell
.\asset_tool.ps1 download --project projects\horror-explainer-episode-01 --ids C0001,C0004,C0008
```

Search more scenes by increasing `--max-scenes` (up to 25). For video clips, use `--kind video`; those clips can be used as scene media just like images. For a hand-drawn explainer, download SVG icons with:

```powershell
.\asset_tool.ps1 icons --project projects\horror-explainer-episode-01 --names search,arrow-right,lightbulb,triangle-alert,circle-check,play
```

### 3. Configure optional API sources

On first use, `asset_tool.ps1` creates a local `.env` file from `.env.example`. It is ignored by Git. Add API keys only there; **never paste keys into source code or commit `.env`**.

- Openverse: works anonymously with rate limits; optional client credentials can be registered on its API site: https://api.openverse.org/v1/
- Wikimedia Commons: no API key needed for normal search; review each file page and its actual license.
- Pixabay: optional `PIXABAY_API_KEY` for photos/video: https://pixabay.com/api/docs/
- Pexels: optional `PEXELS_API_KEY` for photos/video: https://www.pexels.com/api/documentation/. Key issuance may be paused at times; the pipeline works without it.
- Freesound: optional `FREESOUND_API_KEY` for sound search: https://freesound.org/docs/api/. Search results may download an MP3 preview rather than the full-quality original.
- Lucide: the `icons` command downloads SVGs and the ISC license file; those icons are marked reviewed because the included upstream license is explicit.

The manifest records a source URL, creator, license text/URL, downloaded path/time, and whether you personally reviewed the license. A license label is not a legal guarantee. After checking the source and terms, record the review:

```powershell
.\asset_tool.ps1 review-license --project projects\horror-explainer-episode-01 --id C0001 --notes "Verified the license and recorded attribution requirements."
```

Do this for each media item before publication. The gallery visibly flags items that still need review.

### 4. Search for sound effects

```powershell
.\asset_tool.ps1 search-plan --project projects\horror-explainer-episode-01 --kind audio --max-scenes 8 --limit-per-scene 2
Start-Process .\projects\horror-explainer-episode-01\media_gallery.html
```

Choose the audio IDs and download them the same way as images. Then open `media_candidates.csv` in a spreadsheet editor and set `start_seconds` and `volume` for each chosen audio row (for example, a quiet whoosh at 6.4 seconds with volume 0.10). After setting the times, `apply --include-sfx` places those local files on the project's separate audio-effects track. Keep cues sparse and below the narration.

### 5. Optional AI-generated illustration from Hugging Face

This step is optional and **may consume paid inference credits**; availability and price depend on your HF account and selected provider/model. Check the model card and terms first.

1. Create a Hugging Face token with Inference Providers permission and add it to local `.env` as `HF_TOKEN=...`. You can set `HF_IMAGE_MODEL` there too.
2. Install the optional client once:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements-ai.txt
   ```

3. After running `plan`, generate a custom illustration for a selected story beat:

   ```powershell
   .\asset_tool.ps1 generate-image --project projects\horror-explainer-episode-01 --scene-id scene_001 --confirm-possible-cost
   ```

The script uses that scene's sentence as the prompt, stores the result locally, and records model/source information in the manifest. AI-generated output still needs a human check for accuracy, model terms, safety, and visual style. Hugging Face documents the API here: https://huggingface.co/docs/inference-providers/tasks/text-to-image.

### 6. Apply chosen media and build the editable CapCut project

After selecting/downloading scene media, pass the narration audio. The presenter folder is optional:

```powershell
.\asset_tool.ps1 apply --project projects\horror-explainer-episode-01 --audio "D:\Path\to\narration.mp3" --presenter-dir "C:\Path\to\presenter-poses" --include-sfx
.\asset_tool.ps1 build --project projects\horror-explainer-episode-01
```

Remove `--presenter-dir` if the project has no presenter images, and omit `--include-sfx` if you did not set sound-effect times. The build reads that project's own `project.json`, writes reports/assets into its own `build/` folder, creates a dated editable CapCut draft, and attempts to register it. It does not upload local media to GitHub. For proper semantic alignment, review each scene against the narration; the script cannot infer image meaning from filenames alone.

### 7. Reusable animation lab

The `motion-lab/` folder contains editable Remotion source for a whiteboard card, animated word captions, and transition samples. Install and preview it once:

```powershell
cd .\motion-lab
npm install
npm run typecheck
npm run studio
```

Render samples with `npm run render:whiteboard`, `npm run render:caption`, or `npm run render:transitions`. Outputs go to `motion-lab/out/` and are ignored by Git. They can be imported into CapCut as rendered clips; React elements do not turn into independent CapCut layers automatically. The main CapCut builder also applies smooth scale/position/opacity keyframes and phrase-level animated text when Whisper timings or project story text are present.

## Editing principles and sources

- [CapCut: keyframes on PC](https://www.capcut.com/resource/how-to-add-keyframes-in-capcut) — animate position, scale, rotation, opacity, and adjust the timing.
- [Figma: motion design and easing](https://help.figma.com/hc/en-us/articles/41238219562007-Motion-design-fundamentals-Easing) — use acceleration/deceleration intentionally; avoid mechanical linear motion.
- [IBM Design: classic animation principles](https://www.ibm.com/design/language/animation/classic-principles/) — stage the most important information first and avoid competing actions.
- [capcut-cli](https://github.com/renezander030/capcut-cli) and its [keyframe zoom example](https://github.com/renezander030/capcut-cli/blob/master/examples/keyframe-zoom.md) — local editable draft generation, transitions, and keyframes. This is an independent community tool, not an official CapCut product.
- [YouTube audience retention guidance](https://support.google.com/youtube/answer/9314415) — review the intro and retention points when analytics become available.

The style follows a rule of motion hierarchy: the narration and explainer stay primary, the scene card is secondary, and decorative motion is used only to direct attention.
