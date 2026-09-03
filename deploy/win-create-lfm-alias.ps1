# Create Ollama alias lfm-balanced -> LFM 2.5-2.6B Q4
# Important: do NOT set TEMPLATE — inherit ChatML/think template from the source model.
# Overriding with "{{ .Prompt }}" breaks think/answer structure and floods meta text.
param(
    [string]$LabRoot = "D:\lumen-stream-lab",
    [string]$SourceModel = "oamazonasgabriel/lfm2.5-2.6b:q4_k_m-8gbGPU",
    [string]$AliasName = "lfm-balanced",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$env:OLLAMA_MODELS = "D:\ollama\models"
$ollamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"

function Ensure-Ollama {
    try { $null = Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 5; return } catch {}
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

if ((Test-ModelExists $AliasName) -and -not $Force) {
    Write-Host "Alias $AliasName already exists - skip (pass -Force to recreate)" -ForegroundColor Green
    exit 0
}

$sourceBase = ($SourceModel -split ':')[0]
if (-not (Test-ModelExists $SourceModel) -and -not (Test-ModelExists $sourceBase)) {
    Write-Host "Pulling $SourceModel ..." -ForegroundColor Cyan
    $pull = Start-Process -FilePath $ollamaExe -ArgumentList "pull", $SourceModel -Wait -PassThru -NoNewWindow
    if ($pull.ExitCode -ne 0) { throw "pull failed exit $($pull.ExitCode)" }
}

# Inherit TEMPLATE/LICENSE from source. Only override SYSTEM + a few params.
$modelfile = @"
FROM $SourceModel
PARAMETER temperature 0.5
PARAMETER num_predict 192
PARAMETER top_p 0.9
SYSTEM """You are a concise assistant. Answer the user's question directly in plain language. Do not narrate your analysis, plan, or internal reasoning. Prefer short sentences. If steps are needed, use a brief numbered list and end with the final answer."""
"@
$mfPath = Join-Path $LabRoot "deploy\lfm-balanced.Modelfile"
$utf8 = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($mfPath, $modelfile.TrimStart() + "`n", $utf8)

if (Test-ModelExists $AliasName) {
    Write-Host "Removing old alias $AliasName for recreate ..." -ForegroundColor Yellow
    $oldEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $ollamaExe rm $AliasName 2>&1 | Out-Null
    $ErrorActionPreference = $oldEap
    Start-Sleep 1
}

Write-Host "Creating alias $AliasName (inherit source TEMPLATE) ..." -ForegroundColor Cyan
$create = Start-Process -FilePath $ollamaExe -ArgumentList "create", $AliasName, "-f", $mfPath -Wait -PassThru -NoNewWindow
if ($create.ExitCode -ne 0 -and -not (Test-ModelExists $AliasName)) {
    throw "create failed exit $($create.ExitCode)"
}

# Verify template was inherited (must not be bare {{ .Prompt }})
$showBody = @{ model = $AliasName } | ConvertTo-Json
$show = Invoke-RestMethod http://127.0.0.1:11434/api/show -Method Post -Body $showBody -ContentType "application/json" -TimeoutSec 60
$tmpl = [string]$show.template
if ($tmpl -match '^\s*\{\{\s*\.Prompt\s*\}\}\s*$') {
    throw "Alias TEMPLATE collapsed to bare Prompt placeholder - recreate from source failed"
}
if ($tmpl -notmatch 'im_start|think') {
    Write-Host "WARN: template may not be full ChatML (len=$($tmpl.Length))" -ForegroundColor Yellow
} else {
    Write-Host "OK: inherited ChatML/think template (len=$($tmpl.Length))" -ForegroundColor Green
}

Write-Host "OK: ollama run $AliasName" -ForegroundColor Green
