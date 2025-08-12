#!/bin/bash

# Stop all AI Sales Agent servers

echo "Stopping AI Sales Agent servers..."

# Kill uvicorn backend
pkill -f "uvicorn app.main:app" 2>/dev/null

# Kill frontend server
pkill -f "python3 -m http.server 3000" 2>/dev/null

# Kill any Playwright processes
pkill -f "playwright" 2>/dev/null

# Kill any Node.js MCP servers
pkill -f "mcp-server" 2>/dev/null

echo "All servers stopped."