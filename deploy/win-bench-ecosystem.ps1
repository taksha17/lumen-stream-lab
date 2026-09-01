# Re-bench Lumen orchestration + backend shootout + emit ecosystem comparison JSON
# Usage: powershell -File deploy\win-bench-ecosystem.ps1
param(
    [string]$LabRoot = "D:\lumen-stream-lab"
)

$ErrorActionPreference = "Stop"
$outDir = Join-Path $LabRoot "results\ecosystem"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"

Write-Host "=== Ecosystem re-bench ($stamp) ===" -ForegroundColor Cyan

# 1) Always-3B baseline
& "$LabRoot\deploy\win-bench-with-serve.ps1" -Model llama3.2:3b -Runs 3 -Warmup 1 `
    -OutFile (Join-Path $outDir "baseline-always-3b.json")

# 2) Lumen hybrid orchestration mean
& "$LabRoot\deploy\win-orchestration-bench.ps1"
$orchFiles = Get-ChildItem (Join-Path $LabRoot "results\orchestration-bench-*.json") | Sort-Object LastWriteTime -Descending
$orch = Get-Content $orchFiles[0].FullName -Raw | ConvertFrom-Json

# 3) Ollama vs llama.cpp (same 3B weights)
& "$LabRoot\deploy\win-bench-llamacpp-vs-ollama.ps1" -Model llama3.2:3b

$baseline = (Get-Content (Join-Path $outDir "baseline-always-3b.json") -Raw | ConvertFrom-Json).median_decode_tok_s
$refPath = Join-Path $LabRoot "hardware\reference-lab.json"
$canonicalBase = 48.38
if (Test-Path $refPath) {
    $ref = Get-Content $refPath -Raw | ConvertFrom-Json
    $canonicalBase = [double]$ref.measured_baselines.'llama3.2:3b_tok_s'
}
$orchMean = [double]$orch.mean_decode_tok_s
$gainCanonical = if ($canonicalBase -gt 0) { ($orchMean - $canonicalBase) / $canonicalBase } else { 0 }
$gainFresh = if ($baseline -gt 0) { ($orchMean - $baseline) / $baseline } else { 0 }

$comparison = [ordered]@{
    probed_at = (Get-Date).ToString("o")
    hardware = (nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>&1 | Out-String).Trim()
    baseline_fresh_bench_tok_s = $baseline
    canonical_baseline_3b_tok_s = $canonicalBase
    lumen_orchestration_mean_tok_s = [math]::Round($orchMean, 2)
    lumen_gain_vs_canonical_pct = [math]::Round($gainCanonical * 100, 1)
    lumen_gain_vs_fresh_bench_pct = [math]::Round($gainFresh * 100, 1)
    lumen_pass_40pct = ($gainCanonical -ge 0.40)
    orchestration_report = $orchFiles[0].Name
    notes = @{
        lumen = "Hybrid router: 1B fast / LFM general / qwen-lumen domain / 7B quality"
        ollama_always_3b = "Single-model policy (common default)"
        llamacpp = "See results/bench-llamacpp-vs-ollama-*.json from shootout script"
    }
}
$outPath = Join-Path $outDir "ecosystem-comparison-$stamp.json"
$comparison | ConvertTo-Json -Depth 5 | Set-Content $outPath -Encoding UTF8
Write-Host "Wrote $outPath" -ForegroundColor Green
Write-Host ("Lumen: {0} tok/s vs canonical {1} tok/s = +{2}% ({3})" -f $orchMean, $canonicalBase, [math]::Round($gainCanonical*100,1), $(if ($gainCanonical -ge 0.40) {"PASS"} else {"FAIL"}))
