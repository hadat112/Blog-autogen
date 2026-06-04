#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "Installing Story Autogen dependencies..."
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 was not found."
  echo "Please install Python 3.9+ from https://www.python.org/downloads/macos/"
  echo "Then double-click install_mac.command again."
  echo
  read -n 1 -s -r -p "Press any key to close..."
  exit 1
fi

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .

echo
echo "Install complete. You can now double-click run_mac.command."
echo
read -n 1 -s -r -p "Press any key to close..."
