@echo off
setlocal
cd /d "%~dp0"
title Story Autogen

echo Starting Story Autogen...
echo URL: http://127.0.0.1:8000
echo Keep this window open while using the tool.
echo.

if not exist ".venv\Scripts\python.exe" (
  echo ERROR: .venv is missing. Run install_windows.bat first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -c "import fastapi, uvicorn" >nul 2>&1
if errorlevel 1 (
  echo ERROR: FastAPI/Uvicorn are not installed in .venv.
  echo Run install_windows.bat to repair the installation.
  pause
  exit /b 1
)

netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul
if not errorlevel 1 (
  echo ERROR: Port 8000 is already in use.
  echo Close the other application using it, then run this file again.
  netstat -ano | findstr /R /C:":8000 .*LISTENING"
  pause
  exit /b 1
)

.venv\Scripts\python.exe app_launcher.py
set "STATUS=%ERRORLEVEL%"
echo.
if "%STATUS%"=="0" echo Story Autogen stopped.
if not "%STATUS%"=="0" echo Story Autogen stopped with exit code %STATUS%.
pause
exit /b %STATUS%
