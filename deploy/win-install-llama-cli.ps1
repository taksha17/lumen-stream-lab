# Install llama-cli + llama-quantize from prebuilt llama.cpp Windows release
param(
    [string]$LabRoot = "D:\lumen-stream-lab",
    [string]$Tag = "b6927"
)

$ErrorActionPreference = "Stop"
$ToolsDir = Join-Path $LabRoot "tools\llama-cpp-bin"
$BinDest = Join-Path $ToolsDir "bin"
New-Item -ItemType Directory -Path $BinDest -Force | Out-Null

$need = @("llama-cli.exe", "llama-quantize.exe")
$haveAll = $true
foreach ($exe in $need) {
    if (-not (Test-Path (Join-Path $BinDest $exe))) { $haveAll = $false }
}
if ($haveAll) {
    Write-Host "llama.cpp tools already at $BinDest"
    exit 0
}

$Assets = @(
    "https://github.com/ggml-org/llama.cpp/releases/download/$Tag/llama-$Tag-bin-win-cuda-12.4-x64.zip",
    "https://github.com/ggml-org/llama.cpp/releases/download/$Tag/llama-$Tag-bin-win-avx2-x64.zip"
)
$ZipPath = Join-Path $ToolsDir "llama-cpp-bin.zip"
$downloaded = $false
foreach ($url in $Assets) {
    try {
        Write-Host "Downloading $url ..."
        Invoke-WebRequest -Uri $url -OutFile $ZipPath -UseBasicParsing
        $downloaded = $true
        break
    } catch {
        Write-Host "  failed: $_"
    }
}
if (-not $downloaded) { throw "Could not download llama.cpp prebuilt binaries" }

Expand-Archive -Path $ZipPath -DestinationPath (Join-Path $ToolsDir "extract") -Force
foreach ($exe in $need) {
    $found = Get-ChildItem (Join-Path $ToolsDir "extract") -Recurse -Filter $exe | Select-Object -First 1
    if (-not $found) { throw "$exe not found in archive" }
    Copy-Item $found.FullName (Join-Path $BinDest $exe) -Force
    Get-ChildItem (Split-Path $found.FullName) -Filter "*.dll" | ForEach-Object {
        Copy-Item $_.FullName $BinDest -Force -ErrorAction SilentlyContinue
    }
}

# Soup export expects quantize here too
$SoupBin = "$env:USERPROFILE\.soup\llama.cpp\build\bin\Release"
New-Item -ItemType Directory -Path $SoupBin -Force | Out-Null
Copy-Item (Join-Path $BinDest "llama-quantize.exe") (Join-Path $SoupBin "llama-quantize.exe") -Force

Write-Host "Installed llama-cli + llama-quantize -> $BinDest" -ForegroundColor Green
