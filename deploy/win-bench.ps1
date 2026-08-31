# Baseline benchmark on Windows (Ollama)
# Usage: powershell -File D:\lumen-stream-lab\deploy\win-bench.ps1 -Model llama3.2:3b

param(
    [string]$Model = "llama3.2:3b",
    [int]$Warmup = 2,
    [int]$Runs = 5,
    [string]$Prompt = "Explain quantum computing in simple terms."
)

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Error "Ollama not installed. See https://ollama.com/download/windows"
}

Write-Host "=== Lumen Bench (Windows) ===" -ForegroundColor Cyan
Write-Host "Model: $Model"
Write-Host "Warmup: $Warmup | Runs: $Runs"
Write-Host ""

function Invoke-OllamaRun {
    param([string]$Label)
    Write-Host "--- $Label ---" -ForegroundColor Yellow
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $raw = ollama run $Model $Prompt --verbose 2>&1
    $out = ($raw | Out-String)
    $sw.Stop()

    # Strip ANSI escape codes for parsing
    $clean = $out -replace '\x1B\[[0-9;]*[a-zA-Z]', ''

    # Decode/generation rate (NOT prompt eval rate)
    $decodeRate = $null
    if ($clean -match 'eval rate:\s*([\d.]+)\s*tokens/s') {
        $decodeRate = [double]$Matches[1]
    }

    $promptRate = $null
    if ($clean -match 'prompt eval rate:\s*([\d.]+)\s*tokens/s') {
        $promptRate = [double]$Matches[1]
    }

    $evalCount = $null
    if ($clean -match 'eval count:\s*(\d+)') {
        $evalCount = [int]$Matches[1]
    }

    Write-Host "decode_tok_s=$decodeRate prompt_eval_tok_s=$promptRate tokens_generated=$evalCount wall_s=$([math]::Round($sw.Elapsed.TotalSeconds,2))"
    Write-Host ""

    return [pscustomobject]@{
        Label       = $Label
        DecodeTokS  = $decodeRate
        PromptTokS  = $promptRate
        Tokens      = $evalCount
        WallS       = $sw.Elapsed.TotalSeconds
    }
}

$all = @()
foreach ($i in 1..$Warmup) { Invoke-OllamaRun "warmup-$i" | Out-Null }
foreach ($i in 1..$Runs) { $all += Invoke-OllamaRun "run-$i" }

$rates = $all | Where-Object { $_.DecodeTokS -ne $null } | ForEach-Object { $_.DecodeTokS }
if ($rates.Count -gt 0) {
    $sorted = $rates | Sort-Object
    $mid = [math]::Floor(($sorted.Count - 1) / 2)
    $median = $sorted[$mid]
    Write-Host "=== MEDIAN DECODE: $median tok/s ===" -ForegroundColor Cyan
    Write-Host "Record in RESULTS.md"
    Write-Host "Target +40%: $([math]::Round($median * 1.4, 2)) tok/s minimum"

    $result = @{
        model = $Model
        median_decode_tok_s = $median
        target_plus_40pct = [math]::Round($median * 1.4, 2)
        runs = $all | ForEach-Object {
            @{
                label = $_.Label
                decode_tok_s = $_.DecodeTokS
                wall_s = [math]::Round($_.WallS, 2)
            }
        }
        probed_at = (Get-Date).ToString("o")
    }
    $outPath = "D:\lumen-stream-lab\results\baseline.json"
    $result | ConvertTo-Json -Depth 5 | Set-Content $outPath -Encoding UTF8
    Write-Host "Wrote $outPath"
} else {
    Write-Warning "Could not parse decode tok/s from ollama --verbose output"
}
