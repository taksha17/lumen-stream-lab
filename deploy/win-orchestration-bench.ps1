# Orchestration throughput gate — hybrid auto-route vs always-3B baseline (+40% target)
param(
    [string]$LabRoot = "D:\lumen-stream-lab",
    [string]$PromptsFile = "D:\lumen-stream-lab\data\router-eval-prompts.json",
    [double]$Baseline3B = 48.38,
    [double]$MinGain = 0.40,
    [int]$NumPredict = 128,
    [int]$Runs = 1
)

$ErrorActionPreference = "Stop"
$env:OLLAMA_MODELS = "D:\ollama\models"
$ollamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
$resultsDir = Join-Path $LabRoot "results"
New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null

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

function Invoke-AutoRoute([string]$model, [string]$prompt, [int]$numPredict) {
    $payload = New-OllamaGeneratePayload $model $prompt @{
        num_predict = $numPredict
        temperature = 0.3
    }
    $body = $payload | ConvertTo-Json -Depth 5 -Compress
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/generate" -Method Post `
        -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
        -ContentType "application/json; charset=utf-8" -TimeoutSec 300
    $sw.Stop()
    $decode = if ($resp.eval_duration -gt 0) {
        [math]::Round($resp.eval_count / ($resp.eval_duration / 1e9), 2)
    } else { 0 }
    return @{
        model = $model
        decode_tok_s = $decode
        eval_count = $resp.eval_count
        wall_s = [math]::Round($sw.Elapsed.TotalSeconds, 2)
    }
}

Ensure-Ollama
$prompts = Get-Content $PromptsFile -Raw | ConvertFrom-Json
$targetTokS = [math]::Round($Baseline3B * (1 + $MinGain), 2)

Write-Host "=== Lumen Orchestration Bench (hybrid) ===" -ForegroundColor Cyan
Write-Host "Baseline: llama3.2:3b @ $Baseline3B tok/s | Target: >= $targetTokS tok/s (+$($MinGain*100)%)" -ForegroundColor Cyan
Write-Host "Prompts: $($prompts.Count) | num_predict=$NumPredict" -ForegroundColor Cyan

$rows = @()
$speeds = @()

foreach ($p in $prompts) {
    $route = Get-RouteDecision $p.prompt "auto"
    Write-Host "`n$($p.id): tier=$($route.tier) model=$($route.model)" -ForegroundColor Yellow
    Write-Host "  $($route.reason)" -ForegroundColor DarkGray

    $runSpeeds = @()
    for ($r = 1; $r -le $Runs; $r++) {
        $gen = Invoke-AutoRoute $route.model $p.prompt $NumPredict
        $runSpeeds += $gen.decode_tok_s
        Write-Host "  run-$r`: $($gen.decode_tok_s) tok/s ($($gen.eval_count) tokens)"
    }
    $med = ($runSpeeds | Sort-Object)[[math]::Floor(($runSpeeds.Count - 1) / 2)]
    if ($runSpeeds.Count -eq 1) { $med = $runSpeeds[0] }
    $speeds += [double]$med

    $rows += @{
        id = $p.id
        category = $p.category
        tier = $route.tier
        model = $route.model
        reason = $route.reason
        median_decode_tok_s = $med
    }
}

$mean = [math]::Round(($speeds | Measure-Object -Average).Average, 2)
$median = ($speeds | Sort-Object)[[math]::Floor($speeds.Count / 2)]
$gain = [math]::Round((($mean - $Baseline3B) / $Baseline3B) * 100, 1)
$passed = ($mean -ge $targetTokS)

Write-Host "`n=== RESULT ===" -ForegroundColor $(if ($passed) { "Green" } else { "Red" })
Write-Host "Mean auto-route:   $mean tok/s"
Write-Host "Median auto-route: $median tok/s"
Write-Host "vs always-3B:      +$gain% (need +$($MinGain*100)%)"
Write-Host "Target:            $(if ($passed) { 'PASS' } else { 'FAIL' }) (>= $targetTokS tok/s)"

$report = @{
    bench_at = (Get-Date).ToString("o")
    router_mode = "hybrid_speed_first"
    baseline_3b_tok_s = $Baseline3B
    target_tok_s = $targetTokS
    min_gain = $MinGain
    mean_decode_tok_s = $mean
    median_decode_tok_s = $median
    gain_pct = $gain
    pass = $passed
    prompts = $rows
}
$outFile = Join-Path $resultsDir "orchestration-bench-$(Get-Date -Format 'yyyyMMdd-HHmmss').json"
$report | ConvertTo-Json -Depth 6 | Set-Content $outFile -Encoding UTF8
Write-Host "Report: $outFile"

if (-not $passed) { exit 1 }
exit 0
