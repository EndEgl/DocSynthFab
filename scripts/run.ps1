# scripts/run.ps1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ROOT  = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PYEXE = Join-Path $ROOT ".venv\Scripts\python.exe"
$CFG   = Join-Path $ROOT "configs\default.yaml"

param(
  [string]$Out = "",       # boÅŸ bÄ±rak -> config out_root
  [int]$Pages = 0,         # 0 -> config pages
  [int]$Workers = 0,       # 0 -> config workers
  [int]$Seed = -1          # -1 -> config seed
)

if (-not (Test-Path $PYEXE)) { throw ".venv python.exe bulunamadÄ±. Ã–nce scripts\setup_venv.ps1 Ã§alÄ±ÅŸtÄ±r." }
if (-not (Test-Path $CFG))   { throw "Config bulunamadÄ±: $CFG" }

# stdout bozulmasÄ±n diye mÃ¼mkÃ¼n olduÄŸunca sade ortam:
$env:PYTHONUTF8 = "1"

$cmd = @("-m","docsynthfab.cli","--config",$CFG)
if ($Out -ne "")     { $cmd += @("--out",$Out) }
if ($Pages -gt 0)    { $cmd += @("--pages",$Pages) }
if ($Workers -gt 0)  { $cmd += @("--workers",$Workers) }
if ($Seed -ge 0)     { $cmd += @("--seed",$Seed) }

Write-Host "Running:"
Write-Host "$PYEXE $($cmd -join ' ')"
& $PYEXE @cmd



"""
# config default (D:\ai1_dataset_v1)
.\scripts\run.ps1

# override
.\scripts\run.ps1 -Pages 3000 -Workers 6 -Seed 1337 -Out "D:\ai1_dataset_v1"
"""
