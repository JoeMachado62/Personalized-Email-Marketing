#!/bin/bash

# AI Sales Agent - Linux Server Startup Script
# Full enrichment with Serper API + OpenAI + MCP

echo "================================================================"
echo "     AI Sales Agent - Full Enrichment Mode (Linux)"
echo "================================================================"
echo ""

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check for required API keys
if [ -z "$SERPER_API_KEY" ]; then
    echo "ERROR: SERPER_API_KEY not set in .env file"
    exit 1
fi

if [ -z "$LLM_API_KEY" ]; then
    echo "ERROR: LLM_API_KEY not set in .env file"
    exit 1
fi

export OPENAI_API_KEY=$LLM_API_KEY

# Disable browser automation since we have APIs
export USE_PLAYWRIGHT=false
export USE_SELENIUM=false

# Enable MCP
export ENABLE_MCP_FETCH=true

# Set processing parameters
export ENRICHMENT_CONCURRENCY=5
export DEBUG_MODE=false

echo "Configuration:"
echo "  ✓ Serper API configured"
echo "  ✓ OpenAI API configured"
echo "  ✓ MCP Fetch enabled"
echo ""

# Kill any existing servers
echo "Stopping any existing servers..."
pkill -f "uvicorn app.main:app" 2>/dev/null
pkill -f "python3 -m http.server 3000" 2>/dev/null
sleep 2

# Start frontend server in background
echo "Starting frontend server on port 3000..."
cd frontend && python3 -m http.server 3000 &
FRONTEND_PID=$!
cd ..
echo "  ✓ Frontend server started (PID: $FRONTEND_PID)"

# Start backend server
echo "Starting backend server on port 8000..."
echo ""
echo "================================================================"
echo "Server URLs:"
echo "  - Frontend: http://localhost:3000/unified.html"
echo "  - API Docs: http://localhost:8000/docs"
echo ""
echo "Press CTRL+C to stop the server"
echo "================================================================"
echo ""

# Trap CTRL+C to cleanup
trap cleanup INT

cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $FRONTEND_PID 2>/dev/null
    pkill -f "uvicorn app.main:app" 2>/dev/null
    echo "Servers stopped."
    exit 0
}

# Run the backend server
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload