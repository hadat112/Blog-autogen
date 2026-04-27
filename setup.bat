@echo off
echo === Blog-autogen Setup for Windows ===

:: Check if python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b 1
)

:: Create virtual environment if not exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate virtual environment and install
echo Installing dependencies and tool...
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e .

echo.
echo === Setup Complete! ===
echo To start using the tool, run:
echo venv\Scripts\activate
echo blog-autogen
pause
