# API-based benchmark - reliable over SSH (no TTY verbose parsing)
param(
    [string]$Model = "llama3.2:3b",
    [int]$Warmup = 2,
    [int]$Runs = 5,
    [string]$Prompt = "Explain quantum computing in simple terms.",
    [int]$NumPredict = 128,
    [string]$OutFile = "D:\lumen-stream-lab\results\baseline.json"
)

$ErrorActionPreference = "Stop"

function Invoke-OllamaGenerate {
    param([string]$Label)
    $body = @{
        model = $Model
        prompt = $Prompt
        stream = $false
        options = @{
            num_predict = $NumPredict
            temperature = 0
        }
    } | ConvertTo-Json

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/generate" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 600
    $sw.Stop()

    $evalCount = [int]$resp.eval_count
    $evalNs = [double]$resp.eval_duration
    $decodeTokS = if ($evalNs -gt 0) { $evalCount / ($evalNs / 1e9) } else { $null }
    $wallTokS = if ($sw.Elapsed.TotalSeconds -gt 0) { $evalCount / $sw.Elapsed.TotalSeconds } else { $null }

    Write-Host ("{0}: eval_count={1} api_decode_tok_s={2:N2} wall_tok_s={3:N2} total_s={4:N2}" -f $Label, $evalCount, $decodeTokS, $wallTokS, $sw.Elapsed.TotalSeconds)

    return [pscustomobject]@{
        Label = $Label
        EvalCount = $evalCount
        ApiDecodeTokS = $decodeTokS
        WallTokS = $wallTokS
        TotalS = $sw.Elapsed.TotalSeconds
        PromptEvalCount = $resp.prompt_eval_count
        LoadDurationNs = $resp.load_duration
    }
}

Write-Host "=== Lumen API Bench ===" -ForegroundColor Cyan
Write-Host "Model: $Model | num_predict: $NumPredict"

# Ensure Ollama up
try { $null = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 5 }
catch { throw "Ollama API not running. Start ollama serve first." }

foreach ($i in 1..$Warmup) { Invoke-OllamaGenerate "warmup-$i" | Out-Null }

$benchRuns = @()
foreach ($i in 1..$Runs) { $benchRuns += Invoke-OllamaGenerate "run-$i" }

$rates = $benchRuns | ForEach-Object { $_.ApiDecodeTokS } | Where-Object { $_ -ne $null } | Sort-Object
$mid = [math]::Floor(($rates.Count - 1) / 2)
$median = $rates[$mid]

Write-Host ""
Write-Host "=== MEDIAN DECODE (API): $([math]::Round($median, 2)) tok/s ===" -ForegroundColor Green
Write-Host "Target +40%: $([math]::Round($median * 1.4, 2)) tok/s"

$result = @{
    model = $Model
    num_predict = $NumPredict
    median_decode_tok_s = [math]::Round($median, 2)
    target_plus_40pct = [math]::Round($median * 1.4, 2)
    runs = $benchRuns | ForEach-Object {
        @{
            label = $_.Label
            api_decode_tok_s = [math]::Round($_.ApiDecodeTokS, 2)
            eval_count = $_.EvalCount
            total_s = [math]::Round($_.TotalS, 2)
        }
    }
    probed_at = (Get-Date).ToString("o")
}
New-Item -ItemType Directory -Force -Path (Split-Path $OutFile) | Out-Null
$result | ConvertTo-Json -Depth 5 | Set-Content $OutFile -Encoding UTF8
Write-Host "Wrote $OutFile"
