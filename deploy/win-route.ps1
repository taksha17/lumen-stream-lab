# Lumen prompt router — hybrid balanced: LFM (speed) / qwen3b-lumen (domain)
param(
    [Parameter(Mandatory=$true)][string]$Prompt,
    [string]$LabRoot = "D:\lumen-stream-lab",
    [int]$NumPredict = 128,
    [ValidateSet("auto", "fast", "balanced", "quality")]
    [string]$Tier = "auto"
)

$ErrorActionPreference = "Stop"
$env:OLLAMA_MODELS = "D:\ollama\models"
$ollamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"

. (Join-Path $PSScriptRoot "win-router-lib.ps1")

function Ensure-Ollama {
    try { $null = Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 3; return } catch {}
    Get-Process ollama -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue
    Start-Sleep 2
    Start-Process $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep 2
        try { $null = Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 3; return } catch {}
    }
    throw "Ollama not running"
}

if (-not $Prompt) {
    Write-Host "Usage: win-route.ps1 -Prompt 'your question'"
    exit 1
}

Ensure-Ollama
$route = Get-RouteDecision $Prompt $Tier
$model = $route.model
$tier = $route.tier

Write-Host "=== Lumen Router ===" -ForegroundColor Cyan
Write-Host "Tier:  $tier"
Write-Host "Route: $model ($($route.reason))"

$body = (New-OllamaGeneratePayload $model $Prompt @{ num_predict = $NumPredict; temperature = 0.7 }) | ConvertTo-Json -Depth 5 -Compress

$sw = [System.Diagnostics.Stopwatch]::StartNew()
$resp = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/generate" -Method Post -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -ContentType "application/json; charset=utf-8" -TimeoutSec 300
$sw.Stop()

$decode = [math]::Round($resp.eval_count / ($resp.eval_duration / 1e9), 2)
Write-Host "Speed: ${decode} tok/s | wall: $([math]::Round($sw.Elapsed.TotalSeconds,2))s" -ForegroundColor Green
Write-Host ""
Write-Host $resp.response

@{
    prompt = $Prompt
    tier = $tier
    routed_model = $model
    reason = $route.reason
    decode_tok_s = $decode
    response_preview = $resp.response.Substring(0, [math]::Min(200, $resp.response.Length))
} | ConvertTo-Json | Set-Content (Join-Path $LabRoot "results\last-route.json") -Encoding UTF8
