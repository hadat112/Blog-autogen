#!/bin/bash
cd "$(dirname "$0")"

echo "Starting Story Autogen..."
echo
echo "The dashboard will open at http://127.0.0.1:8000"
echo "Keep this window open while using the tool."
echo

if [ -x ".venv/bin/python" ]; then
  .venv/bin/python app_launcher.py
else
  python3 app_launcher.py
fi

echo
echo "Story Autogen stopped."
read -n 1 -s -r -p "Press any key to close..."
