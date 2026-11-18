# Starts the API (port 8000) and the web app (port 3000) in two windows, then opens the browser.
$root = Split-Path $PSScriptRoot -Parent
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root'; `$env:PYTHONIOENCODING='utf-8'; .\.venv\Scripts\python.exe -m uvicorn backend.main:app --port 8000 --reload --reload-dir backend --reload-dir ai --reload-dir analytics"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\frontend'; npm run dev"
Write-Host "Waiting for the servers to start..."
Start-Sleep -Seconds 12
Start-Process "http://localhost:3000"
Write-Host "WealthLens:  http://localhost:3000"
Write-Host "API docs:    http://localhost:8000/docs"
