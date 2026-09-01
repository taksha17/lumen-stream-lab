# S06: real fine-tune on expanded dataset (107 rows, 75 steps)
$ErrorActionPreference = "Stop"
$LabRoot = "D:\lumen-stream-lab"

. "$LabRoot\deploy\win-env-d.ps1"

Write-Host "=== Soup 7B S06 train (107 samples, 75 steps) ===" -ForegroundColor Cyan
Write-Host "C: free $([math]::Round((Get-PSDrive C).Free/1GB,1)) GB | D: free $([math]::Round((Get-PSDrive D).Free/1GB,1)) GB"

Set-Location $LabRoot
soup train --config config/soup/soup-7b-stream-s06.yaml --yes
