# Publish Lumen domain GGUF to Hugging Face Hub
# Usage:
#   set HF_TOKEN=hf_...   (Windows)  OR  export HF_TOKEN=hf_...
#   powershell -File deploy\win-publish-hf.ps1 -RepoId youruser/qwen2.5-3b-lumen
param(
    [string]$LabRoot = "D:\lumen-stream-lab",
    [string]$RepoId = "",
    [string]$Gguf = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
. "$LabRoot\deploy\win-env-d.ps1"

if (-not $Gguf) {
    $Gguf = "$LabRoot\exports\qwen2.5-3b-lumen-s07.q4_k_m.gguf"
}
if (-not (Test-Path $Gguf)) {
    Write-Host "GGUF not found: $Gguf" -ForegroundColor Red
    Write-Host "Run: powershell -File deploy\win-post-s07.ps1" -ForegroundColor Yellow
    exit 1
}

if (-not $RepoId) {
    Write-Host "Set -RepoId your-hf-username/qwen2.5-3b-lumen" -ForegroundColor Yellow
    Write-Host "Example: powershell -File deploy\win-publish-hf.ps1 -RepoId taksha17/qwen2.5-3b-lumen"
    exit 1
}

if (-not $env:HF_TOKEN) {
    Write-Host "HF_TOKEN not set. Create at https://huggingface.co/settings/tokens" -ForegroundColor Red
    exit 1
}

$hfCli = Get-Command huggingface-cli -ErrorAction SilentlyContinue
if (-not $hfCli) {
    Write-Host "Installing huggingface_hub CLI ..." -ForegroundColor DarkGray
    python -m pip install -U "huggingface_hub[cli]"
}

$readme = @"
---
license: apache-2.0
base_model: Qwen/Qwen2.5-3B-Instruct
tags:
  - lumen-stream-lab
  - gguf
  - ollama
---

# qwen2.5-3b-lumen (S07 domain fine-tune)

Domain fine-tune for [Lumen Stream Lab](https://github.com/taksha17/lumen-stream-lab) hybrid router.

## Ollama

``````bash
ollama create qwen2.5-3b-lumen -f Modelfile
``````

Modelfile:

``````
FROM ./qwen2.5-3b-lumen-s07.q4_k_m.gguf
PARAMETER temperature 0.7
``````

Trained with Soup `config/soup/soup-3b-stream-s07.yaml` on reference GTX 1650 lab.
"@

$stage = Join-Path $env:TEMP "lumen-hf-publish"
Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $stage | Out-Null
Copy-Item $Gguf (Join-Path $stage "qwen2.5-3b-lumen-s07.q4_k_m.gguf")
Set-Content (Join-Path $stage "README.md") $readme -Encoding UTF8
@"
FROM ./qwen2.5-3b-lumen-s07.q4_k_m.gguf
PARAMETER temperature 0.7
"@ | Set-Content (Join-Path $stage "Modelfile") -Encoding UTF8

Write-Host "Publishing to huggingface.co/$RepoId" -ForegroundColor Cyan
Write-Host "GGUF: $Gguf ($([math]::Round((Get-Item $Gguf).Length/1GB, 2)) GB)"

if ($DryRun) {
    Write-Host "Dry run - staged at $stage" -ForegroundColor Yellow
    exit 0
}

huggingface-cli upload $RepoId $stage . --repo-type model
Write-Host "Done: https://huggingface.co/$RepoId" -ForegroundColor Green
