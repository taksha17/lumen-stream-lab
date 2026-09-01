# Link D:\lumen-stream-lab to GitHub (first-time setup)
# Usage: powershell -File deploy\win-git-link.ps1
param(
    [string]$LabRoot = "D:\lumen-stream-lab",
    [string]$Remote = "https://github.com/taksha17/lumen-stream-lab.git"
)

$ErrorActionPreference = "Stop"
Set-Location $LabRoot

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Install Git for Windows: https://git-scm.com/download/win" -ForegroundColor Red
    exit 1
}

$backup = Join-Path $LabRoot "backups\pre-git-link-$(Get-Date -Format yyyyMMdd-HHmmss)"
New-Item -ItemType Directory -Path $backup -Force | Out-Null
foreach ($f in @("hardware.json", "lumen.yaml")) {
    if (Test-Path $f) { Copy-Item $f $backup -Force }
}
Write-Host "Backed up local config to $backup" -ForegroundColor DarkGray

if (Test-Path ".git") {
    Write-Host "Git repo exists - pulling origin main ..." -ForegroundColor Cyan
    git pull origin main
    exit $LASTEXITCODE
}

Write-Host "Initializing git and linking to $Remote" -ForegroundColor Cyan
git init
git remote add origin $Remote
git fetch origin main
git checkout -B main
git reset --mixed origin/main
git checkout origin/main -- .
Write-Host ""
Write-Host "Linked to GitHub. Local-only paths remain (results/, exports/, cache/)." -ForegroundColor Green
Write-Host "Restore config from backup if needed: $backup"
Write-Host "Future updates: git pull origin main"
