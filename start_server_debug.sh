#!/bin/bash

# AI Sales Agent - Debug/Testing Server Script with Real-time Monitoring
# Shows detailed output for each enrichment record

echo "================================================================"
echo "     AI Sales Agent - DEBUG MODE with Real-time Monitoring"
echo "================================================================"
echo ""

# Activate virtual environment first
echo "Activating Python virtual environment..."
source venv/bin/activate
echo "  ✓ Virtual environment activated"

# Load environment variables from .env file
if [ -f .env ]; then
    echo "Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | grep '=' | xargs)
    echo "  ✓ Environment loaded"
else
    echo "ERROR: .env file not found!"
    echo "Please copy .env.example to .env and add your API keys"
    exit 1
fi

# Check for required API keys
if [ -z "$SERPER_API_KEY" ]; then
    echo "WARNING: SERPER_API_KEY not set in .env file"
    echo "  → Will use Playwright/Selenium for searches (slower, may hit bot detection)"
else
    echo "  ✓ Serper API Key: ${SERPER_API_KEY:0:10}..."
fi

if [ -z "$LLM_API_KEY" ]; then
    echo "WARNING: LLM_API_KEY not set in .env file"
    echo "  → Content generation will be limited"
else
    echo "  ✓ OpenAI API Key: ${LLM_API_KEY:0:10}..."
    export OPENAI_API_KEY=$LLM_API_KEY
fi

# Check which LLM model is configured
if [ -n "$LLM_MODEL_NAME" ]; then
    echo "  ✓ LLM Model: $LLM_MODEL_NAME"
else
    echo "  ✓ LLM Model: gpt-3.5-turbo (default)"
fi

# Set debug parameters for testing
export ENRICHMENT_CONCURRENCY=1  # Process one at a time for testing
export DEBUG_MODE=true
export LOG_LEVEL=DEBUG

# Enable/disable features based on API availability
if [ -n "$SERPER_API_KEY" ]; then
    export USE_PLAYWRIGHT=false
    export USE_SELENIUM=false
    echo "  ✓ Using Serper API for searches (fast, reliable)"
else
    export USE_PLAYWRIGHT=true
    export USE_SELENIUM=true
    echo "  ⚠ Using browser automation for searches (slower)"
fi

# MCP configuration
export ENABLE_MCP_FETCH=true
echo "  ✓ MCP Fetch enabled for HTML→Markdown conversion"

echo ""
echo "Processing Configuration:"
echo "  - Concurrency: 1 (debug mode - one record at a time)"
echo "  - Debug Mode: ON (verbose logging)"
echo "  - Log Level: DEBUG"
echo ""

# Kill any existing servers
echo "Cleaning up existing processes..."
pkill -f "uvicorn app.main:app" 2>/dev/null
pkill -f "python3 -m http.server" 2>/dev/null
sleep 2

# Start frontend server in background
echo "Starting frontend server on port 3001..."
cd frontend && python3 -m http.server 3001 > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "  ✓ Frontend started (PID: $FRONTEND_PID)"

echo ""
echo "================================================================"
echo "                    SERVER READY FOR TESTING"
echo "================================================================"
echo ""
echo "Access Points:"
echo "  📊 Web Interface: http://localhost:3001/unified.html"
echo "  📚 API Docs:      http://localhost:8001/docs"
echo "  🔍 Health Check:  http://localhost:8001/api/v1/health"
echo ""
echo "Testing Tips:"
echo "  1. Upload a small CSV (1-5 records) for initial testing"
echo "  2. Watch the real-time logs below to see each enrichment"
echo "  3. Press CTRL+C to stop and save your API credits"
echo ""
echo "================================================================"
echo "           STARTING BACKEND WITH REAL-TIME LOGGING"
echo "================================================================"
echo ""

# Trap CTRL+C to cleanup
trap cleanup INT

cleanup() {
    echo ""
    echo "================================================================"
    echo "Shutting down servers..."
    kill $FRONTEND_PID 2>/dev/null
    pkill -f "uvicorn app.main:app" 2>/dev/null
    echo "Servers stopped successfully."
    echo "================================================================"
    exit 0
}

# Run the backend server with detailed logging
# Using --log-level debug and no --reload for cleaner output
python3 -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8001 \
    --log-level debug \
    --access-log \
    --use-colors