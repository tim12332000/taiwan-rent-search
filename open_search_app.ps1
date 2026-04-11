$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

function Test-LocalSite {
    param(
        [int]$Port
    )

    try {
        $statusUrl = "http://127.0.0.1:{0}/api/status" -f $Port
        $response = Invoke-RestMethod -Uri $statusUrl -TimeoutSec 2
        return $response.ok -eq $true
    } catch {
        return $false
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
if (-not (Test-LocalSite -Port $port)) {
    if (-not (Test-PortAvailable -Port $port)) {
        $port = Get-AvailablePort
    }

    Start-Process pythonw -ArgumentList "-m", "src.local_site", "--host", "127.0.0.1", "--port", $port, "--no-browser"

    $deadline = (Get-Date).AddSeconds(6)
    do {
        Start-Sleep -Milliseconds 400
        if (Test-LocalSite -Port $port) {
            break
        }
    } while ((Get-Date) -lt $deadline)

    if (-not (Test-LocalSite -Port $port)) {
        throw "Local search site did not start in time."
    }
}

$siteUrl = "http://127.0.0.1:{0}/" -f $port
Start-Process $siteUrl
