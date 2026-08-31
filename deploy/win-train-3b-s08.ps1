# S08: Qwen2.5-3B stream_layers — expanded domain data, max_length 96
$ErrorActionPreference = "Stop"
$LabRoot = "D:\lumen-stream-lab"

. "$LabRoot\deploy\win-env-d.ps1"
$env:CUDA_VISIBLE_DEVICES = "0"
$env:PYTORCH_CUDA_ALLOC_CONF = "expandable_segments:True"

Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep 2

Write-Host "=== Soup 3B S08 train (train-s08.jsonl, max_length 96) ===" -ForegroundColor Cyan
Write-Host "GPU: $(nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader)"
Write-Host "Rows: $((Get-Content "$LabRoot\data\train-s08.jsonl" | Measure-Object -Line).Lines)"

Set-Location $LabRoot
soup train --config soup-3b-stream-s08.yaml --yes
