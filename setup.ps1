$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$backendDir = Join-Path $root 'backend'
$frontendDir = Join-Path $root 'frontend'
$venvPython = Join-Path $backendDir 'venv\Scripts\python.exe'

function Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Fail($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red; exit 1 }

Info "Prüfe Python"
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Fail "Python fehlt. Installiere: https://www.python.org/downloads/"
}

$pyVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$parts = $pyVersion.Trim().Split('.')
if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 11)) {
  Fail "Python $pyVersion gefunden, benötigt: 3.11+"
}
Info "Python $pyVersion gefunden"

Info "Prüfe Node.js"
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  Fail "Node.js fehlt. Installiere: https://nodejs.org/en/download"
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  Fail "npm fehlt. Installiere Node.js inkl. npm: https://nodejs.org/en/download"
}
Info "Node $(node -v) gefunden"

$envFile = Join-Path $backendDir '.env'
$envExample = Join-Path $backendDir '.env.example'
if (-not (Test-Path $envFile)) {
  if (-not (Test-Path $envExample)) {
    Fail "backend/.env.example fehlt"
  }
  Copy-Item $envExample $envFile
  Info "backend/.env aus .env.example erstellt"
} else {
  Info "backend/.env existiert bereits"
}

if (-not (Test-Path $venvPython)) {
  Info "Erstelle venv unter backend/venv"
  python -m venv (Join-Path $backendDir 'venv')
}

Info "Installiere Python-Dependencies"
& $venvPython -m pip install --upgrade pip | Out-Host
& $venvPython -m pip install -r (Join-Path $backendDir 'requirements.txt') | Out-Host

Info "Installiere Frontend-Dependencies"
Push-Location $frontendDir
npm install | Out-Host
Pop-Location

Info "Starte Test-Suite"
& $venvPython (Join-Path $backendDir 'test_all.py')
if ($LASTEXITCODE -ne 0) {
  Fail "Tests fehlgeschlagen. Setup wird abgebrochen."
}

Info "Starte Backend und Frontend"
$backendProc = Start-Process -FilePath $venvPython -ArgumentList (Join-Path $backendDir 'app.py') -WorkingDirectory $backendDir -PassThru
$frontendProc = Start-Process -FilePath 'npm' -ArgumentList 'run dev -- --host 0.0.0.0 --port 5173' -WorkingDirectory $frontendDir -PassThru

Start-Sleep -Seconds 2
Start-Process 'http://localhost:5173' | Out-Null

Write-Host ''
Write-Host '=== Services ===' -ForegroundColor Green
Write-Host "Backend:  läuft (PID $($backendProc.Id)) -> http://localhost:5000"
Write-Host "Frontend: läuft (PID $($frontendProc.Id)) -> http://localhost:5173"
Write-Host ''
Write-Host 'Setup abgeschlossen ✅' -ForegroundColor Green
