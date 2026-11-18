# One-time setup on Windows. Run from the project root:  .\setup.cmd
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONIOENCODING = "utf-8"

Write-Host "`n==> Checking tools" -ForegroundColor Cyan
python --version
node --version

Write-Host "`n==> Python virtual environment + dependencies" -ForegroundColor Cyan
if (-not (Test-Path .venv)) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip -q
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt -q

if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "Created .env (edit it to add an ANTHROPIC_API_KEY for AI features)" }

Write-Host "`n==> Downloading 20 years of market data (about 30-60 seconds)" -ForegroundColor Cyan
& .\.venv\Scripts\python.exe -m pipeline seed
if ($LASTEXITCODE -ne 0) {
  Write-Host "Live download failed - loading offline sample data instead" -ForegroundColor Yellow
  & .\.venv\Scripts\python.exe -m pipeline seed --offline
}

Write-Host "`n==> Frontend dependencies" -ForegroundColor Cyan
Push-Location frontend
if (-not (Test-Path .env.local)) { Copy-Item .env.example .env.local }
npm install --no-audit --no-fund
Pop-Location

Write-Host "`n==> Running tests" -ForegroundColor Cyan
& .\.venv\Scripts\python.exe -m pytest -q

Write-Host "`nSetup complete! Start the app with:  .\start.cmd" -ForegroundColor Green
