# S10: E12 definition micro-curriculum + S07 replay (run after system-prompt gate check)
$ErrorActionPreference = "Stop"
$LabRoot = "D:\lumen-stream-lab"

. "$LabRoot\deploy\win-env-d.ps1"
$env:CUDA_VISIBLE_DEVICES = "0"
$env:PYTORCH_CUDA_ALLOC_CONF = "expandable_segments:True"

Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep 2

$rows = (Get-Content "$LabRoot\data\train-s10-e12.jsonl" | Measure-Object -Line).Lines
Write-Host "=== Soup 3B S10 E12 micro-curriculum (+ 50% S07 replay) ===" -ForegroundColor Cyan
Write-Host "E12 rows: $rows | max_length 64 | lr 5e-5 | max_steps 30"
Write-Host "GPU: $(nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader)"

Set-Location $LabRoot
soup train `
  --config soup-3b-stream-s10.yaml `
  --replay "$LabRoot\data\train-s07.jsonl" `
  --replay-ratio 0.50 `
  --yes
