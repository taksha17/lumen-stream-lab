# Benchmark 3B with Ollama speculative options (native)
param(
    [string]$LabRoot = "D:\lumen-stream-lab",
    [string]$Model = "llama3.2:3b",
    [string]$Draft = "llama3.2:1b",
    [string]$Prompt = "Explain quantum computing in simple terms."
)

$env:OLLAMA_MODELS = "D:\ollama\models"
$ollamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"

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

Ensure-Ollama

Write-Host "=== Speculative benchmark ===" -ForegroundColor Cyan
Write-Host "Model: $Model | Draft: $Draft"

$rates = @()
foreach ($label in @("warmup", "run-1", "run-2", "run-3")) {
    $body = @{
        model = $Model
        prompt = $Prompt
        stream = $false
        options = @{
            num_predict = 128
            temperature = 0
        }
    }
    # Ollama 0.33+ speculative field
    $body["options"]["speculative"] = $Draft

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/generate" -Method Post -Body ($body | ConvertTo-Json -Depth 5) -ContentType "application/json" -TimeoutSec 600
        $sw.Stop()
        $decode = $resp.eval_count / ($resp.eval_duration / 1e9)
        Write-Host "${label}: $([math]::Round($decode,2)) tok/s"
        if ($label -ne "warmup") { $rates += $decode }
    } catch {
        Write-Host "${label}: FAILED - $_"
    }
}

if ($rates.Count -gt 0) {
    $sorted = $rates | Sort-Object
    $median = $sorted[[math]::Floor($sorted.Count / 2)]
    Write-Host "MEDIAN speculative: $([math]::Round($median,2)) tok/s (baseline was 48.38)"
    @{
        model = $Model
        draft = $Draft
        median_decode_tok_s = [math]::Round($median, 2)
        baseline_3b = 48.38
        gain_pct = [math]::Round(($median - 48.38) / 48.38 * 100, 1)
    } | ConvertTo-Json | Set-Content (Join-Path $LabRoot "results\speculative-native.json") -Encoding UTF8
}
