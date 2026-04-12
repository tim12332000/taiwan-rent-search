$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

Add-Type -AssemblyName Microsoft.VisualBasic
$destination = [Microsoft.VisualBasic.Interaction]::InputBox(
    "請輸入目的地地址",
    "租屋目的地搜尋",
    ""
)
if ([string]::IsNullOrWhiteSpace($destination)) {
    exit 1
}

& (Join-Path $repoRoot "open_search_app.ps1") -NoBrowser
python -m src.smart_search --destination-address $destination --open
