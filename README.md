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
- **Whisper (optional transcription):** can create time-coded captions and candidate narration edit points; it does not decide which image semantically matches each sentence. Install FFmpeg first. From this repository, use `..venvScriptspython.exe -m pip install -U openai-whisper`. The package pulls PyTorch and can be a large installation, so skip it until timed captions are needed.

Keep the original draft and media as backups. Before any MCP edit, close CapCut, clone the target draft, review planned changes, and inspect the saved project in CapCut before exporting.

## Editing principles and sources

- [CapCut: keyframes on PC](https://www.capcut.com/resource/how-to-add-keyframes-in-capcut) — animate position, scale, rotation, opacity, and adjust the timing.
- [Figma: motion design and easing](https://help.figma.com/hc/en-us/articles/41238219562007-Motion-design-fundamentals-Easing) — use acceleration/deceleration intentionally; avoid mechanical linear motion.
- [IBM Design: classic animation principles](https://www.ibm.com/design/language/animation/classic-principles/) — stage the most important information first and avoid competing actions.
- [capcut-cli](https://github.com/renezander030/capcut-cli) and its [keyframe zoom example](https://github.com/renezander030/capcut-cli/blob/master/examples/keyframe-zoom.md) — local editable draft generation, transitions, and keyframes. This is an independent community tool, not an official CapCut product.
- [YouTube audience retention guidance](https://support.google.com/youtube/answer/9314415) — review the intro and retention points when analytics become available.

The style follows a rule of motion hierarchy: the narration and explainer stay primary, the scene card is secondary, and decorative motion is used only to direct attention.
