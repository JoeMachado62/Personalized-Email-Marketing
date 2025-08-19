#!/usr/bin/env python3
"""
Unified Web Scraper - Production-ready web scraping with Playwright.

This replaces the old Selenium-based scraper and provides a unified interface
for all web scraping needs in the enrichment pipeline.

Key Features:
- Playwright-based for modern web handling
- Stealth mode with anti-detection
- Intelligent content extraction with trafilatura
- Search engine integration
- Business registry parsing
- Optimized for personalization data extraction
"""

import asyncio
import logging
import random
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from urllib.parse import urlparse, urljoin, quote_plus
import trafilatura
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import json

from .intelligent_extractor_v2 import (
    PersonalizationIntelligence,
    PlaywrightStealthBrowser,
    IntelligentExtractorV2
)

logger = logging.getLogger(__name__)


class UnifiedWebScraper:
    """
    Unified web scraper that handles all scraping needs for the enrichment pipeline.
    Replaces web_scraper_selenium.py with Playwright-based implementation.
    """
    
    def __init__(self, use_stealth: bool = True, headless: bool = True):
        """
        Initialize the unified scraper.
        
        Args:
            use_stealth: Enable stealth mode for anti-detection
            headless: Run browser in headless mode
        """
        self.use_stealth = use_stealth
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.playwright = None
        
        # Initialize the intelligent extractor
        self.intelligent_extractor = IntelligentExtractorV2()
        
        # Search engines configuration
        self.search_engines = {
            'google': {
                'url': 'https://www.google.com/search?q={query}',
                'parser': self._parse_google_results
            },
            'bing': {
                'url': 'https://www.bing.com/search?q={query}',
                'parser': self._parse_bing_results
            },
            'duckduckgo': {
                'url': 'https://duckduckgo.com/?q={query}',
                'parser': self._parse_duckduckgo_results
            }
        }
    
    async def initialize(self):
        """Initialize Playwright browser with optimal settings."""
        if self.browser:
            return
        
        self.playwright = await async_playwright().start()
        
        # Browser launch arguments for stealth
        launch_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--window-size=1920,1080',
            '--start-maximized',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding'
        ]
        
        if self.use_stealth:
            launch_args.extend([
                '--disable-infobars',
                '--disable-dev-tools',
            ])
        
        # Launch browser
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=launch_args
        )
        
        # Create context with stealth settings
        await self._create_stealth_context()
    
    async def _create_stealth_context(self):
        """Create a browser context with stealth settings."""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=random.choice(user_agents),
            locale='en-US',
            timezone_id='America/New_York',
            geolocation={'latitude': 40.7128, 'longitude': -74.0060},
            permissions=['geolocation'],
            accept_downloads=False,
            ignore_https_errors=True,
            color_scheme='light',
            reduced_motion='no-preference',
            forced_colors='none'
        )
        
        # Add stealth scripts
        if self.use_stealth:
            await self.context.add_init_script("""
                // Override navigator properties
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                
                Object.defineProperty(navigator, 'platform', {
                    get: () => 'Win32'
                });
                
                // Add chrome object
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {}
                };
                
                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Hide automation
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false
                });
                
                // Override console.debug
                console.debug = () => {};
            """)
    
    async def search_web(
        self, 
        query: str, 
        num_results: int = 10,
        search_engine: str = 'google'
    ) -> Dict[str, Any]:
        """
        Search the web and return structured results.
        
        Args:
            query: Search query
            num_results: Number of results to return
            search_engine: Which search engine to use
            
        Returns:
            Dictionary with search results and metadata
        """
        await self.initialize()
        
        results = {
            'query': query,
            'search_engine': search_engine,
            'results': [],
            'success': False,
            'error': None,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Create new page
            page = await self.context.new_page()
            
            # Build search URL
            engine_config = self.search_engines.get(search_engine, self.search_engines['google'])
            search_url = engine_config['url'].format(query=quote_plus(query))
            
            # Navigate with human-like behavior
            await self._navigate_with_behavior(page, search_url)
            
            # Wait for results to load
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            # Parse results
            html_content = await page.content()
            parsed_results = engine_config['parser'](html_content)
            
            results['results'] = parsed_results[:num_results]
            results['success'] = True
            
            await page.close()
            
        except Exception as e:
            logger.error(f"Search failed for '{query}': {e}")
            results['error'] = str(e)
        
        return results
    
    async def gather_web_data(
        self,
        company_name: str,
        location: Optional[str] = None,
        campaign_context: Optional[Dict] = None,
        max_pages: int = 5
    ) -> PersonalizationIntelligence:
        """
        Main method to gather comprehensive web data for a company.
        
        Args:
            company_name: Name of the company
            location: Optional location for better search
            campaign_context: Campaign context for targeted extraction
            max_pages: Maximum pages to analyze
            
        Returns:
            PersonalizationIntelligence with all gathered data
        """
        await self.initialize()
        
        # Step 1: Search for the company
        search_query = f"{company_name}"
        if location:
            search_query += f" {location}"
        
        search_results = await self.search_web(search_query)
        
        # Step 2: Find the company website
        website_url = self._extract_official_website(search_results['results'], company_name)
        
        # Step 3: Use intelligent extractor for comprehensive analysis
        intelligence = await self.intelligent_extractor.extract_personalization_intelligence(
            company_name=company_name,
            website_url=website_url,
            search_results=search_results['results'],
            max_pages=max_pages
        )
        
        # Step 4: Enhance with additional sources if needed
        if campaign_context and campaign_context.get('include_social_media'):
            social_data = await self._gather_social_media_data(company_name, search_results['results'])
            intelligence.social_media_profiles.update(social_data)
        
        # Step 5: Check for business registries (Sunbiz, etc.)
        if location and 'florida' in location.lower():
            registry_data = await self._check_business_registry(company_name, 'sunbiz')
            if registry_data:
                intelligence.owner_name = registry_data.get('owner_name', intelligence.owner_name)
                intelligence.certifications.extend(registry_data.get('licenses', []))
        
        return intelligence
    
    async def scrape_url(
        self,
        url: str,
        extract_type: str = 'full'
    ) -> Dict[str, Any]:
        """
        Scrape a specific URL and extract content.
        
        Args:
            url: URL to scrape
            extract_type: Type of extraction ('full', 'contact', 'about', 'news')
            
        Returns:
            Dictionary with extracted content
        """
        await self.initialize()
        
        result = {
            'url': url,
            'success': False,
            'content': {},
            'error': None
        }
        
        try:
            page = await self.context.new_page()
            
            # Navigate to URL
            await self._navigate_with_behavior(page, url)
            
            # Get page content
            html_content = await page.content()
            page_title = await page.title()
            
            # Extract based on type
            if extract_type == 'full':
                # Use trafilatura for full extraction
                extracted = trafilatura.extract(
                    html_content,
                    output_format='json',
                    include_tables=True,
                    include_comments=False,
                    favor_precision=True
                )
                
                if extracted:
                    result['content'] = json.loads(extracted)
                    result['content']['page_title'] = page_title
            
            elif extract_type == 'contact':
                result['content'] = await self._extract_contact_info(page, html_content)
            
            elif extract_type == 'about':
                result['content'] = await self._extract_about_info(page, html_content)
            
            elif extract_type == 'news':
                result['content'] = await self._extract_news_updates(page, html_content)
            
            result['success'] = True
            await page.close()
            
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            result['error'] = str(e)
        
        return result
    
    async def _navigate_with_behavior(self, page: Page, url: str):
        """Navigate to URL with human-like behavior."""
        # Random delay before navigation
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        # Navigate
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        
        # Random delay after load
        await asyncio.sleep(random.uniform(1.0, 3.0))
        
        # Simulate human scrolling
        await self._human_scroll(page)
        
        # Random mouse movement
        await self._random_mouse_movement(page)
    
    async def _human_scroll(self, page: Page):
        """Simulate human-like scrolling behavior."""
        total_height = await page.evaluate('document.body.scrollHeight')
        viewport_height = 1080
        
        current_position = 0
        while current_position < min(total_height, 3000):  # Limit scrolling
            scroll_distance = random.randint(200, 400)
            await page.evaluate(f'window.scrollBy(0, {scroll_distance})')
            await asyncio.sleep(random.uniform(0.3, 0.8))
            current_position += scroll_distance
            
            # Sometimes scroll back up
            if random.random() < 0.1:
                await page.evaluate(f'window.scrollBy(0, -{random.randint(50, 150)})')
                await asyncio.sleep(random.uniform(0.2, 0.5))
    
    async def _random_mouse_movement(self, page: Page):
        """Simulate random mouse movements."""
        for _ in range(random.randint(2, 4)):
            x = random.randint(100, 1820)
            y = random.randint(100, 980)
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.3))
    
    def _parse_google_results(self, html_content: str) -> List[Dict[str, str]]:
        """Parse Google search results."""
        soup = BeautifulSoup(html_content, 'lxml')
        results = []
        
        # Find result divs
        for result_div in soup.select('div.g'):
            try:
                # Extract title
                title_elem = result_div.select_one('h3')
                title = title_elem.text if title_elem else ''
                
                # Extract link
                link_elem = result_div.select_one('a')
                link = link_elem['href'] if link_elem and 'href' in link_elem.attrs else ''
                
                # Extract snippet
                snippet_elem = result_div.select_one('div.VwiC3b')
                snippet = snippet_elem.text if snippet_elem else ''
                
                if title and link:
                    results.append({
                        'title': title,
                        'link': link,
                        'snippet': snippet,
                        'source': 'google'
                    })
            except Exception as e:
                logger.debug(f"Failed to parse result: {e}")
        
        return results
    
    def _parse_bing_results(self, html_content: str) -> List[Dict[str, str]]:
        """Parse Bing search results."""
        soup = BeautifulSoup(html_content, 'lxml')
        results = []
        
        for result in soup.select('li.b_algo'):
            try:
                title_elem = result.select_one('h2 a')
                title = title_elem.text if title_elem else ''
                link = title_elem['href'] if title_elem and 'href' in title_elem.attrs else ''
                
                snippet_elem = result.select_one('div.b_caption p')
                snippet = snippet_elem.text if snippet_elem else ''
                
                if title and link:
                    results.append({
                        'title': title,
                        'link': link,
                        'snippet': snippet,
                        'source': 'bing'
                    })
            except Exception as e:
                logger.debug(f"Failed to parse Bing result: {e}")
        
        return results
    
    def _parse_duckduckgo_results(self, html_content: str) -> List[Dict[str, str]]:
        """Parse DuckDuckGo search results."""
        soup = BeautifulSoup(html_content, 'lxml')
        results = []
        
        for result in soup.select('div.result'):
            try:
                title_elem = result.select_one('h2.result__title a')
                title = title_elem.text if title_elem else ''
                link = title_elem['href'] if title_elem and 'href' in title_elem.attrs else ''
                
                # DuckDuckGo uses a redirect, extract actual URL
                if link and '?uddg=' in link:
                    import urllib.parse
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
                    if 'uddg' in parsed:
                        link = urllib.parse.unquote(parsed['uddg'][0])
                
                snippet_elem = result.select_one('a.result__snippet')
                snippet = snippet_elem.text if snippet_elem else ''
                
                if title and link:
                    results.append({
                        'title': title,
                        'link': link,
                        'snippet': snippet,
                        'source': 'duckduckgo'
                    })
            except Exception as e:
                logger.debug(f"Failed to parse DuckDuckGo result: {e}")
        
        return results
    
    def _extract_official_website(
        self, 
        search_results: List[Dict], 
        company_name: str
    ) -> Optional[str]:
        """Extract the most likely official website from search results."""
        if not search_results:
            return None
        
        # Priority: official website over directories
        excluded_domains = [
            'facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com',
            'yelp.com', 'yellowpages.com', 'bbb.org', 'manta.com',
            'bizapedia.com', 'wikipedia.org', 'youtube.com'
        ]
        
        for result in search_results:
            url = result.get('link', '')
            if url:
                domain = urlparse(url).netloc.lower()
                
                # Skip social media and directories
                if not any(excluded in domain for excluded in excluded_domains):
                    # Check if company name is in domain
                    company_words = company_name.lower().split()
                    if any(word in domain for word in company_words if len(word) > 3):
                        return url
        
        # Fallback to first non-excluded result
        for result in search_results:
            url = result.get('link', '')
            if url:
                domain = urlparse(url).netloc.lower()
                if not any(excluded in domain for excluded in excluded_domains):
                    return url
        
        return None
    
    async def _gather_social_media_data(
        self,
        company_name: str,
        search_results: List[Dict]
    ) -> Dict[str, str]:
        """Extract social media profiles from search results."""
        social_profiles = {}
        
        social_platforms = {
            'facebook.com': 'facebook',
            'twitter.com': 'twitter',
            'x.com': 'twitter',
            'linkedin.com': 'linkedin',
            'instagram.com': 'instagram',
            'youtube.com': 'youtube'
        }
        
        for result in search_results:
            url = result.get('link', '')
            for platform_domain, platform_name in social_platforms.items():
                if platform_domain in url and platform_name not in social_profiles:
                    social_profiles[platform_name] = url
        
        return social_profiles
    
    async def _check_business_registry(
        self,
        company_name: str,
        registry_type: str
    ) -> Optional[Dict[str, Any]]:
        """Check business registries for additional information."""
        if registry_type == 'sunbiz':
            # This would integrate with your enhanced Sunbiz scraper
            # For now, return placeholder
            return {
                'registry': 'sunbiz',
                'found': False,
                'owner_name': None,
                'licenses': []
            }
        
        return None
    
    async def _extract_contact_info(self, page: Page, html_content: str) -> Dict[str, Any]:
        """Extract contact information from a page."""
        contact = {
            'phones': [],
            'emails': [],
            'addresses': [],
            'social_links': {}
        }
        
        # Phone numbers
        phone_pattern = r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        phones = re.findall(phone_pattern, html_content)
        contact['phones'] = list(set(phones))[:3]
        
        # Email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, html_content)
        contact['emails'] = list(set(emails))[:3]
        
        # Addresses (simplified pattern)
        address_pattern = r'\d+\s+[\w\s]+(?:street|st|avenue|ave|road|rd|boulevard|blvd|drive|dr|lane|ln|way|court|ct),?\s+[\w\s]+,?\s+[A-Z]{2}\s+\d{5}'
        addresses = re.findall(address_pattern, html_content, re.IGNORECASE)
        contact['addresses'] = list(set(addresses))[:2]
        
        return contact
    
    async def _extract_about_info(self, page: Page, html_content: str) -> Dict[str, Any]:
        """Extract about/company information."""
        soup = BeautifulSoup(html_content, 'lxml')
        
        about = {
            'description': '',
            'founded': None,
            'team_size': None,
            'mission': '',
            'values': []
        }
        
        # Look for about section
        about_section = soup.find(['section', 'div'], class_=re.compile('about', re.I))
        if about_section:
            about['description'] = about_section.get_text()[:500]
        
        # Look for founding year
        year_pattern = r'(?:founded|established|since|opened)\s+(?:in\s+)?(\d{4})'
        year_match = re.search(year_pattern, html_content, re.IGNORECASE)
        if year_match:
            about['founded'] = year_match.group(1)
        
        return about
    
    async def _extract_news_updates(self, page: Page, html_content: str) -> Dict[str, Any]:
        """Extract recent news and updates."""
        soup = BeautifulSoup(html_content, 'lxml')
        
        news = {
            'recent_posts': [],
            'announcements': [],
            'events': []
        }
        
        # Look for news/blog posts
        for article in soup.find_all(['article', 'div'], class_=re.compile('post|news|blog', re.I))[:5]:
            title = article.find(['h1', 'h2', 'h3', 'h4'])
            date = article.find(['time', 'span'], class_=re.compile('date', re.I))
            
            if title:
                post = {
                    'title': title.get_text().strip(),
                    'date': date.get_text().strip() if date else None
                }
                news['recent_posts'].append(post)
        
        return news
    
    async def close(self):
        """Close browser and cleanup resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


# Test function
async def test_unified_scraper():
    """Test the unified web scraper."""
    
    scraper = UnifiedWebScraper(use_stealth=True, headless=True)
    
    try:
        # Test search
        search_results = await scraper.search_web("auto dealership Florida", num_results=5)
        print(f"Found {len(search_results['results'])} search results")
        
        # Test comprehensive data gathering
        intelligence = await scraper.gather_web_data(
            company_name="Smith Auto Group",
            location="Florida",
            max_pages=3
        )
        
        print(f"\nExtracted Intelligence:")
        print(f"  Business: {intelligence.business_name}")
        print(f"  Owner: {intelligence.owner_name}")
        print(f"  Recent News: {len(intelligence.recent_announcements)} items")
        print(f"  Services: {len(intelligence.primary_services)} identified")
        print(f"  Confidence: {intelligence.extraction_confidence:.1%}")
        
    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(test_unified_scraper())