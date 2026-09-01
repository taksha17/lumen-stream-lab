# Domain smoke for fast-tier candidates (SmolLM2, Gemma3 1B)
# Usage: powershell -File deploy\win-fast-tier-domain-smoke.ps1
param(
    [string[]]$Models = @(
        "smollm2:1.7b-instruct-q4_K_M",
        "gemma3:1b-it-qat",
        "llama3.2:1b"
    )
)

$ErrorActionPreference = "Stop"
$env:OLLAMA_MODELS = "D:\ollama\models"
$ollama = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
. (Join-Path $PSScriptRoot "win-router-lib.ps1")

try { $null = Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 3 } catch {
    Start-Process $ollama -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep 6
}

function Invoke-Gen([string]$model, [string]$prompt) {
    $payload = New-OllamaGeneratePayload $model $prompt @{ num_predict = 120; temperature = 0 }
    $body = $payload | ConvertTo-Json -Depth 5 -Compress
    $r = Invoke-RestMethod http://127.0.0.1:11434/api/generate -Method Post `
        -Body ([Text.Encoding]::UTF8.GetBytes($body)) `
        -ContentType "application/json; charset=utf-8" -TimeoutSec 180
    return $r.response
}

function Test-LaravelOk([string]$text) {
    $l = $text.ToLower()
    if ($l -match 'not the laravel php|not related to laravel|is not the laravel|unrelated to laravel|not the laravel php microframework') { return $true }
    if ($l -match 'laravel package' -and $l -match 'not|no') { return $true }
    if ($l -match 'no[,\.\s].*laravel') { return $true }
    if ($l -match '^\s*yes[,\s].*related to laravel' -and $l -notmatch 'not the laravel') { return $false }
    return $false
}

function Test-DefinitionOk([string]$text) {
    $l = $text.ToLower()
    if ($l -match 'telecom company|liquid ai company|video streaming cdn|data-driven visual|laravel package|lumen stream platform') { return $false }
    return ($l -match 'orchestrat|ollama|soup|hybrid router')
}

function Test-RoutingOk([string]$text) {
    $l = $text.ToLower()
    return ($l -match '1b|fast' -and $l -match 'balanced|3b|lfm|qwen')
}

$checks = @(
    @{ id = "E11"; prompt = "Is Lumen Stream Lab related to Laravel Lumen?"; test = { Test-LaravelOk $args[0] } },
    @{ id = "E12"; prompt = "What is Lumen Stream Lab?"; test = { Test-DefinitionOk $args[0] } },
    @{ id = "E05"; prompt = "When should Lumen route to a 1B vs 3B vs 7B model?"; test = { Test-RoutingOk $args[0] } }
)

$summary = [System.Collections.Generic.List[object]]::new()
$anyPromote = $false

foreach ($model in $Models) {
    Write-Host "`n=== Fast-tier candidate: $model ===" -ForegroundColor Cyan
    $fails = @()
    foreach ($c in $checks) {
        try {
            $resp = Invoke-Gen $model $c.prompt
        } catch {
            Write-Host "  $($c.id): ERROR - $($_.Exception.Message)" -ForegroundColor Red
            $fails += $c.id
            continue
        }
        $ok = & $c.test $resp
        Write-Host "  $($c.id): $(if ($ok) { 'PASS' } else { 'FAIL' })" -ForegroundColor $(if ($ok) { 'Green' } else { 'Red' })
        if (-not $ok) { $fails += $c.id }
    }
    $pass = ($fails.Count -eq 0)
    if ($pass -and $model -ne "llama3.2:1b") { $anyPromote = $true }
    [void]$summary.Add([pscustomobject]@{
        model = $model
        domain_gate = if ($pass) { "PASS" } else { "FAIL ($($fails -join ', '))" }
        promote_candidate = $pass
    })
    Write-Host "  Overall: $(if ($pass) { 'PASS - candidate for fast tier' } else { "FAIL ($($fails -join ', '))" })" -ForegroundColor $(if ($pass) { 'Green' } else { 'Yellow' })
}

$outPath = "D:\lumen-stream-lab\results\fast-tier-candidate-gate.json"
$summary | ConvertTo-Json -Depth 4 | Set-Content $outPath -Encoding UTF8
Write-Host "`nWrote $outPath" -ForegroundColor Green

if ($anyPromote) {
    Write-Host "At least one new model passed all domain checks - consider updating fast tier in lumen_router.py / win-router-lib.ps1" -ForegroundColor Cyan
}
exit 0
