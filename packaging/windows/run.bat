@echo off
cd /d "%~dp0"
title Story Autogen
echo Starting Story Autogen...
echo.
echo The dashboard will open at http://127.0.0.1:8000
echo Keep this window open while using the tool.
echo.
python app_launcher.py
if errorlevel 1 (
  echo.
  echo Failed to start. Please install Python 3.9+ and run install_windows.bat first.
  pause
)
