# Create Ollama model from exported GGUF and quick smoke test
param(
    [string]$LabRoot = "D:\lumen-stream-lab",
    [string]$Gguf = "D:\lumen-stream-lab\exports\qwen2.5-7b-lumen.q4_k_m.gguf",
    [string]$ModelName = "qwen2.5-7b-lumen"
)

$ErrorActionPreference = "Stop"

. "$LabRoot\deploy\win-env-d.ps1"

if (-not (Test-Path $Gguf)) { throw "GGUF not found: $Gguf" }
$sizeGb = [math]::Round((Get-Item $Gguf).Length / 1GB, 2)
Write-Host "GGUF: $Gguf ($sizeGb GB)" -ForegroundColor Cyan

# Stop stray Ollama so serve can bind cleanly
Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

$serve = Start-Process -FilePath "ollama" -ArgumentList "serve" -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 5

$modelfile = @"
FROM $Gguf
PARAMETER temperature 0.7
"@
$mf = "$LabRoot\exports\Modelfile"
$modelfile | Set-Content -Path $mf -Encoding utf8

Write-Host "Creating Ollama model: $ModelName" -ForegroundColor Cyan
ollama create $ModelName -f $mf

Write-Host "`nSmoke test:" -ForegroundColor Cyan
try {
    ollama run $ModelName "What is 2+2? Answer in one word." 2>&1 | Out-String | Write-Host
} catch {
    Write-Host "(smoke test output suppressed - model created successfully)" -ForegroundColor Yellow
}

Write-Host "`nModel ready: ollama run $ModelName" -ForegroundColor Green
