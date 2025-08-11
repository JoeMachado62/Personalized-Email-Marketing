#!/bin/bash

# Setup script for Linux VPS
# Installs all dependencies and configures the environment

echo "================================================================"
echo "     AI Sales Agent - Linux Setup Script"
echo "================================================================"
echo ""

# Update system
echo "1. Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install Python and pip
echo ""
echo "2. Installing Python and dependencies..."
sudo apt install -y python3 python3-pip python3-venv python3-dev

# Install Node.js for MCP servers
echo ""
echo "3. Installing Node.js 18.x for MCP servers..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Create virtual environment
echo ""
echo "4. Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python requirements
echo ""
echo "5. Installing Python requirements..."
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright and browsers
echo ""
echo "6. Installing Playwright..."
pip install playwright
playwright install-deps
playwright install chromium

# Install MCP servers
echo ""
echo "7. Installing MCP servers..."
npm install -g @modelcontextprotocol/server-fetch

# Create necessary directories
echo ""
echo "8. Creating project directories..."
mkdir -p uploads
mkdir -p outputs
mkdir -p data
mkdir -p logs

# Set permissions
chmod +x start_server.sh
chmod +x stop_server.sh

# Create .env.example file
echo ""
echo "9. Creating environment configuration template..."
cat > .env.example << EOF
# API Keys (REQUIRED - Add your keys here)
SERPER_API_KEY=YOUR_SERPER_API_KEY_HERE
LLM_API_KEY=YOUR_OPENAI_API_KEY_HERE
LLM_MODEL_NAME=gpt-3.5-turbo

# Processing Configuration
ENRICHMENT_CONCURRENCY=5
ENABLE_MCP_FETCH=true
USE_PLAYWRIGHT=false
USE_SELENIUM=false
EOF

echo ""
echo "IMPORTANT: Copy .env.example to .env and add your API keys:"
echo "  cp .env.example .env"
echo "  nano .env  # Add your API keys"

echo ""
echo "================================================================"
echo "     Setup Complete!"
echo "================================================================"
echo ""
echo "To start the server:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run server: ./start_server.sh"
echo ""
echo "For production with PM2:"
echo "  npm install -g pm2"
echo "  pm2 start ecosystem.config.js"
echo ""