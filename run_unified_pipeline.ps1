param([switch]$SkipMotionLabCheck)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

# This launcher never changes branches, pulls, resets, or cleans the user's working tree.
$Branch = (git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0) { throw "Could not read the current Git branch." }
if ($Branch -ne "feat/universal-montage-engine") {
    throw "Expected feat/universal-montage-engine, currently on '$Branch'. Switch deliberately before running this launcher."
}

$Project = "projects\nutty-putty-cave"
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$ConfigPath = Join-Path $RepoRoot "$Project\project.json"
$BuildDir = Join-Path $RepoRoot "$Project\build"

Write-Host ""
Write-Host "=== Video1 unified documentary production pipeline ===" -ForegroundColor Cyan
Write-Host "Branch: $Branch"
Write-Host "This launcher does not perform Git operations or install packages."

if (-not (Test-Path -LiteralPath $Python)) {
    throw "The existing .venv Python was not found: $Python"
}
$DependencyCheck = & $Python -c "import PIL; print('Pillow ready')" 2>&1
if ($LASTEXITCODE -ne 0) { throw "Pillow is unavailable in the existing .venv: $DependencyCheck" }

foreach ($Name in @("node", "npm", "npx", "ffmpeg", "ffprobe", "capcut")) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name was not found on PATH. Restore the existing tool; no installation was attempted."
    }
}

$CapCutProcess = Get-Process -Name "CapCut" -ErrorAction SilentlyContinue
if ($CapCutProcess) {
    throw "CapCut is open. Save changes and close it completely before building."
}

$RemotionPackage = Join-Path $RepoRoot "motion-lab\node_modules\remotion\package.json"
$GsapPackage = Join-Path $RepoRoot "motion-lab\node_modules\gsap\package.json"
if (-not $SkipMotionLabCheck -and (-not (Test-Path $RemotionPackage) -or -not (Test-Path $GsapPackage))) {
    throw "Remotion/GSAP are not both installed in motion-lab. Review motion-lab\package.json, then run 'npm install' inside motion-lab. This launcher will not install them automatically."
}

$HyperFramesTemplate = Join-Path $RepoRoot "hyperframes-engine\hyperframes.json"
if (-not (Test-Path -LiteralPath $HyperFramesTemplate)) {
    throw "The local HyperFrames template is missing: $HyperFramesTemplate. Keep the existing hyperframes-engine folder; initialize it before building."
}

Write-Host ""
Write-Host "=== Phase 1: prepare source assets, narration timing and visual requirements ===" -ForegroundColor Cyan
& $Python (Join-Path $RepoRoot "scripts\prepare_nutty_putty.py") --stage prepare --project $Project
if ($LASTEXITCODE -ne 0) { throw "Preparation failed; no CapCut draft was built." }

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
foreach ($Item in @($Config.hyperframes.elements)) {
    if ($Item.type -eq "image" -and $Item.path) { $AssetPaths.Add([string]$Item.path) }
}
$MissingPaths = @($AssetPaths | Select-Object -Unique | Where-Object { -not (Test-Path -LiteralPath $_ -PathType Leaf) })
if ($MissingPaths.Count -gt 0) {
    $MissingPaths | ForEach-Object { Write-Host "MISSING: $_" -ForegroundColor Red }
    throw "Media preflight failed; repair the missing local files before building."
}
Write-Host ("Media preflight passed: " + (@($AssetPaths | Select-Object -Unique).Count) + " local files.")

Write-Host ""
Write-Host "=== Phase 2: build CapCut timeline and route specialist graphics ===" -ForegroundColor Cyan
& $Python (Join-Path $RepoRoot "scripts\build_montage.py") --config $ConfigPath --build-dir $BuildDir
$BuildExitCode = $LASTEXITCODE

Write-Host ""
Write-Host "=== Phase 3: write visual QA and production reports ===" -ForegroundColor Cyan
& $Python (Join-Path $RepoRoot "scripts\prepare_nutty_putty.py") --stage finalize --project $Project --build-exit-code $BuildExitCode
if ($LASTEXITCODE -ne 0) { throw "Could not write the final QA report." }
if ($BuildExitCode -ne 0) { throw "The draft build failed. Review the build log and QA_REPORT.md." }

Write-Host ""
Write-Host "BUILD SUCCESSFUL" -ForegroundColor Green
Write-Host "CapCut draft was created; no final MP4 was exported automatically."
Write-Host "Production plan: $(Join-Path $BuildDir 'production_plan.json')"
Write-Host "Toolchain report: $(Join-Path $BuildDir 'TOOLCHAIN_REPORT.md')"
Write-Host "Renderer manifest: $(Join-Path $BuildDir 'RENDERER_MANIFEST.json')"
Write-Host "QA report: $(Join-Path $BuildDir 'QA_REPORT.md')"
Write-Host "Open the newest CapCut draft and review it before exporting."
