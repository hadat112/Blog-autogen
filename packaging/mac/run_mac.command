#!/bin/bash

# Used from packaging/mac/ in the source tree and from the root of a release.
set -u

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
  PROJECT_ROOT="$SCRIPT_DIR"
elif [ -f "$SCRIPT_DIR/../../pyproject.toml" ]; then
  PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
else
  echo "ERROR: Could not find pyproject.toml. Run this file from the extracted release folder."
  printf "\nPress Enter to close..."
  read -r
  exit 1
fi

VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
LAUNCHER="$PROJECT_ROOT/app_launcher.py"
[ -f "$LAUNCHER" ] || LAUNCHER="$PROJECT_ROOT/packaging/app_launcher.py"

pause_before_exit() {
  printf "\nPress Enter to close..."
  read -r
}

cd "$PROJECT_ROOT" || {
  echo "ERROR: Could not enter project root: $PROJECT_ROOT"
  pause_before_exit
  exit 1
}

echo "Starting Story Autogen from: $PROJECT_ROOT"
echo "URL: http://127.0.0.1:8000"
echo "Keep this Terminal window open while using the app."
echo

if [ ! -x "$VENV_PYTHON" ]; then
  echo "ERROR: The project virtual environment is missing."
  echo "Run install_mac.command first, then run this file again."
  pause_before_exit
  exit 1
fi

if ! "$VENV_PYTHON" -c 'import fastapi, uvicorn' >/dev/null 2>&1; then
  echo "ERROR: FastAPI/Uvicorn are not installed in .venv."
  echo "Run install_mac.command to repair the installation, then retry."
  pause_before_exit
  exit 1
fi

if [ ! -f "$LAUNCHER" ]; then
  echo "ERROR: app_launcher.py was not found in the release."
  pause_before_exit
  exit 1
fi

if lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "ERROR: Port 8000 is already in use."
  echo "Close the other app using port 8000, then run this file again."
  echo
  lsof -nP -iTCP:8000 -sTCP:LISTEN || true
  pause_before_exit
  exit 1
fi

"$VENV_PYTHON" "$LAUNCHER"
status=$?

echo
if [ "$status" -eq 130 ]; then
  echo "Story Autogen stopped by Ctrl+C."
else
  echo "Story Autogen stopped with exit code $status."
  [ "$status" -eq 0 ] || echo "Review the error above and run install_mac.command if dependencies are missing."
fi
pause_before_exit
exit "$status"
