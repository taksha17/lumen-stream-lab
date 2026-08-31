# Sample nvidia-smi to a file for a few seconds
param(
    [string]$OutFile = "D:\lumen-stream-lab\results\gpu-samples.txt",
    [int]$Count = 40,
    [int]$IntervalMs = 400
)
"" | Set-Content $OutFile -Encoding ASCII
1..$Count | ForEach-Object {
    $t = Get-Date -Format "HH:mm:ss.fff"
    $g = nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader
    Add-Content -Path $OutFile -Value "$t $g"
    Start-Sleep -Milliseconds $IntervalMs
}
