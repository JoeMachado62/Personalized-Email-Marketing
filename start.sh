#!/bin/bash

echo "========================================"
echo "Starting Production Server"
echo "========================================"
echo

# Kill any existing processes on our ports
echo "Closing existing processes on ports 8001 and 3001..."
lsof -ti:8001 | xargs kill -9 2>/dev/null
lsof -ti:3001 | xargs kill -9 2>/dev/null
sleep 2

# Activate virtual environment
echo "Activating virtual environment..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "ERROR: Virtual environment not found! Please run: python3 -m venv venv"
    exit 1
fi

# Set production environment
export DEBUG_MODE=false
export LOG_LEVEL=INFO

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found!"
    echo "Please copy .env.example to .env and configure your API keys"
    exit 1
fi

# Initialize database
echo "Initializing database..."
python -c "from app.db.connection import init_db; init_db()" 2>/dev/null

# Start backend
echo "Starting FastAPI backend on port 8001..."
nohup uvicorn app.main:app --host 0.0.0.0 --port 8001 --log-level warning > backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start frontend server
echo "Starting frontend server on port 3001..."
nohup python -m http.server 3001 --directory frontend > frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to start
sleep 2

# Save PIDs for stop script
echo $BACKEND_PID > backend.pid
echo $FRONTEND_PID > frontend.pid

echo
echo "========================================"
echo "Server Started Successfully!"
echo "========================================"
echo
echo "Access Points:"
echo "  Web Interface:  http://localhost:3001/unified.html"
echo "  API Docs:       http://localhost:8001/docs"
echo
echo "Server is running in the background."
echo "Logs: backend.log and frontend.log"
echo "To stop: Run ./stop.sh"
echo