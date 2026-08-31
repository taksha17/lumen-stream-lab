# Hardware probe for Windows server laptop
param(
    [string]$LabRoot = "D:\lumen-stream-lab"
)

$out = Join-Path $LabRoot "hardware.json"

# CPU
$cpu = (Get-CimInstance Win32_Processor | Select-Object -First 1).Name
$cores = (Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors

# RAM
$ramGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)

# GPU
$gpuName = "none"
$vramMB = 0
$driver = "none"
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    $gpuLine = nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>$null | Select-Object -First 1
    if ($gpuLine) {
        $parts = $gpuLine -split ","
        $gpuName = $parts[0].Trim()
        $vramMB = [int](($parts[1] -replace "[^0-9]", ""))
        $driver = $parts[2].Trim()
    }
}

# D: drive free space
$diskFreeGB = 0
if (Test-Path "D:\") {
    $diskFreeGB = [math]::Round((Get-PSDrive D).Free / 1GB, 1)
}

$cudaAvailable = $false
if (Get-Command python -ErrorAction SilentlyContinue) {
    $cudaCheck = python -c "import torch; print(torch.cuda.is_available())" 2>$null
    $cudaAvailable = ($cudaCheck -eq "True")
}

$obj = [ordered]@{
    probed_at       = (Get-Date).ToString("o")
    hostname        = $env:COMPUTERNAME
    os              = "Windows"
    cpu             = @{ model = $cpu.Trim(); cores = $cores }
    ram_gb          = $ramGB
    gpu             = @{
        name            = $gpuName
        vram_mb         = $vramMB
        driver          = $driver
        cuda_available  = $cudaAvailable
    }
    disk            = @{
        drive           = "D:"
        free_gb         = $diskFreeGB
        lab_path        = $LabRoot
    }
    notes           = "Server laptop - Ryzen 5600H + GTX 1650 4GB target"
}

$json = $obj | ConvertTo-Json -Depth 4
Set-Content -Path $out -Value $json -Encoding UTF8

Write-Host "Wrote $out"
Write-Host $json
