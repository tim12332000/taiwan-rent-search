param(
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

function Get-ExpectedLocalSiteVersion {
    $version = & python -c "from src.local_site_state import get_local_site_version; print(get_local_site_version())"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to determine expected local site version."
    }
    return ($version | Select-Object -Last 1).Trim()
}

function Get-LocalSiteStatus {
    param(
        [int]$Port
    )

    try {
        $statusUrl = "http://127.0.0.1:{0}/api/status" -f $Port
        return Invoke-RestMethod -Uri $statusUrl -TimeoutSec 2
    } catch {
        return $null
    }
}

function Read-LocalSiteState {
    $statePath = Join-Path $repoRoot ".omx\state\local_site.json"
    if (-not (Test-Path $statePath)) {
        return $null
    }
    try {
        return Get-Content $statePath -Raw -Encoding utf8 | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Stop-TrackedLocalSite {
    $state = Read-LocalSiteState
    if (-not $state) {
        return
    }
    if ($state.pid) {
        Stop-Process -Id $state.pid -Force -ErrorAction SilentlyContinue
    }
}

function Test-PortAvailable {
    param(
        [int]$Port
    )

    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
        $listener.Start()
        $listener.Stop()
        return $true
    } catch {
        return $false
    }
}

function Get-AvailablePort {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    $port = $listener.LocalEndpoint.Port
    $listener.Stop()
    return $port
}

$port = 8765
$expectedVersion = Get-ExpectedLocalSiteVersion
$status = Get-LocalSiteStatus -Port $port
Stop-TrackedLocalSite
Start-Sleep -Milliseconds 300
$status = $null

if (-not (Test-PortAvailable -Port $port)) {
    $port = Get-AvailablePort
}

Start-Process pythonw -ArgumentList "-m", "src.local_site", "--host", "127.0.0.1", "--port", $port, "--no-browser"

$deadline = (Get-Date).AddSeconds(6)
do {
    Start-Sleep -Milliseconds 400
    $status = Get-LocalSiteStatus -Port $port
    if ($status -and $status.ok -eq $true -and $status.version -eq $expectedVersion) {
        break
    }
} while ((Get-Date) -lt $deadline)

if (-not $status -or $status.ok -ne $true -or $status.version -ne $expectedVersion) {
    throw "Local search site did not start in time."
}

$siteUrl = "http://127.0.0.1:{0}/" -f $port
if (-not $NoBrowser) {
    Start-Process $siteUrl
    try {
        Start-Process pythonw -ArgumentList "-m", "src.ai_cooking_review", "--latest", "--max-listings", "8", "--max-images", "3", "--refresh-search-app"
    } catch {
        Write-Warning "AI image review refresh failed to start in the background."
    }
}
