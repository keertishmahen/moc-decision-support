# start.ps1 — Start both FastAPI backend and React frontend
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

Write-Host "Starting FastAPI backend on http://localhost:8000 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass; uvicorn api.main:app --reload --port 8000"

Start-Sleep -Seconds 2

Write-Host "Starting React frontend on http://localhost:5173 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass; npm run dev --prefix frontend"

Write-Host ""
Write-Host "App running at: http://localhost:5173" -ForegroundColor Green
Write-Host "API running at: http://localhost:8000" -ForegroundColor Green
Write-Host "API docs at:    http://localhost:8000/docs" -ForegroundColor Green
