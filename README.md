# Video1 Test — editable CapCut montage builder

This repository builds a **local, editable CapCut desktop draft** from a voiceover, scene images, and presenter pose images. It does not upload your media to GitHub and does not flatten the edit into a single MP4.

## What it builds

- A main visual track with slow Ken Burns-style zooms and small alternating pans.
- Controlled Mix transitions between the scene images.
- A separate voice track, with the original narration kept dominant.
- Optional presenter cutouts on a separate overlay track, with alternating left/right placement. The script asks CapCut's smart-matting command to remove the JPEG backgrounds when supported.
- Optional editable captions if the local Whisper CLI is installed.
- A CSV shot plan and a sound-effect cue sheet to review timing and add the best matching CapCut library sounds.

## Important limitation

The audio and images are on your computer, so GitHub cannot inspect or edit them remotely. The script checks them when run locally. It can use Whisper sentence timings to make cuts feel more intentional, but it does **not** claim semantic image-to-sentence matching: filenames and timestamps do not reveal exactly what an image depicts. Review build/scene_timing.csv before rendering, and move shots in CapCut when an image does not match the spoken line.

The presenter images are JPEGs, not transparent PNGs. CapCut smart matting may remove their backgrounds, but the result depends on the actual images and installed CapCut version. Inspect the first output before building the final video.

## Requirements

- Windows 10/11
- Node.js 18 or newer
- CapCut Desktop installed
- Python 3.10 or newer
- capcut-cli, installed from npm
- mutagen (installed from requirements.txt)
- Optional: OpenAI Whisper CLI for transcript-driven boundaries and captions. If Whisper is not found, the project is still created with duration-based timing.

## Run on Windows

Close CapCut first, then open this repository in VS Code. Run these commands in the VS Code PowerShell terminal:

~~~powershell
node --version
npm --version
npm install -g capcut-cli

py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

.\.venv\Scripts\python.exe .\scripts\build_montage.py
~~~

An easier option is to run the included Windows launcher. It creates the virtual environment, installs the small Python dependency, and installs capcut-cli through npm if needed:

~~~powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\run_montage.ps1
~~~

The script reads paths from config.json. Update a path if it does not exist on your machine. The source images and MP3 remain local and are excluded from Git.

Optional captions: install Whisper and its FFmpeg dependency separately, then verify that whisper --help works in the same terminal. Whisper is optional because its PyTorch download can be large.

~~~powershell
whisper --help
capcut doctor
~~~

## Open the draft

When the script finishes, it prints the draft directory and writes build/build_report.json. Reopen CapCut and find **Video1 Test - Professional Montage** in Projects. If it does not appear, read the draft directory in the report and check that drafts_dir in config.json points to your installed CapCut draft-library folder. Do not move the generated draft directory after creation.

The project is editable: visual shots, presenter overlays, narration, and captions (when available) are separate timeline segments. Review the timeline and sound-effect cues before exporting the final video from CapCut.

## First-pass sound design

The builder creates build/SFX_Cue_Sheet.csv; it does not falsely claim to have inserted CapCut catalogue effects. Search the listed terms in CapCut's Audio / Sound effects library and place a few well-timed cues on a separate audio track. Keep effects quiet under speech; avoid a whoosh on every single cut.

## Editing references

- YouTube audience retention: https://support.google.com/youtube/answer/9314415
- CapCut keyframe animation: https://www.capcut.com/tools/keyframe-animation
- capcut-cli project and command reference: https://github.com/renezander030/capcut-cli
- capcut-cli Ken Burns workflow: https://github.com/renezander030/capcut-cli/blob/master/examples/keyframe-zoom.md

This project is a community workflow built on capcut-cli, not an official CapCut product.
