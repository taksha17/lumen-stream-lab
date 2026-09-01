# S08 VRAM smoke: max_length 96, 3 steps
$ErrorActionPreference = "Stop"
$LabRoot = "D:\lumen-stream-lab"

. "$LabRoot\deploy\win-env-d.ps1"
$env:CUDA_VISIBLE_DEVICES = "0"
$env:PYTORCH_CUDA_ALLOC_CONF = "expandable_segments:True"

Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep 2

Write-Host "=== Soup 3B S08 SMOKE (max_length 96, 3 steps) ===" -ForegroundColor Cyan
Write-Host "GPU: $(nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader)"

Set-Location $LabRoot
soup train --config soup-3b-stream-s08-smoke.yaml --yes
