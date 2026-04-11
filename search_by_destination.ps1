$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$destination = Read-Host "請輸入目的地地址"
if ([string]::IsNullOrWhiteSpace($destination)) {
    Write-Host "未輸入目的地，已取消。"
    exit 1
}

python -m src.smart_search --destination-address $destination --open
