# Video1 Test — independent Bendia-style montage builder

This branch builds a new editable CapCut draft for the Nutty Putty Cave story. The current Nutty Putty edit is a clean rebuild, not a revision of the earlier Whiteboard/Hybrid montage.

## Current production path

Run only:

\`\`\`powershell
.\run_nutty_putty.ps1
\`\`\`

The runner uses \`scripts/build_bendia_cut.py\`. It does not call or import the earlier \`prepare_nutty_putty.py\`, \`build_montage.py\`, or \`hybrid_engine.py\` montage pipeline.

The new edit is created only from:
- The original ElevenLabs narration file.
- The 28 original Nutty Putty story illustrations.
- The local Saoud_SFX_Pack sound library.
- Freshly generated scene plates, graphics and cave ambience made by the new script.

No files from the old CapCut timeline, old presenter poses, old generated cards, old music, old captions, or old visual plates are used.

## Visual direction

The edit is a Bendia-inspired documentary montage, not a static whiteboard presentation:
- No opening title card. The first illustration and narration both start at 00:00.
- 16:9, 1920×1080, 30 fps.
- Approximately 40–48 visual cuts for a 104-second narration, with a fast 1.5–3 second rhythm.
- Alternating dark evidence punches, clean white editorial frames, split compositions and changing image scale.
- Original illustrations placed in framed archive-style compositions.
- Large, short impact words and numbers; restrained red/yellow hand-marked arrows, pointers and underlines.
- Fast pop/slide/zoom motion and occasional controlled shock shake.
- No full-sentence subtitle track.
- Saoud sound effects placed at story events, with a newly generated low-level cave air bed.

The edit is not claimed to be a frame-for-frame copy of Bendia. It uses an original composition system based on the style analysis already performed.

## Build requirements

- Windows PowerShell.
- Existing repository \`.venv\` with Pillow.
- \`ffmpeg\`, \`ffprobe\`, and \`capcut\` available on PATH.
- \`capcut-cli\` current enough to support \`compile --into\` and \`register --materials\`.
- Original source files in \`F:\Videos Chanel\videos\v2\p1\`.
- Saoud sound library at \`F:\video1_test\Saoud_SFX_Pack\` or a path set in \`SAOUD_SFX_PACK\`.

If the local source paths differ, set them before running:

\`\`\`powershell
$env:NUTTY_PUTTY_AUDIO = "FULL_PATH_TO_ORIGINAL_NARRATION.mp3"
$env:NUTTY_PUTTY_IMAGES_DIR = "FOLDER_CONTAINING_THE_28_ORIGINAL_IMAGES"
$env:SAOUD_SFX_PACK = "FULL_PATH_TO_SAOUD_SFX_PACK"
\`\`\`

## CapCut project shell

For modern CapCut builds, create a fresh empty project in the installed CapCut app first:
1. Open CapCut and create a new empty project named \`Nutty Putty Cave — Bendia Cut\`.
2. Save it and close CapCut completely.
3. In PowerShell, set \`NUTTY_PUTTY_CAPCUT_SHELL\` to that project's folder:

\`\`\`powershell
$store = Join-Path $env:LOCALAPPDATA "CapCut\User Data\Projects\com.lveditor.draft"
$shell = Get-ChildItem -LiteralPath $store -Directory |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "draft_content.json") } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $shell) { throw "No CapCut project shell found." }

$env:NUTTY_PUTTY_CAPCUT_SHELL = $shell.FullName
\`\`\`

Then run \`.\run_nutty_putty.ps1\`. The build first checks that the selected project is empty, fills it with the new timeline, registers its media, and writes a compatibility report.

## Deletion scope

The runner removes only:
- The rejected previous draft folder named \`Video1_Whiteboard_Pro_20261112_104348\`.
- The previous generated workspace \`projects\nutty-putty-cave\`.
- Any previous output in the new workspace \`projects\nutty-putty-bendia-cut\` before rebuilding.

It does not delete the original audio, the 28 original source images, Saoud_SFX_Pack, or any other CapCut project.

## Output

The new independent workspace is:

\`projects\nutty-putty-bendia-cut\`

Important files:
- \`build/BENDIA_EDIT_MANIFEST.json\` — shot sequence and timing.
- \`build/BENDIA_EDIT_NOTES.md\` — edit design and source policy.
- \`build/CAPCUT_COMPATIBILITY_REPORT.txt\` — CapCut version, lint and diagnose output.
- \`assets/bendia_scenes/\` — fresh visual plates created for this edit.
- \`assets/audio/\` — newly processed voice and generated ambience.

This creates an editable CapCut draft. It does not export the final MP4; review the full timeline and mix in CapCut, then export from the app.
