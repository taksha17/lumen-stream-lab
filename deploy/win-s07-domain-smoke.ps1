$ErrorActionPreference = "Stop"
$env:OLLAMA_MODELS = "D:\ollama\models"
$ollama = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
. (Join-Path $PSScriptRoot "win-router-lib.ps1")
try { $null = Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 3 } catch {
  Start-Process $ollama -ArgumentList "serve" -WindowStyle Hidden
  Start-Sleep 6
}
function Gen([string]$model, [string]$prompt) {
  $payload = New-OllamaGeneratePayload $model $prompt @{ num_predict = 80; temperature = 0 }
  $body = $payload | ConvertTo-Json -Depth 5 -Compress
  $r = Invoke-RestMethod http://127.0.0.1:11434/api/generate -Method Post -Body ([Text.Encoding]::UTF8.GetBytes($body)) -ContentType "application/json; charset=utf-8" -TimeoutSec 180
  Write-Host "=== $model :: $prompt ==="
  Write-Host $r.response
  Write-Host ""
}
Gen "qwen2.5-3b-lumen" "Is Lumen Stream Lab related to Laravel Lumen?"
Gen "qwen2.5-3b-lumen" "What is Lumen Stream Lab?"
Gen "qwen2.5-3b-lumen" "When should Lumen route to a 1B vs 3B vs 7B model?"
Gen "llama3.2:3b" "Is Lumen Stream Lab related to Laravel Lumen?"
