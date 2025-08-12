#!/bin/bash

# Change to the script's directory
cd "$(dirname "$0")"

echo "================================================================"
echo "     AI Sales Agent - Starting Server"
echo "================================================================"
echo ""

# Activate virtual environment
echo "Activating Python environment..."
source venv/bin/activate

# Load environment variables
if [ -f .env ]; then
    set -a
    source .env
    set +a
    echo "✓ Environment variables loaded"
fi

# Check API keys
if [ -n "$SERPER_API_KEY" ]; then
    echo "✓ Serper API Key: ${SERPER_API_KEY:0:10}..."
else
    echo "⚠ No Serper API Key (will use browser automation)"
fi

if [ -n "$LLM_API_KEY" ]; then
    echo "✓ OpenAI API Key: ${LLM_API_KEY:0:10}..."
    export OPENAI_API_KEY=$LLM_API_KEY
else
    echo "⚠ No OpenAI API Key (limited functionality)"
fi

echo ""

# Kill existing servers
pkill -f "uvicorn app.main:app" 2>/dev/null
pkill -f "python3 -m http.server 3001" 2>/dev/null
sleep 1

# Start frontend
echo "Starting frontend on port 3001..."
(cd frontend && python3 -m http.server 3001 2>/dev/null) &
FRONTEND_PID=$!

echo ""
echo "================================================================"
echo "URLs:"
echo "  Web UI: http://localhost:3001/unified.html"
echo "  API: http://localhost:8001/docs"
echo ""
echo "Press CTRL+C to stop"
echo "================================================================"
echo ""

# Cleanup on exit
trap 'kill $FRONTEND_PID 2>/dev/null; pkill -f "uvicorn app.main:app"; exit' INT

# Start backend (from the correct directory)
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001