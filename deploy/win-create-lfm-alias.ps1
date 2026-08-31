# Create Ollama alias lfm-balanced -> LFM 2.5-2.6B Q4
param(
    [string]$LabRoot = "D:\lumen-stream-lab",
    [string]$SourceModel = "oamazonasgabriel/lfm2.5-2.6b:q4_k_m-8gbGPU",
    [string]$AliasName = "lfm-balanced"
)

$ErrorActionPreference = "Stop"
$env:OLLAMA_MODELS = "D:\ollama\models"
$ollamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"

function Ensure-Ollama {
    try { $null = Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 5; return } catch {}
    Get-Process ollama -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue
    Start-Sleep 3
    Start-Process $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep 2
        try { $null = Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 5; return } catch {}
    }
    throw "Ollama failed to start"
}

function Test-ModelExists([string]$name) {
    $tags = Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 10
    return [bool]($tags.models | Where-Object { $_.name -eq $name -or $_.name -eq "${name}:latest" })
}

Ensure-Ollama

if (Test-ModelExists $AliasName) {
    Write-Host "Alias $AliasName already exists - skip" -ForegroundColor Green
    exit 0
}

if (-not (Test-ModelExists ($SourceModel.Split(':')[0]))) {
    Write-Host "Pulling $SourceModel ..." -ForegroundColor Cyan
    $pull = Start-Process -FilePath $ollamaExe -ArgumentList "pull", $SourceModel -Wait -PassThru -NoNewWindow
    if ($pull.ExitCode -ne 0) { throw "pull failed exit $($pull.ExitCode)" }
}

$modelfile = "FROM $SourceModel`nPARAMETER temperature 0.7`nPARAMETER num_predict 128"
$mfPath = Join-Path $LabRoot "deploy\lfm-balanced.Modelfile"
$modelfile | Set-Content $mfPath -Encoding UTF8

Write-Host "Creating alias $AliasName ..." -ForegroundColor Cyan
$create = Start-Process -FilePath $ollamaExe -ArgumentList "create", $AliasName, "-f", $mfPath -Wait -PassThru -NoNewWindow
if ($create.ExitCode -ne 0 -and -not (Test-ModelExists $AliasName)) {
    throw "create failed exit $($create.ExitCode)"
}

Write-Host "OK: ollama run $AliasName" -ForegroundColor Green
