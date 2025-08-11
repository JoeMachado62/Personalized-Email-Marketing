"""
Simple MCP Fetch client for content extraction.
Converts HTML to clean Markdown for FREE (no token costs).
"""

import asyncio
import json
import logging
import subprocess
import sys
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class MCPFetchClient:
    """
    Direct MCP Fetch integration for content extraction.
    Uses the fetch MCP server to convert HTML to Markdown.
    """
    
    def __init__(self):
        """Initialize MCP Fetch client."""
        self.mcp_command = self._find_mcp_command()
        
    def _find_mcp_command(self) -> str:
        """Find the appropriate MCP fetch command."""
        # Try different possible commands
        commands = [
            "npx -y @modelcontextprotocol/server-fetch",
            "mcp-server-fetch",
            "python -m mcp_server_fetch",
            "node mcp-server-fetch"
        ]
        
        for cmd in commands:
            try:
                # Test if command exists
                test_cmd = cmd.split()[0]
                result = subprocess.run(
                    ["where" if sys.platform == "win32" else "which", test_cmd],
                    capture_output=True,
                    timeout=2
                )
                if result.returncode == 0:
                    logger.info(f"Found MCP command: {cmd}")
                    return cmd
            except:
                continue
        
        logger.warning("MCP Fetch command not found - will use fallback")
        return None
    
    async def fetch_url(self, url: str) -> Dict[str, Any]:
        """
        Fetch and convert URL content to Markdown using MCP.
        
        Args:
            url: URL to fetch
            
        Returns:
            Dictionary with content and metadata
        """
        if not self.mcp_command:
            return await self._fallback_fetch(url)
        
        try:
            # Create MCP request
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "fetch",
                    "arguments": {
                        "url": url
                    }
                },
                "id": 1
            }
            
            # Run MCP command
            process = await asyncio.create_subprocess_exec(
                *self.mcp_command.split(),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Send request and get response
            stdout, stderr = await asyncio.wait_for(
                process.communicate(json.dumps(request).encode()),
                timeout=30
            )
            
            if process.returncode == 0:
                response = json.loads(stdout.decode())
                
                if "result" in response:
                    content = response["result"].get("content", [])
                    if content and isinstance(content, list):
                        # Extract text from content array
                        text_content = ""
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                text_content += item.get("text", "")
                        
                        return {
                            "content": text_content,
                            "markdown": text_content,
                            "url": url,
                            "source": "mcp_fetch",
                            "success": True
                        }
            
            logger.warning(f"MCP Fetch failed for {url}, using fallback")
            return await self._fallback_fetch(url)
            
        except Exception as e:
            logger.error(f"MCP Fetch error: {e}")
            return await self._fallback_fetch(url)
    
    async def _fallback_fetch(self, url: str) -> Dict[str, Any]:
        """
        Fallback method using basic HTTP fetch.
        
        Args:
            url: URL to fetch
            
        Returns:
            Basic content dictionary
        """
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        html = await response.text()
                        
                        # Basic HTML to text conversion
                        import re
                        # Remove script and style elements
                        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
                        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
                        # Remove HTML tags
                        text = re.sub(r'<[^>]+>', ' ', html)
                        # Clean up whitespace
                        text = ' '.join(text.split())
                        
                        return {
                            "content": text[:5000],  # Limit content
                            "markdown": text[:5000],
                            "url": url,
                            "source": "fallback",
                            "success": True
                        }
        except Exception as e:
            logger.error(f"Fallback fetch failed: {e}")
        
        return {
            "content": "",
            "markdown": "",
            "url": url,
            "source": "error",
            "success": False
        }


class SimpleMCPExtractor:
    """
    Simple wrapper for MCP content extraction.
    Compatible with existing code.
    """
    
    def __init__(self):
        """Initialize extractor."""
        self.client = MCPFetchClient()
    
    async def extract(self, url: str) -> Dict[str, Any]:
        """
        Extract content from URL.
        
        Args:
            url: URL to extract from
            
        Returns:
            Extracted content dictionary
        """
        result = await self.client.fetch_url(url)
        
        if result.get("success"):
            content = result.get("markdown", "")
            
            # Extract useful information
            extracted = {
                "text": content,
                "title": self._extract_title(content),
                "description": content[:500] if content else "",
                "contact_info": self._extract_contacts(content),
                "source": result.get("source", "unknown")
            }
            
            return extracted
        
        return {
            "text": "",
            "title": "",
            "description": "",
            "contact_info": {},
            "error": "Failed to extract content"
        }
    
    def _extract_title(self, content: str) -> str:
        """Extract title from content."""
        lines = content.split('\n')
        for line in lines[:5]:
            if line.strip() and len(line) < 100:
                return line.strip()
        return ""
    
    def _extract_contacts(self, content: str) -> Dict[str, list]:
        """Extract contact information from content."""
        import re
        
        contacts = {
            "phones": [],
            "emails": []
        }
        
        # Phone patterns
        phone_patterns = [
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
            r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}',
            r'\b\d{10}\b'
        ]
        
        for pattern in phone_patterns:
            phones = re.findall(pattern, content)
            contacts["phones"].extend(phones[:3])
        
        # Email pattern
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content)
        contacts["emails"] = emails[:3]
        
        # Remove duplicates
        contacts["phones"] = list(set(contacts["phones"]))[:3]
        contacts["emails"] = list(set(contacts["emails"]))[:3]
        
        return contacts


# For backward compatibility
MCPContentExtractor = SimpleMCPExtractor