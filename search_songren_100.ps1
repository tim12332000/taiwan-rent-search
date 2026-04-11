$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

& (Join-Path $repoRoot "open_search_app.ps1") -NoBrowser
python -m src.songren_100_case --open
