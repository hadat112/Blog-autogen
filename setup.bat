@echo off
echo === Blog-autogen Setup for Windows ===

:: 1. Check and Install Python via winget
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Attempting to install via winget...
    winget install -e --id Python.Python.3.11
    if %errorlevel% neq 0 (
        echo Could not install Python automatically. Please download from https://www.python.org/downloads/
        pause
        exit /b 1
    )
    echo Python installed. Please RESTART your terminal and run this script again.
    pause
    exit /b 0
)

:: 2. Create virtual environment
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

:: 3. Activate and Install
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
