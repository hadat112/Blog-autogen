#!/bin/bash

# Function to kill background processes on exit
cleanup() {
    echo "Stopping services..."
    kill $(jobs -p)
    exit
}

trap cleanup SIGINT SIGTERM

echo "Starting Story Autogen Services..."

# Use the project virtual environment when available so dev runs do not pick up
# globally installed Python tools from an older interpreter.
if [ -x "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
else
    PYTHON="python3"
fi

# Start Backend (FastAPI)
echo "Starting Backend on http://localhost:8000..."
PYTHONPATH=. "$PYTHON" -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 &

# Wait a moment for backend to initialize
sleep 2

# Start Frontend (Vite)
echo "Starting Frontend on http://localhost:5173..."
cd frontend && pnpm dev &

# Keep the script running
wait
