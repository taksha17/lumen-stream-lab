# Lumen Stream Lab — Windows setup on D: drive
# Run: powershell -ExecutionPolicy Bypass -File D:\lumen-stream-lab\deploy\win-setup.ps1

$ErrorActionPreference = "Stop"
$LabRoot = if ($PSScriptRoot) { Split-Path $PSScriptRoot -Parent } else { "D:\lumen-stream-lab" }

Write-Host "=== Lumen Stream Lab Setup ===" -ForegroundColor Cyan
Write-Host "Root: $LabRoot"

# --- Disk check (D: drive) ---
$drive = (Split-Path $LabRoot -Qualifier)  # e.g. D:
if (-not (Test-Path $drive)) {
    Write-Warning "Drive $drive not found. Using current location."
    $drive = "D:"
}

$disk = Get-PSDrive ($drive.TrimEnd(':')) -ErrorAction SilentlyContinue
if ($disk) {
    $freeGB = [math]::Round($disk.Free / 1GB, 1)
    Write-Host "Free space on ${drive}: ${freeGB} GB" -ForegroundColor Green
    if ($freeGB -lt 20) {
        Write-Warning "Less than 20 GB free - large models will not fit."
    }
} else {
    Write-Warning "Could not read free space for $drive"
}

# --- GPU check ---
Write-Host "`n--- GPU ---" -ForegroundColor Yellow
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
} else {
    Write-Warning "nvidia-smi not found. Install NVIDIA drivers for GTX 1650."
}

# --- Python check ---
Write-Host "`n--- Python ---" -ForegroundColor Yellow
if (Get-Command python -ErrorAction SilentlyContinue) {
    python --version
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    python3 --version
} else {
    Write-Warning "Python not found. Install from python.org for scripts/compare.py"
}

# --- Ollama check (fastest baseline backend) ---
Write-Host "`n--- Ollama ---" -ForegroundColor Yellow
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    ollama --version
    Write-Host "Pull a small baseline model:" -ForegroundColor DarkGray
    Write-Host "  ollama pull llama3.2:3b" -ForegroundColor DarkGray
} else {
    Write-Host "Ollama not installed." -ForegroundColor Yellow
    Write-Host "Install: https://ollama.com/download/windows" -ForegroundColor DarkGray
    Write-Host "Set OLLAMA_MODELS to D: if you want models on D drive:" -ForegroundColor DarkGray
    Write-Host "  Set env: OLLAMA_MODELS=D:\ollama\models" -ForegroundColor DarkGray
}

# --- Write hardware.json ---
Write-Host "`n--- Writing hardware.json ---" -ForegroundColor Yellow
& "$LabRoot\deploy\win-probe.ps1" -LabRoot $LabRoot

# --- Create results dir ---
New-Item -ItemType Directory -Force -Path "$LabRoot\results" | Out-Null

# --- Copy config template ---
$cfgExample = "$LabRoot\lumen.yaml.example"
$cfg = "$LabRoot\lumen.yaml"
if ((Test-Path $cfgExample) -and -not (Test-Path $cfg)) {
    Copy-Item $cfgExample $cfg
    Write-Host "Created lumen.yaml from example"
}

Write-Host "`n=== Setup complete ===" -ForegroundColor Green
Write-Host "Next steps:"
Write-Host "  1. nvidia-smi                    # confirm GTX 1650"
Write-Host "  2. ollama pull llama3.2:3b        # baseline model on D: (optional env)"
Write-Host "  3. cd $LabRoot"
Write-Host "  4. ollama run llama3.2:3b         # first chat test"
Write-Host "  5. Record tok/s in RESULTS.md"
Write-Host ""
Write-Host "Docs: VISION.md (goal) | ARCHITECTURE.md (plan) | PLAYBOOK.md (reference)"
