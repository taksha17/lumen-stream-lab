# Sample nvidia-smi to a file. Paths passed in — no hardcoded drive letters.
param(
    [Parameter(Mandatory = $true)]
    [string]$OutFile,
    [int]$Count = 40,
    [int]$IntervalMs = 200
)
"" | Set-Content $OutFile -Encoding ASCII
1..$Count | ForEach-Object {
    $t = Get-Date -Format "HH:mm:ss.fff"
    $g = nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader
    Add-Content -Path $OutFile -Value "$t $g"
    Start-Sleep -Milliseconds $IntervalMs
}
