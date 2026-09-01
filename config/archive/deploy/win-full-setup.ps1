# Full remote setup - Ollama, PyTorch, baseline benchmark
# Run: powershell -ExecutionPolicy Bypass -File D:\lumen-stream-lab\deploy\win-full-setup.ps1
param(
    [string]$LabRoot = "D:\lumen-stream-lab",
    [string]$Model = "llama3.2:3b",
    [switch]$SkipOllamaPull,
    [switch]$SkipPyTorch
)

$ErrorActionPreference = "Continue"
$LogFile = Join-Path $LabRoot "results\setup-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
New-Item -ItemType Directory -Force -Path (Split-Path $LogFile) | Out-Null

function Log($msg) {
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

Log "=== Lumen Full Setup ==="
Log "LabRoot: $LabRoot"

# --- OLLAMA_MODELS on D: ---
$ollamaModels = "D:\ollama\models"
New-Item -ItemType Directory -Force -Path $ollamaModels | Out-Null
[System.Environment]::SetEnvironmentVariable("OLLAMA_MODELS", $ollamaModels, "User")
$env:OLLAMA_MODELS = $ollamaModels
Log "OLLAMA_MODELS=$ollamaModels"

# --- Find ollama.exe ---
$ollamaExe = (Get-Command ollama -ErrorAction SilentlyContinue).Source
if (-not $ollamaExe) {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
        "$env:ProgramFiles\Ollama\ollama.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { $ollamaExe = $c; break }
    }
}

if ($ollamaExe) {
    Log "Ollama: $ollamaExe"

    # Kill stale ollama if hung
    Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep 2

    # Start serve in background
    $serveArgs = "serve"
    Log "Starting: $ollamaExe serve"
    Start-Process -FilePath $ollamaExe -ArgumentList $serveArgs -WindowStyle Hidden
    Start-Sleep 8

    # Wait for API
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        try {
            $r = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3 -ErrorAction Stop
            $ready = $true
            Log "Ollama API ready (attempt $($i+1))"
            break
        } catch {
            Start-Sleep 2
        }
    }

    if (-not $ready) {
        Log "WARN: Ollama API not ready - may need desktop session"
    } else {
        if (-not $SkipOllamaPull) {
            Log "Pulling model: $Model (this may take several minutes)..."
            & $ollamaExe pull $Model 2>&1 | ForEach-Object { Log $_ }
            Log "Pull complete"
        }
    }
} else {
    Log "WARN: ollama.exe not found"
}

# --- PyTorch + CUDA ---
if (-not $SkipPyTorch) {
    Log "Installing PyTorch with CUDA 12.1..."
    python -m pip install --upgrade pip 2>&1 | ForEach-Object { Log $_ }
    python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 2>&1 | ForEach-Object { Log $_ }
    $cudaCheck = python -c "import torch; print('cuda=', torch.cuda.is_available()); print('device=', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')" 2>&1
    $cudaCheck | ForEach-Object { Log $_ }
}

# --- Re-run probe ---
Log "Updating hardware.json..."
& "$LabRoot\deploy\win-probe.ps1" -LabRoot $LabRoot

# --- Baseline benchmark if Ollama ready ---
try {
    $null = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3
    Log "Running baseline benchmark..."
    & "$LabRoot\deploy\win-bench.ps1" -Model $Model -Runs 3 -Warmup 1 2>&1 | ForEach-Object { Log $_ }
} catch {
    Log "Skipping benchmark - Ollama not available"
}

Log "=== Full setup done. Log: $LogFile ==="
