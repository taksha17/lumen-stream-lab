# Optional: Hermes Agent + Lumen on Windows reference lab
# Does NOT install full hermes-agent repo (large) — prepares Ollama-native helper + prints config.
param(
    [string]$LabRoot = "D:\lumen-stream-lab",
    [switch]$InstallNative
)

$ErrorActionPreference = "Continue"
Write-Host "=== Hermes + Lumen setup (optional) ===" -ForegroundColor Cyan

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "Python not found. Install Python 3.10+ and re-run." -ForegroundColor Yellow
    exit 1
}
Write-Host "Python: $($py.Source)"

if ($InstallNative) {
    Write-Host "Installing hermes-ollama-native (pip)..." -ForegroundColor DarkGray
    python -m pip install --upgrade hermes-ollama-native
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK. Set: `$env:HERMES_OLLAMA_NATIVE = '1' before starting Hermes." -ForegroundColor Green
    } else {
        Write-Host "pip install failed — install manually: pip install hermes-ollama-native" -ForegroundColor Yellow
    }
} else {
    Write-Host "Skip pip install (pass -InstallNative to install hermes-ollama-native)." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "1) Start Lumen gateway (routes each prompt to best tier):" -ForegroundColor Cyan
Write-Host "   cd $LabRoot"
Write-Host "   python lumen.py probe"
Write-Host "   python scripts\lumen_gateway.py --port 8080"
Write-Host ""
Write-Host "2) Hermes Agent: https://github.com/NousResearch/hermes-agent" -ForegroundColor Cyan
Write-Host "   Use separate Ollama models per profile, or call Lumen /v1/plan before each generate."
Write-Host ""
Write-Host "3) Suggested Hermes local models (Ollama):" -ForegroundColor Cyan
Write-Host "   fast / utility  -> llama3.2:1b"
Write-Host "   general agent   -> lfm-balanced  (deploy\win-create-lfm-alias.ps1)"
Write-Host "   domain / docs   -> qwen2.5-3b-lumen"
Write-Host "   long context    -> qwen2.5-7b-lumen  (opt-in quality tier)"
Write-Host ""
Write-Host "4) Docs: docs\AGENT-INTEGRATION.md" -ForegroundColor Green
