# Domain smoke with simple keyword gate (exit 1 if answers look wrong)
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
    @{
        id = "E11"
        prompt = "Is Lumen Stream Lab related to Laravel Lumen?"
        test = { Test-LaravelOk $args[0] }
    },
    @{
        id = "E12"
        prompt = "What is Lumen Stream Lab?"
        test = { Test-DefinitionOk $args[0] }
    },
    @{
        id = "E05"
        prompt = "When should Lumen route to a 1B vs 3B vs 7B model?"
        test = { Test-RoutingOk $args[0] }
    }
)

$failures = @()
Write-Host "=== Domain smoke gate (qwen2.5-3b-lumen) ===" -ForegroundColor Cyan

foreach ($c in $checks) {
    $resp = Invoke-Gen "qwen2.5-3b-lumen" $c.prompt
    $ok = & $c.test $resp
    Write-Host "`n--- $($c.id): $($c.prompt) ---" -ForegroundColor Yellow
    Write-Host $resp
    Write-Host "GATE: $(if ($ok) { 'PASS' } else { 'FAIL' })" -ForegroundColor $(if ($ok) { 'Green' } else { 'Red' })
    if (-not $ok) { $failures += $c.id }
}

Write-Host "`n=== Domain gate: $(if ($failures.Count -eq 0) { 'PASS' } else { "FAIL ($($failures -join ', '))" }) ===" -ForegroundColor $(if ($failures.Count -eq 0) { 'Green' } else { 'Red' })
if ($failures.Count -gt 0) { exit 1 }
exit 0
