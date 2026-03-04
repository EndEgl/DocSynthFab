# scripts/check_deps.ps1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

param(
  [switch]$SkipLatex
)

function Test-Cmd([string]$cmd) {
  $null = Get-Command $cmd -ErrorAction Stop
}

Write-Host "Checking telemetry dependencies..."

# --- GPU temp: nvidia-smi ---
try {
  Test-Cmd "nvidia-smi"
  $temp = & nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>$null | Select-Object -First 1
  if (-not $temp) { throw "nvidia-smi çıktı boş geldi." }
  [int]$t = $temp
  Write-Host ("OK: GPU temp readable -> {0}C" -f $t)
} catch {
  throw "telemetry/no-temp-sensor: GPU sıcaklığı okunamadı (nvidia-smi). Hata: $($_.Exception.Message)"
}

# --- LaTeX: pdflatex ---
if (-not $SkipLatex) {
  try {
    Test-Cmd "pdflatex"
    $v = & pdflatex --version 2>$null | Select-Object -First 1
    Write-Host "OK: pdflatex bulundu."
    if ($v) { Write-Host $v }
  } catch {
    throw "render/latex-missing: pdflatex bulunamadı. MiKTeX kurulumu / PATH kontrol et."
  }
} else {
  Write-Host "SkipLatex aktif: pdflatex kontrolü atlandı."
}

Write-Host "OK: bağımlılık kontrolleri geçti."



"""
.\scripts\check_deps.ps1
# veya latex kontrolünü atla
.\scripts\check_deps.ps1 -SkipLatex
"""