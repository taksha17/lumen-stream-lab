# Export S06 adapter to GGUF and redeploy Ollama model
$ErrorActionPreference = "Stop"
$LabRoot = "D:\lumen-stream-lab"
$Model = "$LabRoot\output-7b-stream-s06"
$DeployName = "qwen2.5-7b-lumen"

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

. "$LabRoot\deploy\win-env-d.ps1"
& "$LabRoot\deploy\win-setup-llama-cpp.ps1"

$ExportDir = "$LabRoot\exports"
if (-not (Test-Path $ExportDir)) { New-Item -ItemType Directory -Path $ExportDir -Force | Out-Null }

Write-Host "=== S06 export -> GGUF -> Ollama ===" -ForegroundColor Cyan
Set-Location $LabRoot
soup export `
  --model $Model `
  --base Qwen/Qwen2.5-7B-Instruct `
  --format gguf `
  --quant q4_k_m `
  --output "$ExportDir\qwen2.5-7b-lumen-s06.q4_k_m.gguf"

Write-Host "Export done. Run win-deploy-ollama-7b.ps1 or win-post-s06.ps1 to deploy." -ForegroundColor Green
