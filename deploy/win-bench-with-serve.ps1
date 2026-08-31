# Start Ollama if needed, then run API benchmark in one session (survives SSH)
param(
    [string]$Model = "llama3.2:3b",
    [int]$Runs = 5,
    [int]$Warmup = 2,
    [string]$OutFile = "D:\lumen-stream-lab\results\baseline.json"
)

$ollamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
$env:OLLAMA_MODELS = "D:\ollama\models"

function Ensure-Ollama {
    try {
        $null = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3
        return
    } catch {}
    Write-Host "Starting Ollama..."
    Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep 2
    Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep 2
        try {
            $null = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3
            Write-Host "Ollama ready."
            return
        } catch {}
    }
    throw "Ollama failed to start"
}

Ensure-Ollama
& "$PSScriptRoot\win-bench-api.ps1" -Model $Model -Runs $Runs -Warmup $Warmup -OutFile $OutFile
