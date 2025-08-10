"""
Test MCP configuration and initialization
"""

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("\n=== MCP Configuration Check ===\n")

# Check environment variables
print("1. Environment Variables:")
print(f"   ENABLE_MCP_FETCH: {os.getenv('ENABLE_MCP_FETCH', 'NOT SET')}")
print(f"   MCP_FETCH_COMMAND: {os.getenv('MCP_FETCH_COMMAND', 'NOT SET')}")
print(f"   MCP_FETCH_TIMEOUT: {os.getenv('MCP_FETCH_TIMEOUT', 'NOT SET')}")
print(f"   MCP_FETCH_MAX_LENGTH: {os.getenv('MCP_FETCH_MAX_LENGTH', 'NOT SET')}")

# Check if MCP server is available
print("\n2. MCP Server Availability:")
import subprocess
try:
    result = subprocess.run(['python', '-m', 'mcp_server_fetch', '--help'], 
                          capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        print("   [OK] MCP Fetch server is installed and accessible")
    else:
        print(f"   [ERROR] MCP server error: {result.stderr}")
except Exception as e:
    print(f"   [ERROR] Failed to run MCP server: {e}")

# Test MCP client initialization
print("\n3. MCP Client Initialization:")
from auto_enrich.mcp_client import MCPClientManager

async def test_init():
    manager = MCPClientManager()
    
    # Show loaded config
    print(f"   Config loaded: {manager.config}")
    
    # Try to initialize
    success = await manager.initialize()
    print(f"   Initialization success: {success}")
    print(f"   Fetch client: {manager.fetch_client}")
    
    if manager.fetch_client:
        # Test a simple fetch
        print("\n4. Testing Fetch:")
        try:
            result = await manager.fetch_url("https://example.com")
            print(f"   Fetch result: {result}")
        except Exception as e:
            print(f"   Fetch error: {e}")
    
    await manager.close()

asyncio.run(test_init())

print("\n=== Rate Limiting Information ===\n")
print("MCP Fetch Server Rate Limiting:")
print("- The MCP Fetch server itself has NO rate limits")
print("- It's a local service that converts HTML to Markdown")
print("- No API keys or external services involved")
print("- Processing speed limited only by your CPU/network")
print("\nWebsite Rate Limiting Concerns:")
print("- Individual websites may rate limit or block requests")
print("- MCP Fetch uses standard HTTP requests (no special bypassing)")
print("- For aggressive scraping, consider:")
print("  * Adding delays between requests")
print("  * Rotating user agents")
print("  * Using proxy services if needed")
print("\nSelenium Fallback:")
print("- Selenium with real Chrome is more robust against blocking")
print("- Looks like a real user browsing")
print("- Slower but more reliable for difficult sites")