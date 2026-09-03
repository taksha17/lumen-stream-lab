# Sync, pull experimental coder, GPU sample + code-tier smoke.
# Usage (from repo): powershell -File deploy\win-upgrade-smoke.ps1
# Does not enable LUMEN_CODE_TIER in production — only tests the flag.
param(
    [string]$LabRoot = "",
    [string]$CoderModel = "qwen2.5-coder:3b",
    [string]$GpuModel = "llama3.2:3b",
    [switch]$SkipPull,
    [switch]$SkipGit
)

$ErrorActionPreference = "Stop"
if (-not $LabRoot) { $LabRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path }
Set-Location $LabRoot

Write-Host "=== Lumen upgrade smoke ===" -ForegroundColor Cyan
Write-Host "Root: $LabRoot"

if (-not $SkipGit) {
    git pull origin main
    if ($LASTEXITCODE -ne 0) { throw "git pull failed" }
}

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $py) { throw "python not in PATH" }
$python = $py.Source

Write-Host "`n--- unittest (parity + code tier) ---" -ForegroundColor Cyan
& $python -m unittest tests.test_router_parity tests.test_code_tier tests.test_gpu_metrics -q
if ($LASTEXITCODE -ne 0) { throw "unit tests failed" }

Write-Host "`n--- route default vs --tier code ---" -ForegroundColor Cyan
$e07 = "Write a Python function to compute median decode tok/s from a list of benchmark runs."
& $python lumen.py route --prompt $e07
Write-Host "--- forced code ---"
& $python lumen.py route --tier code --prompt $e07

if (-not $SkipPull) {
    Write-Host "`n--- ollama pull $CoderModel ---" -ForegroundColor Cyan
    ollama pull $CoderModel
}

Write-Host "`n--- GPU sample during generate ($GpuModel) ---" -ForegroundColor Cyan
& $python lumen.py gpu --model $GpuModel --num-predict 64

Write-Host "`n--- probe upgrade candidates ---" -ForegroundColor Cyan
& $python scripts\probe_upgrade_models.py

Write-Host "`n=== upgrade smoke done ===" -ForegroundColor Green
Write-Host "Auto code-route still OFF. Enable only after tok/s bench: `$env:LUMEN_CODE_TIER=1"
