# Pull + bench Phase D2 candidates (baselines already in results/phase-d2/)
param(
    [string]$LabRoot = "D:\lumen-stream-lab",
    [int]$Runs = 3,
    [int]$Warmup = 1
)

$ErrorActionPreference = "Continue"
$env:OLLAMA_MODELS = "D:\ollama\models"
$ollamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
$outDir = Join-Path $LabRoot "results\phase-d2"
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
    Write-Host "  Pulling $model ..." -ForegroundColor DarkGray
    & $ollamaExe pull $model 2>&1 | Tee-Object -Variable pullOut | Out-Null
    if ($LASTEXITCODE -ne 0) {
        $tail = ($pullOut | Select-Object -Last 6) -join "`n"
        throw "pull exit $LASTEXITCODE`n$tail"
    }
    Write-Host "  Pull OK" -ForegroundColor Green
}

$Candidates = @(
    @{ id = "D2-01"; model = "oamazonasgabriel/lfm2.5-2.6b:q4_k_m-8gbGPU"; family = "Liquid AI LFM2.5" },
    @{ id = "D2-02"; model = "gemma4:e2b-it-qat"; family = "Google Gemma 4" },
    @{ id = "D2-03"; model = "gemma4:e4b"; family = "Google Gemma 4" },
    @{ id = "D2-04"; model = "nemotron-3.5-lightning"; family = "NVIDIA Nemotron" }
)

$summaryPath = Join-Path $outDir "phase-d2-summary.json"
$runsList = [System.Collections.Generic.List[object]]::new()
$startedAt = (Get-Date).ToString("o")

if (Test-Path $summaryPath) {
    $existing = Get-Content $summaryPath -Raw | ConvertFrom-Json
    if ($existing.started_at) { $startedAt = $existing.started_at }
    foreach ($r in @($existing.runs)) {
        if ($r.id -notmatch '^D2-') { [void]$runsList.Add($r) }
    }
}

Ensure-Ollama

foreach ($c in $Candidates) {
    Write-Host "`n=== $($c.id): $($c.model) ===" -ForegroundColor Cyan
    $outFile = Join-Path $outDir "$($c.id)-$($c.model -replace '[\\/:*?""<>|]', '_').json"
    try {
        Pull-Model $c.model
        & "$PSScriptRoot\win-bench-with-serve.ps1" -Model $c.model -Runs $Runs -Warmup $Warmup -OutFile $outFile
        $bench = Get-Content $outFile -Raw | ConvertFrom-Json
        [void]$runsList.Add([pscustomobject]@{ id = $c.id; model = $c.model; family = $c.family; status = "ok"; median_decode_tok_s = $bench.median_decode_tok_s })
        Write-Host "  BENCH OK: $($bench.median_decode_tok_s) tok/s" -ForegroundColor Green
    } catch {
        [void]$runsList.Add([pscustomobject]@{ id = $c.id; model = $c.model; family = $c.family; status = "failed"; error = $_.Exception.Message })
        Write-Host "  FAILED: $($_.Exception.Message)" -ForegroundColor Red
    }
}

$summaryObj = [ordered]@{
    started_at = $startedAt
    ended_at = (Get-Date).ToString("o")
    gpu = (nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>&1 | Out-String).Trim()
    runs = $runsList
}
$summaryObj | ConvertTo-Json -Depth 6 | Set-Content $summaryPath -Encoding UTF8
Write-Host "`nUpdated $summaryPath" -ForegroundColor Green
