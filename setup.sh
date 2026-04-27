#!/bin/bash

echo "=== Blog-autogen Setup for Unix-like Systems ==="

# Check if python3 is installed
if ! command -v python3 &> /dev/null
then
    echo "Error: Python3 is not installed. Please install it first."
    exit 1
fi

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install
echo "Installing dependencies and tool..."
source venv/bin/activate
pip install --upgrade pip
pip install -e .

echo ""
echo "=== Setup Complete! ==="
echo "To start using the tool, run:"
echo "source venv/bin/activate"
echo "blog-autogen"
