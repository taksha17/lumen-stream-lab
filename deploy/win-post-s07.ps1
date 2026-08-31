# After S07 training: export -> Ollama deploy -> update note -> router eval
$ErrorActionPreference = "Stop"
$LabRoot = "D:\lumen-stream-lab"
$Gguf = "$LabRoot\exports\qwen2.5-3b-lumen-s07.q4_k_m.gguf"
$ModelName = "qwen2.5-3b-lumen"

& "$LabRoot\deploy\win-export-3b-s07.ps1"

if (-not (Test-Path $Gguf)) { throw "Export failed - GGUF missing: $Gguf" }

& "$LabRoot\deploy\win-deploy-ollama-7b.ps1" -Gguf $Gguf -ModelName $ModelName

Write-Host "`n=== Post-S07 router eval ===" -ForegroundColor Cyan
& "$LabRoot\deploy\win-router-eval.ps1"

Write-Host "`n=== S07 pipeline complete ===" -ForegroundColor Green
Write-Host "Router balanced tier should use: $ModelName"
