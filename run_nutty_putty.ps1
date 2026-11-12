$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0

# Use the script's own directory. MyInvocation can be empty in nested/script-hosted calls.
if ([string]::IsNullOrWhiteSpace($PSScriptRoot)) {
    throw "Could not determine the repository directory. Run .\run_nutty_putty.ps1 from its file path."
}
$RepoRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
Set-Location -LiteralPath $RepoRoot

$Branch = "feat/bendia-inspired-nutty-putty"
$OldProject = Join-Path $RepoRoot "projects\nutty-putty-cave"
$NewProject = Join-Path $RepoRoot "projects\nutty-putty-bendia-cut"
$BuildDir = Join-Path $NewProject "build"
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$PythonScript = Join-Path $RepoRoot "scripts\build_bendia_cut.py"
$OldDraft = Join-Path $env:LOCALAPPDATA "CapCut\User Data\Projects\com.lveditor.draft\Video1_Whiteboard_Pro_20261112_104348"

Write-Host ""
Write-Host "=== NUTTY PUTTY - FRESH BENDIA-STYLE REBUILD ===" -ForegroundColor Cyan
Write-Host "This is a new edit pipeline. It does not import the previous montage, its timeline, generated plates, presenter assets, or old music."
Write-Host "The opening frame and original narration both start at 00:00. There is no intro card."
Write-Host "Repository: $RepoRoot"
Write-Host ""

# Update the local branch before checking/building.
git switch $Branch
$GitExitCode = $LASTEXITCODE
if ($GitExitCode -ne 0) { throw "Could not switch to $Branch. Git exit code: $GitExitCode" }

git pull --ff-only origin $Branch
$GitExitCode = $LASTEXITCODE
if ($GitExitCode -ne 0) { throw "Git pull failed. Git exit code: $GitExitCode. Resolve Git status before building." }

# Verify all prerequisites before deleting any previous generated output.
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "The existing .venv Python was not found: $Python"
}
if (-not (Test-Path -LiteralPath $PythonScript -PathType Leaf)) {
    throw "The new Python builder was not found: $PythonScript"
}

$DependencyCheck = & $Python -c "import PIL; print('Pillow ready')" 2>&1
$PythonExitCode = $LASTEXITCODE
if ($PythonExitCode -ne 0) {
    throw "Pillow is not available in the existing .venv. Python exit code: $PythonExitCode. Details: $DependencyCheck"
}
Write-Host $DependencyCheck

foreach ($Name in @("ffmpeg", "ffprobe", "capcut")) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name is missing from PATH. Install/repair that tool before building."
    }
}

$CapCutProcess = Get-Process -Name "CapCut" -ErrorAction SilentlyContinue
if ($CapCutProcess) {
    throw "Close CapCut completely before rebuilding. The script will not terminate the editor."
}

# Re-read original media directly; never use assets from the previous montage.
if ([string]::IsNullOrWhiteSpace($env:NUTTY_PUTTY_AUDIO)) {
    $env:NUTTY_PUTTY_AUDIO = "F:\Videos Chanel\videos\v2\p1\ElevenLabs_2026-06-03T09_19_08_Mark - Natural Conversations_pvc_sp100_s39_sb75_se0_b_m2.mp3"
}
if ([string]::IsNullOrWhiteSpace($env:NUTTY_PUTTY_IMAGES_DIR)) {
    $env:NUTTY_PUTTY_IMAGES_DIR = "F:\Videos Chanel\videos\v2\p1"
}
if ([string]::IsNullOrWhiteSpace($env:SAOUD_SFX_PACK)) {
    $env:SAOUD_SFX_PACK = Join-Path $RepoRoot "Saoud_SFX_Pack"
}
if ([string]::IsNullOrWhiteSpace($env:NUTTY_PUTTY_CAPCUT_SHELL)) {
    throw 'Create a NEW empty CapCut project, save it, close CapCut, then set $env:NUTTY_PUTTY_CAPCUT_SHELL to its full folder path.'
}

if (-not (Test-Path -LiteralPath $env:NUTTY_PUTTY_AUDIO -PathType Leaf)) {
    throw "Original narration file not found: $env:NUTTY_PUTTY_AUDIO"
}
if (-not (Test-Path -LiteralPath $env:NUTTY_PUTTY_IMAGES_DIR -PathType Container)) {
    throw "Original illustrations folder not found: $env:NUTTY_PUTTY_IMAGES_DIR"
}

$ShellPath = [System.IO.Path]::GetFullPath($env:NUTTY_PUTTY_CAPCUT_SHELL)
if (-not (Test-Path -LiteralPath $ShellPath -PathType Container)) {
    throw "The NUTTY_PUTTY_CAPCUT_SHELL folder does not exist: $ShellPath"
}
$ShellHasDraftFile = (Test-Path -LiteralPath (Join-Path $ShellPath "draft_content.json") -PathType Leaf) -or
                     (Test-Path -LiteralPath (Join-Path $ShellPath "draft_info.json") -PathType Leaf)
if (-not $ShellHasDraftFile) {
    throw "The selected folder is not a CapCut project shell (draft_content.json/draft_info.json missing): $ShellPath"
}
$OldDraftFull = [System.IO.Path]::GetFullPath($OldDraft).TrimEnd("\")
$ShellFull = $ShellPath.TrimEnd("\")
if ([string]::Equals($ShellFull, $OldDraftFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "The selected shell is the rejected old montage. Create a separate NEW empty project in CapCut."
}

Write-Host ""
Write-Host "Preflight passed." -ForegroundColor Green
Write-Host "Original audio: $env:NUTTY_PUTTY_AUDIO"
Write-Host "Original illustrations: $env:NUTTY_PUTTY_IMAGES_DIR"
Write-Host "Saoud effects: $env:SAOUD_SFX_PACK"
Write-Host "New CapCut shell: $ShellPath"
Write-Host ""

# Remove only the exact rejected draft and generated workspaces requested for replacement.
if (Test-Path -LiteralPath $OldDraft) {
    Remove-Item -LiteralPath $OldDraft -Recurse -Force
    Write-Host "Deleted the rejected old CapCut montage draft." -ForegroundColor Yellow
}
if (Test-Path -LiteralPath $OldProject) {
    Remove-Item -LiteralPath $OldProject -Recurse -Force
    Write-Host "Deleted the previous generated montage workspace. Original source files remain untouched." -ForegroundColor Yellow
}
if (Test-Path -LiteralPath $NewProject) {
    Remove-Item -LiteralPath $NewProject -Recurse -Force
}

Write-Host ""
Write-Host "=== BUILDING THE NEW BENDIA-INSPIRED TIMELINE ===" -ForegroundColor Cyan
& $Python -u $PythonScript
$PythonExitCode = $LASTEXITCODE
if ($PythonExitCode -ne 0) {
    throw "The new Bendia edit failed. Python exit code: $PythonExitCode. Read the [bendia-cut] error above."
}

# Do not report success unless all expected outputs actually exist.
$ManifestPath = Join-Path $BuildDir "BENDIA_EDIT_MANIFEST.json"
$NotesPath = Join-Path $BuildDir "BENDIA_EDIT_NOTES.md"
$CompatibilityPath = Join-Path $BuildDir "CAPCUT_COMPATIBILITY_REPORT.txt"
foreach ($OutputPath in @($ManifestPath, $NotesPath, $CompatibilityPath)) {
    if (-not (Test-Path -LiteralPath $OutputPath -PathType Leaf)) {
        throw "Python returned success, but an expected output is missing: $OutputPath"
    }
}

Write-Host ""
Write-Host "BUILD SUCCESSFUL" -ForegroundColor Green
Write-Host "New project folder: $NewProject"
Write-Host "Edit manifest: $ManifestPath"
Write-Host "Edit notes: $NotesPath"
Write-Host "CapCut compatibility: $CompatibilityPath"
Write-Host "Open the new project named: Nutty Putty Cave - Bendia Cut"
