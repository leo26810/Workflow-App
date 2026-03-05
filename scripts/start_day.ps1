param(
    [switch]$SkipBuild,
    [switch]$SkipStatus,
    [int]$HealthTimeoutSeconds = 90
)

$ErrorActionPreference = 'Stop'

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Test-DockerAvailable {
    & cmd /c "docker info >nul 2>nul"
    return ($LASTEXITCODE -eq 0)
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
    throw "Python venv nicht gefunden: $venvPython"
}

Write-Step 'Docker Compose starten'
$dockerAvailable = Test-DockerAvailable
if ($dockerAvailable) {
    $composeArgs = @('compose', 'up', '-d')
    if (-not $SkipBuild) {
        $composeArgs += '--build'
    }

    & docker @composeArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Warning 'docker compose up ist fehlgeschlagen.'
        $dockerAvailable = $false
    }
} else {
    Write-Warning 'Docker ist nicht erreichbar (Docker Desktop aus?). Compose-Start wird übersprungen.'
}

Write-Step 'Auf Backend-Health warten'
$backendReady = $false
if ($dockerAvailable) {
    $deadline = (Get-Date).AddSeconds($HealthTimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-RestMethod -Uri 'http://localhost:5000/api/health' -Method Get -TimeoutSec 3
            if ($response.status -eq 'ok') {
                $backendReady = $true
                break
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
}

if ($backendReady) {
    Write-Host 'Backend ist erreichbar.' -ForegroundColor Green
} elseif ($dockerAvailable) {
    Write-Warning "Backend wurde innerhalb von $HealthTimeoutSeconds Sekunden nicht erreichbar."
} else {
    Write-Warning 'Backend-Healthcheck wurde übersprungen, weil Docker nicht verfügbar ist.'
}

if (-not $SkipStatus) {
    Write-Step 'Status-Report ausführen'
    & $venvPython 'scripts/project_status.py'
}

Write-Step 'Compose-Status'
if ($dockerAvailable) {
    & docker compose ps
    if ($LASTEXITCODE -ne 0) {
        Write-Warning 'docker compose ps konnte nicht ausgeführt werden.'
    }
} else {
    Write-Warning 'Compose-Status übersprungen (Docker nicht verfügbar).'
}

Write-Host "`nStartsequenz abgeschlossen." -ForegroundColor Green
