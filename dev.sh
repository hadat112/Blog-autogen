#!/bin/bash

# Function to kill background processes on exit
cleanup() {
    echo "Stopping services..."
    kill $(jobs -p)
    exit
}

trap cleanup SIGINT SIGTERM

echo "Starting Story Autogen Services..."

# Start Backend (FastAPI)
echo "Starting Backend on http://localhost:8000..."
PYTHONPATH=. uvicorn api.main:app --host 0.0.0.0 --port 8000 &

# Wait a moment for backend to initialize
sleep 2

# Start Frontend (Vite)
echo "Starting Frontend on http://localhost:5173..."
cd frontend && npm run dev &

# Keep the script running
wait
