param([switch]$BasicOnly)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot
$Branch = "feat/bendia-inspired-nutty-putty"
$Project = "projects\nutty-putty-cave"
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"

Write-Host ""
Write-Host "=== Nutty Putty Cave: local-first CapCut build + licensed stock B-roll ===" -ForegroundColor Cyan
Write-Host "This run will not install Python/npm packages or download AI models."
Write-Host "Full mode may query Openverse/Wikimedia online and uses Pexels/Pixabay only when local API keys are configured."
Write-Host "Downloaded stock assets and provenance stay local in the project assets\stock folder."
Write-Host "Updating only the existing GitHub project code..."
git switch $Branch
if ($LASTEXITCODE -ne 0) { throw "Could not switch to $Branch." }
git pull origin $Branch
if ($LASTEXITCODE -ne 0) { throw "Git pull failed. Resolve Git status before building." }

# Fail fast rather than creating environments or installing dependencies.
if (-not (Test-Path -LiteralPath $Python)) {
    throw "The existing .venv Python was not found. No environment was created. Restore the existing local .venv before running this offline build."
}
$DependencyCheck = & $Python -c "import PIL; print('Pillow ready')" 2>&1
if ($LASTEXITCODE -ne 0) { throw "Pillow is not available in the existing .venv. No packages were installed. Details: $DependencyCheck" }

foreach ($Name in @("ffmpeg", "ffprobe", "capcut")) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name was not found on PATH. No tools or packages were installed. Restore the already-installed $Name command, then rerun."
    }
}

$CapCutProcess = Get-Process -Name "CapCut" -ErrorAction SilentlyContinue
if ($CapCutProcess) {
    throw "CapCut is currently open. Save changes and close CapCut completely, then run .\run_nutty_putty.ps1 again. The script will not force-close CapCut."
}

$MotionLabPackage = Join-Path $RepoRoot "motion-lab\node_modules\remotion\package.json"
if (Test-Path -LiteralPath $MotionLabPackage) {
    Write-Host "Remotion dependencies found: the animated two-second title may render."
} else {
    Write-Host "Remotion dependencies are not present; skipping the title render. No npm install will run." -ForegroundColor Yellow
}
$WhisperPackage = & $Python -c "import importlib.util; print('yes' if importlib.util.find_spec('faster_whisper') else 'no')" 2>$null
if ($WhisperPackage -match "yes") {
    Write-Host "faster-whisper package found. The script will use it only if the model is already cached."
} else {
    Write-Host "faster-whisper is absent; timing will be estimated from the supplied script. No pip install/model download." -ForegroundColor Yellow
}

Write-Host ""
if ($BasicOnly) {
    Write-Host "=== Phase 1: basic preparation (original narration + supplied images) ===" -ForegroundColor Cyan
    & $Python (Join-Path $RepoRoot "scripts\prepare_nutty_putty.py") --stage prepare --project $Project --simple
} else {
    Write-Host "=== Phase 1: full-style preparation (local motion, callouts, music, Saoud SFX) ===" -ForegroundColor Cyan
    & $Python (Join-Path $RepoRoot "scripts\prepare_nutty_putty.py") --stage prepare --project $Project
}
if ($LASTEXITCODE -ne 0) { throw "Asset preparation failed. Read the error above; no CapCut draft was built." }

Write-Host ""
Write-Host "=== Phase 2: offline preflight of all generated media ===" -ForegroundColor Cyan
$ConfigPath = Join-Path $RepoRoot "$Project\project.json"
$Config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
$AssetPaths = [System.Collections.Generic.List[string]]::new()
foreach ($Candidate in @($Config.audio, $Config.background_music.path, $Config.settings.flash_overlay_path, $Config.settings.horror_overlay_path)) {
    if ($Candidate -and ([string]$Candidate).Trim()) { $AssetPaths.Add([string]$Candidate) }
}
foreach ($Candidate in @($Config.scene_images)) {
    if ($Candidate -and ([string]$Candidate).Trim()) { $AssetPaths.Add([string]$Candidate) }
}
foreach ($Candidate in @($Config.presenter_images)) {
    if ($Candidate -and ([string]$Candidate).Trim()) { $AssetPaths.Add([string]$Candidate) }
}
foreach ($Item in @($Config.settings.sound_effects)) {
    if ($Item.path) { $AssetPaths.Add([string]$Item.path) }
}
foreach ($Item in @($Config.settings.sfx_pool)) {
    if ($Item.path) { $AssetPaths.Add([string]$Item.path) }
}
foreach ($Item in @($Config.settings.icon_overlays)) {
    if ($Item.path) { $AssetPaths.Add([string]$Item.path) }
}
foreach ($Item in @($Config.settings.callout_overlays)) {
    if ($Item.path) { $AssetPaths.Add([string]$Item.path) }
}
$MissingPaths = @($AssetPaths | Select-Object -Unique | Where-Object { -not (Test-Path -LiteralPath $_ -PathType Leaf) })
if ($MissingPaths.Count -gt 0) {
    $MissingPaths | ForEach-Object { Write-Host "MISSING: $_" -ForegroundColor Red }
    throw "Offline preflight failed because one or more local files are missing."
}
Write-Host ("Preflight passed: " + (@($AssetPaths | Select-Object -Unique).Count) + " local media paths exist.")

Write-Host ""
Write-Host "=== Phase 3: build editable CapCut draft ===" -ForegroundColor Cyan
$BuildDir = Join-Path $RepoRoot "$Project\build"
& $Python (Join-Path $RepoRoot "scripts\build_montage.py") --config $ConfigPath --build-dir $BuildDir
$BuildExitCode = $LASTEXITCODE

Write-Host ""
Write-Host "=== Phase 4: timeline and QA report ===" -ForegroundColor Cyan
& $Python (Join-Path $RepoRoot "scripts\prepare_nutty_putty.py") --stage finalize --project $Project --build-exit-code $BuildExitCode
if ($LASTEXITCODE -ne 0) { throw "Could not write the final QA report." }
if ($BuildExitCode -ne 0) { throw "CapCut draft build failed. Review the build output and QA_REPORT.md before retrying." }

Write-Host ""
Write-Host "BUILD SUCCESSFUL" -ForegroundColor Green
Write-Host "Project data: $BuildDir"
Write-Host "QA report: $(Join-Path $BuildDir 'QA_REPORT.md')"
Write-Host "Asset catalog: $(Join-Path $BuildDir 'ASSET_CATALOG_SUMMARY.md')"
Write-Host "Contact sheet: $(Join-Path $BuildDir 'ASSET_CONTACT_SHEET.jpg')"
Write-Host "Stock B-roll contact sheet: $(Join-Path $BuildDir 'ASSET_STOCK_CONTACT_SHEET.jpg')" 
Write-Host "SFX pack manifest: $(Join-Path $BuildDir 'SFX_PACK_MANIFEST.json')"
Write-Host "CapCut compatibility report: $(Join-Path $BuildDir 'CAPCUT_COMPATIBILITY_REPORT.txt')"
Write-Host ""
Write-Host "Open CapCut Desktop and review the new Nutty Putty Cave draft before exporting."
if ($BasicOnly) {
    Write-Host "Basic-only mode was selected. It does not include title, captions, music, SFX, or callouts."
} else {
    Write-Host "Full style was selected. Optional title/Whisper are skipped when their existing local components are unavailable."
}
