$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot
$Branch = "feat/capcut-montage-pipeline"
$Project = "projects\nutty-putty-cave"
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"

Write-Host ""
Write-Host "=== Nutty Putty Cave: local CapCut build ===" -ForegroundColor Cyan
Write-Host "Updating the shared montage toolchain..."
git switch $Branch
if ($LASTEXITCODE -ne 0) { throw "Could not switch to $Branch." }
git pull origin $Branch
if ($LASTEXITCODE -ne 0) { throw "Git pull failed. Resolve Git status before building." }

if (-not (Test-Path $Python)) {
    Write-Host "Creating the Python environment and installing base requirements..."
    & (Join-Path $RepoRoot "asset_tool.ps1") --help
    if ($LASTEXITCODE -ne 0) { throw "Could not initialize the Python environment." }
}
if (-not (Test-Path $Python)) { throw "Python environment was not created at $Python." }

$CapCutProcess = Get-Process -Name "CapCut" -ErrorAction SilentlyContinue
if ($CapCutProcess) {
    throw "CapCut is currently open. Save any changes, close CapCut completely, then run .\run_nutty_putty.ps1 again. The script will not force-close CapCut."
}

Write-Host ""
Write-Host "=== Phase 1: inventory source assets, align narration, create effects ===" -ForegroundColor Cyan
& $Python (Join-Path $RepoRoot "scripts\prepare_nutty_putty.py") --stage prepare --project $Project
if ($LASTEXITCODE -ne 0) { throw "Asset preparation failed. Read the error above; no draft was built." }

Write-Host ""
Write-Host "=== Phase 2: validate paths and project settings ===" -ForegroundColor Cyan
& (Join-Path $RepoRoot "asset_tool.ps1") preflight --project $Project
if ($LASTEXITCODE -ne 0) { throw ("Preflight failed. Review " + (Join-Path $RepoRoot "$Project\build\preflight_report.json") + ".") }

Write-Host ""
Write-Host "=== Phase 3: build editable CapCut draft ===" -ForegroundColor Cyan
$ConfigPath = Join-Path $RepoRoot "$Project\project.json"
$BuildDir = Join-Path $RepoRoot "$Project\build"
& $Python (Join-Path $RepoRoot "scripts\build_montage.py") --config $ConfigPath --build-dir $BuildDir
$BuildExitCode = $LASTEXITCODE

Write-Host ""
Write-Host "=== Phase 4: update timeline and QA report ===" -ForegroundColor Cyan
& $Python (Join-Path $RepoRoot "scripts\prepare_nutty_putty.py") --stage finalize --project $Project --build-exit-code $BuildExitCode
if ($LASTEXITCODE -ne 0) { throw "Could not write the final QA report." }
if ($BuildExitCode -ne 0) { throw "CapCut draft build failed. Review build output and QA_REPORT.md before retrying." }

Write-Host ""
Write-Host "BUILD SUCCESSFUL" -ForegroundColor Green
Write-Host "Project data: $BuildDir"
Write-Host "QA report: $(Join-Path $BuildDir 'QA_REPORT.md')"
Write-Host "Contact sheet: $(Join-Path $BuildDir 'ASSET_CONTACT_SHEET.jpg')"
Write-Host ""
Write-Host "Open CapCut Desktop and look for the newly registered Nutty Putty Cave draft."
Write-Host "Preview the first 10 seconds, rope-snap / no-pulse moments, sealed-cave ending and final teaser before export."
