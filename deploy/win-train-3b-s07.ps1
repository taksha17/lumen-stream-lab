# S07: Qwen2.5-3B stream_layers on expanded Lumen dataset
$ErrorActionPreference = "Stop"
$LabRoot = "D:\lumen-stream-lab"

. "$LabRoot\deploy\win-env-d.ps1"
$env:CUDA_VISIBLE_DEVICES = "0"
$env:PYTORCH_CUDA_ALLOC_CONF = "expandable_segments:True"

# Ensure nothing else holds VRAM
Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep 2

Write-Host "=== Soup 3B S07 train (train-s07.jsonl) ===" -ForegroundColor Cyan
Write-Host "GPU: $(nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader)"
Write-Host "Rows: $((Get-Content "$LabRoot\data\train-s07.jsonl" | Measure-Object -Line).Lines)"

Set-Location $LabRoot
soup train --config config/soup/soup-3b-stream-s07.yaml --yes
