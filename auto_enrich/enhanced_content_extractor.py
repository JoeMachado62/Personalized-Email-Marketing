"""
Enhanced content extractor with MCP primary and Playwright fallback.
Ensures we always get content even if MCP fails.
"""

import asyncio
import json
import logging
import subprocess
import sys
import re
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class EnhancedContentExtractor:
    """
    Content extraction with multiple fallback strategies:
    1. MCP Fetch (free, fast)
    2. Playwright browser extraction (reliable)
    3. Basic HTTP fetch (last resort)
    """
    
    def __init__(self):
        """Initialize extractor with all methods."""
        self.mcp_available = self._check_mcp_availability()
        self.playwright_available = self._check_playwright_availability()
        
    def _check_mcp_availability(self) -> bool:
        """Check if MCP fetch is available."""
        try:
            # Try to run npx command
            result = subprocess.run(
                ["npx", "-y", "@modelcontextprotocol/server-fetch", "--help"],
                capture_output=True,
                timeout=5,
                shell=True
            )
            available = result.returncode == 0
            if available:
                logger.info("MCP Fetch is available")
            else:
                logger.warning("MCP Fetch not available")
            return available
        except Exception as e:
            logger.warning(f"MCP Fetch check failed: {e}")
            return False
    
    def _check_playwright_availability(self) -> bool:
        """Check if Playwright is available."""
        try:
            from playwright.async_api import async_playwright
            logger.info("Playwright is available for fallback")
            return True
        except ImportError:
            logger.warning("Playwright not available for fallback")
            return False
    
    async def extract(self, url: str) -> Dict[str, Any]:
        """
        Extract content from URL using best available method.
        
        Args:
            url: URL to extract content from
            
        Returns:
            Extracted content dictionary
        """
        logger.info(f"Extracting content from: {url}")
        
        # Try MCP first (free and fast)
        if self.mcp_available:
            content = await self._extract_with_mcp(url)
            if content and content.get('text'):
                logger.info(f"Successfully extracted with MCP: {len(content.get('text', ''))} chars")
                return content
            else:
                logger.warning("MCP returned empty content, trying fallback")
        
        # Try Playwright fallback
        if self.playwright_available:
            content = await self._extract_with_playwright(url)
            if content and content.get('text'):
                logger.info(f"Successfully extracted with Playwright: {len(content.get('text', ''))} chars")
                return content
            else:
                logger.warning("Playwright returned empty content, trying final fallback")
        
        # Final fallback - basic HTTP
        content = await self._extract_with_http(url)
        if content and content.get('text'):
            logger.info(f"Successfully extracted with HTTP: {len(content.get('text', ''))} chars")
        else:
            logger.error(f"All extraction methods failed for {url}")
        
        return content
    
    async def _extract_with_mcp(self, url: str) -> Dict[str, Any]:
        """Extract using MCP Fetch."""
        try:
            # Create the MCP request
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
            
            # Run MCP fetch command
            process = await asyncio.create_subprocess_shell(
                f'npx -y @modelcontextprotocol/server-fetch',
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Send request
            stdout, stderr = await asyncio.wait_for(
                process.communicate(json.dumps(request).encode()),
                timeout=15
            )
            
            if stderr:
                logger.debug(f"MCP stderr: {stderr.decode()[:200]}")
            
            if stdout:
                try:
                    # Parse response
                    response = json.loads(stdout.decode())
                    
                    if "result" in response and response["result"]:
                        content = response["result"].get("content", [])
                        
                        # Extract text from content array
                        text_parts = []
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                text_parts.append(item.get("text", ""))
                            elif isinstance(item, str):
                                text_parts.append(item)
                        
                        full_text = "\n".join(text_parts)
                        
                        if full_text:
                            return self._parse_content(full_text, url, "mcp")
                    
                    # Check for error in response
                    if "error" in response:
                        logger.error(f"MCP error response: {response['error']}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"MCP JSON decode error: {e}")
                    logger.debug(f"Raw stdout: {stdout.decode()[:500]}")
            
        except asyncio.TimeoutError:
            logger.error(f"MCP timeout for {url}")
        except Exception as e:
            logger.error(f"MCP extraction error: {e}")
        
        return {}
    
    async def _extract_with_playwright(self, url: str) -> Dict[str, Any]:
        """Extract using Playwright browser."""
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                page = await context.new_page()
                
                # Navigate to page
                await page.goto(url, wait_until='domcontentloaded', timeout=15000)
                await page.wait_for_load_state('networkidle', timeout=5000)
                
                # Extract text content
                text_content = await page.evaluate("""
                    () => {
                        // Remove scripts and styles
                        const scripts = document.querySelectorAll('script, style');
                        scripts.forEach(el => el.remove());
                        
                        // Get text content
                        return document.body ? document.body.innerText : '';
                    }
                """)
                
                # Extract title
                title = await page.title()
                
                await browser.close()
                
                if text_content:
                    return self._parse_content(text_content, url, "playwright", title)
                    
        except Exception as e:
            logger.error(f"Playwright extraction error: {e}")
        
        return {}
    
    async def _extract_with_http(self, url: str) -> Dict[str, Any]:
        """Basic HTTP extraction as final fallback."""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        html = await response.text()
                        
                        # Basic HTML cleaning
                        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
                        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
                        text = re.sub(r'<[^>]+>', ' ', text)
                        text = ' '.join(text.split())
                        
                        if text:
                            return self._parse_content(text[:10000], url, "http")
                            
        except Exception as e:
            logger.error(f"HTTP extraction error: {e}")
        
        return {}
    
    def _parse_content(self, text: str, url: str, source: str, title: str = "") -> Dict[str, Any]:
        """Parse and structure extracted content."""
        # Extract contact information
        contacts = self._extract_contacts(text)
        
        # Get title if not provided
        if not title:
            lines = text.split('\n')
            for line in lines[:10]:
                if line.strip() and len(line) < 100:
                    title = line.strip()
                    break
        
        # Extract business-specific information
        business_info = self._extract_business_info(text)
        
        return {
            "text": text[:5000],  # Limit for processing
            "full_text": text,
            "title": title,
            "description": text[:500],
            "contact_info": contacts,
            "business_info": business_info,
            "url": url,
            "source": source,
            "success": True
        }
    
    def _extract_contacts(self, text: str) -> Dict[str, list]:
        """Extract contact information from text."""
        contacts = {
            "phones": [],
            "emails": [],
            "addresses": []
        }
        
        # Phone patterns
        phone_patterns = [
            r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
            r'\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b'
        ]
        
        for pattern in phone_patterns:
            phones = re.findall(pattern, text)
            contacts["phones"].extend(phones[:5])
        
        # Email pattern
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        contacts["emails"] = list(set(emails))[:5]
        
        # Clean up
        contacts["phones"] = list(set(contacts["phones"]))[:5]
        
        return contacts
    
    def _extract_business_info(self, text: str) -> Dict[str, Any]:
        """Extract business-specific information."""
        info = {
            "has_pricing": "price" in text.lower() or "$" in text,
            "has_inventory": "inventory" in text.lower() or "stock" in text.lower(),
            "has_hours": "hours" in text.lower() or "monday" in text.lower(),
            "has_about": "about" in text.lower() or "founded" in text.lower(),
            "word_count": len(text.split())
        }
        
        # Look for business hours
        hours_pattern = r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[\s\S]{0,50}(?:am|pm|AM|PM)'
        if re.search(hours_pattern, text):
            info["has_hours"] = True
        
        return info


# For compatibility
SimpleMCPExtractor = EnhancedContentExtractor
MCPContentExtractor = EnhancedContentExtractor