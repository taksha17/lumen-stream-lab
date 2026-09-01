# Phase D2 - cross-family bench: newer models (Gemma 4, Nemotron, LFM)
# Same protocol as win-bench-with-serve.ps1; results -> results/phase-d2/
param(
    [string]$LabRoot = "D:\lumen-stream-lab",
    [int]$Runs = 3,
    [int]$Warmup = 1
)

$ErrorActionPreference = "Stop"
$env:OLLAMA_MODELS = "D:\ollama\models"
$outDir = Join-Path $LabRoot "results\phase-d2"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

# GTX 1650 4GB - realistic Ollama candidates (new families, not Qwen/Llama reruns)
$Candidates = @(
    @{
        id = "D2-01"
        model = "oamazonasgabriel/lfm2.5-2.6b:q4_k_m-8gbGPU"
        family = "Liquid AI LFM2.5"
        slot = "balanced/fast"
        note = "~1.7GB Q4, built for 8GB GPU - best fit on 4GB"
        expect = "should_run"
    },
    @{
        id = "D2-02"
        model = "gemma4:e2b-it-qat"
        family = "Google Gemma 4"
        slot = "balanced"
        note = "4.3GB QAT variant - only Gemma4 likely to fit 4GB VRAM"
        expect = "maybe"
    },
    @{
        id = "D2-03"
        model = "gemma4:e4b"
        family = "Google Gemma 4"
        slot = "balanced"
        note = "9.6GB default - likely OOM on 4GB; document fail"
        expect = "likely_oom"
    },
    @{
        id = "D2-04"
        model = "nemotron-3.5-lightning"
        family = "NVIDIA Nemotron"
        slot = "quality/agent"
        note = "25GB MoE (3B active) - likely OOM; worth documenting"
        expect = "likely_oom"
    }
)

# Baselines to compare against (already on server)
$Baselines = @(
    @{ id = "BL-01"; model = "llama3.2:1b"; slot = "fast" },
    @{ id = "BL-02"; model = "qwen2.5-3b-lumen"; slot = "balanced" },
    @{ id = "BL-03"; model = "qwen2.5-7b-lumen"; slot = "quality" }
)

$summary = @{
    started_at = (Get-Date).ToString("o")
    ollama_version = (ollama --version 2>&1 | Out-String).Trim()
    gpu = (nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>&1 | Out-String).Trim()
    runs = @()
}

function Test-Model([hashtable]$entry) {
    $outFile = Join-Path $outDir "$($entry.id)-$($entry.model -replace '[\\/:*?\"<>|]', '_').json"
    Write-Host "`n=== $($entry.id): $($entry.model) ($($entry.family)) ===" -ForegroundColor Cyan
    Write-Host "  $($entry.note)"

    try {
        Write-Host "  Pulling..." -ForegroundColor DarkGray
        ollama pull $entry.model 2>&1 | Out-Null
    } catch {
        $summary.runs += @{
            id = $entry.id; model = $entry.model; status = "pull_failed"; error = $_.Exception.Message
        }
        Write-Host "  PULL FAILED: $($_.Exception.Message)" -ForegroundColor Red
        return
    }

    try {
        & "$PSScriptRoot\win-bench-with-serve.ps1" -Model $entry.model -Runs $Runs -Warmup $Warmup -OutFile $outFile
        $bench = Get-Content $outFile -Raw | ConvertFrom-Json
        $summary.runs += @{
            id = $entry.id
            model = $entry.model
            family = $entry.family
            slot = $entry.slot
            status = "ok"
            median_decode_tok_s = $bench.median_decode_tok_s
            expect = $entry.expect
        }
        Write-Host "  OK: $($bench.median_decode_tok_s) tok/s" -ForegroundColor Green
    } catch {
        $summary.runs += @{
            id = $entry.id; model = $entry.model; status = "bench_failed"; error = $_.Exception.Message
        }
        Write-Host "  BENCH FAILED: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "=== Phase D2: newer model families ===" -ForegroundColor Cyan
Write-Host "Ollama: $($summary.ollama_version)"
Write-Host "GPU: $($summary.gpu)"

foreach ($b in $Baselines) {
    $outFile = Join-Path $outDir "$($b.id)-baseline-$($b.model -replace ':','_').json"
    Write-Host "`n--- Baseline $($b.id): $($b.model) ---" -ForegroundColor Yellow
    try {
        & "$PSScriptRoot\win-bench-with-serve.ps1" -Model $b.model -Runs $Runs -Warmup $Warmup -OutFile $outFile
        $bench = Get-Content $outFile -Raw | ConvertFrom-Json
        $summary.runs += @{ id = $b.id; model = $b.model; status = "baseline"; median_decode_tok_s = $bench.median_decode_tok_s }
    } catch {
        Write-Host "  Baseline skip: $_" -ForegroundColor DarkYellow
    }
}

foreach ($c in $Candidates) { Test-Model $c }

$summary.ended_at = (Get-Date).ToString("o")
$summaryPath = Join-Path $outDir "phase-d2-summary.json"
$summary | ConvertTo-Json -Depth 6 | Set-Content $summaryPath -Encoding UTF8

Write-Host "`n=== Phase D2 complete ===" -ForegroundColor Green
Write-Host "Summary: $summaryPath"
