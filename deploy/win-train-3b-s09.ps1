# S09: domain curriculum + S07 replay (no --resume; checkpoint torch.load blocked)
$ErrorActionPreference = "Stop"
$LabRoot = "D:\lumen-stream-lab"

. "$LabRoot\deploy\win-env-d.ps1"
$env:CUDA_VISIBLE_DEVICES = "0"
$env:PYTORCH_CUDA_ALLOC_CONF = "expandable_segments:True"

Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep 2

$rows = (Get-Content "$LabRoot\data\train-s09-domain.jsonl" | Measure-Object -Line).Lines
Write-Host "=== Soup 3B S09 curriculum (domain + 35% S07 replay) ===" -ForegroundColor Cyan
Write-Host "Domain rows: $rows | max_length 64 | lr 8e-5 | max_steps 40"
Write-Host "GPU: $(nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader)"

Set-Location $LabRoot
soup train `
  --config soup-3b-stream-s09.yaml `
  --replay "$LabRoot\data\train-s07.jsonl" `
  --replay-ratio 0.35 `
  --yes
