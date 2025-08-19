#!/usr/bin/env python3
"""
Free search implementation using Playwright to scrape Google search results.
This reduces reliance on paid Serper API.
"""

import asyncio
import logging
from typing import List, Dict, Optional
from urllib.parse import quote_plus
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


class FreeGoogleSearch:
    """
    Free Google search using Playwright browser automation.
    No API costs - uses actual Google search through browser.
    """
    
    def __init__(self, use_stealth: bool = True):
        """
        Initialize free Google search.
        
        Args:
            use_stealth: Use stealth browsing techniques
        """
        self.use_stealth = use_stealth
        self.browser = None
        self.context = None
    
    async def initialize(self):
        """Initialize Playwright browser."""
        if self.browser:
            return
        
        playwright = await async_playwright().start()
        
        # Launch browser with stealth settings
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            ]
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            ignore_https_errors=True
        )
    
    async def search(
        self,
        query: str,
        num_results: int = 10
    ) -> List[Dict[str, str]]:
        """
        Search Google and extract results.
        
        Args:
            query: Search query
            num_results: Number of results to return
            
        Returns:
            List of search results with title, link, snippet
        """
        try:
            await self.initialize()
            
            # Create search URL
            search_url = f"https://www.google.com/search?q={quote_plus(query)}&num={num_results}"
            logger.info(f"Free Google search for: {query}")
            
            # Create new page
            page = await self.context.new_page()
            
            # Navigate to Google
            await page.goto(search_url, wait_until='domcontentloaded', timeout=15000)
            
            # Wait for results
            await page.wait_for_selector('div#search', timeout=5000)
            
            # Extract search results
            results = []
            
            # Get all search result divs
            result_elements = await page.query_selector_all('div.g')
            
            for element in result_elements[:num_results]:
                try:
                    # Extract title
                    title_elem = await element.query_selector('h3')
                    title = await title_elem.inner_text() if title_elem else ''
                    
                    # Extract link
                    link_elem = await element.query_selector('a')
                    link = await link_elem.get_attribute('href') if link_elem else ''
                    
                    # Extract snippet
                    snippet_elem = await element.query_selector('div.VwiC3b, span.st')
                    snippet = await snippet_elem.inner_text() if snippet_elem else ''
                    
                    if title and link:
                        results.append({
                            'title': title,
                            'link': link,
                            'snippet': snippet,
                            'source': 'google_free'
                        })
                
                except Exception as e:
                    logger.debug(f"Error extracting result: {e}")
                    continue
            
            # Also check for Google My Business panel
            gmb_panel = await page.query_selector('div.kp-wholepage')
            if gmb_panel:
                # Extract business info from knowledge panel
                business_info = {}
                
                # Business name
                name_elem = await gmb_panel.query_selector('h2[data-attrid="title"]')
                if name_elem:
                    business_info['name'] = await name_elem.inner_text()
                
                # Website
                website_elem = await gmb_panel.query_selector('a[data-attrid="visit_official_site"]')
                if website_elem:
                    business_info['website'] = await website_elem.get_attribute('href')
                
                # Phone
                phone_elem = await gmb_panel.query_selector('span[data-attrid="kc:/local:phonenumber"]')
                if phone_elem:
                    business_info['phone'] = await phone_elem.inner_text()
                
                # Address
                address_elem = await gmb_panel.query_selector('span[data-attrid="kc:/location/location:address"]')
                if address_elem:
                    business_info['address'] = await address_elem.inner_text()
                
                # Add as first result if we got business info
                if business_info.get('name'):
                    results.insert(0, {
                        'title': business_info.get('name', ''),
                        'link': business_info.get('website', ''),
                        'snippet': f"Phone: {business_info.get('phone', 'N/A')} | Address: {business_info.get('address', 'N/A')}",
                        'source': 'google_knowledge_panel',
                        'business_info': business_info
                    })
            
            await page.close()
            
            logger.info(f"Found {len(results)} free search results")
            return results
            
        except Exception as e:
            logger.error(f"Free Google search failed: {e}")
            return []
    
    async def search_business(
        self,
        business_name: str,
        location: str = ""
    ) -> List[Dict[str, str]]:
        """
        Search for a specific business.
        
        Args:
            business_name: Name of the business
            location: Location (city, state)
            
        Returns:
            Search results
        """
        query = f"{business_name}"
        if location:
            query += f" {location}"
        
        return await self.search(query)
    
    async def close(self):
        """Close the browser."""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.context = None


async def test_free_search():
    """Test the free Google search."""
    
    searcher = FreeGoogleSearch()
    
    try:
        # Test business search
        results = await searcher.search_business(
            "BROADWAY AUTO BROKERS INC",
            "Fort Lauderdale FL"
        )
        
        print("\n" + "="*60)
        print("FREE GOOGLE SEARCH RESULTS")
        print("="*60)
        
        for i, result in enumerate(results[:5], 1):
            print(f"\n{i}. {result['title']}")
            print(f"   Link: {result['link']}")
            print(f"   Snippet: {result['snippet'][:100]}...")
            if 'business_info' in result:
                print(f"   Business Info: {result['business_info']}")
        
        return results
        
    finally:
        await searcher.close()


if __name__ == "__main__":
    results = asyncio.run(test_free_search())
    print(f"\n✅ Found {len(results)} results using FREE Google search!")