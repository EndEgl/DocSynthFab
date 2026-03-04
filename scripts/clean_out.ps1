# scripts/clean_out.ps1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

param(
  [string]$Out = "D:\ai1_dataset_v1",
  [switch]$All
)

$tmp = Join-Path $Out "_tmp"

if (-not (Test-Path $Out)) { throw "Out root yok: $Out" }

if ($All) {
  Write-Host "WARNING: Tüm çıktıyı siliyor -> $Out"
  Remove-Item -Recurse -Force -Path $Out
  Write-Host "OK: silindi."
  exit 0
}

if (Test-Path $tmp) {
  Remove-Item -Recurse -Force -Path $tmp
  Write-Host "OK: _tmp temizlendi -> $tmp"
} else {
  Write-Host "Tmp yok -> $tmp"
}