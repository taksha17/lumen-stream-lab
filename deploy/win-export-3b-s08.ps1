$ErrorActionPreference = "Stop"
$LabRoot = "D:\lumen-stream-lab"
$Model = "$LabRoot\output-3b-stream-s08"

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

. "$LabRoot\deploy\win-env-d.ps1"
& "$LabRoot\deploy\win-setup-llama-cpp.ps1"

$ExportDir = "$LabRoot\exports"
if (-not (Test-Path $ExportDir)) { New-Item -ItemType Directory -Path $ExportDir -Force | Out-Null }

Write-Host "=== S08 export 3B -> GGUF ===" -ForegroundColor Cyan
Set-Location $LabRoot
soup export `
  --model $Model `
  --base Qwen/Qwen2.5-3B-Instruct `
  --format gguf `
  --quant q4_k_m `
  --output "$ExportDir\qwen2.5-3b-lumen-s08.q4_k_m.gguf"

Write-Host "Export done: $ExportDir\qwen2.5-3b-lumen-s08.q4_k_m.gguf" -ForegroundColor Green
