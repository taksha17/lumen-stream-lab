# Verify which GPU Ollama actually uses during inference
$ErrorActionPreference = "Stop"
$env:OLLAMA_MODELS = "D:\ollama\models"
$ollama = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
$log = "D:\lumen-stream-lab\results\gpu-check.txt"
$sampleFile = "D:\lumen-stream-lab\results\gpu-samples.txt"

function Ensure-Ollama {
    try { $null = Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 3; return } catch {}
    Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep 2
    Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden
    for ($i = 0; $i -lt 25; $i++) {
        Start-Sleep 2
        try { $null = Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 3; return } catch {}
    }
    throw "Ollama failed to start"
}

Write-Host "=== GPU CHECK $(Get-Date -Format o) ==="
nvidia-smi --query-gpu=name,memory.used,memory.free,utilization.gpu --format=csv
Get-CimInstance Win32_VideoController | ForEach-Object { Write-Host "VideoController: $($_.Name)" }

Ensure-Ollama
Write-Host "Ollama ready"

# Background sampler
$sampler = Start-Process -FilePath "powershell" -ArgumentList @(
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", "D:\lumen-stream-lab\deploy\win-gpu-sample.ps1",
    "-OutFile", $sampleFile
) -WindowStyle Hidden -PassThru

Start-Sleep -Milliseconds 600

$bodyObj = @{
    model = "llama3.2:3b"
    prompt = "Explain gravity in one short paragraph with enough detail to use GPU."
    stream = $false
    options = @{ num_predict = 128; temperature = 0.2 }
}
$body = $bodyObj | ConvertTo-Json -Depth 5 -Compress

$sw = [System.Diagnostics.Stopwatch]::StartNew()
$resp = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/generate" -Method Post -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -ContentType "application/json; charset=utf-8" -TimeoutSec 180
$sw.Stop()

Start-Sleep 1
if (-not $sampler.HasExited) { Stop-Process -Id $sampler.Id -Force -ErrorAction SilentlyContinue }

$decode = if ($resp.eval_duration -gt 0) { [math]::Round($resp.eval_count / ($resp.eval_duration / 1e9), 2) } else { 0 }

$report = @()
$report += "=== GENERATE ==="
$report += "decode_tok_s=$decode eval_count=$($resp.eval_count) wall_s=$([math]::Round($sw.Elapsed.TotalSeconds,2))"
$report += "load_duration_ms=$([math]::Round($resp.load_duration/1e6,1))"
$report += "=== nvidia-smi samples during generate ==="
if (Test-Path $sampleFile) { $report += (Get-Content $sampleFile) } else { $report += "(no samples)" }
$report += "=== ollama ps ==="
$report += (& $ollama ps | Out-String)
$report += "=== final nvidia-smi ==="
$report += (nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.free --format=csv)

$reportText = $report -join "`n"
$reportText | Set-Content $log -Encoding UTF8
Write-Host $reportText
Write-Host "`nWrote $log"
