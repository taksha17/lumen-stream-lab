# Sample nvidia-smi during one Ollama generate. No machine-specific paths.
# Usage (from repo root):
#   powershell -File deploy\win-gpu-check.ps1
#   powershell -File deploy\win-gpu-check.ps1 -Model llama3.2:3b
param(
    [string]$LabRoot = "",
    [string]$Model = "llama3.2:3b",
    [int]$NumPredict = 128
)

$ErrorActionPreference = "Stop"
if (-not $LabRoot) { $LabRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path }
$results = Join-Path $LabRoot "results"
New-Item -ItemType Directory -Path $results -Force | Out-Null
$log = Join-Path $results "gpu-check.txt"
$sampleFile = Join-Path $results "gpu-samples.txt"

Write-Host "=== GPU CHECK (nvidia-smi CUDA util, not Task Manager 3D) ==="
nvidia-smi --query-gpu=name,memory.used,memory.free,utilization.gpu --format=csv

$sampler = Join-Path $PSScriptRoot "win-gpu-sample.ps1"
$sp = $null
if (Test-Path $sampler) {
    $sp = Start-Process -FilePath "powershell" -ArgumentList @(
        "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", $sampler,
        "-OutFile", $sampleFile
    ) -WindowStyle Hidden -PassThru
}

$bodyObj = @{
    model  = $Model
    prompt = "Explain gravity in one short paragraph with enough detail to use GPU."
    stream = $false
    options = @{ num_predict = $NumPredict; temperature = 0.2 }
}
$body = $bodyObj | ConvertTo-Json -Depth 5 -Compress
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$resp = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/generate" -Method Post -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -ContentType "application/json; charset=utf-8" -TimeoutSec 180
$sw.Stop()
Start-Sleep 1
if ($sp -and -not $sp.HasExited) { Stop-Process -Id $sp.Id -Force -ErrorAction SilentlyContinue }

$decode = if ($resp.eval_duration -gt 0) { [math]::Round($resp.eval_count / ($resp.eval_duration / 1e9), 2) } else { 0 }
$report = @()
$report += "decode_tok_s=$decode wall_s=$([math]::Round($sw.Elapsed.TotalSeconds,2))"
$report += "=== nvidia-smi samples ==="
if (Test-Path $sampleFile) { $report += (Get-Content $sampleFile) } else { $report += "(no samples — Task Manager 3D can stay at 0% while CUDA is busy)" }
$report += "=== ollama ps ==="
$report += (ollama ps 2>&1 | Out-String)
$reportText = $report -join "`n"
$reportText | Set-Content $log -Encoding UTF8
Write-Host $reportText
Write-Host "Wrote $log"
