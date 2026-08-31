# Router quality eval — hybrid balanced + auto-route throughput check
param(
    [string]$LabRoot = "D:\lumen-stream-lab",
    [string]$PromptsFile = "D:\lumen-stream-lab\data\router-eval-prompts.json",
    [int]$NumPredict = 128,
    [switch]$TiersOnly
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

function Invoke-TierGenerate([string]$model, [string]$prompt, [int]$numPredict) {
    $payload = New-OllamaGeneratePayload $model $prompt @{
        num_predict = $numPredict
        temperature = 0.3
    }
    $body = $payload | ConvertTo-Json -Depth 5 -Compress
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/generate" -Method Post -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -ContentType "application/json; charset=utf-8" -TimeoutSec 300
    } catch {
        return @{
            model = $model
            response = "ERROR: $_"
            eval_count = 0
            decode_tok_s = 0
            wall_s = 0
            error = $_.Exception.Message
        }
    }
    $sw.Stop()
    $decode = if ($resp.eval_duration -gt 0) { [math]::Round($resp.eval_count / ($resp.eval_duration / 1e9), 2) } else { 0 }
    return @{
        model = $model
        response = $resp.response
        eval_count = $resp.eval_count
        decode_tok_s = $decode
        wall_s = [math]::Round($sw.Elapsed.TotalSeconds, 2)
    }
}

Ensure-Ollama
$prompts = Get-Content $PromptsFile -Raw | ConvertFrom-Json
$report = @{
    evaluated_at = (Get-Date).ToString("o")
    num_predict = $NumPredict
    router_mode = "hybrid_balanced"
    prompts = @()
}

Write-Host "=== Lumen Router Quality Eval (hybrid) ===" -ForegroundColor Cyan
Write-Host "Prompts: $($prompts.Count) | fast / balanced(LFM|qwen) / quality" -ForegroundColor Cyan

foreach ($p in $prompts) {
    Write-Host "`n--- $($p.id): $($p.category) ---" -ForegroundColor Yellow
    $route = Get-RouteDecision $p.prompt "auto"
    $autoTier = $route.tier
    $tierMatch = ($autoTier -eq $p.expected_auto_tier)
    Write-Host "Auto tier: $autoTier -> $($route.model) ($($route.reason))"
    Write-Host "Expected: $($p.expected_auto_tier) $(if($tierMatch){'OK'}else{'MISMATCH'})"

    $balancedPick = Get-BalancedModel $p.prompt
    $entry = @{
        id = $p.id
        category = $p.category
        prompt = $p.prompt
        expected_auto_tier = $p.expected_auto_tier
        actual_auto_tier = $autoTier
        auto_tier_match = $tierMatch
        balanced_model = $balancedPick.model
        balanced_reason = $balancedPick.reason
        tiers = @{}
    }

    Write-Host "  fast ($($script:RouterModels.fast))..." -NoNewline
    $entry.tiers["fast"] = Invoke-TierGenerate $script:RouterModels.fast $p.prompt $NumPredict
    Write-Host " $($entry.tiers.fast.decode_tok_s) tok/s"

    Write-Host "  balanced_lfm ($($script:RouterModels.balanced))..." -NoNewline
    $entry.tiers["balanced_lfm"] = Invoke-TierGenerate $script:RouterModels.balanced $p.prompt $NumPredict
    Write-Host " $($entry.tiers.balanced_lfm.decode_tok_s) tok/s"

    Write-Host "  balanced_domain ($($script:RouterModels.balanced_domain))..." -NoNewline
    $entry.tiers["balanced_domain"] = Invoke-TierGenerate $script:RouterModels.balanced_domain $p.prompt $NumPredict
    Write-Host " $($entry.tiers.balanced_domain.decode_tok_s) tok/s"

    Write-Host "  quality ($($script:RouterModels.quality))..." -NoNewline
    $entry.tiers["quality"] = Invoke-TierGenerate $script:RouterModels.quality $p.prompt $NumPredict
    Write-Host " $($entry.tiers.quality.decode_tok_s) tok/s"

    if (-not $TiersOnly) {
        Write-Host "  auto-route ($($route.model))..." -NoNewline
        $entry.auto_route = Invoke-TierGenerate $route.model $p.prompt $NumPredict
        Write-Host " $($entry.auto_route.decode_tok_s) tok/s"
    }

    $report.prompts += $entry
}

$tierSpeeds = @{ fast = @(); balanced_lfm = @(); balanced_domain = @(); quality = @(); auto_route = @() }
$tierMatches = 0
foreach ($e in $report.prompts) {
    if ($e.auto_tier_match) { $tierMatches++ }
    $tierSpeeds.fast += $e.tiers.fast.decode_tok_s
    $tierSpeeds.balanced_lfm += $e.tiers.balanced_lfm.decode_tok_s
    $tierSpeeds.balanced_domain += $e.tiers.balanced_domain.decode_tok_s
    $tierSpeeds.quality += $e.tiers.quality.decode_tok_s
    if ($e.auto_route) { $tierSpeeds.auto_route += $e.auto_route.decode_tok_s }
}

$median = @{
    fast = ($tierSpeeds.fast | Sort-Object)[[math]::Floor($tierSpeeds.fast.Count/2)]
    balanced_lfm = ($tierSpeeds.balanced_lfm | Sort-Object)[[math]::Floor($tierSpeeds.balanced_lfm.Count/2)]
    balanced_domain = ($tierSpeeds.balanced_domain | Sort-Object)[[math]::Floor($tierSpeeds.balanced_domain.Count/2)]
    quality = ($tierSpeeds.quality | Sort-Object)[[math]::Floor($tierSpeeds.quality.Count/2)]
}
$autoMean = if ($tierSpeeds.auto_route.Count -gt 0) {
    [math]::Round(($tierSpeeds.auto_route | Measure-Object -Average).Average, 2)
} else { 0 }

$baseline3B = 48.38
$orchGain = if ($autoMean -gt 0) { [math]::Round((($autoMean - $baseline3B) / $baseline3B) * 100, 1) } else { 0 }

$summary = @{
    routing_accuracy = "$tierMatches/$($report.prompts.Count)"
    median_decode_tok_s = $median
    auto_route_mean_tok_s = $autoMean
    vs_always_3b_baseline = @{
        baseline_tok_s = $baseline3B
        gain_pct = $orchGain
        pass_40pct = ($orchGain -ge 40)
    }
}
$report.summary = $summary

$outFile = Join-Path $resultsDir "router-eval-$(Get-Date -Format 'yyyyMMdd-HHmmss').json"
$report | ConvertTo-Json -Depth 8 | Set-Content $outFile -Encoding UTF8

Write-Host "`n=== Summary ===" -ForegroundColor Green
Write-Host "Routing accuracy: $($summary.routing_accuracy)"
Write-Host "Median decode: fast=$($median.fast) | LFM=$($median.balanced_lfm) | domain=$($median.balanced_domain) | quality=$($median.quality) tok/s"
Write-Host "Auto-route mean: $autoMean tok/s vs always-3B $baseline3B -> +$orchGain% $(if($summary.vs_always_3b_baseline.pass_40pct){'PASS'}else{'below 40%'})"
Write-Host "Report: $outFile"

& (Join-Path $PSScriptRoot "win-compare-target.ps1") -RouterEvalFile $outFile
