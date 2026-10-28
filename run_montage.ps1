$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw "Node.js was not found. Install Node.js 18 or newer, then reopen VS Code."
}
$NodeMajor = [int](node -p "Number(process.versions.node.split('.')[0])")
if ($NodeMajor -lt 18) {
    throw "capcut-cli requires Node.js 18 or newer. Current major version: $NodeMajor"
}

if (-not (Get-Command capcut -ErrorAction SilentlyContinue)) {
    Write-Host "Installing capcut-cli globally through npm..."
    npm install -g capcut-cli
    if ($LASTEXITCODE -ne 0) {
        throw "npm could not install capcut-cli."
    }
    $NpmGlobal = Join-Path $env:APPDATA "npm"
    if (Test-Path $NpmGlobal) {
        $env:Path = $env:Path + ";" + $NpmGlobal
    }
    if (-not (Get-Command capcut -ErrorAction SilentlyContinue)) {
        throw "capcut is still not on PATH. Close and reopen VS Code, then run this script again."
    }
}

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Host "Creating a local Python environment..."
    py -3.13 -m venv (Join-Path $RepoRoot ".venv")
    if ($LASTEXITCODE -ne 0) {
        throw "Python 3 could not create the virtual environment."
    }
}
Write-Host "Installing/checking the small Python dependencies..."
& $Python -m pip install -r (Join-Path $RepoRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    throw "Could not install requirements.txt."
}

Write-Host "Building the editable Whiteboard PRO CapCut draft. Close CapCut before continuing."
& $Python (Join-Path $RepoRoot "scripts\build_montage.py")
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
