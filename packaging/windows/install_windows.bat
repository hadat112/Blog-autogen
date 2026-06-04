@echo off
cd /d "%~dp0"
title Install Story Autogen
echo Installing Story Autogen dependencies...
echo.
python --version >nul 2>&1
if errorlevel 1 (
  echo Python was not found.
  echo Please install Python 3.9+ from https://www.python.org/downloads/
  echo Make sure to tick "Add Python to PATH" during installation.
  pause
  exit /b 1
)

python -m pip install --upgrade pip
python -m pip install -e .

echo.
echo Install complete. You can now double-click run.bat.
pause
