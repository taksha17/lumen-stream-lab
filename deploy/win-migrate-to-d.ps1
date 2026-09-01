# Migrate Soup + HuggingFace caches from C: to D:
# Run once: powershell -ExecutionPolicy Bypass -File D:\lumen-stream-lab\deploy\win-migrate-to-d.ps1

$ErrorActionPreference = "Stop"
$LabRoot = "D:\lumen-stream-lab"
$CacheRoot = "$LabRoot\cache"
$HfCache = "$CacheRoot\huggingface"
$SoupLayerCache = "$CacheRoot\soup-layer-stream"
$SoupHome = "$LabRoot\.soup"
$OllamaModels = "D:\ollama\models"

$oldSoup = Join-Path $env:USERPROFILE ".soup"
$oldHf = Join-Path $env:USERPROFILE ".cache\huggingface"
$oldLayerStream = Join-Path $oldSoup "layer-stream"

function Get-DirSizeGB($path) {
    if (-not (Test-Path $path)) { return 0 }
    $sum = (Get-ChildItem $path -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    return [math]::Round($sum / 1GB, 2)
}

Write-Host "=== Migrate caches C: -> D: ===" -ForegroundColor Cyan
Write-Host "C: free before: $([math]::Round((Get-PSDrive C).Free/1GB,1)) GB"
Write-Host "D: free before: $([math]::Round((Get-PSDrive D).Free/1GB,1)) GB"

New-Item -ItemType Directory -Force -Path $CacheRoot, $HfCache, $SoupLayerCache, $SoupHome, $OllamaModels | Out-Null

# --- Move Soup layer-stream shards (~19 GB) ---
if (Test-Path $oldLayerStream) {
    $size = Get-DirSizeGB $oldLayerStream
    Write-Host "Moving Soup layer-stream ($size GB) -> $SoupLayerCache"
    if ((Get-ChildItem $SoupLayerCache -ErrorAction SilentlyContinue | Measure-Object).Count -eq 0) {
        robocopy $oldLayerStream $SoupLayerCache /E /MOVE /R:2 /W:5 /NFL /NDL /NJH /NJS | Out-Null
    } else {
        Write-Host "  Target not empty, merging with robocopy /E"
        robocopy $oldLayerStream $SoupLayerCache /E /MOVE /R:2 /W:5 /NFL /NDL /NJH /NJS | Out-Null
    }
    if (Test-Path $oldLayerStream) { Remove-Item $oldLayerStream -Recurse -Force -ErrorAction SilentlyContinue }
}

# --- Move other .soup metadata (small) ---
foreach ($item in @("audit.jsonl", "experiments.db", "namespace_pin.db", "namespace_pin.db.lock", "spectrum")) {
    $src = Join-Path $oldSoup $item
    $dst = Join-Path $SoupHome $item
    if (Test-Path $src) {
        if (-not (Test-Path $dst)) {
            Move-Item $src $dst -Force -ErrorAction SilentlyContinue
        }
    }
}

# --- Move HuggingFace cache ---
if (Test-Path $oldHf) {
    $size = Get-DirSizeGB $oldHf
    Write-Host "Moving HuggingFace cache ($size GB) -> $HfCache"
    robocopy $oldHf $HfCache /E /MOVE /R:2 /W:5 /NFL /NDL /NJH /NJS | Out-Null
}

# --- Set permanent User environment variables ---
$vars = @{
    "HF_HOME"                      = $HfCache
    "HUGGINGFACE_HUB_CACHE"        = "$HfCache\hub"
    "TRANSFORMERS_CACHE"           = $HfCache
    "SOUP_LAYER_STREAM_CACHE_DIR"  = $SoupLayerCache
    "OLLAMA_MODELS"                = $OllamaModels
    "LUMEN_LAB_ROOT"               = $LabRoot
}
foreach ($kv in $vars.GetEnumerator()) {
    [System.Environment]::SetEnvironmentVariable($kv.Key, $kv.Value, "User")
    Set-Item -Path "env:$($kv.Key)" -Value $kv.Value
    Write-Host "Set $($kv.Key)=$($kv.Value)"
}

# --- Write env bootstrap for scripts ---
@"
# Auto-generated - source before training
`$env:HF_HOME = '$HfCache'
`$env:HUGGINGFACE_HUB_CACHE = '$HfCache\hub'
`$env:TRANSFORMERS_CACHE = '$HfCache'
`$env:SOUP_LAYER_STREAM_CACHE_DIR = '$SoupLayerCache'
`$env:OLLAMA_MODELS = '$OllamaModels'
`$env:LUMEN_LAB_ROOT = '$LabRoot'
"@ | Set-Content "$LabRoot\deploy\win-env-d.ps1" -Encoding UTF8

Write-Host ""
Write-Host "C: free after:  $([math]::Round((Get-PSDrive C).Free/1GB,1)) GB" -ForegroundColor Green
Write-Host "D: free after:  $([math]::Round((Get-PSDrive D).Free/1GB,1)) GB" -ForegroundColor Green
Write-Host ""
Write-Host "Done. New shells will use D: caches automatically." -ForegroundColor Green
Write-Host "Re-run training: cd $LabRoot && soup train --config config/soup/soup-7b-stream.yaml --yes"
