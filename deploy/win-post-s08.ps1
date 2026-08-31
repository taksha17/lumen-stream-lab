# S08: export -> Ollama deploy -> domain smoke -> regression gate
$ErrorActionPreference = "Stop"
$LabRoot = "D:\lumen-stream-lab"
$Gguf = "$LabRoot\exports\qwen2.5-3b-lumen-s08.q4_k_m.gguf"
$ModelName = "qwen2.5-3b-lumen"

& "$LabRoot\deploy\win-export-3b-s08.ps1"
if (-not (Test-Path $Gguf)) { throw "Export failed - GGUF missing: $Gguf" }

& "$LabRoot\deploy\win-deploy-ollama-7b.ps1" -Gguf $Gguf -ModelName $ModelName

Write-Host "`n=== Post-S08 domain smoke ===" -ForegroundColor Cyan
& "$LabRoot\deploy\win-s07-domain-smoke.ps1"

Write-Host "`n=== Post-S08 regression gate ===" -ForegroundColor Cyan
& "$LabRoot\deploy\win-regression.ps1"

Write-Host "`n=== S08 pipeline complete ===" -ForegroundColor Green
Write-Host "Domain model updated: $ModelName (hybrid balanced domain tier)"
