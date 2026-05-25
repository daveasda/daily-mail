# Run the app using only the project venv.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Host "No .venv found. Run: .\scripts\setup.ps1"
    exit 1
}

function Get-PortOwner([int]$Port) {
    $line = netstat -ano | Select-String ":$Port\s" | Select-String "LISTENING" | Select-Object -First 1
    if (-not $line) { return $null }
    $parts = ($line -replace '\s+', ' ').ToString().Trim().Split(' ')
    return [int]$parts[-1]
}

& .\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = $Root

$port = 8000
if ($env:PORT) { $port = [int]$env:PORT }

$owner = Get-PortOwner $port
if ($owner) {
    $alt = $port + 1
    Write-Host "Port $port is in use (PID $owner)."
    if (-not $env:PORT -and -not (Get-PortOwner $alt)) {
        $port = $alt
        Write-Host "Using port $port instead. Set `$env:PORT to override."
    } else {
        Write-Host "Stop the other process or run: `$env:PORT=$alt; .\scripts\run.ps1"
        Write-Host "If Daily Mail is already running, open http://127.0.0.1:$($port - 1)"
        exit 1
    }
}

Write-Host "Daily Mail at http://127.0.0.1:$port (Ctrl+C to stop)"
uvicorn app.main:app --reload --host 127.0.0.1 --port $port
