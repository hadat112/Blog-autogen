#!/bin/bash

# Used from packaging/mac/ in the source tree and from the root of a release.
set -u

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
  PROJECT_ROOT="$SCRIPT_DIR"
elif [ -f "$SCRIPT_DIR/../../pyproject.toml" ]; then
  PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
else
  echo "ERROR: Could not find pyproject.toml. Run this installer from the extracted release folder."
  printf "\nPress Enter to close..."
  read -r
  exit 1
fi

VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

pause_before_exit() {
  printf "\nPress Enter to close..."
  read -r
}

fail() {
  echo
  echo "INSTALL FAILED: $1"
  echo "Nothing was marked as complete. Check Python and your Internet/PyPI connection."
  echo "Do not use sudo; run install_mac.command again after fixing the problem."
  pause_before_exit
  exit 1
}

cd "$PROJECT_ROOT" || fail "Could not enter the project folder."
echo "Story Autogen macOS installer"
echo "Project: $PROJECT_ROOT"
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 was not found."
  echo "Install Python 3.9 or newer from: https://www.python.org/downloads/macos/"
  echo "Then right-click this file, choose Open, and run it again."
  pause_before_exit
  exit 1
fi

if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
  echo "Python 3.9 or newer is required. Current version:"
  python3 --version 2>&1 || true
  echo "Install a current Python from: https://www.python.org/downloads/macos/"
  pause_before_exit
  exit 1
fi

echo "Using $(python3 --version 2>&1)."
if [ -x "$VENV_PYTHON" ]; then
  echo "Reusing existing virtual environment: .venv"
else
  echo "Creating virtual environment: .venv"
  python3 -m venv "$PROJECT_ROOT/.venv" || fail "Could not create .venv."
fi

echo "Upgrading pip, setuptools, and wheel..."
"$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel || fail "Could not install packaging tools. The network may not reach PyPI."

echo "Installing project dependencies from pyproject.toml..."
"$VENV_PYTHON" -m pip install --editable "$PROJECT_ROOT" || fail "Project dependencies were not installed. Check Internet access and PyPI, then retry."

echo "Verifying required imports..."
"$VENV_PYTHON" -c 'import fastapi, uvicorn, requests, yaml, tqdm, sqlalchemy, multipart' || fail "The installation finished with missing imports."

echo
echo "Install complete. You can now double-click run_mac.command."
echo "The app will open at http://127.0.0.1:8000."
pause_before_exit
exit 0
