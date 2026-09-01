# Pull latest main and run full validation suite on reference lab
# Usage: powershell -File deploy\win-sync-and-validate.ps1
param(
    [string]$LabRoot = "D:\lumen-stream-lab",
    [switch]$SkipPull,
    [switch]$Full
)

$ErrorActionPreference = "Stop"
Set-Location $LabRoot

Write-Host "=== Lumen sync + validate ===" -ForegroundColor Cyan

if (-not $SkipPull) {
    Write-Host "git pull origin main ..." -ForegroundColor DarkGray
    git pull origin main
    if ($LASTEXITCODE -ne 0) { throw "git pull failed" }
}

Write-Host "`n--- Regression gate ---" -ForegroundColor Cyan
if ($Full) {
    powershell -ExecutionPolicy Bypass -File "$LabRoot\deploy\win-regression.ps1" -Full
} else {
    powershell -ExecutionPolicy Bypass -File "$LabRoot\deploy\win-regression.ps1"
}
if ($LASTEXITCODE -ne 0) { throw "regression FAILED" }

Write-Host "`n--- Fast-tier candidate domain smoke ---" -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File "$LabRoot\deploy\win-fast-tier-domain-smoke.ps1"
# non-fatal — informational for promotion decision

Write-Host "`n--- Hermes setup check ---" -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File "$LabRoot\deploy\win-setup-hermes.ps1"

Write-Host "`n--- Git link (first-time server setup) ---" -ForegroundColor Cyan
Write-Host "Run once: powershell -File $LabRoot\deploy\win-git-link.ps1" -ForegroundColor DarkGray

Write-Host "`n=== ALL REQUIRED GATES PASS ===" -ForegroundColor Green
Write-Host "Optional: start gateway with: python scripts\lumen_gateway.py --port 8080"
