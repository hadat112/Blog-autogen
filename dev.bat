@echo off
echo Starting Story Autogen Services...

:: Start Backend in a separate window
start cmd /k "set PYTHONPATH=. && uvicorn apps.api.main:app --host 0.0.0.0 --port 8000"

:: Wait 2 seconds
timeout /t 2 /nobreak > nul

:: Start Frontend in a separate window
start cmd /k "cd frontend && pnpm dev"

echo Services are starting in separate windows.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
