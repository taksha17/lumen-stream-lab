# Publish Lumen domain GGUF to Hugging Face Hub
# Usage:
#   set HF_TOKEN=hf_...
#   powershell -File deploy\win-publish-hf.ps1 -RepoId youruser/qwen2.5-3b-lumen
#   powershell -File deploy\win-publish-hf.ps1 -Variant 7b -RepoId youruser/qwen2.5-7b-lumen
param(
    [string]$LabRoot = "D:\lumen-stream-lab",
    [ValidateSet("3b", "7b")]
    [string]$Variant = "3b",
    [string]$RepoId = "",
    [string]$Gguf = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
. "$LabRoot\deploy\win-env-d.ps1"

$profiles = @{
    "3b" = @{
        default_gguf = "$LabRoot\exports\qwen2.5-3b-lumen-s07.q4_k_m.gguf"
        artifact     = "qwen2.5-3b-lumen-s07.q4_k_m.gguf"
        ollama_name  = "qwen2.5-3b-lumen"
        base_model   = "Qwen/Qwen2.5-3B-Instruct"
        title        = "qwen2.5-3b-lumen (S07 domain fine-tune)"
        soup         = "config/soup/soup-3b-stream-s07.yaml"
        post_script  = "deploy\win-post-s07.ps1"
    }
    "7b" = @{
        default_gguf = "$LabRoot\exports\qwen2.5-7b-lumen-s06.q4_k_m.gguf"
        artifact     = "qwen2.5-7b-lumen-s06.q4_k_m.gguf"
        ollama_name  = "qwen2.5-7b-lumen"
        base_model   = "Qwen/Qwen2.5-7B-Instruct"
        title        = "qwen2.5-7b-lumen (S06 quality tier)"
        soup         = "config/soup/soup-7b-stream-s06.yaml"
        post_script  = "deploy\win-post-s07.ps1"
    }
}

$p = $profiles[$Variant]
if (-not $Gguf) { $Gguf = $p.default_gguf }
if (-not (Test-Path $Gguf)) {
    Write-Host "GGUF not found: $Gguf" -ForegroundColor Red
    Write-Host "Export first or pass -Gguf path" -ForegroundColor Yellow
    exit 1
}

if (-not $RepoId) {
    Write-Host "Set -RepoId your-hf-username/qwen2.5-$Variant-lumen" -ForegroundColor Yellow
    Write-Host "Example: powershell -File deploy\win-publish-hf.ps1 -Variant $Variant -RepoId takshathosani17/qwen2.5-$Variant-lumen"
    exit 1
}

if (-not $env:HF_TOKEN) {
    Write-Host "HF_TOKEN not set. Create at https://huggingface.co/settings/tokens" -ForegroundColor Red
    exit 1
}

$hfCli = Get-Command hf -ErrorAction SilentlyContinue
if (-not $hfCli) {
    Write-Host "Installing huggingface_hub CLI ..." -ForegroundColor DarkGray
    python -m pip install -U "huggingface_hub[cli]"
    $hfCli = Get-Command hf -ErrorAction SilentlyContinue
}
if (-not $hfCli) {
    Write-Host "hf CLI not found after install." -ForegroundColor Red
    exit 1
}

$artifact = $p.artifact
$ollama = $p.ollama_name
$readme = @"
---
license: apache-2.0
base_model: $($p.base_model)
tags:
  - lumen-stream-lab
  - gguf
  - ollama
---

# $($p.title)

Domain/quality tier model for [Lumen Stream Lab](https://github.com/taksha17/lumen-stream-lab) hybrid router.

## Ollama

``````bash
ollama create $ollama -f Modelfile
``````

Modelfile:

``````
FROM ./$artifact
PARAMETER temperature 0.7
``````

Trained with Soup ``$($p.soup)`` on reference GTX 1650 lab (~10 tok/s quality tier).
"@

$stage = Join-Path $env:TEMP "lumen-hf-publish-$Variant"
Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $stage | Out-Null
Copy-Item $Gguf (Join-Path $stage $artifact)
Set-Content (Join-Path $stage "README.md") $readme -Encoding UTF8
@"
FROM ./$artifact
PARAMETER temperature 0.7
"@ | Set-Content (Join-Path $stage "Modelfile") -Encoding UTF8

Write-Host "Publishing to huggingface.co/$RepoId ($Variant)" -ForegroundColor Cyan
Write-Host "GGUF: $Gguf ($([math]::Round((Get-Item $Gguf).Length/1GB, 2)) GB)"

if ($DryRun) {
    Write-Host "Dry run - staged at $stage" -ForegroundColor Yellow
    exit 0
}

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

& hf upload $RepoId $stage . --repo-type model
if ($LASTEXITCODE -ne 0) {
    Write-Host "Upload failed (exit $LASTEXITCODE). Staged at $stage" -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "Done: https://huggingface.co/$RepoId" -ForegroundColor Green
