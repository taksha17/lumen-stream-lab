# Resident backend shootout: Ollama API vs llama-cli on same GGUF blob
param(
    [string]$LabRoot = "D:\lumen-stream-lab",
    [string]$Model = "llama3.2:3b",
    [string]$GgufPath = "",
    [string]$Prompt = "Explain quantum computing in simple terms.",
    [int]$NumPredict = 128,
    [int]$Warmup = 2,
    [int]$Runs = 5
)

$ErrorActionPreference = "Stop"
$env:OLLAMA_MODELS = if ($env:OLLAMA_MODELS) { $env:OLLAMA_MODELS } else { "D:\ollama\models" }
$ollamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
$resultsDir = Join-Path $LabRoot "results"
New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null

& (Join-Path $PSScriptRoot "win-install-llama-cli.ps1") -LabRoot $LabRoot
$llamaCli = Join-Path $LabRoot "tools\llama-cpp-bin\bin\llama-cli.exe"
if (-not (Test-Path $llamaCli)) { throw "llama-cli missing at $llamaCli" }

function Ensure-Ollama {
    try { $null = Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 5; return } catch {}
    Get-Process ollama -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue
    Start-Sleep 2
    Start-Process $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep 2
        try { $null = Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 3; return } catch {}
    }
    throw "Ollama not running"
}

function Resolve-OllamaGguf([string]$modelName) {
    if ($GgufPath -and (Test-Path $GgufPath)) { return $GgufPath }
    $parts = $modelName.Split(":")
    $lib = $parts[0]
    $tag = if ($parts.Count -gt 1) { $parts[1] } else { "latest" }
    $manifest = Join-Path $env:OLLAMA_MODELS "manifests\registry.ollama.ai\library\$lib\$tag"
    if (-not (Test-Path $manifest)) {
        throw "Ollama manifest not found: $manifest (pull $modelName first or pass -GgufPath)"
    }
    $json = Get-Content $manifest -Raw | ConvertFrom-Json
    $layer = $json.layers | Where-Object { $_.mediaType -match "application/vnd.ollama.image.model" } | Select-Object -First 1
    if (-not $layer) { throw "No model layer in manifest" }
    $digest = $layer.digest -replace '^sha256:', 'sha256-'
    $blob = Join-Path $env:OLLAMA_MODELS "blobs\$digest"
    if (-not (Test-Path $blob)) { throw "Blob missing: $blob" }
    return $blob
}

function Invoke-OllamaBench {
    $rates = @()
    $rows = @()
    for ($i = 1; $i -le ($Warmup + $Runs); $i++) {
        $label = if ($i -le $Warmup) { "warmup-$i" } else { "run-$($i - $Warmup)" }
        $body = @{
            model = $Model
            prompt = $Prompt
            stream = $false
            options = @{ num_predict = $NumPredict; temperature = 0 }
        } | ConvertTo-Json -Depth 5
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $resp = Invoke-RestMethod http://127.0.0.1:11434/api/generate -Method Post `
            -Body ([Text.Encoding]::UTF8.GetBytes($body)) -ContentType "application/json" -TimeoutSec 600
        $sw.Stop()
        $rate = if ($resp.eval_duration -gt 0) { [math]::Round($resp.eval_count / ($resp.eval_duration / 1e9), 2) } else { 0 }
        Write-Host "ollama $label`: $rate tok/s"
        $rows += @{ label = $label; decode_tok_s = $rate; eval_count = $resp.eval_count }
        if ($i -gt $Warmup -and $rate -gt 0) { $rates += $rate }
    }
    $med = ($rates | Sort-Object)[[math]::Floor(($rates.Count - 1) / 2)]
    if ($rates.Count -eq 1) { $med = $rates[0] }
    return @{ backend = "ollama"; model = $Model; median_decode_tok_s = $med; runs = $rows }
}

function Invoke-LlamaCppBench([string]$gguf) {
    $rates = @()
    $rows = @()
    for ($i = 1; $i -le ($Warmup + $Runs); $i++) {
        $label = if ($i -le $Warmup) { "warmup-$i" } else { "run-$($i - $Warmup)" }
        $args = @("-m", $gguf, "-p", $Prompt, "-n", "$NumPredict", "--temp", "0", "-ngl", "99", "--no-display-prompt")
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $out = & $llamaCli @args 2>&1 | Out-String
        $sw.Stop()
        $rate = 0.0
        $tokens = 0
        if ($out -match '(\d+\.?\d*)\s*tokens per second') { $rate = [double]$Matches[1] }
        if ($out -match 'eval time\s*=\s*[\d.]+\s*ms\s*/\s*(\d+)\s*runs') { $tokens = [int]$Matches[1] }
        if ($rate -eq 0 -and $tokens -gt 0 -and $sw.Elapsed.TotalSeconds -gt 0) {
            $rate = [math]::Round($tokens / $sw.Elapsed.TotalSeconds, 2)
        }
        Write-Host "llamacpp $label`: $rate tok/s"
        $rows += @{ label = $label; decode_tok_s = $rate; eval_count = $tokens }
        if ($i -gt $Warmup -and $rate -gt 0) { $rates += $rate }
    }
    $med = ($rates | Sort-Object)[[math]::Floor(($rates.Count - 1) / 2)]
    if ($rates.Count -eq 1) { $med = $rates[0] }
    return @{ backend = "llamacpp"; gguf = $gguf; median_decode_tok_s = $med; runs = $rows }
}

Ensure-Ollama
$gguf = Resolve-OllamaGguf $Model
Write-Host "=== Backend shootout: $Model ===" -ForegroundColor Cyan
Write-Host "GGUF blob: $gguf"
Write-Host "Prompt: $Prompt | num_predict=$NumPredict"
Write-Host ""

Write-Host "--- Ollama ---" -ForegroundColor Yellow
$ollama = Invoke-OllamaBench
Write-Host "--- llama.cpp ---" -ForegroundColor Yellow
$llama = Invoke-LlamaCppBench $gguf

$o = [double]$ollama.median_decode_tok_s
$l = [double]$llama.median_decode_tok_s
$winner = if ($o -ge $l) { "ollama" } else { "llamacpp" }
$delta = if ([math]::Min($o, $l) -gt 0) { [math]::Round((([math]::Max($o, $l) - [math]::Min($o, $l)) / [math]::Min($o, $l)) * 100, 1) } else { 0 }

$report = @{
    evaluated_at = (Get-Date).ToString("o")
    model = $Model
    gguf = $gguf
    prompt = $Prompt
    num_predict = $NumPredict
    ollama = $ollama
    llamacpp = $llama
    summary = @{
        ollama_median_tok_s = $o
        llamacpp_median_tok_s = $l
        winner = $winner
        delta_pct = $delta
    }
}

$outFile = Join-Path $resultsDir ("backend-shootout-{0}.json" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
$report | ConvertTo-Json -Depth 6 | Set-Content $outFile -Encoding UTF8

Write-Host ""
Write-Host "=== SUMMARY ===" -ForegroundColor Green
Write-Host "Ollama:    $o tok/s"
Write-Host "llama.cpp: $l tok/s"
Write-Host "Winner:    $winner (+$delta%)"
Write-Host "Report:    $outFile"
