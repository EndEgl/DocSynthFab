# scripts/smoke.ps1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ROOT  = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PYEXE = Join-Path $ROOT ".venv\Scripts\python.exe"
$CFG   = Join-Path $ROOT "configs\default.yaml"

param(
  [int]$Pages = 20,
  [int]$Workers = 2,
  [int]$Seed = 1337,
  [string]$OutRoot = "D:\ai1_dataset_smoke"
)

if (-not (Test-Path $PYEXE)) { throw ".venv python.exe bulunamadÄ±. Ã–nce scripts\setup_venv.ps1 Ã§alÄ±ÅŸtÄ±r." }
if (-not (Test-Path $CFG))   { throw "Config bulunamadÄ±: $CFG" }

$env:PYTHONUTF8 = "1"

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$out = Join-Path $OutRoot ("run_" + $ts)
New-Item -ItemType Directory -Force -Path $out | Out-Null

Write-Host "Smoke OUT: $out"
& $PYEXE -m docsynthfab.cli --config $CFG --out $out --pages $Pages --workers $Workers --seed $Seed
