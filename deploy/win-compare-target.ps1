# Compare hybrid orchestration vs always-3B baseline (+40% lab target)
param(
    [string]$LabRoot = "D:\lumen-stream-lab",
    [string]$BenchFile = "",
    [double]$Baseline3B = 48.38,
    [double]$MinGain = 0.40
)

$ErrorActionPreference = "Stop"
$targetTokS = [math]::Round($Baseline3B * (1 + $MinGain), 2)

function Test-Gain([double]$baseline, [double]$optimized, [double]$minGain) {
    $gain = ($optimized - $baseline) / $baseline
    return @{
        gain_pct = [math]::Round($gain * 100, 1)
        need_tok_s = [math]::Round($baseline * (1 + $minGain), 2)
        pass = ($gain -ge $minGain)
    }
}

Write-Host "=== Lumen +40% Target Check ===" -ForegroundColor Cyan
Write-Host "Baseline: always llama3.2:3b @ $Baseline3B tok/s"
Write-Host "Target:   >= $targetTokS tok/s (+$($MinGain*100)%)" -ForegroundColor Cyan
Write-Host ""

if (-not $BenchFile) {
    $latest = Get-ChildItem (Join-Path $LabRoot "results\orchestration-bench-*.json") -EA SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latest) { $BenchFile = $latest.FullName }
}

if ($BenchFile -and (Test-Path $BenchFile)) {
    $bench = Get-Content $BenchFile -Raw | ConvertFrom-Json
    $mean = [double]$bench.mean_decode_tok_s
    $r = Test-Gain $Baseline3B $mean $MinGain
    Write-Host "--- PRIMARY: hybrid orchestration (live) ---" -ForegroundColor Yellow
    Write-Host "  Source: $BenchFile"
    Write-Host ("  Mean auto-route: {0} tok/s  +{1}%  [{2}]" -f $mean, $r.gain_pct, $(if ($r.pass) { "PASS" } else { "FAIL" }))
    Write-Host ""
} else {
    Write-Host "No orchestration bench yet. Run: deploy\win-orchestration-bench.ps1" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "--- Reference: single-tool baselines ---" -ForegroundColor Yellow
foreach ($pair in @(
    @{ name = "llama3.2:3b (baseline)"; opt = 48.38 },
    @{ name = "LFM 2.5-2.6B"; opt = 65.20 },
    @{ name = "qwen2.5-3b-lumen"; opt = 56.53 },
    @{ name = "llama3.2:1b"; opt = 96.87 }
)) {
    $r = Test-Gain $Baseline3B $pair.opt $MinGain
    Write-Host ("  {0,-28} {1,6} tok/s  +{2,5}%  [{3}]" -f $pair.name, $pair.opt, $r.gain_pct, $(if ($r.pass) { "PASS" } else { "FAIL" }))
}

Write-Host ""
Write-Host "Quality 7B (~10 tok/s) is opt-in via -Tier quality or prompts >50 words."
Write-Host "Hybrid routes Lumen-domain prompts to qwen2.5-3b-lumen; general balanced uses LFM."

if ($BenchFile -and (Test-Path $BenchFile) -and -not $r.pass) { exit 1 }
exit 0
