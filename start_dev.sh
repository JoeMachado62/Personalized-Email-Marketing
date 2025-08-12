#!/bin/bash

echo "========================================"
echo "Starting Development Server with Verbose Output"
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

# Set development environment variables
echo "Setting development environment..."
export DEBUG_MODE=true
export LOG_LEVEL=DEBUG
export PYTHONUNBUFFERED=1

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found!"
    echo "Please copy .env.example to .env and configure your API keys"
    exit 1
fi

# Initialize database
echo "Initializing database..."
python -c "from app.db.connection import init_db; init_db()" 2>/dev/null

# Start backend with verbose output
echo
echo "Starting FastAPI backend on port 8001 with verbose logging..."
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload --log-level debug &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start frontend server
echo "Starting frontend server on port 3001..."
python -m http.server 3001 --directory frontend &
FRONTEND_PID=$!

# Wait for frontend to start
sleep 2

echo
echo "========================================"
echo "Development Server Started Successfully!"
echo "========================================"
echo
echo "Access Points:"
echo "  Web Interface:  http://localhost:3001/unified.html"
echo "  API Docs:       http://localhost:8001/docs"
echo "  API Base:       http://localhost:8001/api/v1"
echo
echo "Debug Features Enabled:"
echo "  - Auto-reload on code changes"
echo "  - Verbose logging (DEBUG level)"
echo "  - Detailed error messages"
echo
echo "To stop: Press Ctrl+C or run ./stop.sh"
echo
echo "Process IDs:"
echo "  Backend PID: $BACKEND_PID"
echo "  Frontend PID: $FRONTEND_PID"
echo

# Trap Ctrl+C to cleanup
trap cleanup INT

cleanup() {
    echo
    echo "Stopping servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    lsof -ti:8001 | xargs kill -9 2>/dev/null
    lsof -ti:3001 | xargs kill -9 2>/dev/null
    echo "Servers stopped."
    exit 0
}

# Keep script running
echo "Press Ctrl+C to stop all servers..."
wait