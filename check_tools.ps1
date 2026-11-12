$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

$Checks = [System.Collections.Generic.List[object]]::new()

function Add-Check {
    param(
        [string]$Component,
        [ValidateSet("READY", "OPTIONAL", "MISSING", "WARNING")][string]$Status,
        [string]$Detail
    )
    $Checks.Add([pscustomobject]@{
        Component = $Component
        Status = $Status
        Detail = $Detail
    })
}

function Get-FirstLine {
    param([string]$CommandName, [string[]]$Arguments)
    try {
        $output = & $CommandName @Arguments 2>&1
        return ($output | Select-Object -First 1 | Out-String).Trim()
    } catch {
        return $_.Exception.Message
    }
}

$Py = Get-Command py -ErrorAction SilentlyContinue
$PythonInfo = if ($Py) { Get-FirstLine "py" @("-3.13", "--version") } else { "Python launcher (py) not found" }
if ($PythonInfo -match "^Python 3\.13") {
    Add-Check "Python 3.13" "READY" $PythonInfo
} else {
    Add-Check "Python 3.13" "MISSING" "$PythonInfo - install Python 3.13, then reopen PowerShell."
}

$Node = Get-Command node -ErrorAction SilentlyContinue
if ($Node) {
    $NodeVersion = Get-FirstLine "node" @("--version")
    $NodeMajor = 0
    if ($NodeVersion -match "v?(\d+)\.") { $NodeMajor = [int]$Matches[1] }
    if ($NodeMajor -ge 18) {
        Add-Check "Node.js" "READY" $NodeVersion
    } else {
        Add-Check "Node.js" "MISSING" "$NodeVersion - capcut-cli and Remotion require Node 18 or newer."
    }
} else {
    Add-Check "Node.js" "MISSING" "Not found on PATH."
}

if (Get-Command npm -ErrorAction SilentlyContinue) {
    Add-Check "npm" "READY" (Get-FirstLine "npm" @("--version"))
} else {
    Add-Check "npm" "MISSING" "Not found on PATH; install Node.js with npm."
}

if (Get-Command capcut -ErrorAction SilentlyContinue) {
    $CapcutVersion = Get-FirstLine "capcut" @("--version")
    if (-not $CapcutVersion) { $CapcutVersion = "capcut command is available" }
    Add-Check "capcut-cli" "READY" $CapcutVersion
} else {
    Add-Check "capcut-cli" "MISSING" "Run .\run_montage.ps1 to install it globally through npm."
}

foreach ($Name in @("ffmpeg", "ffprobe")) {
    if (Get-Command $Name -ErrorAction SilentlyContinue) {
        Add-Check $Name "READY" (Get-FirstLine $Name @("-version"))
    } else {
        Add-Check $Name "OPTIONAL" "Not found. Recommended for media inspection, previews, and Whisper."
    }
}

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $DependencyCheck = & $VenvPython -c "import mutagen, PIL; print('mutagen and Pillow import successfully')" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Add-Check "Project Python packages" "READY" (($DependencyCheck | Select-Object -First 1 | Out-String).Trim())
    } else {
        Add-Check "Project Python packages" "WARNING" "Run .\asset_tool.ps1 --help or .\run_montage.ps1 to repair the environment."
    }
} else {
    Add-Check "Project Python packages" "OPTIONAL" "The shared .venv will be created by asset_tool.ps1 or run_montage.ps1."
}

$Whisper = Get-Command whisper -ErrorAction SilentlyContinue
$LocalWhisper = Join-Path $RepoRoot ".venv\Scripts\whisper.exe"
if ($Whisper -or (Test-Path $LocalWhisper)) {
    Add-Check "Whisper" "READY" "Detected; timed captions may be available."
} else {
    Add-Check "Whisper" "OPTIONAL" "Not installed. Automatic transcription is unavailable; scene text callouts can still work."
}

$MotionLabPackage = Join-Path $RepoRoot "motion-lab\node_modules\remotion\package.json"
if (Test-Path $MotionLabPackage) {
    Add-Check "Remotion motion-lab" "READY" "Dependencies found in motion-lab\node_modules."
} else {
    Add-Check "Remotion motion-lab" "OPTIONAL" "Run cd .\motion-lab; npm install before using Remotion renders."
}

$EnvPath = Join-Path $RepoRoot ".env"
if (Test-Path $EnvPath) {
    $EnvText = Get-Content $EnvPath -Raw
    foreach ($Key in @("PIXABAY_API_KEY", "PEXELS_API_KEY", "FREESOUND_API_KEY", "HF_TOKEN")) {
        $Configured = $false
        foreach ($Line in ($EnvText -split "\r?\n")) {
            if ($Line -match ("^\s*" + [regex]::Escape($Key) + "\s*=\s*(.+?)\s*$")) {
                if ($Matches[1].Trim().Trim('"').Trim("'")) { $Configured = $true }
            }
        }
        if ($Configured) {
            Add-Check $Key "READY" "Configured in local .env (value hidden)."
        } else {
            Add-Check $Key "OPTIONAL" "Not configured; related provider will be skipped."
        }
    }
} else {
    Add-Check "Optional API keys" "OPTIONAL" "Run .\asset_tool.ps1 --help once to create .env from .env.example."
}

foreach ($File in @("presets\motion_presets.json", "presets\text_animation_presets.json", "presets\asset_sources.json", "requirements-ai.txt", "scripts\prepare_assets.py", "scripts\build_montage.py")) {
    if (Test-Path (Join-Path $RepoRoot $File)) {
        Add-Check "File: $File" "READY" "Present."
    } else {
        Add-Check "File: $File" "MISSING" "Expected system file is missing."
    }
}

$BuildDir = Join-Path $RepoRoot "build"
New-Item -ItemType Directory -Path $BuildDir -Force | Out-Null
$ReportPath = Join-Path $BuildDir "tool_check_report.json"
$MissingCount = @($Checks | Where-Object { $_.Status -eq "MISSING" }).Count
$Report = @{
    checked_at = (Get-Date).ToString("o")
    repository_root = $RepoRoot
    checks = @($Checks)
    ready = ($MissingCount -eq 0)
}
$Report | ConvertTo-Json -Depth 5 | Set-Content -Path $ReportPath -Encoding utf8

$Checks | Format-Table -AutoSize | Out-Host
Write-Host ""
Write-Host "Report: $ReportPath"
if ($MissingCount -gt 0) {
    Write-Host "One or more core requirements are missing. Fix the MISSING rows before building." -ForegroundColor Yellow
    exit 2
}
Write-Host "Core tools are ready. OPTIONAL rows are enhancements, not blockers." -ForegroundColor Green
exit 0
