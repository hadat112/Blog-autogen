@echo off
setlocal
cd /d "%~dp0"
title Install Story Autogen

echo Story Autogen Windows installer
echo.

where py >nul 2>&1
if not errorlevel 1 (
  py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
  if not errorlevel 1 set "PYTHON=py -3"
)
if not defined PYTHON (
  where python >nul 2>&1
  if not errorlevel 1 (
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
    if not errorlevel 1 set "PYTHON=python"
  )
)
if not defined PYTHON (
  echo ERROR: Python 3.9 or newer was not found.
  echo Install it from https://www.python.org/downloads/windows/
  echo Enable "Add Python to PATH" and run this installer again.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  %PYTHON% -m venv .venv
  if errorlevel 1 goto :fail
) else (
  echo Reusing existing .venv...
)

echo Upgrading pip, setuptools, and wheel...
.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :fail

echo Installing project dependencies from pyproject.toml...
.venv\Scripts\python.exe -m pip install --editable .
if errorlevel 1 goto :fail

echo Verifying required imports...
.venv\Scripts\python.exe -c "import fastapi, uvicorn, requests, yaml, tqdm, sqlalchemy, multipart"
if errorlevel 1 goto :fail

echo.
echo Install complete. You can now double-click run.bat.
echo The app will open at http://127.0.0.1:8000.
pause
exit /b 0

:fail
echo.
echo INSTALL FAILED. Check Python and your Internet/PyPI connection, then run this installer again.
echo Nothing was marked as complete.
pause
exit /b 1
