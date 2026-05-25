# Creates and uses a project-local Python venv (no global pip/npm mixing).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python not found. Install Python 3.11+ and try again."
}

if (-not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Host "Created .venv"
}

& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Copied .env.example -> .env (add your GEMINI_API_KEY)"
}

Write-Host ""
Write-Host "Setup complete. Run: .\scripts\run.ps1"
