# scripts/setup_venv.ps1
# Python: >=3.10,<3.14 (öneri: 3.11)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ROOT = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VENV = Join-Path $ROOT ".venv"
$REQ  = Join-Path $ROOT "requirements.txt"
$REQD = Join-Path $ROOT "requirements-dev.txt"

param(
  [string]$Py = "py -3.11",
  [switch]$WithDev
)

Write-Host "ROOT: $ROOT"
Write-Host "VENV: $VENV"

if (-not (Test-Path $REQ)) { throw "requirements.txt bulunamadı: $REQ" }
if ($WithDev -and -not (Test-Path $REQD)) { throw "requirements-dev.txt bulunamadı: $REQD" }

if (-not (Test-Path $VENV)) {
  Write-Host "Creating venv..."
  & $Py -m venv $VENV
} else {
  Write-Host "venv zaten var."
}

$PYEXE = Join-Path $VENV "Scripts\python.exe"
if (-not (Test-Path $PYEXE)) { throw "venv python.exe bulunamadı: $PYEXE" }

Write-Host "Upgrading pip..."
& $PYEXE -m pip install -U pip

Write-Host "Installing runtime requirements..."
& $PYEXE -m pip install -r $REQ

if ($WithDev) {
  Write-Host "Installing dev/test requirements..."
  & $PYEXE -m pip install -r $REQD
}

Write-Host "OK: venv hazır."
& $PYEXE --version


"""
# sadece runtime
.\scripts\setup_venv.ps1

# runtime + pytest vs.
.\scripts\setup_venv.ps1 -WithDev

"""