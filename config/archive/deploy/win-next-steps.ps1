# Pull models and run benchmark suite on server
param(
    [switch]$SkipPull,
    [switch]$SkipSoup
)

$ErrorActionPreference = "Continue"
$LabRoot = "D:\lumen-stream-lab"
$env:OLLAMA_MODELS = "D:\ollama\models"
$ollamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
$log = Join-Path $LabRoot "results\next-steps-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"

function Log($m) {
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $m"
    Write-Host $line
    Add-Content $log $line
}

function Ensure-Ollama {
    try { $null = Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 3; return } catch {}
    Log "Starting Ollama..."
    Get-Process ollama -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue
    Start-Sleep 2
    Start-Process $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep 2
        try { $null = Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 3; Log "Ollama ready"; return } catch {}
    }
    throw "Ollama failed to start"
}

Log "=== Lumen Next Steps ==="
Ensure-Ollama

if (-not $SkipPull) {
    foreach ($m in @("llama3.2:1b", "mistral:7b-instruct-q4_0")) {
        Log "Pulling $m ..."
        & $ollamaExe pull $m 2>&1 | ForEach-Object { Log $_ }
    }
}

# --- Benchmarks ---
$models = @(
    @{ name = "llama3.2:3b"; out = "baseline-llama3.2-3b.json" },
    @{ name = "llama3.2:1b"; out = "baseline-llama3.2-1b.json" },
    @{ name = "mistral:7b-instruct-q4_0"; out = "baseline-mistral-7b.json" }
)

foreach ($cfg in $models) {
    $outFile = Join-Path $LabRoot "results\$($cfg.out)"
    Log "Benchmark: $($cfg.name)"
    try {
        & "$LabRoot\deploy\win-bench-api.ps1" -Model $cfg.name -Runs 3 -Warmup 1 -OutFile $outFile
    } catch {
        Log "WARN benchmark failed for $($cfg.name): $_"
    }
}

# --- Speculative decode test (Ollama native) ---
Log "Testing speculative decode: llama3.2:3b with llama3.2:1b draft"
$specBody = @{
    model = "llama3.2:3b"
    prompt = "Explain quantum computing in simple terms."
    stream = $false
    options = @{
        num_predict = 128
        temperature = 0
    }
} | ConvertTo-Json

# Ollama 0.3+ supports speculative via model options in some builds - try API with draft
try {
    $specPayload = @{
        model = "llama3.2:3b"
        prompt = "Explain quantum computing in simple terms."
        stream = $false
        options = @{ num_predict = 128; temperature = 0 }
        # draft model field (Ollama experimental)
        draft = "llama3.2:1b"
    } | ConvertTo-Json -Depth 4

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/generate" -Method Post -Body $specPayload -ContentType "application/json" -TimeoutSec 600
    $sw.Stop()
    $decode = $resp.eval_count / ($resp.eval_duration / 1e9)
    Log "Speculative decode: $([math]::Round($decode,2)) tok/s (wall $($sw.Elapsed.TotalSeconds)s)"
    @{
        model = "llama3.2:3b"
        draft = "llama3.2:1b"
        decode_tok_s = [math]::Round($decode, 2)
        baseline_target = 66.26
        gain_vs_47 = [math]::Round(($decode - 47.33) / 47.33 * 100, 1)
    } | ConvertTo-Json | Set-Content (Join-Path $LabRoot "results\speculative-decode.json") -Encoding UTF8
} catch {
    Log "Speculative API test: $_ (may need Ollama flag or newer API)"
}

if (-not $SkipSoup) {
    Log "=== Soup smoke test setup ==="
    $dataDir = Join-Path $LabRoot "data"
    New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
    @(
        @{ instruction = "What is 2+2?"; input = ""; output = "4" },
        @{ instruction = "Capital of France?"; input = ""; output = "Paris" },
        @{ instruction = "Say hello"; input = ""; output = "Hello!" }
    ) | ForEach-Object {
        @{ instruction = $_.instruction; input = $_.input; output = $_.output } | ConvertTo-Json -Compress
    } | Set-Content (Join-Path $dataDir "train.jsonl") -Encoding UTF8

    $soupYaml = @"
base: Qwen/Qwen2.5-0.5B-Instruct
task: sft
data:
  train: $dataDir\train.jsonl
  format: alpaca
training:
  epochs: 1
  lr: 2e-4
  batch_size: 1
  max_steps: 5
  stream_layers: false
  quantization: 4bit
  lora:
    r: 8
    alpha: 16
output: $LabRoot\output-smoke
"@
    Set-Content (Join-Path $LabRoot "soup-smoke.yaml") $soupYaml -Encoding UTF8
    Log "Running soup train smoke (Qwen2.5-0.5B, 5 steps)..."
    Push-Location $LabRoot
    soup train --config soup-smoke.yaml 2>&1 | ForEach-Object { Log $_ }
    Pop-Location
}

Log "=== Done. Log: $log ==="
