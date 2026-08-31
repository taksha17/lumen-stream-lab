# Regression gate: speed (+40%) + domain smoke; optional full router eval
param(
    [string]$LabRoot = "D:\lumen-stream-lab",
    [switch]$Full
)

$ErrorActionPreference = "Stop"
$deploy = Join-Path $LabRoot "deploy"
$failures = @()

Write-Host "=== Lumen Regression Gate ===" -ForegroundColor Cyan

Write-Host "`n[1/3] LFM alias" -ForegroundColor Yellow
& "$deploy\win-create-lfm-alias.ps1" -LabRoot $LabRoot
if ($LASTEXITCODE -ne 0) { $failures += "lfm-alias" }

Write-Host "`n[2/3] Orchestration bench (+40%)" -ForegroundColor Yellow
& "$deploy\win-orchestration-bench.ps1" -LabRoot $LabRoot
if ($LASTEXITCODE -ne 0) { $failures += "orchestration-bench" }

Write-Host "`n[3/3] Domain smoke (qwen2.5-3b-lumen)" -ForegroundColor Yellow
& "$deploy\win-s07-domain-smoke.ps1"

if ($Full) {
    Write-Host "`n[optional] Router eval (hybrid, ~30 min)" -ForegroundColor Yellow
    & "$deploy\win-router-eval.ps1" -LabRoot $LabRoot
}

Write-Host "`n=== Regression Summary ===" -ForegroundColor $(if ($failures.Count -eq 0) { "Green" } else { "Red" })
if ($failures.Count -eq 0) {
    Write-Host "ALL PASS"
    exit 0
}
Write-Host "FAILED: $($failures -join ', ')"
exit 1
