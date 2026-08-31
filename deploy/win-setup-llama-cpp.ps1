# Download prebuilt llama.cpp Windows binaries (llama-quantize) — no MSVC needed
$ErrorActionPreference = "Stop"
$ToolsDir = "D:\lumen-stream-lab\tools\llama-cpp-bin"
$LlamaRepo = "$env:USERPROFILE\.soup\llama.cpp"
$BinDest = Join-Path $LlamaRepo "build\bin\Release"

New-Item -ItemType Directory -Path $ToolsDir -Force | Out-Null
New-Item -ItemType Directory -Path $BinDest -Force | Out-Null

if (Test-Path (Join-Path $BinDest "llama-quantize.exe")) {
    Write-Host "llama-quantize.exe already present at $BinDest"
    exit 0
}

# CUDA 12.x build for GTX 1650 + driver 581; fallback to AVX2 CPU build
$Tag = "b6927"
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

Expand-Archive -Path $ZipPath -DestinationPath $ToolsDir -Force
$quantize = Get-ChildItem -Path $ToolsDir -Recurse -Filter "llama-quantize.exe" | Select-Object -First 1
if (-not $quantize) { throw "llama-quantize.exe not found in archive" }

Copy-Item $quantize.FullName (Join-Path $BinDest "llama-quantize.exe") -Force
# copy sibling DLLs if any
Get-ChildItem (Split-Path $quantize.FullName) -Filter "*.dll" | ForEach-Object {
    Copy-Item $_.FullName $BinDest -Force -ErrorAction SilentlyContinue
}
Write-Host "Installed llama-quantize.exe -> $BinDest" -ForegroundColor Green
