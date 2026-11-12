$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Host "Creating the shared Python environment..."
    py -3.13 -m venv (Join-Path $RepoRoot ".venv")
    if ($LASTEXITCODE -ne 0) { throw "Python 3.13 is required. Install Python 3.13 and retry." }
}
$RequirementsFile = Join-Path $RepoRoot "requirements.txt"
$RequirementsMarker = Join-Path $RepoRoot ".venv\.requirements.sha256"
$RequirementsHash = (Get-FileHash -Path $RequirementsFile -Algorithm SHA256).Hash
$InstalledHash = if (Test-Path $RequirementsMarker) { (Get-Content $RequirementsMarker -Raw).Trim() } else { "" }
if ($RequirementsHash -ne $InstalledHash) {
    Write-Host "Installing/updating shared Python requirements..."
    & $Python -m pip install -r $RequirementsFile
    if ($LASTEXITCODE -ne 0) { throw "Could not install the base Python requirements." }
    Set-Content -Path $RequirementsMarker -Value $RequirementsHash -NoNewline
} else {
    Write-Host "Shared Python requirements are already current."
}

if (-not (Test-Path (Join-Path $RepoRoot ".env")) -and (Test-Path (Join-Path $RepoRoot ".env.example"))) {
    Copy-Item (Join-Path $RepoRoot ".env.example") (Join-Path $RepoRoot ".env")
    Write-Host "Created .env from .env.example. Add your optional API keys to .env; never commit that file."
}

$AssetScript = Join-Path $RepoRoot "scripts\prepare_assets.py"
& $Python $AssetScript @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
