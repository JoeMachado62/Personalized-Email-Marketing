"""
Enhanced content extractor with Playwright primary and HTTP fallback.
Uses markdownify for HTML to Markdown conversion for better AI processing.
"""

import asyncio
import json
import logging
import subprocess
import sys
import re
from typing import Dict, Any, Optional
from pathlib import Path
from markdownify import markdownify as md

logger = logging.getLogger(__name__)


class EnhancedContentExtractor:
    """
    Content extraction with multiple fallback strategies:
    1. Playwright browser extraction (most reliable)
    2. Basic HTTP fetch (last resort)
    """
    
    def __init__(self):
        """Initialize extractor with available methods."""
        self.playwright_available = self._check_playwright_availability()
        
    def _check_playwright_availability(self) -> bool:
        """Check if Playwright is available."""
        try:
            import playwright
            logger.info("Playwright is available for fallback")
            return True
        except ImportError:
            logger.warning("Playwright not available")
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
        
        # Try Playwright first (most reliable)
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
                
                # Get full HTML content for registry parser
                html_content = await page.content()
                
                # Clean HTML before conversion - remove script and style tags completely
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style", "meta", "link", "noscript"]):
                    script.decompose()
                
                # Get cleaned HTML
                cleaned_html = str(soup)
                
                # Convert HTML to Markdown for better AI processing
                markdown_content = md(cleaned_html, 
                                    heading_style="ATX",
                                    bullets='-',
                                    code_language='',
                                    escape_misc=False)
                
                # Extract text content as fallback
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
                
                if markdown_content or text_content:
                    return self._parse_content(
                        markdown_content if markdown_content else text_content,
                        url, 
                        "playwright", 
                        title,
                        raw_html=html_content
                    )
                    
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
                        
                        # Clean HTML before conversion
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Remove script and style elements
                        for script in soup(["script", "style", "meta", "link", "noscript"]):
                            script.decompose()
                        
                        # Get cleaned HTML
                        cleaned_html = str(soup)
                        
                        # Convert HTML to Markdown for better structure preservation
                        markdown_content = md(cleaned_html, 
                                            heading_style="ATX",
                                            bullets='-',
                                            code_language='',
                                            escape_misc=False)
                        
                        if markdown_content:
                            return self._parse_content(
                                markdown_content[:10000], 
                                url, 
                                "http",
                                raw_html=html
                            )
                            
        except Exception as e:
            logger.error(f"HTTP extraction error: {e}")
        
        return {}
    
    def _parse_content(self, text: str, url: str, source: str, title: str = "", raw_html: str = "") -> Dict[str, Any]:
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
            "raw_html": raw_html,  # Preserve raw HTML for registry parser
            "title": title,
            "description": text[:500],
            "contact_info": contacts,
            "business_info": business_info,
            "url": url,
            "source": source,
            "method": source,
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
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        contacts["emails"].extend(emails[:5])
        
        # Address pattern (simplified)
        address_pattern = r'\d+\s+[\w\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct)\b'
        addresses = re.findall(address_pattern, text, re.IGNORECASE)
        contacts["addresses"].extend(addresses[:3])
        
        return contacts
    
    def _extract_business_info(self, text: str) -> Dict[str, Any]:
        """Extract business-specific information."""
        info = {}
        
        # Look for hours of operation
        hours_pattern = r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday).*?(?:am|pm|AM|PM)'
        hours = re.findall(hours_pattern, text)
        if hours:
            info["hours"] = hours[:7]
        
        # Look for prices
        price_pattern = r'\$[\d,]+(?:\.\d{2})?'
        prices = re.findall(price_pattern, text)
        if prices:
            info["prices"] = prices[:10]
        
        # Look for ratings
        rating_pattern = r'(\d+(?:\.\d+)?)\s*(?:stars?|rating|★|☆)'
        ratings = re.findall(rating_pattern, text, re.IGNORECASE)
        if ratings:
            info["ratings"] = ratings[:5]
        
        # Look for review counts
        review_pattern = r'(\d+)\s*(?:reviews?|ratings?)'
        reviews = re.findall(review_pattern, text, re.IGNORECASE)
        if reviews:
            info["review_count"] = reviews[0]
        
        return info