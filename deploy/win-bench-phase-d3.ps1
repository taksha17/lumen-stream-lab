# Phase D3 — bench recent small-model families on reference lab (4GB VRAM)
# Usage: powershell -File deploy\win-bench-phase-d3.ps1
param(
    [string]$LabRoot = "D:\lumen-stream-lab",
    [int]$Runs = 3,
    [int]$Warmup = 1,
    [switch]$SkipPull
)

$ErrorActionPreference = "Continue"
$env:OLLAMA_MODELS = "D:\ollama\models"
$ollamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
$outDir = Join-Path $LabRoot "results\phase-d3"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

function Ensure-Ollama {
    try { $null = Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 3; return } catch {}
    Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep 2
    Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep 2
        try { $null = Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 3; return } catch {}
    }
    throw "Ollama failed to start"
}

function Pull-Model([string]$model) {
    if ($SkipPull) { return }
    Write-Host "  Pulling $model ..." -ForegroundColor DarkGray
    & $ollamaExe pull $model 2>&1 | Tee-Object -Variable pullOut | Out-Null
    if ($LASTEXITCODE -ne 0) {
        $tail = ($pullOut | Select-Object -Last 8) -join "`n"
        throw "pull exit $LASTEXITCODE`n$tail"
    }
    Write-Host "  Pull OK" -ForegroundColor Green
}

# Baselines re-benched + newer Ollama families (4GB-safe targets)
$Candidates = @(
    @{ id = "BL-01"; model = "llama3.2:1b"; family = "Meta Llama 3.2"; note = "fast tier" },
    @{ id = "BL-02"; model = "llama3.2:3b"; family = "Meta Llama 3.2"; note = "+40% baseline" },
    @{ id = "BL-03"; model = "qwen2.5:3b-instruct-q4_K_M"; family = "Alibaba Qwen 2.5"; note = "stock 3B" },
    @{ id = "D3-01"; model = "phi4-mini"; family = "Microsoft Phi-4"; note = "recent small" },
    @{ id = "D3-02"; model = "smollm2:1.7b-instruct-q4_K_M"; family = "HuggingFace SmolLM2"; note = "recent 1.7B" },
    @{ id = "D3-03"; model = "gemma3:1b-it-qat"; family = "Google Gemma 3"; note = "recent 1B QAT" },
    @{ id = "D3-04"; model = "gemma3:4b-it-qat"; family = "Google Gemma 3"; note = "recent 4B QAT" },
    @{ id = "D3-05"; model = "lfm-balanced"; family = "Liquid AI LFM 2.5"; note = "balanced alias" },
    @{ id = "D3-06"; model = "qwen2.5-3b-lumen"; family = "Qwen 2.5 Lumen"; note = "domain fine-tune" }
)

$summaryPath = Join-Path $outDir "phase-d3-summary.json"
$runsList = [System.Collections.Generic.List[object]]::new()
$startedAt = (Get-Date).ToString("o")

Ensure-Ollama

foreach ($c in $Candidates) {
    Write-Host "`n=== $($c.id): $($c.model) ($($c.family)) ===" -ForegroundColor Cyan
    $safeName = ($c.model -replace '[\\/:*?""<>|]', '_')
    $outFile = Join-Path $outDir "$($c.id)-$safeName.json"
    try {
        if ($c.model -notmatch '^lfm-balanced$|^qwen2\.5-3b-lumen$') {
            Pull-Model $c.model
        }
        & "$LabRoot\deploy\win-bench-with-serve.ps1" -Model $c.model -Runs $Runs -Warmup $Warmup -OutFile $outFile
        $bench = Get-Content $outFile -Raw | ConvertFrom-Json
        [void]$runsList.Add([pscustomobject]@{
            id = $c.id
            model = $c.model
            family = $c.family
            note = $c.note
            status = "ok"
            median_decode_tok_s = $bench.median_decode_tok_s
        })
        Write-Host "  BENCH OK: $($bench.median_decode_tok_s) tok/s" -ForegroundColor Green
    } catch {
        [void]$runsList.Add([pscustomobject]@{
            id = $c.id
            model = $c.model
            family = $c.family
            note = $c.note
            status = "failed"
            error = $_.Exception.Message
        })
        Write-Host "  FAILED: $($_.Exception.Message)" -ForegroundColor Red
    }
}

$summaryObj = [ordered]@{
    phase = "D3"
    started_at = $startedAt
    ended_at = (Get-Date).ToString("o")
    gpu = (nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>&1 | Out-String).Trim()
    ollama_version = (ollama --version 2>&1 | Out-String).Trim()
    prompt = "Explain quantum computing in simple terms."
    num_predict = 128
    runs = $Runs
    warmup = $Warmup
    results = $runsList
}
$summaryObj | ConvertTo-Json -Depth 6 | Set-Content $summaryPath -Encoding UTF8
Write-Host "`nUpdated $summaryPath" -ForegroundColor Green
