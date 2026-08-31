# After S06 training: export -> Ollama deploy -> router eval
$ErrorActionPreference = "Stop"
$LabRoot = "D:\lumen-stream-lab"
$Gguf = "$LabRoot\exports\qwen2.5-7b-lumen-s06.q4_k_m.gguf"

& "$LabRoot\deploy\win-export-7b-s06.ps1"

if (-not (Test-Path $Gguf)) { throw "Export failed - GGUF missing: $Gguf" }

& "$LabRoot\deploy\win-deploy-ollama-7b.ps1" -Gguf $Gguf -ModelName "qwen2.5-7b-lumen"

Write-Host "`n=== Post-S06 router eval ===" -ForegroundColor Cyan
& "$LabRoot\deploy\win-router-eval.ps1"

Write-Host "`n=== S06 pipeline complete ===" -ForegroundColor Green
