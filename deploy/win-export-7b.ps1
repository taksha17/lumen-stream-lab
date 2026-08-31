# Export trained 7B LoRA to GGUF and deploy to Ollama
$ErrorActionPreference = "Stop"
$LabRoot = "D:\lumen-stream-lab"
$Model = "$LabRoot\output-7b-stream"
$DeployName = "qwen2.5-7b-lumen"

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

. "$LabRoot\deploy\win-env-d.ps1"
& "$LabRoot\deploy\win-setup-llama-cpp.ps1"

Write-Host "=== Soup export 7B -> GGUF -> Ollama ===" -ForegroundColor Cyan
Write-Host "Model: $Model"
Write-Host "Ollama models: $env:OLLAMA_MODELS"
Write-Host "C: free $([math]::Round((Get-PSDrive C).Free/1GB,1)) GB | D: free $([math]::Round((Get-PSDrive D).Free/1GB,1)) GB"

$ExportDir = "$LabRoot\exports"
if (-not (Test-Path $ExportDir)) { New-Item -ItemType Directory -Path $ExportDir -Force | Out-Null }

Set-Location $LabRoot
soup export `
  --model $Model `
  --base Qwen/Qwen2.5-7B-Instruct `
  --format gguf `
  --quant q4_k_m `
  --output "$LabRoot\exports\qwen2.5-7b-lumen.q4_k_m.gguf" `
  --deploy ollama `
  --deploy-name $DeployName

Write-Host "`n=== Done. Test with: ollama run $DeployName ===" -ForegroundColor Green
