# Run Soup 7B stream_layers training with D: caches and env loaded
$ErrorActionPreference = "Stop"
$LabRoot = "D:\lumen-stream-lab"

. "$LabRoot\deploy\win-env-d.ps1"

Write-Host "=== Soup 7B stream_layers train ===" -ForegroundColor Cyan
Write-Host "HF_HOME: $env:HF_HOME"
Write-Host "SOUP_LAYER_STREAM_CACHE_DIR: $env:SOUP_LAYER_STREAM_CACHE_DIR"
Write-Host "C: free $([math]::Round((Get-PSDrive C).Free/1GB,1)) GB | D: free $([math]::Round((Get-PSDrive D).Free/1GB,1)) GB"

Set-Location $LabRoot
soup train --config soup-7b-stream.yaml --yes
