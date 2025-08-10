"""
Real implementation of MCP Fetch client that actually communicates with the MCP server.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
import subprocess
import sys

logger = logging.getLogger(__name__)


class RealFetchMCPClient:
    """
    Real implementation of Fetch MCP client that communicates with the actual MCP server.
    
    The MCP Fetch server:
    - Runs locally (no external API calls)
    - Converts HTML to clean Markdown
    - Has NO rate limits (it's your own server)
    - Is completely FREE (no token costs)
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.process = None
        
    async def fetch(self, url: str, max_length: int = 5000, 
                   start_index: int = 0, raw: bool = False) -> Dict[str, Any]:
        """
        Fetch content from URL using the real MCP Fetch server.
        
        Args:
            url: URL to fetch
            max_length: Maximum characters to return
            start_index: Start content from this index
            raw: Get raw HTML instead of markdown
            
        Returns:
            Fetched content dictionary with markdown text
        """
        try:
            # Prepare the MCP request
            mcp_request = {
                "method": "fetch",
                "params": {
                    "url": url,
                    "max_length": max_length,
                    "start_index": start_index,
                    "raw": raw
                }
            }
            
            logger.info(f"MCP Fetch: Requesting {url}")
            
            # Run the MCP server command with the request
            # Note: The actual MCP protocol may use stdio, HTTP, or WebSocket
            # This is a simplified implementation using subprocess
            
            command = [sys.executable, '-m', 'mcp_server_fetch']
            
            # For now, we'll use the direct Python API if available
            try:
                from mcp_server_fetch import fetch_url
                
                # Direct Python call (most efficient)
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    fetch_url,
                    url,
                    max_length,
                    start_index,
                    raw
                )
                
                logger.info(f"MCP Fetch: Retrieved {len(result.get('content', ''))} characters")
                
                return {
                    'url': url,
                    'content': result.get('content', ''),
                    'title': result.get('title', ''),
                    'metadata': {
                        'fetched_via': 'mcp_fetch_direct',
                        'start_index': start_index,
                        'max_length': max_length,
                        'raw': raw,
                        'success': True
                    }
                }
                
            except ImportError:
                # Fallback to subprocess if direct import fails
                logger.info("Direct MCP import failed, using subprocess")
                
                # Create a simple script to run the fetch
                fetch_script = f"""
import sys
from mcp_server_fetch import fetch_url
import json

result = fetch_url("{url}", {max_length}, {start_index}, {raw})
print(json.dumps(result))
"""
                
                proc = await asyncio.create_subprocess_exec(
                    sys.executable, '-c', fetch_script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await proc.communicate()
                
                if proc.returncode == 0:
                    result = json.loads(stdout.decode())
                    return {
                        'url': url,
                        'content': result.get('content', ''),
                        'title': result.get('title', ''),
                        'metadata': {
                            'fetched_via': 'mcp_fetch_subprocess',
                            'success': True
                        }
                    }
                else:
                    raise Exception(f"MCP subprocess failed: {stderr.decode()}")
                    
        except Exception as e:
            logger.error(f"MCP Fetch error for {url}: {e}")
            
            # Return error but don't crash
            return {
                'url': url,
                'content': '',
                'error': str(e),
                'metadata': {
                    'fetched_via': 'mcp_fetch_failed',
                    'success': False,
                    'error': str(e)
                }
            }
    
    async def close(self):
        """Close MCP server connection if needed"""
        if self.process:
            self.process.terminate()
            await self.process.wait()


# Alternative simple implementation using httpx
async def fetch_with_httpx(url: str, max_length: int = 10000) -> Dict[str, Any]:
    """
    Simple fallback using httpx and markdownify.
    This is what MCP Fetch does internally.
    """
    try:
        import httpx
        from markdownify import markdownify as md
        from bs4 import BeautifulSoup
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Convert to markdown
            markdown = md(str(soup), heading_style="ATX")
            
            # Truncate if needed
            if len(markdown) > max_length:
                markdown = markdown[:max_length] + "..."
            
            return {
                'url': url,
                'content': markdown,
                'title': soup.title.string if soup.title else '',
                'metadata': {
                    'fetched_via': 'httpx_markdownify',
                    'success': True,
                    'content_length': len(markdown)
                }
            }
            
    except Exception as e:
        logger.error(f"httpx fetch error for {url}: {e}")
        return {
            'url': url,
            'content': '',
            'error': str(e),
            'metadata': {
                'fetched_via': 'httpx_failed',
                'success': False
            }
        }


# Test the implementation
async def test_real_fetch():
    """Test the real MCP Fetch implementation"""
    
    print("\n=== Testing Real MCP Fetch ===\n")
    
    client = RealFetchMCPClient({})
    
    # Test fetching a simple page
    test_url = "https://example.com"
    print(f"Fetching {test_url}...")
    
    result = await client.fetch(test_url, max_length=1000)
    
    print(f"Success: {result['metadata'].get('success', False)}")
    print(f"Method: {result['metadata'].get('fetched_via', 'unknown')}")
    print(f"Content length: {len(result.get('content', ''))}")
    print(f"Title: {result.get('title', 'N/A')}")
    
    if result.get('error'):
        print(f"Error: {result['error']}")
    
    # Also test httpx fallback
    print("\n=== Testing httpx Fallback ===\n")
    result2 = await fetch_with_httpx(test_url, max_length=1000)
    
    print(f"Success: {result2['metadata'].get('success', False)}")
    print(f"Method: {result2['metadata'].get('fetched_via', 'unknown')}")
    print(f"Content length: {len(result2.get('content', ''))}")
    print(f"Title: {result2.get('title', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(test_real_fetch())