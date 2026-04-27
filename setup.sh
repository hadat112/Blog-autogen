#!/bin/bash

echo "=== Blog-autogen Setup for Unix-like Systems ==="

# 1. Check and Install Python if missing
if ! command -v python3 &> /dev/null
then
    echo "Python3 not found. Attempting to install..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Ubuntu/Debian
        if command -v apt &> /dev/null; then
            sudo apt update && sudo apt install -y python3 python3-venv python3-pip
        else
            echo "Please install python3, python3-venv, and python3-pip manually."
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install python
        else
            echo "Homebrew not found. Please install Homebrew first or download Python from python.org"
            exit 1
        fi
    else
        echo "OS not supported for auto-install. Please install Python3 manually."
        exit 1
    fi
fi

# 2. Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment (venv)..."
    python3 -m venv venv || { echo "Error creating venv. You might need to install python3-venv"; exit 1; }
fi

# 3. Activate and Install
echo "Installing dependencies and tool..."
source venv/bin/activate
pip install --upgrade pip
pip install -e .

echo ""
echo "=== Setup Complete! ==="
echo "To start using the tool, run:"
echo "source venv/bin/activate"
echo "blog-autogen"
