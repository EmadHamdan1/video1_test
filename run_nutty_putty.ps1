$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot
$Branch = "feat/bendia-inspired-nutty-putty"
$OldProject = Join-Path $RepoRoot "projects\nutty-putty-cave"
$NewProject = Join-Path $RepoRoot "projects\nutty-putty-bendia-cut"
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$OldDraft = Join-Path $env:LOCALAPPDATA "CapCut\User Data\Projects\com.lveditor.draft\Video1_Whiteboard_Pro_20261112_104348"

Write-Host ""
Write-Host "=== NUTTY PUTTY — FRESH BENDIA-STYLE REBUILD ===" -ForegroundColor Cyan
Write-Host "This is a new edit pipeline. It does not import the previous montage, its timeline, generated plates, presenter assets, or old music."
Write-Host "The opening frame and original narration both start at 00:00. There is no intro card."
Write-Host ""

git switch $Branch
if ($LASTEXITCODE -ne 0) { throw "Could not switch to $Branch." }
git pull --ff-only origin $Branch
if ($LASTEXITCODE -ne 0) { throw "Git pull failed. Resolve Git status before building." }

if (-not (Test-Path -LiteralPath $Python)) {
    throw "The existing .venv Python was not found: $Python"
}
$DependencyCheck = & $Python -c "import PIL; print('Pillow ready')" 2>&1
if ($LASTEXITCODE -ne 0) { throw "Pillow is not available in the existing .venv: $DependencyCheck" }

foreach ($Name in @("ffmpeg", "ffprobe", "capcut")) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name is missing from PATH. Install/repair that tool before building."
    }
}

$CapCutProcess = Get-Process -Name "CapCut" -ErrorAction SilentlyContinue
if ($CapCutProcess) {
    throw "Close CapCut completely before rebuilding. The script will not terminate the editor."
}

# Source media are re-read from the original media folder, never from the previous project's copied assets.
if (-not $env:NUTTY_PUTTY_AUDIO) {
    $env:NUTTY_PUTTY_AUDIO = "F:\Videos Chanel\videos\v2\p1\ElevenLabs_2026-06-03T09_19_08_Mark - Natural Conversations_pvc_sp100_s39_sb75_se0_b_m2.mp3"
}
if (-not $env:NUTTY_PUTTY_IMAGES_DIR) {
    $env:NUTTY_PUTTY_IMAGES_DIR = "F:\Videos Chanel\videos\v2\p1"
}
if (-not $env:SAOUD_SFX_PACK) {
    $env:SAOUD_SFX_PACK = Join-Path $RepoRoot "Saoud_SFX_Pack"
}
if (-not $env:NUTTY_PUTTY_CAPCUT_SHELL) {
    throw 'Create a NEW empty project in CapCut, save it, close CapCut, then set $env:NUTTY_PUTTY_CAPCUT_SHELL to the full project folder path.'
}

$ShellPath = [System.IO.Path]::GetFullPath($env:NUTTY_PUTTY_CAPCUT_SHELL)
if (-not (Test-Path -LiteralPath $ShellPath -PathType Container)) {
    throw "The NUTTY_PUTTY_CAPCUT_SHELL folder does not exist: $ShellPath"
}
if ($ShellPath -eq [System.IO.Path]::GetFullPath($OldDraft)) {
    throw "The selected shell is the rejected old montage. Create a separate NEW empty project in CapCut."
}

# The user's explicit request is to remove the rejected previous edit. Delete only its known draft folder and old generated workspace.
if (Test-Path -LiteralPath $OldDraft) {
    Remove-Item -LiteralPath $OldDraft -Recurse -Force
    Write-Host "Deleted the rejected old CapCut montage draft." -ForegroundColor Yellow
}
if (Test-Path -LiteralPath $OldProject) {
    Remove-Item -LiteralPath $OldProject -Recurse -Force
    Write-Host "Deleted the previous generated montage workspace. Original files in F:\Videos Chanel remain untouched." -ForegroundColor Yellow
}
if (Test-Path -LiteralPath $NewProject) {
    Remove-Item -LiteralPath $NewProject -Recurse -Force
}

Write-Host ""
Write-Host "Original audio: $env:NUTTY_PUTTY_AUDIO"
Write-Host "Original illustrations: $env:NUTTY_PUTTY_IMAGES_DIR"
Write-Host "Saoud effects: $env:SAOUD_SFX_PACK"
Write-Host "New CapCut shell: $ShellPath"
Write-Host ""
Write-Host "=== Building a completely new Bendia-inspired timeline ===" -ForegroundColor Cyan

& $Python (Join-Path $RepoRoot "scripts\build_bendia_cut.py")
if ($LASTEXITCODE -ne 0) {
    throw "The new Bendia edit failed. No old montage was restored. Read the error above."
}

$BuildDir = Join-Path $RepoRoot "projects\nutty-putty-bendia-cut\build"
Write-Host ""
Write-Host "BUILD SUCCESSFUL" -ForegroundColor Green
Write-Host "New project folder: $(Join-Path $RepoRoot 'projects\nutty-putty-bendia-cut')"
Write-Host "Edit manifest: $(Join-Path $BuildDir 'BENDIA_EDIT_MANIFEST.json')"
Write-Host "Edit notes: $(Join-Path $BuildDir 'BENDIA_EDIT_NOTES.md')"
Write-Host "CapCut compatibility: $(Join-Path $BuildDir 'CAPCUT_COMPATIBILITY_REPORT.txt')"
Write-Host "Open the new project named: Nutty Putty Cave — Bendia Cut"
