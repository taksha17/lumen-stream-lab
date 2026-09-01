# S10: export -> deploy -> domain gate -> regression (rollback on gate fail)
$ErrorActionPreference = "Stop"
$LabRoot = "D:\lumen-stream-lab"
$Gguf = "$LabRoot\exports\qwen2.5-3b-lumen-s10.q4_k_m.gguf"
$S07Gguf = "$LabRoot\exports\qwen2.5-3b-lumen-s07.q4_k_m.gguf"
$ModelName = "qwen2.5-3b-lumen"

& "$LabRoot\deploy\win-export-3b-s10.ps1"
if (-not (Test-Path $Gguf)) { throw "Export failed - GGUF missing: $Gguf" }

& "$LabRoot\deploy\win-deploy-ollama-7b.ps1" -Gguf $Gguf -ModelName $ModelName

Write-Host "`n=== S10 domain gate (with system prompt) ===" -ForegroundColor Cyan
& "$LabRoot\deploy\win-domain-smoke-gate.ps1"
$gateOk = ($LASTEXITCODE -eq 0)

if (-not $gateOk) {
    Write-Host "Domain gate FAILED - rolling back to S07 GGUF" -ForegroundColor Red
    if (Test-Path $S07Gguf) {
        & "$LabRoot\deploy\win-deploy-ollama-7b.ps1" -Gguf $S07Gguf -ModelName $ModelName
    }
    exit 1
}

Write-Host "`n=== S10 regression gate ===" -ForegroundColor Cyan
& "$LabRoot\deploy\win-regression.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Regression FAILED - rolling back to S07" -ForegroundColor Red
    & "$LabRoot\deploy\win-deploy-ollama-7b.ps1" -Gguf $S07Gguf -ModelName $ModelName
    exit 1
}

Write-Host "`n=== S10 PROMOTED to production ===" -ForegroundColor Green
