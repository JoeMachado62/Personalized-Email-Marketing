#!/bin/bash

echo "========================================"
echo "Stopping All Servers"
echo "========================================"
echo

# Try to stop using saved PIDs first
if [ -f "backend.pid" ]; then
    BACKEND_PID=$(cat backend.pid)
    echo "Stopping backend (PID: $BACKEND_PID)..."
    kill $BACKEND_PID 2>/dev/null
    rm backend.pid
fi

if [ -f "frontend.pid" ]; then
    FRONTEND_PID=$(cat frontend.pid)
    echo "Stopping frontend (PID: $FRONTEND_PID)..."
    kill $FRONTEND_PID 2>/dev/null
    rm frontend.pid
fi

# Kill any remaining processes on ports
echo "Killing any remaining processes on ports..."
lsof -ti:8001 | xargs kill -9 2>/dev/null
lsof -ti:3001 | xargs kill -9 2>/dev/null

# Kill any uvicorn or http.server processes
pkill -f "uvicorn app.main:app" 2>/dev/null
pkill -f "python -m http.server 3001" 2>/dev/null

sleep 2

echo
echo "========================================"
echo "All servers stopped successfully!"
echo "========================================"
echo